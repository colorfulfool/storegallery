@app.before_request
def before_request():
    g.db = sqlite3.connect(app.config['DATABASE'])

@app.teardown_request
def teardown_request(exception):
    g.db.close()

def query(query, args=(), entity=DatabaseObject):
	cur = g.db.execute(query, args)
	rv = [entity(dict((cur.description[idx][0], value) for idx, value in enumerate(row))) for row in cur.fetchall()]
	return rv