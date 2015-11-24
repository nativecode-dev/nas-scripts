#!/usr/bin/env python

import os
import re

REGEX_FILENAME=re.compile('(.*)\s(\(\d{4}\)).*')

def main():
    extensions = ['.avi', '.mkv', '.mp4', '.wmv', '.mpeg', '.mpg', '.m4v']
    root = '/share/Media/Movies'

    for dir_path, dir_names, dir_files in os.walk(root):
        for dir_file in dir_files:
            file_name, file_extension = os.path.splitext(dir_file)
            file_original = os.path.join(dir_path, dir_file)

            if file_extension in extensions:
                match = REGEX_FILENAME.match(file_name)

                if not match:
                    continue

                title = match.group(1)
                year = match.group(2)

                file_renamed = os.path.join(dir_path, "%s %s%s" % (title, year, file_extension))

                if file_original != file_renamed:
                    os.rename(file_original, file_renamed)
                    print "[RENAME] %s -> %s" % (file_original, file_renamed)
            else:
                os.remove(file_original)
                print "[DELETE] %s" % file_original


main()
