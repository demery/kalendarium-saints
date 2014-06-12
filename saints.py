#!usr/bin/env python
# -*- coding: utf-8 -*-

import os, re, json

from flask import Flask
from flask import jsonify, request

app = Flask(__name__)

class Saint(object):
	def __init__(self, name, id, primary_date, secondary_dates, death, info_pieces, spelling_variants, attributes):
		self.name = name
		self.id = id
		day, month = primary_date.split("/")
		self.primary_date = Date(day, month)
		self.secondary_dates = set()
		if secondary_dates:
			for d in secondary_dates:
				day, month = d.split("/")
				date = Date(day, month)
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
		if attributes:
			self.attributes = set(attributes)
		else:
			self.attributes = set()
		return

	def to_dict(self):
		D = {}
		D["name"] = self.name
		D["id"] = self.id
		D["primary_date"] = self.primary_date.to_string()
		D["secondary_dates"] = [d.to_string() for d in self.secondary_dates]
		D["death"] = self.death
		D["info_pieces"] = [str(d) for d in self.info_pieces]
		D["spelling_variants"] = [str(d) for d in self.spelling_variants]
		D["attributes"] = [str(d) for d in self.attributes]
		return D

class Date(object):
	def __init__(self, day, month):
		self.day = day
		self.month = month
		return

	def to_string(self):
		return self.day+"/"+self.month

def load(path):
	# parse the grotefend data-file:
	saints = {}
	with open(path,'r') as inF:
		lines = [line.strip() for line in inF.readlines()][1:]
		for line in lines:
			print len(line.split('\t'))
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
			saints[name] = Saint(name, id, primary_date, secondary_dates, death, info_pieces, spelling_variants, attributes)
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

# load the date
saints, primary_lookup, secondary_lookup = load(path=os.path.join(os.path.dirname(__file__),"saints.tsv"))

@app.route("/api")
def index():
	q = request.args.get('q','')
	q = json.loads(q)
	date = q.get("date")
	saint_dict = {}
	saint_dict["primary_saints"] = []
	saint_dict["secondary_saints"] = []
	if date in primary_lookup:
		for saint_name in primary_lookup[date]:
			saint = saints[saint_name]
			saint_dict["primary_saints"].append(saint.to_dict())
	if date in secondary_lookup:
		for saint in secondary_lookup[date]:
			saint = saints[saint_name]
			saint_dict["secondary_saints"].append(saint.to_dict())
	return json.dumps(saint_dict, indent=4)

#query = '{"date":"2/Januar"}'
#print index(query)

if __name__ == "__main__":
    app.run("127.0.0.1", port=8080, debug=True)
# http://127.0.0.1:8080/api?q={"date":"2/Januar"}
