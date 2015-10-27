from sqlobject import *
from Link import *
from ImdbLink import *
from TvdbLink import *
from RssFeed import *
from RssFeedItem import *
from RssMovieItem import *
from RssSeriesItem import *

def connect_database(uri):
    sqlhub.processConnection = connectionForURI(uri)
