import guessit
import feedparser

from utils import *

class FeedImporter(object):
    """Determines how many iterations will incur a cooldown period."""
    _cooldown_max_count = 20

    """Duration of the cooldown period expressed in seconds"""
    _cooldown_period = 2.0

    def __init__(self):
        return

    def import_feed(self, url):
        try:
            feed = Retry(lambda: feedparser.parse(url))
            return self._parse_feed(feed)
        except Exception as e:
            print('Failed to read or parse %s due to %s.' % (url, e))
            raise

    def _guess(self, title):
        guess = guessit.guess_movie_info(title)
        return {
            'title' : title if 'title' not in guess else guess['title'],
            'year' : None if 'year' not in guess else int(guess['year'])
        }

    def _parse_feed(self):
        return
