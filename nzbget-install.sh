#!/bin/sh

echo '$0 = ' $0
echo '$1 = ' $1

cd /volume1/.@plugins/AppCentral/nzbget/nzbget/scripts

ln -s /share/Data/Scripts/nzbget/Completion.py Completion.py
ln -s /share/Data/Scripts/nzbget/EventHelper.py EventHelper.py
ln -s /share/Data/Scripts/nzbget/FileMover.py FileMover.py
ln -s /share/Data/Scripts/nzbget/Rejector.py Rejector.py
ln -s /share/Data/Scripts/nzbget/nzb.py nzb.py
