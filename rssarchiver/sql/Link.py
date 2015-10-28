from sqlobject import *
from sqlobject.inheritance import InheritableSQLObject

class Link(InheritableSQLObject):
    title = UnicodeCol(length=256)
    url = UnicodeCol(length=512)
