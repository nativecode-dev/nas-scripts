# Imports
##############################################################################
import json
import nzb
import os
import re
import subprocess
import traceback


# Constants
##############################################################################

MEDIA_EXTENSIONS=['.mkv', '.avi', '.divx', '.xvid', '.mov', '.wmv', '.mp4', '.mpg', '.mpeg', '.vob', '.iso', '.m4v']


# File and path functions
##############################################################################

def get_new_files(filelist, cache_filepath=None):
    """
    Gets the list of files in the provided filelist. If a cache_filepath is
    provided, it will join the lists together, removing files that already
    existed in the cache.
    """
    if cache_filepath and os.path.isfile(cache_filepath):
        with open(cache_filepath, 'r') as cachefile:
            cachedlist = cachefile.read().splitlines()
            cachefile.close()

        return list(set(filelist)-set(cachedlist))
    else:
        return filelist


# RAR functions
##############################################################################

RAR_PASSWORD_STRINGS='*,wrong password,The specified password is incorrect,encrypted headers'

def get_rar():
    """
    Attempt to find the platform-specific command to unrar.
    """
    filename = 'unrar.exe' if os.name == 'nt' else 'unrar'
    filepath = os.environ['NZBOP_UNRARCMD']

    if os.path.isfile(filepath) and filepath.lower().endswith(filename):
        return filepath

    parts = shlex.split(filepath)
    for part in parts:
        if part.lower().endswith(filename):
            return part

    return filename


def get_rar_filelist(filepath):
    """
    Gets the list of the file contents from a RAR file.
    """
    try:
        rar_command = [get_rar(), 'vb', filepath]
        process = subprocess.Popen(rar_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        filelist, error = process.communicate()

        return filelist.splitlines()
    except Exception as e:
        nzb.log_error('Failed checking RAR contents for %s. Error was %s.' % (filepath, e))
        traceback.print_exc()
        pass


def get_rar_xmlfiles(filelist):
    """
    Provided a filelist from XMLRPC, enumerate the files and determine the part
    number and return a list of parsed files.
    """
    files = []
    for file in filelist:
        file_id = file['ID']
        file_name = file['Filename']
        file_nzbid = file['NZBID']
        name, extension = os.path.splitext(file_name)
        number = get_rar_number(file_name)

        # If the file was successfully parsed for a number, add it to the files.
        if number:
            files.append({
                'filename' : file_name,
                'fileid' : file_id,
                'number' : number
            })

    return files


def get_rar_number(filename):
    re_part = re.compile('.*\.part(\d+)\.rar', re.IGNORECASE)
    re_rar = re.compile('.*\.r(\d+)', re.IGNORECASE)

    match = re_part.match(filename) or re_rar.match(filename)

    if match:
        return int(match.group(1))


def is_rar_password_requested(text, error):
    nzb.log_debug(text.translate(None, '\r\n'))
    nzb.log_debug(error.translate(None, '\r\n'))

    password_strings = RAR_PASSWORD_STRINGS.split(',')

    for password_string in password_strings:
        cleaned = password_string.strip().lower()
        if cleaned and (cleaned in text.lower() or cleaned in error.lower()):
            return True

    return False


def is_rar_protected(filepath):
    """
    Attempts to check if the RAR is password protected.
    """
    try:
        rar_command = [get_rar(), 'l', '-p-', '-c-', filepath]
        rar_process = subprocess.Popen(rar_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        text, error = rar_process.communicate()

        if is_rar_password_requested(text, error):
            return True
    except Exception as e:
        nzb.log_error('Failed checking RAR %s for password. Error was %s.' % (filepath, e))
        traceback.print_exc()
        return False
