from FeedItem import *

class SeriesFeedItem(FeedItem):
    def get_episode_string(self):
        if self.season_number and self.episode_number:
            return 'S%02dE%02d' % (self.season_number, self.episode_number)

        return None

    def get_season_string(self):
        if self.season_title:
            return season_title

        if self.season_number:
            return 'Season %s' % self.season_number

        return None

    episode_number = int()
    episode_title = str()
    season_number = int()
    season_title = str()
    tvdb_id = int()

    episode_string = property(get_episode_string)
    season_string = property(get_season_string)
