import guessit
import feedparser
import imdb
import re
import sys

from dateutil import parser

try:
    from rssarchiver.utils import *
except Exception:
    from utils import *

class FeedImporter(object):
    """Determines how many iterations will incur a cooldown period."""
    _cooldown_max_count = 20

    """Duration of the cooldown period expressed in seconds"""
    _cooldown_period = 2.0

    """IMDB client used to access searches."""
    _imdb_client = imdb.IMDb()

    REGEX_IMDB_TITLE=re.compile('.*\s\((\d{4})\)', re.IGNORECASE)
    REGEX_IMDB_URL=re.compile('http://www.imdb.com/title/tt(\d+)', re.IGNORECASE)

    def __init__(self, logger, callback_exists=None, callback_parsed=None):
        self.callback_exists = callback_exists
        self.callback_parsed = callback_parsed
        self.logger = logger


    def import_feed(self, url):
        try:
            feed = Retry(lambda: feedparser.parse(url))
            return self._parse_feed(feed)
        except Exception as e:
            self.logger.error('Failed to read or parse %s due to %s.' % (url, e))
            self.logger.exception(e)
            raise


    def _create_feed_item(self, item):
        return


    def _guess(self, feed_item):
        guess = guessit.guess_file_info(feed_item.title)
        feed_item.title_parsed = title if not 'title' in guess else guess['title']
        feed_item.year = None if not 'year' in guess else int(guess['year'])


    def _parse_datetime(self, datetime):
        return parser.parse(datetime)


    def _parse_feed(self, feed):
        items = []
        cooldown_counter = 0

        for item in feed['items']:
            try:
                feed_item = self._parse_feed_item(item)

                if feed_item:
                    items.append(feed_item)
                    if self.callback_parsed: self.callback_parsed(feed_item)
                    cooldown_counter += 1
            except Exception as e:
                self.logger.error('Failed to parse feed item due to %s.' % e)
                self.logger.exception(e)
                pass

            if cooldown_counter > FeedImporter._cooldown_max_count:
                cooldown_counter = 0
                self.logger.debug('Cooldown period reached, waiting %s seconds.' % FeedImporter._cooldown_period)
                time.sleep(FeedImporter._cooldown_period)

        return items


    def _parse_feed_item(self, item):
        feed_item = self._create_feed_item(item)

        feed_item.date_published = self._parse_datetime(item['published'])
        feed_item.description = None if not 'description' in item else item['description']
        feed_item.title = item['title']
        feed_item.url = item['link']

        self.logger.debug('Parsing feed item %s.' % feed_item.title)

        if self.callback_exists and self.callback_exists(feed_item.url):
            return None

        # Try to guess as much data as we can from the filename.
        self._guess(feed_item)

        # Try to populate the IMDb ID based on our guess.
        self._set_imdb_id(feed_item)

        return feed_item


    def _set_imdb_id(self, feed_item):
        if feed_item.description:
            match = FeedImporter.REGEX_IMDB_URL.match(feed_item.description)
            feed_item.imdb_id = None if not match else int(match.group(1))
