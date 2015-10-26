from sqlobject import *
from Link import *
from ImdbLink import *
from TvdbLink import *
from MediaInfo import *
from MovieInfo import *
from SeriesInfo import *
from RssFeed import *
from RssFeedItem import *

def connect_database(uri):
    sqlhub.processConnection = connectionForURI(uri)
