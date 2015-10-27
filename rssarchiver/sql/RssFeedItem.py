from sqlobject import *

class RssFeedItem(SQLObject):
    date_published = DateTimeCol(default=None)
    description = StringCol(default=None)
    title = StringCol(length=256)
    url = StringCol(length=512, unique=True)

    feed = ForeignKey('RssFeed')
