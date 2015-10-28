from RssFeedItem import *

class RssMovieItem(RssFeedItem):
    imdb_id = IntCol(default=None)
    imdb_url = UnicodeCol(length=512)
