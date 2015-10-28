#!/bin/sh

ln -s /share/Data/Source/nas-scripts/nzbget/EventHelper.py \
    /volume1/.@plugins/AppCentral/nzbget/nzbget/scripts/EventHelper.py

ln -s /share/Data/Source/nas-scripts/nzbget/HealthCheck.py \
    /volume1/.@plugins/AppCentral/nzbget/nzbget/scripts/HealthCheck.py

ln -s /share/Data/Source/nas-scripts/nzbget/FileMover.py \
    /volume1/.@plugins/AppCentral/nzbget/nzbget/scripts/FileMover.py

ln -s /share/Data/Source/nas-scripts/nzbget/Rejector.py \
    /volume1/.@plugins/AppCentral/nzbget/nzbget/scripts/Rejector.py

ln -s /share/Data/Source/nas-scripts/nzbget/nzb.py \
    /volume1/.@plugins/AppCentral/nzbget/nzbget/scripts/nzb.py
