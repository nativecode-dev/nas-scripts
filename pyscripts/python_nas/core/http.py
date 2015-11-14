import base64
import urllib2

def get_basic_auth(username, password):
    """
    Returns a base-64 encoded string representing the authorization value.
    """
    return base64.encodestring('%s:%s'% (username, password)).replace('\n', '')


def get_basic_auth_header(username, password):
    """
    Returns a dictionary representing the authorization header.
    """
    return { 'authorization': "Basic %s" % get_basic_auth(username, password) }


def get(url, headers = {}, timeout = 30):
    request = urllib2.Request(url, headers = headers)
    return urllib2.urlopen(request, timeout = timeout)
