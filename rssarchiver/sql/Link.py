from sqlobject import *
from sqlobject.inheritance import InheritableSQLObject

class Link(InheritableSQLObject):
    title = StringCol(length=256)
    url = StringCol(length=512)
