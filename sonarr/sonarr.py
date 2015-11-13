#!/usr/bin/env python

import json
import os
import urllib
import urllib2

SONARR_APIKEY='7bc5c3b191584491a6ec125a19e2b2e8'
SONARR_HOST='nativecode.dyndns.org'
SONARR_PORT='8989'

def sonarr_request(command, parameters={}):
    url = 'http://%s:%s/api/%s' % (SONARR_HOST, SONARR_PORT, command)

    queries = []
    for key in parameters.keys():
        value = parameters[key]
        queries.append('%s=%s' % (key, value))

    if len(queries) > 0:
        url = '%s/?%s' % (url, '&'.join(queries))

    request = urllib2.Request(url)
    request.add_header('X-Api-Key', SONARR_APIKEY)

    response = urllib2.urlopen(request)
    return json.loads(response.read())


def main():
    shows = sonarr_request('series')
    print 'Found %s shows.' % len(shows)

    for show in shows:
        series_id = show['id']

        episodes = sonarr_request('episodefile', { 'seriesId' : series_id })
        for episode in episodes:
            #print json.dumps(episode, sort_keys=True, indent=4, separators=(',', ': '))
            episodefile_id = episode['id']
            filename = os.path.basename(episode['path'])
            quality = episode['quality']['quality']['name']
            if quality == 'HDTV-720p':
                print '  [%s] "%s" (%s)' % (episodefile_id, filename, quality)

main()
