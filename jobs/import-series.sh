#!/bin/sh

/volume1/.@plugins/AppCentral/python/bin/python /share/Data/Scripts/rssarchiver \
    --schema sqlite:/share/Data/Databases/rssarchiver/rss.db \
    --type series \
    --url http://nativecode.no-ip.org:82/shows.rss \
    --logfile /share/Data/Databases/rssarchiver/rss.log
