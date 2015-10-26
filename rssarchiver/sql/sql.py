# Imports
###############################################################################
import os
import sys
from datetime import date, time
from sqlobject import *
from sqlobject.inheritance import InheritableSQLObject

class Link(InheritableSQLObject):
    title = StringCol(length=256)
    url = StringCol(length=512)
    info = RelatedJoin('MediaInfo')

class ImdbLink(Link):
    imdb_id = IntCol()

class TvdbLink(Link):
    tvdb_id = IntCol()

class RssLink(Link):
    feed_date = DateTimeCol()
    feed_id = StringCol(unique=True)
    feed_url = StringCol(length=512)

class MediaInfo(InheritableSQLObject):
    def get_title_cleaned(self):
        if self.date_released:
            return '%s (%s)' % (self.title, self.date_released.year)
        return self.title

    date_released = DateCol(default=None)
    links = RelatedJoin('Link')
    title = StringCol(length=256)
    title_cleaned = property(get_title_cleaned)

class MovieInfo(MediaInfo):
    collection_name = StringCol(default=None)

class SeriesInfo(MediaInfo):
    season = IntCol()
    season_title = StringCol(length=256)
    episode = IntCol()
    episode_title = StringCol(length=256)


def main():
    connection_string = 'sqlite:/:memory:'
    connection_uri = connectionForURI(connection_string)
    sqlhub.processConnection = connection_uri

    Link.createTable()
    ImdbLink.createTable()
    TvdbLink.createTable()
    MediaInfo.createTable()
    MovieInfo.createTable()
    SeriesInfo.createTable()


main()
