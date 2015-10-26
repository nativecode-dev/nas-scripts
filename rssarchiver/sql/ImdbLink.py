from sqlobject import *
from Link import *

class ImdbLink(Link):
    imdb_id = IntCol(unique=True)
