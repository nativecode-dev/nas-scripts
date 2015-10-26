from sqlobject import *
from MediaInfo import *

class MovieInfo(MediaInfo):
    collection_name = StringCol(default=None)
