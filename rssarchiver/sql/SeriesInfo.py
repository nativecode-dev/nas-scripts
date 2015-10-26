from sqlobject import *
from MediaInfo import *

class SeriesInfo(MediaInfo):
    season = IntCol()
    season_title = StringCol(length=256)
    episode = IntCol()
    episode_title = StringCol(length=256)
