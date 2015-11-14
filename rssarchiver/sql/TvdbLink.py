from sqlobject import *
from Link import *

class TvdbLink(Link):
    tvdb_id = IntCol()
