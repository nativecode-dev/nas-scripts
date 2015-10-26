import argparse
import json
import os
import traceback

from feeds import *
from sql import *


def run_script():
    parser = argparse.ArgumentParser()
    parser.add_argument('--schema', dest='schema', default='sqlite:/usr/local/share/rss.db', type=str)
    parser.add_argument('--type', dest='type', required=True, type=str)
    parser.add_argument('--url', dest='url', required=True, type=str)
    args = parser.parse_args()

    import_feed(args.schema, args.type, args.url)


def import_feed(schema, type, url):
    try:
        _initialize_database(schema)
        global rss_feed
        rss_feed = RssFeed.select(RssFeed.q.url==url).getOne(None)

        if not rss_feed:
            rss_feed = RssFeed(url=url)

        if type.lower() == 'movies':
            print('Importing movie feed items from "%s"...' % url)
            importer = MovieFeedImporter()
            importer.import_feed(url, _movie_feed_exists, _movie_feed_item_parsed)
        else:
            print('Could not determine what feed importer to use for %s.' % type)
    except Exception as e:
        traceback.print_exc()


def _initialize_database(schema, drop=False):
    # Delete existing database file.
    if drop and os.path.isfile(schema):
        os.remove(schema)

    # Connect to the database.
    connect_database(schema)

    # Create tables
    Link.createTable(ifNotExists=True)
    ImdbLink.createTable(ifNotExists=True)
    TvdbLink.createTable(ifNotExists=True)
    MediaInfo.createTable(ifNotExists=True)
    MovieInfo.createTable(ifNotExists=True)
    SeriesInfo.createTable(ifNotExists=True)
    RssFeed.createTable(ifNotExists=True)
    RssFeedItem.createTable(ifNotExists=True)


def _movie_feed_exists(url):
    exists = RssFeedItem.select(RssFeedItem.q.url==url).getOne(None)

    if exists:
        print('Feed for %s already exists.' % url)

    return exists


def _movie_feed_item_parsed(feed_item):
    imdb_link = ImdbLink.select(ImdbLink.q.imdb_id==feed_item.imdb_id).getOne(None)
    if not imdb_link:
        imdb_link = ImdbLink(title=feed_item.title_canonical, url=feed_item.imdb_url, imdb_id=feed_item.imdb_id)

    rss_feed_item = RssFeedItem.select(RssFeedItem.q.url==feed_item.url).getOne(None)
    if not rss_feed_item:
        RssFeedItem(description=feed_item.description, title=feed_item.title, url=feed_item.url, rss_feed=rss_feed)
        print('Cached RSS URL %s.' % feed_item.url)


if __name__ == '__main__':
    run_script()
