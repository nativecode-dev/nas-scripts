#!/usr/bin/env python

# IMPORTS
# -----------------------------------------------------------------------------
import argparse
import logging
import logging.handlers
import os
import sys


EXTENSIONS=['.avi', '.mkv', '.mov', '.mpg', '.mpeg', '.mp4', '.mv4']


class Options(object):
    def __init__(self, logger, parser):
        self._logger = logger
        self.__init_arguments(parser)


    def __init_arguments(self, parser):
        pass


    def set_options(self, args):
        pass
        

def main():
    logger = initialize_logger()
    parser = argparse.ArgumentParser()
    options = Options(logger, parser)
    options.set_options(parser.parse_args())


def initialize_logger():
    logger = logging.Logger('shrink_videos')

    console = logging.StreamHandler(stream=sys.stdout)
    console.setLevel(logging.INFO)
    logger.addHandler(logger)

    syslog = logging.handlers.SysLogHandler(address='/dev/log')
    syslog.setLevel(logging.ERROR)
    logger.addHandler(syslog)

    return logger


if __name__ == '__main__':
    main()
