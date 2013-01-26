from flask import g

class DatabaseObject(object):
	inner_self = dict()

	def __init__(self, data=None):
		if data:
			self.inner_self = data
		self.table_name = self.__class__.__name__.lower() + 's'

	def __getitem__(self, key):
		return self.inner_self[key]

	def __setitem__(self, key, value):
		self.inner_self[key] = value

	def __delitem__(self, key):
		del self.inner_self[key]

	def save(self):
		columns = []
		values = []
		for column, value in self.inner_self.items():
			columns.append(column)
			values.append(value)

		if 'id' not in self.inner_self:
			g.db.execute(u"insert into {table_name} ({columns_list}) values ({placeholders_list})".format(
				placeholders_list = ','.join( ['?' for place in range(len(values))] ),
				table_name = self.table_name,
				columns_list = ','.join(columns)
			), values)
		else:
			g.db.execute(u"update {table_name} set {columns_and_placeholders}".format(
				columns_and_placeholders = ','.join( ['%s=?' % column for column in columns] ),
				table_name = self.table_name
			), values)
		g.db.commit()

	def url(self):
		return '/{table_name}/{id}/'.format(table_name=self.table_name, id=self['id'])

class Picture(DatabaseObject):
	def cover_image_url(self):
		return self['image_url']

class Thing(DatabaseObject):
	pass

class Comment(DatabaseObject):
	pass

class Visitor(DatabaseObject):
	pass

class Poster(DatabaseObject):
	pass

class Thumbnail(DatabaseObject):
	pass