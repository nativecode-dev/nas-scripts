from sqlobject import *

class RssFeed(SQLObject):
    url = StringCol(length=512, unique=True)
