# soundsieve-backend
SoundSieve backend for the iOS application
Version 1, 2/8/2015:
  - retrieves track and comment metadata from Soundcloud
  - returns json for genre search queries
  - implementation of comment density algorithm
  - efficient data manage through memcache and datastore
  - sorts returned list of tracks randomly (shuffle)
  - to do:
    - implement hotness algorithm to sort comments (give user choice of random or hot)
    - allows for multiple genres
    - bigger queries? (soundcloud might not allow...)
