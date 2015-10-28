import argparse
import json
import logging
import logging.handlers
import os
import sys
import traceback

from feeds import *
from sql import *

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def run_script():
    parser = argparse.ArgumentParser()
    parser.add_argument('--command')
    parser.add_argument('--cooldown-retries', dest='cooldown_retries', default=5, type=int)
    parser.add_argument('--cooldown-seconds', dest='cooldown_seconds', default=0.5, type=float)
    subparsers = parser.add_subparsers()

    # Import required
    parser_import = subparsers.add_parser('import', help='import RSS feed for archiving')
    parser_import.add_argument('--type', dest='type', choices=['movies', 'series'], required=True, type=str)
    parser_import.add_argument('--url', dest='url', required=True, type=str)
    parser_import.set_defaults(func=_import)

    # Import optional
    parser_import.add_argument('--logaddress', dest='logaddress', default='/dev/log', type=str)
    parser_import.add_argument('--logfile', dest='logfile', default='/tmp/rssarchive.log', type=str)
    parser_import.add_argument('--schema', dest='schema', default='sqlite:/usr/local/share/rss.db', type=str)

    # Update required
    parser_update = subparsers.add_parser('update', help='update media information from feeds')
    parser_update.set_defaults(func=_update)

    args = parser.parse_args()
    args.func(args)


def _import(args):
    _initialize_logging(args.logfile, args.logaddress)
    import_feed(args.schema, args.type, args.url)


def _update(args):
    print('Would perform update.')
    return


def import_feed(schema, type, url):
    try:
        _initialize_database(schema)
        feed = RssFeed.select(RssFeed.q.url==url).getOne(None)

        if not feed:
            feed = RssFeed(type=type.lower(), url=url)

        if type.lower() == 'movies':
            importer = MovieFeedImporter(logger,
                lambda url: _handle_exists(RssMovieItem, url),
                lambda feed_item: _handle_movie(feed, feed_item))
        elif type.lower() == 'series':
            importer = SeriesFeedImporter(logger,
                lambda url: _handle_exists(RssSeriesItem, url),
                lambda feed_item: _handle_series(feed, feed_item))
        else:
            logger.info('Could not determine what feed importer to use for %s.' % type)
            sys.exit(1)

        logger.info('Importing %s feed items from "%s"...' % (type, url))
        importer.import_feed(url)
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
    RssFeed.createTable(ifNotExists=True)
    RssFeedItem.createTable(ifNotExists=True)
    RssMovieItem.createTable(ifNotExists=True)
    RssSeriesItem.createTable(ifNotExists=True)

def _initialize_logging(filelog, syslog):
    # Log format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler
    handler_stream = logging.StreamHandler(stream=sys.stdout)
    handler_stream.setLevel(logging.INFO)
    logger.addHandler(handler_stream)

    # SysLog handler
    handler_syslog = logging.handlers.SysLogHandler(address=syslog)
    handler_syslog.setFormatter(formatter)
    logger.addHandler(handler_syslog)

    # File handler
    rollover_size = 10240000
    handler_file = logging.handlers.RotatingFileHandler(filename=filelog, maxBytes=rollover_size)
    handler_file.setFormatter(formatter)
    handler_file.setLevel(logging.DEBUG)
    logger.addHandler(handler_file)


def _handle_exists(type, url):
    exists = type.select(type.q.url==url).getOne(None)

    if exists:
        logger.info('Feed for %s already exists.' % url)

    return exists


def _handle_movie(feed, feed_item):
    imdb_link = ImdbLink.select(ImdbLink.q.imdb_id==feed_item.imdb_id).getOne(None)
    if not imdb_link:
        imdb_link = ImdbLink(title=feed_item.title_canonical, url=feed_item.imdb_url, imdb_id=feed_item.imdb_id)

    rss_item = RssMovieItem.select(RssFeedItem.q.url==feed_item.url).getOne(None)
    if not rss_item:
        RssMovieItem(date_published=feed_item.date_published, description=feed_item.description,
                    title=feed_item.title, url=feed_item.url, imdb_id=feed_item.imdb_id, 
                    imdb_url=feed_item.imdb_url, feed=feed)
        logger.info('Cached RSS URL %s.' % feed_item.url)


def _handle_series(feed, feed_item):
    imdb_link = ImdbLink.select(ImdbLink.q.imdb_id==feed_item.imdb_id).getOne(None)
    if not imdb_link and feed_item.imdb_id:
        imdb_link = ImdbLink(title=feed_item.title_canonical, url=feed_item.imdb_url, imdb_id=feed_item.imdb_id)

    rss_item = RssSeriesItem.select(RssFeedItem.q.url==feed_item.url).getOne(None)
    if not rss_item:
        RssSeriesItem(date_published=feed_item.date_published, description=feed_item.description,
                      title=feed_item.title, url=feed_item.url, episode_number=feed_item.episode_number,
                      episode_title=feed_item.episode_title, season_number=feed_item.season_number,
                      season_title=feed_item.season_title, series_title=feed_item.title_canonical,
                      tvdb_id=feed_item.tvdb_id, feed=feed)
        logger.info('Cached RSS URL %s.' % feed_item.url)


if __name__ == '__main__':
    run_script()
