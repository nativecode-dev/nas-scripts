import os

class MediaFile(object):
    def __init__(self, fullpath):
        path, filename = os.path.split(fullpath)
        name, extension = os.path.splitext(filename)

        self.extension = extension
        self.fullpath = fullpath
        self.filename = filename
        self.name = name
        self.path = path
