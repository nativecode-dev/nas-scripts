from sqlobject import *

class RssFeed(SQLObject):
    type = EnumCol(enumValues=['movies', 'series'])
    url = StringCol(length=512, unique=True)

    items = MultipleJoin('RssFeedItem')
