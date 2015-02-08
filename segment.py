import webapp2
import os
import jinja2
import json
import time
import urllib
import urllib2
import soundcloud
import sys
import soundcloud
import random
from google.appengine.ext import db
from google.appengine.api import memcache

template_dir = os.path.dirname(__file__)
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), 
								autoescape = True)

#handler for the jinja2 env. allows us to use templates! c/p this code all you want for other projects
#https://api-v2.soundcloud.com/explore/techno?limit=100&linked_partitioning=1
# stream url: https://api.soundcloud.com/tracks/189594894/stream?client_id=6ec16ffb5ed930fce00949be480f746b&allows_redirect=false#t=50
# comment url: https://api.soundcloud.com/tracks/189594894/comments?client_id=6ec16ffb5ed930fce00949be480f746b
url = 'https://api-v2.soundcloud.com/explore/'
url2 = 'https://api.soundcloud.com/tracks/resolve.json?url=6ec16ffb5ed930fce00949be480f746b&client_id=6ec16ffb5ed930fce00949be480f746b' #just for now
client_id = '6ec16ffb5ed930fce00949be480f746b'
client = soundcloud.Client(client_id=client_id, client_secret='1fb20f87e139fcb82f6d856ab6cac086')
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
		genre = urllib.quote(genre1) 		#to make sure it's url valid
		arr = []
		comments = []
		####
		#requirements for a song to be considered
		#downloadable, minimum duration (2 min), minimum playbacks (1000), minimum likes (5), minimum comments (5)
		#hotness = plays / (time elapsed)^1.2
		#store song snippets on box
		url = 'https://api-v2.soundcloud.com/explore/' + genre + '?limit=50'
		self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
		mc_genre = memcache.get('genre')
		tracks = memcache.get('tracks_' + genre)
		tracks_filtered = memcache.get('tracks_filtered_' + genre) 			#type string or None
		if tracks:
			tracks = json.loads(tracks)

		filter_change_needed = False
		if str(mc_genre) != str(genre): 		#if memcache needs to update
			#url = url + genre + "?limit=50"
			tracks = json.load(urllib2.urlopen(url)).get('tracks')
			memcache.set('tracks_'+genre, json.dumps(tracks))
			memcache.set('genre', genre)
			filter_change_needed = True

		if tracks_filtered and not filter_change_needed: 					#if the filtered tracks list exists in memcache and change isn't needed
			tracks_filtered = json.loads(tracks_filtered) 					#convert to list of track objects

		elif filter_change_needed: 											#if memcache needs to update
			query = db.GqlQuery('SELECT * FROM ReqJSON')					#query db to check if we already did this before
			query = list(query)
			in_db = False
			#maybe check created property and update if too old?
			for q in query:
				if q.genre == genre:										#if found in db
					in_db = True
					tracks_filtered = json.loads(q.json_str)
			if not in_db:													#if not in db (and memcache needs to be updated), we send http requests, and then store to db
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
						comments = json.load(urllib2.urlopen(link)) #retrieve comments
						#are we retrieving comments correctly? sanity check
						# for b in range(len(comments)):
						# 	arr.append(comments[b].get('timestamp'))
						#okay this works

						arr = [0] * (int(tracks[a].get('duration')/1000)+10)
						for b in range(len(comments)):
							if comments[b].get('timestamp') and comments[b].get('timestamp') < len(arr)*1000:
								arr[int(comments[b].get('timestamp'))/1000] += 1
						for index in range(1,len(arr)-segmentLen):
							tempsum = sum(arr[index:(index+segmentLen)])
							if tempsum>greatestSum:
								greatestSum = tempsum
								startTime = index

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

		#write random function
		#tracks = json.load(urllib2.urlopen(url)).get('tracks') #url is hardcoded for now...
		# self.write(tracks[random.randint(0,99)].get('id'))
		if tracks_filtered: random.shuffle(tracks_filtered)
		self.write(json.dumps(tracks_filtered))
		#self.write("This should spit out a random song")

class APIHandler(Handler):
	def get(self, inp):
		self.write(inp)