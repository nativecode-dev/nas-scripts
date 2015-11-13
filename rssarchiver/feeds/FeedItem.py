class FeedItem(object):
    def get_imdb_id_string(self):
        return 'tt%s' % self.imdb_id if self.imdb_id else ''

    def get_imdb_url(self):
        return 'http://www.imdb.com/title/%s' % self.imdb_id_string

    def get_title_canonical(self):
        return '%s (%s)' % (self.title_parsed, self.year) if self.year else self.title_parsed

    date_published = None
    description = str()
    imdb_id = int()
    title = str()
    title_parsed = str()
    url = str()
    year = int()

    title_canonical = property(get_title_canonical)
    imdb_id_string = property(get_imdb_id_string)
    imdb_url = property(get_imdb_url)
