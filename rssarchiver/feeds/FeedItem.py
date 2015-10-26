class FeedItem(object):
    def get_title_canonical(self):
        return '%s (%s)' % (self.title_parsed, self.year) if self.year else self.title_parsed

    description = str()
    url = str()
    title = str()
    title_canonical = property(get_title_canonical)
    title_parsed = str()
    year = int()
