#!/bin/sh

rm /share/Data/Databases/rssarchiver/*

/bin/sh $(dirname $0)/import-movies.sh
/bin/sh $(dirname $0)/rss-movies.sh

/bin/sh $(dirname $0)/import-series.sh
/bin/sh $(dirname $0)/rss-series.sh
