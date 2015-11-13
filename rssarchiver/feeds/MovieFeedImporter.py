import feedparser
import guessit
import imdb

from FeedImporter import *
from MovieFeedItem import *

try:
    from rssarchiver.utils import *
except Exception:
    from utils import *

class MovieFeedImporter(FeedImporter):
    def _create_feed_item(self, item):
        return MovieFeedItem()


    def _guess(self, feed_item):
        guess = guessit.guess_movie_info(feed_item.title)

        try:
            feed_item.title_parsed = title if not 'title' in guess else guess['title']
            feed_item.year = None if not 'year' in guess else guess['year']
            self.logger.debug('Guessed "%s" from %s.' % (feed_item.title_canonical, feed_item.title))
        except Exception:
            self.logger.error(guess)
            raise


    def _set_imdb_id(self, feed_item):
        FeedImporter._set_imdb_id(self, feed_item)

        # Bail out if the base class found it for us.
        if feed_item.imdb_id:
            return

        title = feed_item.title_canonical
        year = feed_item.year
        self.logger.debug('[IMDB] Matching movie %s.' % title)
        movies = Retry(lambda: FeedImporter._imdb_client.search_movie(title))

        for movie in movies:
            self.logger.debug('[IMDB] Found movie %s.' % movie['title'])
            title_canonical = movie['long imdb canonical title']
            match = FeedImporter.REGEX_IMDB_TITLE.match(title_canonical)

            # If we can't regex the match, try the next one.
            if not match:
                continue

            match_year = int(match.group(1))
            # First one to match the year is likely the right one, because
            # it should be sorted by relevance.
            if match_year == year:
                feed_item.imdb_id = int(FeedImporter._imdb_client.get_imdbID(movie))
                self.logger.debug('Matched title %s with IMDB %s.' % (title_canonical, feed_item.imdb_id))
                return
            else:
                self.logger.debug('Failed to match title %s with an IMDB ID.' % title_canonical)
