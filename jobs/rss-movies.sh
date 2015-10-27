#!/bin/sh

/volume1/.@plugins/AppCentral/python/bin/python /share/Data/Scripts/rssarchiver \
    --schema sqlite:/share/Data/Databases/rssarchiver/rss.db \
    --type movies \
    --url http://bit.ly/1wYYP1r \
    --logfile /share/Data/Databases/rssarchiver/rss.log
