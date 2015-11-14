import json
import os
import sys

def get_path(name):
    """
    Gets a configuration file path for the current user.
    """
    userpath = get_user_path()
    return os.path.join(userpath, '.config', name)


def get_user_path():
    """
    Gets the current user's home directory.
    """
    return os.path.expanduser('~')


def read(name):
    """
    Reads the configuration file contents if it exists,
    otherwise it will be created.
    """
    configpath = get_path(name)
    configdir = os.path.dirname(configpath)

    if not os.path.isdir(configdir):
        os.makedirs(configdir)

    if not os.path.isfile(configpath):
        open(configpath, 'a').close()
    else:
        with open(configpath, 'r') as file:
            return file.read()


def read_json(name):
    """
    Reads the configuration file and deserializes the JSON.
    """
    serialized = read(name)
    if serialized:
        return json.loads(serialized)
    else:
        return {}


def write(name, contents):
    """
    Writes the configuration file contents.
    """
    configpath = get_path(name)
    configdir = os.path.dirname(configpath)

    if not os.path.isdir(configdir):
        os.makedirs(configdir)

    with open(configpath, 'w') as file:
        file.write(contents)


def write_json(name, objinstance):
    """
    Writes an object as a JSON file.
    """
    contents = json.dumps(objinstance, sort_keys=True, indent=4, separators=(',', ': '))
    write(name, contents)


def dict_addstring(config, dictstring, required_keys = ['key']):
    required_keys = list(set(['key']) | set(required_keys))
    options = dict([x.split('=') for x in list_split(dictstring)])

    for required_key in required_keys:
        if required_key not in options:
            raise Exception("Required key '%s' was not specified." % required_key)

    key = options['key']

    if key not in config:
        config[key] = {}

    for option_key in options.keys():
        if option_key != 'key':
            config[key][option_key] = options[option_key]


def dict_remove(config, key):
    if key in config:
        del config[key]


def list_add(config, key, values):
    if not key in config:
        config[key] = []

    existing = config[key]
    config[key] = list(set(existing) | set(values))


def list_remove(config, key, values):
    if key in config:
        existing = config[key]
        config[key] = [item for item in existing if not item in values]


def list_split(commastring):
    return [x.strip() for x in commastring.split(',')]
