# soundsieve-backend
SoundSieve backend for the iOS application

Version 1.03, 2/15/2015:
  - added multi-genre functionality. url format is now using parameters only, i.e. /api?sort=<sort method>&genre=<genre>&genre=<genre>...etc
  - increased http response deadline so we get deadlineExceeded errors less frequently (ideally, while it's loading the app should have a loading screen or something) (maybe we can solve this with async?)

Version 1.02, 2/14/2015:
  - now updates the database and memcache if over an hour old!
  - attempt at pagination has been uploaded, but because of some error on soundcloud's API (fairly sure it's their end since I spent ~3 hours trying to figure out why I can't load past ~100 tracks) the main segment.py file instead just gets as many tracks from soundcloud as it's willing to spit out from the API call
  
Version 1.01, 2/8/2015:
  - implemented modified version of Reddit's hotness algorithm to sort tracks based on hotness
  - default sort option is still set to random, but tracks sorted by hotness can be access by &lt;genre&gt;/hot

Version 1, 2/8/2015:
  - retrieves track and comment metadata from Soundcloud
  - returns json for genre search queries
  - implementation of comment density algorithm
  - efficient data manage through memcache and datastore
  - sorts returned list of tracks randomly (shuffle)


To do:
  - weighted comments (e.g. if comment contains "boring" weight is -1, comment contains "awesome" weight is +2, else comment is worth 1)
  - store upvotes/downvotes of song (swipe right or left)
  - async requests for concurrent requests:
    - store in memcache a boolean value for whether it's requesting or not
    - if not requesting: send soundcloud api request and set bool var to true, callback function is to update the database with new info and set bool var to false
    - then, retrieve info from memcache or db
