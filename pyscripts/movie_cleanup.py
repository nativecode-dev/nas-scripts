#!/usr/bin/env python

import os
import re

REGEX_FILENAME=re.compile('(.*)\s(\(\d{4}\)).*')
EXTENSIONS=['.avi', '.m4v', '.mkv', '.mov', '.mp2', '.mp4', '.mpeg', '.mpg', '.mpv', '.webm', '.wmv']

def main():
    root = '/share/Media/Movies'

    for dir_path, dir_names, dir_files in os.walk(root):
        for dir_file in dir_files:
            file_name, file_extension = os.path.splitext(dir_file)
            file_original = os.path.join(dir_path, dir_file)

            if file_extension in EXTENSIONS:
                _rename(file_original, dir_path, file_name, file_extension)
            else:
                _delete(file_original)


def _rename(original, dir_path, file_name, file_extension):
    match = REGEX_FILENAME.match(file_name)

    if match:
        title = match.group(1)
        year = match.group(2)

        renamed = os.path.join(dir_path, "%s %s%s" % (title, year, file_extension))

        if original != renamed:
            os.rename(original, renamed)
            print "[RENAME] %s -> %s" % (original, renamed)


def _delete(filename):
    os.remove(filename)
    print "[DELETE] %s" % filename


main()
