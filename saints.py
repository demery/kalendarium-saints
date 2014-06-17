#!usr/bin/env python
# -*- coding: utf-8 -*-

import os, re, json
from flask import Flask
from flask import jsonify, request
from flask.ext.cors import cross_origin

# NB Data is dirty, note variants below
month_names = {'Juni': 6, 'Juli':7, 'Januar':1, 'October':10, 'April':4,
			   'Februar': 2, 'December':12, 'November':11, 'Mai': 5,
			   'März':3, 'Mars':3, 'August': 8, 'September': 9, 'Oct': 10,
			   'Sept': 9, '6':6}

name_fix_re = re.compile("\s+\([0-9]+\)$")
alt_name_re = re.compile("^(.+)\s+\((.+)\)$")


BASE_URL = "http://localhost:8080"
CONTEXT = "%s/ns/context.json" % BASE_URL

app = Flask(__name__)

class Saint(object):
	def __init__(self, name, id, primary_date, secondary_dates, death, info_pieces,
		spelling_variants, attributes):

		name = name_fix_re.sub("", name)
		m = alt_name_re.match(name)
		if m:
			g = m.groups()
			name = g[0]
			if spelling_variants:
				spelling_variants.append(g[1])
			else:
				spelling_variants = [g[1]]
		self.name = name
		self.id = int(id)
		day, month = primary_date.split("/")
		self.primary_date = Date(day, month)
		self.secondary_dates = set()
		if secondary_dates:
			for d in secondary_dates:
				day, month = d.split("/")
				date = Date(day, month)
				if date.to_string() != self.primary_date.to_string():
					self.secondary_dates.add(date)
		if death != "NA":
			self.death = death
		else:
			self.death = None
		if info_pieces:
			self.info_pieces = set(info_pieces)
		else:
			self.info_pieces = set()
		if spelling_variants:
			self.spelling_variants = set(spelling_variants)
		else:
			self.spelling_variants = set()
		self.attributes = set()
		if attributes:
			for a in attributes:
				cidx = a.find(',')
				if cidx > -1:
					a = a[:cidx]
				self.attributes.add("%s/attribute/%s" % (BASE_URL, a))


	def to_dict(self):
		D = {}
		D["name"] = self.name
		D["@id"] = "%s%s%s" % (BASE_URL, "/api/saint/", self.id)
		D['@type'] = "SaintOrEvent"
		D["primary_date"] = self.primary_date.to_dict()
		if self.secondary_dates:
			D["secondary_dates"] = [d.to_dict() for d in self.secondary_dates]
		if self.death:
			D["death"] = self.death
		if self.info_pieces:
			if len(self.info_pieces) == 1:
				D['description'] = str(list(self.info_pieces)[0])
			else:
				D["description"] = [str(d) for d in self.info_pieces]
		if self.spelling_variants:
			if len(self.spelling_variants) == 1:
				D['name_variant'] = str(list(self.spelling_variants)[0])
			else:
				D["name_variant"] = [str(d) for d in self.spelling_variants]
		if self.attributes:
			if len(self.attributes) == 1:
				D['attribute'] = str(list(self.attributes)[0])
			else:
				D["attribute"] = [str(d) for d in self.attributes]
		return D

class Date(object):
	def __init__(self, day, month):
		try:
			self.day = int(day)
		except:
			print day
			self.day = 0

		if type(month) in [str, unicode]:
			if month[-1] == '.':
				month = month[:-1]
			try:
				self.month = month_names[month]
			except:
				print "BROKEN MONTH: %s" % month
				self.month = 0
		elif type(month) == int:
			self.month = month

	def to_string(self):
		return "%s/%s" % (self.day, self.month)

	def to_dict(self):
		# Date --> time:DateTimeDescription
		return {"@type":"Date", "day":self.day, "month":self.month}


def load(path):
	# parse the grotefend data-file:
	saints = {}
	with open(path,'r') as inF:
		lines = [line.strip() for line in inF.readlines()][1:]
		for line in lines:
			name, id, primary_date, secondary_dates, death, info_pieces, spelling_variants, attributes = line.split("\t")
			if secondary_dates != "NA":
				secondary_dates = secondary_dates.split("$")
			else:
				secondary_dates = None
			if info_pieces != "NA":
				info_pieces = info_pieces.split("$")
			else:
				info_pieces = None
			if spelling_variants != "NA":
				spelling_variants = spelling_variants.split("$")
			else:
				spelling_variants = None
			if attributes != "NA":
				attributes = attributes.split("$")
			else:
				attributes = None
			# Multiple saints can have the same name, surely
			s = Saint(name, id, primary_date, secondary_dates, death, info_pieces, spelling_variants, attributes)
			saints[s.id] = s

	# make the lookup index (both for primary and secondary dates)
	primary_lookup, secondary_lookup = {}, {}
	for saint_name, saint in saints.items():
		try:
			primary_lookup[saint.primary_date.to_string()].add(saint_name)
		except KeyError:
			primary_lookup[saint.primary_date.to_string()] = set()
			primary_lookup[saint.primary_date.to_string()].add(saint_name)
		for date in saint.secondary_dates:
			try:
				secondary_lookup[date.to_string()].add(saint_name)
			except KeyError:
				secondary_lookup[date.to_string()] = set()
				secondary_lookup[date.to_string()].add(saint_name)
	return (saints, primary_lookup, secondary_lookup)

# start the app
#app = App()

# load the data
saints, primary_lookup, secondary_lookup = load(path=os.path.join(os.path.dirname(__file__),"saints.tsv"))

@app.route("/api/date/<int:month>/<int:day>")
@cross_origin()
def by_date(month, day):
	#  /api/date/:MONTH/:DAY

	date_obj = Date(day, month)
	date = date_obj.to_string()
	saint_dict = {"@context" : CONTEXT}
	saint_dict["@id"] = "%s/%s/%s/%s" % (BASE_URL, "api/date", month, day)

	saint_dict["primary_saints"] = []
	saint_dict["secondary_saints"] = []
	if date in primary_lookup:
		for saint_name in primary_lookup[date]:
			saint = saints[saint_name]
			saint_dict["primary_saints"].append(saint.to_dict())
	saint_dict["primary_saints"].sort()

	if date in secondary_lookup:
		for saint in secondary_lookup[date]:
			saint = saints[saint_name]
			saint_dict["secondary_saints"].append(saint.to_dict())
	if not saint_dict["secondary_saints"]:
		del saint_dict["secondary_saints"]
	else:
		saint_dict["primary_saints"].sort()
	return json.dumps(saint_dict, indent=4, sort_keys=True)

@app.route("/api/saint/<int:idn>")
@cross_origin()
def by_id(idn):
	#  /api/saint/:ID
	if saints.has_key(idn):
		saint = saints[idn]
	else:
		# 404
		return "{}"
	saint_d = saint.to_dict()
	saint_d["@context"] = CONTEXT
	return json.dumps(saint_d, indent=4, sort_keys=True)

if __name__ == "__main__":
    app.run("127.0.0.1", port=8080, debug=True)

