from sqlobject import *
from sqlobject.inheritance import InhertiableSQLObject

class Link(InheritableSQLObject):
    title = StringCol(length=256)
    url = StringCol(length=512)
    info = RelatedJoin('MediaInfo')
