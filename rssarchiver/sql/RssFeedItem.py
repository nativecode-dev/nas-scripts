from sqlobject import *

class RssFeedItem(SQLObject):
    description = StringCol(default=None)
    title = StringCol(length=256)
    url = StringCol(length=512)

    rss_feed = ForeignKey('RssFeed')
