#!/bin/sh

/volume1/.@plugins/AppCentral/python/bin/python /share/Data/Source/nas-scripts/rssarchiver import \
    --schema sqlite:/share/Data/Databases/rssarchiver/rss.db \
    --type series \
    --url http://bit.ly/1tye55k \
    --logfile /share/Data/Databases/rssarchiver/rss.log
