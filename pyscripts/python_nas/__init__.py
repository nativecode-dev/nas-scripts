import core
import networking
import notifications

class Enum(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


    def __init__(self, kvp):
        for key in kvp.keys():
            self[key] = kvp[key]


    def get_names(self):
        return self.keys()


    def get_value(self, key):
        return self[key]
