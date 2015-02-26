import webapp2
import os
import jinja2
import json
import datetime
import time
import urllib
import urllib2
import soundcloud
import sys
import random
import math
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api.urlfetch import fetch
from secret import client_id, client_secret

template_dir = os.path.dirname(__file__)
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), 
								autoescape = True)

#handler for the jinja2 env. allows us to use templates! c/p this code all you want for other projects
client = soundcloud.Client(client_id=client_id, client_secret=client_secret)
segmentLen = 3

class Handler(webapp2.RequestHandler):
	def write(self, *a, **kw):
		self.response.out.write(*a, **kw)

	def render_str(self, template, **params):
		t = jinja_env.get_template(template)
		return t.render(params)

	def render(self, template, **kw):
		self.write(self.render_str(template,**kw))

class SegmentHandler(Handler):
	def get(self):
		self.write('hello world')

class ReqJSON(db.Model):
	genre = db.StringProperty(required = True)
	json_str = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)

class RandomHandler(Handler):
	def get(self, genre1):
		genre = urllib.quote(genre1) 			#to make sure it's url valid
		if '/' in genre: 
			genre, sortOption = genre.split('/')
		else:
			sortOption = 'random'				#random by default
		arr = []
		comments = []
		url = 'https://api-v2.soundcloud.com/explore/' + genre + '?limit=200'

		self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
		tracks = memcache.get('tracks_' + genre)
		tracks_filtered = memcache.get('tracks_filtered_' + genre) 					#type string or None
		lastUpdated = memcache.get('lastUpdated_' + genre)							#type string or None

		if tracks:
			tracks = json.loads(tracks)

		filter_change_needed = False
		if lastUpdated is None or int(time.time()) - float(lastUpdated) > 3600*24: 	#if memcache needs to update bc too old
			req = json.loads(fetch(url, deadline=200).content)
			tracks = req.get('tracks')
			# print req.get('next_href')
			memcache.set('tracks_'+genre, json.dumps(tracks))
			memcache.set('lastUpdated_'+genre, int(time.time()))
			filter_change_needed = True

		if tracks_filtered and not filter_change_needed: 					#if the filtered tracks list exists in memcache and change isn't needed
			tracks_filtered = json.loads(tracks_filtered) 					#convert to list of track objects

		elif filter_change_needed: 											#if memcache needs to update (or not found in memcache)
			query = db.GqlQuery('SELECT * FROM ReqJSON')					#query db to check if we already did this before
			query = list(query)
			# print "DB QUERY"
			in_db = False
			tooOld = False 													#check if db needs to update as well
			for q in query:
				if q.genre == genre:										#if found in db. USE THIS TO IMPLEMENT MULTIPLE GENRE FEATURE
					in_db = True
					if time.time() - time.mktime(q.created.timetuple()) > 3600*24:	#if the db entry is more than a day old, delete and refresh. ***CHANGE THIS
						q.delete()												#delete old entry
						tooOld = True
					tracks_filtered = json.loads(q.json_str)
			if not in_db or tooOld:												#if not in db or db needs to be updated(along with memcache), we send http requests, and then store to db
				tracks_filtered = []											#going to generate list of track objects
				for a in range(len(tracks)):
					if tracks[a].get('streamable') == True and \
					tracks[a].get('duration') > 120000 and \
					tracks[a].get('duration') < 360000 and \
					tracks[a].get('commentable') == True and \
					tracks[a].get('playback_count') > 1000 and \
					tracks[a].get('comment_count') > 5 and \
					tracks[a].get('likes_count') > 50:							#if this track isn't spam and can be applicable to the app
						intrack = {}
						startTime = 0
						greatestSum = 0
						#now we find best part based on comment density
						#retrieve comments
						#instantiate array with length = length of song in seconds
						#parse through comments, increment index of list that it appears in
						#parse through array, set starting index as startTime if sum is greater than greatestSum
						link = tracks[a].get('uri') + "/comments?client_id=" + client_id
						comments = json.loads(fetch(link, deadline=200).content) #retrieve comments
						#are we retrieving comments correctly? sanity check
						# for b in range(len(comments)):
						# 	arr.append(comments[b].get('timestamp'))
						#okay this works
						#calculating startTime based on comment density now
						arr = [0] * (int(tracks[a].get('duration')/1000)+10)
						for b in range(len(comments)):
							if comments[b].get('timestamp') and comments[b].get('timestamp') < len(arr)*1000:
								arr[int(comments[b].get('timestamp'))/1000] += 1
						for index in range(1,len(arr)-segmentLen):
							tempsum = sum(arr[index:(index+segmentLen)])
							if tempsum>greatestSum:
								greatestSum = tempsum
								startTime = index

						# how about reddit's hot algorithm? include a hotness attr
						# hotness value = log(num_likes * 20*num_comments) + time_elapsed/45000
						if tracks[a].get('release_day'):
							time_track = datetime.datetime(tracks[a].get('release_year'), tracks[a].get('release_month'), tracks[a].get('release_day'))
						else:
							time_track = datetime.datetime(2011,5,1)
						time_obj = time_track - datetime.datetime(2007, 8, 1)
						time_dif = time_obj.days*3600*24 + time_obj.seconds
						hotness = math.log(20*len(comments) * tracks[a].get('likes_count'), 10) + time_dif/45000
						intrack['hotness'] = hotness
						# var title: String
						#    var id: Int
						#    var duration: Int
						#    var stream_url: String
						#    var start_time: Int
						#    var permalink_url: String   
						#    // Optional Variables (could be nil if not there)
						#    var genre: String?
						#    var subtitle: String?
						#    var artwork_url: String?

					 	#extracting only the necessary json parts 
						intrack['start_time'] = startTime*1000
						attributes = ['id', 'duration', 'stream_url', 'permalink_url', 'genre', 'description', 'artwork_url', 'title', 'comment_count']
						for attr in attributes:
							if attr == 'artwork_url': 		#exception since we want the highest quality album art
								intrack[attr] = str(tracks[a].get(attr)).replace('large', 't500x500')
							else:
								intrack[attr] = tracks[a].get(attr)
						tracks_filtered.append(intrack)
				track = ReqJSON(genre = genre, json_str=json.dumps(tracks_filtered)) 		#add to db
				track.put()
			memcache.set('tracks_filtered_'+genre, json.dumps(tracks_filtered))
		#now, to return json
		#just return tracks_filtered list of objects, each one with an additional start time for most popular segment

		#sort randomly (shuffle)
		if tracks_filtered and sortOption == 'random': 
			random.shuffle(tracks_filtered)
		#or sort based on reddit's hot algorithm?
		elif tracks_filtered:
			tracks_filtered.sort(key=lambda x: x.get('hotness'), reverse=True)
		self.write(json.dumps(tracks_filtered))

class APIHandler(Handler):
	def get(self, inp):
		self.write(inp)

class MultiGenreHandler(Handler): #new format is soundsieve-backend.appspot.com/api/<sort option>?genre=<genre>&genre=<genre>...etc
	def get(self):
		self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
		genres = self.request.get_all('genre')
		sort = self.request.get('sort')
		tracks = []
		for genre in genres:
			genre = urllib.quote(genre)
			newtracks = json.loads(fetch('https://soundsieve-backend.appspot.com/api/randomTrack/' + str(genre), deadline=1500).content)
			if newtracks:
				tracks = tracks + list(newtracks)
		if sort == 'hot':
			tracks.sort(key=lambda x: x.get('hotness'), reverse=True)
		else:		#default is random
			random.shuffle(tracks)
		self.write(json.dumps(tracks))

