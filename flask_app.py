#coding=utf-8

import sqlite3
from flask import Flask, render_template, g, request, url_for, Markup, session, redirect, abort
from werkzeug import secure_filename
from datetime import datetime
from hashlib import sha256, md5
from pymorphy import get_morph
import Image
import os

from objects import *

from pdb import set_trace

app = Flask(__name__)
app.config.from_object('settings')

@app.before_request
def before_request():
    g.db = sqlite3.connect(app.config['DATABASE'])

@app.teardown_request
def teardown_request(exception):
    g.db.close()

def query(query, args=(), entity=DatabaseObject, return_list=False):
	cur = g.db.execute(query, args)
	rv = [entity(dict((cur.description[idx][0], value) for idx, value in enumerate(row))) for row in cur.fetchall()]

	if not return_list:
		return rv[0] if len(rv) == 1 else (None if len(rv) == 0 else rv)
	else:
		return rv

def execute(query, args=()):
	g.db.execute(query, args)
	g.db.commit()

def perform_visitor_tagging():
	now_is = datetime.now()

	if session.get('tagged'):
		try:
			poster_id, poster_hash = session['tagged'].split('_')
			g.db.execute('update posters set visits = visits+1, last_visit = ? where id = ?', (now_is, poster_id))
		except ValueError:
			g.db.execute('update visitors set visits = visits+1, last_visit = ? where id = ?', (now_is, session['tagged']))
		g.db.commit()
	else:
		visitor_object = Visitor( {'last_visit': now_is} )
		visitor_object.save()
		visitor_object = query('select id from visitors where last_visit = ?', [now_is])

		session['tagged'] = '{0}'.format(visitor_object['id'])

def level_required(view_function, level):
	def decorated(*args, **kwargs):
		try:
			this_user = query('select level from users where id = ?', [session['logged']])

			if this_user['level'] <= level:
				return view_function(*args, **kwargs)
			else:
				abort(401)
		except KeyError:
			abort(401)

	return decorated

@app.context_processor
def misc_utilites():
	morpher = get_morph('static/res/pymorphy/')

	def pluralize(number, word):
		return morpher.pluralize_inflected_ru(word.upper(), number).lower()

	return {'pluralize': pluralize}

@app.context_processor
def thumbnail_maker():
	def thumbnail_for(image_url, width=None, height=None, full_object=False):
		width_heigth = '{0}_{1}'.format(width, height)
		thumbnail_object = query('select thumbnail, thumbnail_width from thumbnails where image = ? and args = ?', [image_url, width_heigth])

		if not thumbnail_object:
			image_path = u'static/' + image_url.replace(u'/static/', u'')
			image = Image.open(image_path)

			resulting_size = list(image.size)
			if width: resulting_size[0] = width
			if height: resulting_size[1] = height

			image.thumbnail(resulting_size, Image.ANTIALIAS)

			name, extension = os.path.splitext(image_path)
			thumbnail_name = '{name}{ext}'.format(name=md5(name + width_heigth).hexdigest(), ext=extension)
			image.save('static/' + thumbnail_name)

			thumbnail_object = Thumbnail( {
				'image': image_url,
				'thumbnail': '/static/' + thumbnail_name,
				'args': width_heigth,
				'thumbnail_width': image.size[0]
			} )
			thumbnail_object.save()

		if not full_object:
			return thumbnail_object['thumbnail']
		else:
			return thumbnail_object

	return {'thumbnail_for': thumbnail_for}

@app.route('/')
def recent_stuff():
	perform_visitor_tagging()

	objects_on_page = 10
	objects = sorted(
		query('select * from pictures order by sent limit ?', [objects_on_page], entity=Picture, return_list=True) +
		query('select * from things order by sent limit ?', [objects_on_page], entity=Thing, return_list=True),
		key = lambda obj: obj['sent'], reverse=True
	)[:objects_on_page]

	return render_template('main.html', objects = objects, todays_message=u'Андер констракшн')

@app.route('/youve-got-mail-which-means-i-sent-something/', methods=['POST'])
def post_from_mail():
	import json
	from base64 import b64decode
	from email.utils import mktime_tz, parsedate_tz

	email = json.loads(request.data)
	picture_object = Picture()

	picture_object["title"] = email["Subject"].replace('Fwd: ', '')
	# picture_object["description"] = email["TextBody"]
	picture_object["sent"] = datetime.fromtimestamp(mktime_tz(parsedate_tz(email["Date"])))

	image_emailed = email["Attachments"][0]
	filename = secure_filename(image_emailed["Name"])
	with open('static/' + filename, 'w') as image_file:
		image_file.write(b64decode(image_emailed["Content"]))
	picture_object["image_url"] = url_for('static', filename=filename)

	picture_object.save()

	return 'Processed successfully.'

@app.context_processor
def comments_block():
	def comments_block_for(subject):
		object_class = subject.__class__.__name__
		object_id = subject["id"]

		comments = query("select posters.name as author_name, posters.info as author_info, message, posted, in_reply_to from comments join posters on comments.poster_id = posters.id where comments.object_id = ? and comments.object_class = ?", 
			(object_id, object_class), entity=Comment, return_list=True)

		prior_poster_data = dict()
		if session.get('tagged'):
			try:
				poster_id, poster_hash = session.get('tagged').split('_')
				poster_object = query('select name, info from posters where id = ?', [poster_id])

				prior_poster_data.update({'name': poster_object["name"], 'info': poster_object["info"]})
			except ValueError:
				pass

		return Markup(render_template("comments.html", 
			comments = comments if len(comments) > 0 else [],
			form_target='/post-comment/{0}/{1}/'.format(object_class, object_id), form_default_values=prior_poster_data
		))

	def comments_count_for(subject):
		comments_count = query('select count(id) as count from comments where object_id = ? and object_class = ?',
			(subject['id'], subject.__class__.__name__))

		return comments_count['count']

	return {'comments_block_for': comments_block_for, 'comments_count_for': comments_count_for}

@app.route("/post-comment/<object_class>/<int:object_id>/", methods=['POST'])
def post_comment(object_class, object_id):
	poster_object = query(u"select id from posters where name = ? and info = ?", [request.form['name'], request.form['info']])

	if not poster_object:
		poster_object = Poster( {
			'name': request.form['name'],
			'info': request.form['info'],
			'last_visit': datetime.now()
		} )

		if session.get('tagged') and len(session.get('tagged').split('_')) == 1: #он визитер
			poster_object['visits'] = query('select visits from visitors where id = ?', [session.pop('tagged')])['visits']

		poster_object.save()

		poster_object = query(u"select id from posters where name = ? and info = ?", [request.form['name'], request.form['info']])
	else:
		g.db.execute('update posters set last_visit = ?', [datetime.now()]) #он уже есть, просто обновлю записи
		g.db.commit()

	if not session.get('tagged'):
		session['tagged'] = '{id}_poster'.format(id=poster_object['id'])

	comment_object = Comment( {
		'object_class': object_class,
		'object_id': object_id,
		'message': request.form['message'],
		'poster_id': poster_object['id'],
		'in_reply_to': request.form['in_reply_to'] if request.form.get('in_reply_to') else '',
		'posted': datetime.now()
	} )

	comment_object.save()

	return comments_block()['comments_block_for'](globals()[object_class]( {'id': object_id} ))

@app.route("/pictures/<int:object_id>/")
def picture_page(object_id):
	picture_object = query('select * from pictures where id = ?', [object_id], entity=Picture)

	g.db.execute('update pictures set views = ? where id = ?', (picture_object['views']+1, picture_object['id']))

	return render_template('picture_page.html', picture = picture_object)

@app.route("/things/<int:object_id>/")
def thing_page(object_id):
	thing_object = query('select * from things where id = ?', [object_id], entity=Thing)

	g.db.execute('update things set views = ? where id = ?', (thing_object['views']+1, thing_object['id']))

	return render_template('thing_page.html', thing = thing_object)

@app.route("/log-in/", methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		user_object = query(u"select password, id from users where username = ?", [request.form['username']])

		if sha256(sha256(request.form['password']).hexdigest() + 'sugar').hexdigest() == sha256(sha256(user_object['password_hash']).hexdigest() + 'sugar').hexdigest():
			session['logged'] = user_object['id']

		return redirect(request.referrer)

@app.route("/create-item/<object_class>/", methods=['POST', 'GET'])
def post_to_database(object_class):
	if request.method == 'POST':
		object_to_post = globals()[object_class]()

		for field, value in request.form.items():
			if field in ['submit']: continue

			object_to_post[field] = value

		for field, file_object in request.files.items():
			filename = secure_filename(file_object.filename)
			file_object.save('static/' + filename)

			object_to_post[field] = url_for('static', filename=filename)

		object_to_post.save()

		return '{object_class} saved successfully.'.format(object_class=object_class)

	if request.method == 'GET':
		return render_template('master/{object_class}_form.html'.format(object_class=object_class.lower()))

if __name__ == '__main__':
	app.run()