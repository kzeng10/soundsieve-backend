# soundsieve-backend
SoundSieve backend for the iOS application

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
  - allows for multiple genres
  - update the database every x hours so users get new content...
  - bigger queries? (soundcloud might not allow...)
  - weighted comments (e.g. if comment contains "boring" weight is -1, comment contains "awesome" weight is +2, else comment is worth 1)
  - store upvotes/downvotes of song (swipe right or left)
  - put passkeys and client ids on a local, uncommited file (oops)
