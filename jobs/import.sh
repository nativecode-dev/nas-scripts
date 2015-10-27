#!/bin/sh

rm /share/Data/Databases/rssarchiver/*

/bin/sh /share/Data/Scripts/jobs/import-movies.sh
/bin/sh /share/Data/Scripts/jobs/rss-movies.sh

/bin/sh /share/Data/Scripts/jobs/import-series.sh
/bin/sh /share/Data/Scripts/jobs/rss-series.sh
