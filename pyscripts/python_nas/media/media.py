import os

from MediaFile import MediaFile

EXTENSIONS=['.avi', '.m4v', '.mkv', '.mov', '.mp2', '.mp4', '.mpeg', '.mpg', '.mpv', '.webm', '.wmv', '.xvid']

def get_media_files(path):
    media_files = []

    for dir_path, dir_names, dir_files in os.walk(path):
        for dir_file in dir_files:
            name, extension = os.path.splitext(dir_file)

            if extension in EXTENSIONS:
                fullpath = os.path.join(dir_path, dir_file)
                media_files.append(MediaFile(fullpath))

    return media_files
