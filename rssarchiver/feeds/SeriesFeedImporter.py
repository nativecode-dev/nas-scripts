import feedparser
import guessit
import tvdb_api

from FeedImporter import *
from SeriesFeedItem import *

try:
    from rssarchiver.utils import *
except Exception:
    from utils import *

class SeriesFeedImporter(FeedImporter):
    def _create_feed_item(self, item):
        return SeriesFeedItem()


    def _guess(self, feed_item):
        # Try to guess the episode info from the filename.
        guess = guessit.guess_episode_info(feed_item.title)

        try:
            feed_item.episode_number = None if not 'episodeNumber' in guess else int(guess['episodeNumber'])
            feed_item.episode_title = None if not 'title' in guess else guess['title']
            feed_item.season_number = None if not 'season' in guess else int(guess['season'])
            feed_item.title_parsed = title if not 'series' in guess else guess['series']
            feed_item.year = None if not 'year' in guess else int(guess['year'])

            self.logger.info('Guessed "%s" [%s] from %s.' % (feed_item.title_canonical,
                feed_item.episode_string, feed_item.title))
        except Exception:
            self.logger.error(guess)
            raise


    def _set_imdb_id(self, feed_item):
        FeedImporter._set_imdb_id(self, feed_item)

        # Bail out if the base class found it for us.
        if feed_item.imdb_id:
            return

        # Getting the TVDB data might also net us an IMDB ID.
        self._set_tvdb_id(feed_item)


    def _set_tvdb_id(self, feed_item):
        tvdb = tvdb_api.Tvdb()
        title = feed_item.title_canonical
        season = feed_item.season_number
        episode = feed_item.episode_number

        if not (season and episode):
            self.logger.debug('No season or episode number for %s.' % title)
            return

        try:
            self.logger.debug('[TVDB] Matching show %s (%s).' % (title, feed_item.episode_string))
            # Get all the shows matching the name.
            shows = Retry(lambda: tvdb.search(title))

            for show in shows:
                seriesname = show['seriesname']
                self.logger.debug('[TVDB] Found series %s.' % seriesname)
                if seriesname.lower() == title.lower():
                    try:
                        seriesid = int(show['id'])

                        # Some shows don't have an IMDB ID.
                        imdb_id = None if not 'imdb_id' in show else int(show['imdb_id'].replace('tt', ''))

                        ep = tvdb[seriesid][season][episode]
                        episodename = ep['episodename']
                        self.logger.debug('Matched %s with TVDB %s.' % (title, episodename))

                        # Set the feed item properties.
                        feed_item.imdb_id = imdb_id
                        feed_item.tvdb_id = seriesid
                        feed_item.episode_title = episodename
                        return
                    except tvdb_api.tvdb_seasonnotfound as e:
                        # We might find the season in another listing.
                        self.logger.debug(show)
                        self.logger.exception(e)
                        pass
                    except tvdb_api.tvdb_episodenotfound as e:
                        # We might find the episode in another listing.
                        self.logger.exception(e)
                        pass
                else:
                    self.logger.debug('No match for %s and %s.' % (seriesname, title))
        except Exception as e:
            self.logger.exception(e)
            pass
