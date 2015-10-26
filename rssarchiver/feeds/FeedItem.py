class FeedItem(object):
    def get_title_canonical(self):
        return '%s (%s)' % (self.title, self.year) if self.year else self.title

    description = str()
    link = str()
    title = str()
    title_canonical = property(get_title_canonical)
    year = int()
