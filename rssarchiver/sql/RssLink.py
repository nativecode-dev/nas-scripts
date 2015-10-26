from sqlobject import *
from Link import *

class RssLink(Link):
    feed_date = DateTimeCol()
    feed_id = StringCol(unique=True)
    feed_url = StringCol(length=512)
