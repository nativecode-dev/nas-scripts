from RssFeedItem import *

class RssSeriesItem(RssFeedItem):
    episode_number = IntCol(default=None)
    episode_title = UnicodeCol(length=256, default=None)
    season_number = IntCol(default=None)
    season_title = UnicodeCol(length=256, default=None)
    series_title = UnicodeCol(length=256)
    tvdb_id = IntCol(default=None)
