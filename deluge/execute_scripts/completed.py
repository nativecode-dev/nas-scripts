#!/usr/bin/env python

import logging
import logging.handlers
import os
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.handlers.SysLogHandler(address=('localhost', 514)))

def main():
    logger.info('Deluge called completed.')

    torrent_id = sys.argv[1]
    torrent_name = sys.argv[2]
    torrent_dir = sys.argv[3]

    # Log the parameters that were passed.
    logger.info('Torrent hash: %s.' % torrent_id)
    logger.info('Torrent name: %s.' % torrent_name)
    logger.info('Torrent dir: %s.' % torrent_dir)

main()
