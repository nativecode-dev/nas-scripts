#!/bin/sh

/usr/bin/env ifconfig | python /share/Data/Source/nas-scripts/jobs/vpn-notify.py
