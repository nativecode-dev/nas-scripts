from sqlobject import *

class RssFeedItem(SQLObject):
    date_published = DateTimeCol(default=None)
    description = UnicodeCol(default=None)
    title = UnicodeCol(length=256)
    url = UnicodeCol(length=512, unique=True)

    feed = ForeignKey('RssFeed')
