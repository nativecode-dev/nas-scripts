#!/usr/bin/env python

import logging
import logging.handlers
import os
import sys


def _setup_logging():
    logger = logging.getLogger('Deluge')
    logger.setLevel(logging.DEBUG)

    _setup_logging_handlers(logger)

    return logger


def _setup_logging_handlers(logger):
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console
    handler_console = logging.StreamHandler(stream=sys.stdout)
    handler_console.setLevel(logging.DEBUG)
    logger.addHandler(handler_console)

    # SysLog
    handler_syslog = logging.handlers.SysLogHandler(address='/dev/log')
    handler_syslog.setFormatter(formatter)
    handler_syslog.setLevel(logging.DEBUG)
    logger.addHandler(handler_syslog)

    # File
    logfile = '/share/Data/Logs/Deluge/completed.log'
    handler_file = logging.handlers.TimedRotatingFileHandler(logfile, when='midnight')
    handler_file.setFormatter(formatter)
    handler_file.setLevel(logging.INFO)
    logger.addHandler(handler_file)


def _torrent_completed(logger, id, name, directory):
    logger.info('torrent_completed(%s, %s, %s)' % (id, name, directory))

    if os.path.isdir(directory):
        for root, dirs, files in os.walk(directory):
            for file in files:
                path = os.path.join(root, file)
                logger.debug(path)


def main():
    logger = _setup_logging()

    torrent_id = sys.argv[1]
    torrent_name = sys.argv[2]
    torrent_dir = sys.argv[3]

    _torrent_completed(logger, torrent_id, torrent_name, torrent_dir)


main()
