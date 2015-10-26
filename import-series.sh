#!/bin/sh

/volume1/.@plugins/AppCentral/python/bin/python /share/Data/Scripts/rssarchiver \
    --schema sqlite:/share/Data/Databases/rssarchiver/rss-series.db \
    --type series \
    --url http://bit.ly/1tye55k
