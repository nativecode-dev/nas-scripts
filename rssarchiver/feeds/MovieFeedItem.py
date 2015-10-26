from FeedItem import *

class MovieFeedItem(FeedItem):
    def get_imdb_id_string(self):
        return 'tt%s' % self.imdb_id if self.imdb_id else ''

    imdb_id = int()
    imdb_id_string = property(get_imdb_id_string)
