from RssFeedItem import *

class RssMovieItem(RssFeedItem):
    imdb_id = IntCol(default=None)
    imdb_url = StringCol(length=512)
