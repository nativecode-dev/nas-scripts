from sqlobject import *
from sqlobject.inheritance import InheritableSQLObject

class MediaInfo(InheritableSQLObject):
    def get_title_cleaned(self):
        if self.date_released:
            return '%s (%s)' % (self.title, self.date_released.year)
        return self.title

    date_released = DateCol(default=None)
    links = RelatedJoin('Link')
    title = StringCol(length=256)
    title_cleaned = property(get_title_cleaned)
