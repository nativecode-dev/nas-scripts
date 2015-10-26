import json
import traceback

from feeds import *

def main():
    url = 'http://nativecode.no-ip.org:82/movies.rss'
    importer = MovieFeedImporter()
    print('Importing items from "%s"...' % url)

    try:
        items = importer.import_feed(url)

        json_path = '/share/Data/movies.json'
        print('Saving items to %s.' % json_path)
        json.dump(items, open(json_path, 'w'))
    except Exception:
        traceback.print_exc()

main()
