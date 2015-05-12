#!/usr/env/python

import sqlite3
import os.path
import sys
import time
import urllib2
import liblinearutil
import cPickle
import re
import dateutil.parser
from xml.etree import ElementTree
from contextlib import closing



__all__ = ["RssReaderCore"]



VERSION = "0.1"
CONFIG_DIR = "/.rssreader/"
DB_NAME = 'main.db'
TRAINING_NAME = 'training.data'
NR_FEATURES = 65536



def message(mesg, level = 'Info', die = False):
	sys.stderr.write('{0}: {1}\n'.format(level, mesg))
	if die: sys.exit(1)



class Storage:
	def create_table(self):
		with closing(self.db_conn.cursor()) as cursor:
			cursor.execute('''SELECT name FROM sqlite_master WHERE type='table'  ''')
			tables = cursor.fetchall()
			tables = [line[0] for line in tables]
			if 'rss_urls' not in tables:
				message('Create table rss_urls')
				self.db_conn.execute('''
					CREATE TABLE rss_urls (
						url TEXT UNIQUE PRIMARY KEY,
						alias TEXT,
						title TEXT,
						link TEXT,
						description TEXT,
						time REAL
					)''')

			if 'rss_items' not in tables:
				message('Create table rss_items')
				self.db_conn.execute('''
					CREATE TABLE rss_items (
						guid TEXT UNIQUE PRIMARY KEY,
						rss_url TEXT,
						title TEXT,
						link TEXT,
						description TEXT,
						date REAL,
						read_count INTEGER DEFAULT 0,
						deleted INTEGER DEFAULT 0,
						time REAL
					)''')
			
	
	def get_file(self, filename):
		from os.path import expanduser

		self.home = expanduser("~")
		if not os.path.exists(self.home + CONFIG_DIR):
			message('Create directory ' + self.home + CONFIG_DIR)
			os.mkdir(self.home + CONFIG_DIR)

		return self.home + CONFIG_DIR + filename


	def init(self):
		self.db_conn = sqlite3.connect(self.get_file(DB_NAME))

		self.rss_urls_cols = ["url", "alias", "title", "link", "description", "time"]
		self.rss_items_cols = ["guid", "rss_url", "title", "link", "date", "description", "read_count", "deleted", "time"]
		
		self.create_table()


	def __init__(self):
		self.init()

	def __del__(self):
		self.db_conn.rollback()
		self.db_conn.close()

	def set_url(self, url, alias, title, link, description, t = time.time()):
		with closing(self.db_conn.cursor()) as cursor:
			cursor.execute('''
				SELECT * from rss_urls
				WHERE url = ?
			''', (url,))
			if len(cursor.fetchall()) != 0:
				message('URL ' + url + ' already exists')
				return

			cursor.execute('''
				INSERT INTO rss_urls 
				({0})
				VALUES
				({1})
			'''.format(
				','.join(self.rss_urls_cols), 
				','.join(['?']*len(self.rss_urls_cols))
				), 
				(url, alias, title, link, description, t))
			self.db_conn.commit()

	def set_item(self, guid, rss_url, title, link, date, description, read_count = 0, deleted = 0, t = time.time()):
		with closing(self.db_conn.cursor()) as cursor:
			cursor.execute('''
				SELECT * from rss_items
				WHERE guid = ? AND deleted = 0
			''', (guid,))
			if len(cursor.fetchall()) != 0:
				message('URL ' + url + ' already exists')
				return

			cursor.execute('''
				INSERT INTO rss_items
				({0})
				VALUES
				({1})
			'''.format(
				','.join(self.rss_items_cols), 
				','.join(['?']*len(self.rss_items_cols))
				), 
				(guid, rss_url, title, link, date, description, read_count, deleted, t))
			self.db_conn.commit()


	def get_urls(self):
		with closing(self.db_conn.cursor()) as cursor:
			cursor.execute('''
				SELECT {0}
				FROM rss_urls
				ORDER BY time DESC
			'''.format(','.join(self.rss_urls_cols)))


			output = []
			
			while True:
				row = cursor.fetchone()
				if row is None: break
				output.append(dict(zip(self.rss_urls_cols, row)))	

			return output

	def get_items_by_url(self, url):
		with closing(self.db_conn.cursor()) as cursor:
			cursor.execute('''
				SELECT {0}
				FROM rss_items
				WHERE rss_url = ?
				ORDER BY time DESC
			'''.format(','.join(self.rss_items_cols)), (url, ))


			output = []
			
			while True:
				row = cursor.fetchone()
				if row is None: break
				output.append(dict(zip(self.rss_items_cols, row)))	
			return output

	def get_item(self, guid):
		with closing(self.db_conn.cursor()) as cursor:
			cursor.execute('''
				SELECT {0}
				FROM rss_items
				WHERE guid = ?
			'''.format(','.join(self.rss_items_cols), guid), (guid,))


			output = []
			
			while True:
				row = cursor.fetchone()
				if row is None: break
				output.append(dict(zip(self.rss_items_cols, row)))	
			if len(output) == 0:
				return None
			elif len(output) == 1:
				return output[0]
			else:
				message('fetal error: inconsistent status in DB: guid: ' + guid, 'Error', die = True)

	def increase_item_count(self, guid):
		with closing(self.db_conn.cursor()) as cursor:
			cursor.execute('''
				UPDATE rss_items
				SET read_count = read_count + 1
				WHERE guid = ?
			''', (guid,))

			self.db_conn.commit()

	def set_item_deleted(self, guid):
		with closing(self.db_conn.cursor()) as cursor:
			cursor.execute('''
				UPDATE rss_items
				SET deleted = 1
				WHERE guid = ?
			''', (guid,))

			self.db_conn.commit()



namespace = {'atom': 'http://www.w3.org/2005/Atom'}
class RssFetcher:

	@staticmethod
	def get_rss(url):
		url_file = urllib2.urlopen(url)
		url_data = url_file.read()
		url_file.close()
		tree = ElementTree.fromstring(url_data)
		channels = tree.find('channel')
		if channels is not None:
			return channels
		return tree

	@staticmethod
	def get_items(root):
		return root.findall('item') or root.findall('atom:entry', namespace)

	@staticmethod
	def get_guid(root):
		return root.findtext('guid') or root.find('atom:id', namespace).text
	
	@staticmethod
	def get_date(root):
		date = root.findtext('pubDate') or root.find('atom:published', namespace).text
		date = time.mktime(dateutil.parser.parse(date).timetuple())

		return date

	@staticmethod
	def get_description(root):
		description = root.findtext('description') 
		if description is not None: return description
		
		summary = root.find('atom:summary', namespace)
		if summary is not None: return summary.text

		return ''
	
	@staticmethod
	def get_title(root):
		return root.findtext('title') or root.find('atom:title', namespace).text
	
	@staticmethod
	def get_link(root):
		return root.findtext('link') or root.find('atom:link', namespace).text



class Recommender:
	def __init__(self, storage):
		self.storage = storage
		self.training_path = storage.get_file(TRAINING_NAME)

		self.training = [[], []]
		if os.path.exists(self.training_path):
			self.training = cPickle.load(open(self.training_path, 'rb'))


	def __del__(self):
		cPickle.dump(self.training, open(self.training_path, 'wb'), -1)


	def to_instance(self, title):
		title = title.lower()
		title = re.sub(u'([\u2E80-\u9FFF])', u' \\1 ', title)

		title = title.split()
		weight = 1./len(title)

		last = '[BEGIN]'
		inst = {1:1}
		for w in title:
			k = hash((last, w)) % NR_FEATURES + 1
			if k in inst:
				inst[k] += weight
			else:
				inst[k] = weight
			k = hash(w) % NR_FEATURES + 1
			if k in inst:
				inst[k] += weight
			else:
				inst[k] = weight

			last = w

		k = hash((w, '[END]')) % NR_FEATURES + 1
		if k in inst:
			inst[k] += weight
		else:
			inst[k] = weight

		return inst


	def add_title(self, title):
		inst = self.to_instance(title)
		self.training[0].append(1)
		self.training[1].append(inst)
	
	
	def add_negative_title(self, title):
		inst = self.to_instance(title)
		self.training[0].append(-1)
		self.training[1].append(inst)
		

	def train(self):
		y = list(self.training[0])
		x = list(self.training[1])
		y.append(-1)
		x.append({1:1})

		if len(x) <= 1:
			message('unable to recommend because you have not read any feed.', 'Error', die=True)

		return liblinearutil.train(y, x, '-q')


	def get_scores(self, items):
		model = self.train()
	
		insts = []
		for item in items:
			inst = self.to_instance(item['title'])
			insts.append(inst)

		## XXX dirty hack to hide messages printed by LIBLINEAR
		old_out = sys.stdout
		sys.stdout = open('/dev/null', 'wb')
		dummy, dummy, decs = liblinearutil.predict([], insts, model)
		sys.stdout = old_out

		return decs



class RssReaderCore:

	def __init__(self):
		self.rss_fetcher = RssFetcher()
		self.storage = Storage()
		self.recommender = Recommender(self.storage)
	
	def set_url(self, url, alias = None):
		rss_fetcher = self.rss_fetcher
		rss = rss_fetcher.get_rss(url)
		title = rss_fetcher.get_title(rss)
		link = rss_fetcher.get_link(rss)
		description = rss_fetcher.get_description(rss)

		if alias is None: alias = title
		self.storage.set_url(url, alias, title, link, description)

	def get_urls(self):
		return self.storage.get_urls()

	def update_items(self, rss_url):
		rss_fetcher = self.rss_fetcher
		url = rss_url['url']
		rss = rss_fetcher.get_rss(url)
		for item in rss_fetcher.get_items(rss):
			guid = rss_fetcher.get_guid(item)
			old_item = self.storage.get_item(guid)
			if old_item is not None: continue
			
			title = rss_fetcher.get_title(item)
			link = rss_fetcher.get_link(item)
			date = rss_fetcher.get_date(item)
			description = rss_fetcher.get_description(item)
			
			self.storage.set_item(guid, url, title, link, date, description)

	def get_items(self, aliases = None):
		rss_urls = self.get_urls()
		if aliases is not None:
			urls = []
			for alias in set(aliases):
				for rss_url in rss_urls:
					if rss_url['alias'] == alias:
						urls.append(rss_url)
						break
				else:
					message('alias ' + alias + ' not found', 'Error', die=True)

			rss_urls = urls

		items = []
		for rss_url in rss_urls:
			self.update_items(rss_url)
			items += self.storage.get_items_by_url(rss_url['url'])

		return items

	def get_item(self, guid):
		item = self.storage.get_item(guid)
		if item is not None:
			self.storage.increase_item_count(guid)
			self.recommender.add_title(item['title'])

		return item

	def remove_item(self, guid):
		item = self.storage.get_item(guid)
		if item is None:
			message('not found: ' + args.guid, 'Error', die=True)

		self.storage.set_item_deleted(guid)
		self.recommender.add_negative_title(item['title'])

		return item

	def get_best_n(self, items, n):
		n = min(n, len(items))
		if n < 0: n = len(items)
	
		scores = self.recommender.get_scores(items)
		
		sorted_pair = sorted(zip(scores, items), reverse=True)[:n]

		return [p[1] for p in sorted_pair]

