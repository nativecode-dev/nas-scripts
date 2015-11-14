from python_nas.core import utils

python_pushover = None

def send(apikey, clientkey, message, title=None):
    global python_pushover

    if not python_pushover:
        try:
            python_pushover = utils.import_non_local('pushover', 'python_pushover')
        except Exception as e:
            raise Exception("Failed to load pushover module. Requires the python-pushover package.")

    client = python_pushover.Client(clientkey, api_token=apikey)
    client.send_message(message, title=title)


def send_multiple(config, message, title=None):
    for key in config.keys():
        options = config[key]
        required_keys = ['apikey', 'clientkey']

        for required_key in required_keys:
            if required_key not in options:
                raise Exception("Required key '%s' was not specified." % required_key)

        apikey = options['apikey']
        clientkey = options['clientkey']

        send(apikey, clientkey, message, title)
