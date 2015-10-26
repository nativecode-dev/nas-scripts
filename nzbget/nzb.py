# Copyright (C) 2015 NativeCode Development <support@nativecode.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
##############################################################################
#
# Some of the code has been inspired and/or lifted from other scripts written
# by talented individuals.
#
#   PasswordDetector: https://github.com/JVMed/PasswordDetector
#   FakeDetector: https://github.com/nzbget/FakeDetector
#   Completion: http://forum.nzbget.net/viewtopic.php?f=8&t=1736
#
##############################################################################


# Imports
#############################################################################

import base64
import datetime
import json
import os
import re
import shlex
import subprocess
import sys
import time
import traceback
import urllib
import urllib2


# Import aliases
#############################################################################

from xmlrpclib import ServerProxy


# Constants
#############################################################################

PROCESS_FAIL_ENVIRONMENT=10
PROCESS_FAIL_RUNTIME=11
PROCESS_FAIL_PROXY=12
PROCESS_SUCCESS=93
PROCESS_ERROR=94
PROCESS_NONE=95

NZBGET_HOST=os.environ['NZBOP_CONTROLIP']
NZBGET_PORT=os.environ['NZBOP_CONTROLPORT']
NZBGET_USERNAME=os.environ['NZBOP_CONTROLUSERNAME']
NZBGET_PASSWORD=os.environ['NZBOP_CONTROLPASSWORD']

# If the IP address has no real value, set to localhost.
if NZBGET_HOST == '0.0.0.0': NZBGET_HOST = '127.0.0.1'

MEDIA_EXTENSIONS=[
    '.avi',
    '.divx',
    '.m4v',
    '.mkv',
    '.mov',
    '.mp4',
    '.mpeg',
    '.mpg',
    '.wmv',
    '.xvid'
]

EVENTS = {
    'FILE_DOWNLOADED' : None,
    'NZB_ADDED' : None,
    'NZB_DOWNLOADED' : None,
    'POST_PROCESSING' : None,
    'QUEUEING' : None,
    'SCANNING' : None,
    'SCHEDULED' : None,
    'UNKNOWN' : None
}


# Logging
#############################################################################

def log_debug(message):
    log_write('DEBUG', message)


def log_detail(message):
    log_write('DETAIL', message)


def log_error(message):
    log_write('ERROR', message)


def log_info(message):
    log_write('INFO', message)


def log_warning(message):
    log_write('WARNING', message)


def log_write(type, message):
    print('[%s] %s' % (type, message))


# API
#############################################################################

def command(url_command):
    url = 'http://%s:%s/jsonrpc/%s' % (NZBGET_HOST, NZBGET_PORT, url_command)
    log_debug('Command: %s.' % url)

    auth = '%s:%s' % (NZBGET_USERNAME, NZBGET_PASSWORD)
    auth_token = base64.encodestring(auth).replace('\n', '')

    request = urllib2.Request(url)
    request.add_header('Authorization', 'Basic %s' % auth_token)

    response = retry(lambda: urllib2.urlopen(request))

    return response.read()


def proxy():
    # Make sure we encode the username and password since it will be used in
    # the url we create.
    username = urllib.quote(NZBGET_USERNAME, safe='')
    password = urllib.quote(NZBGET_PASSWORD, safe='')
    url = 'http://%s:%s@%s:%s/xmlrpc' % (username, password, NZBGET_HOST, NZBGET_PORT)

    log_debug('Proxy: %s.' % url)

    return ServerProxy(url)


# Script checking
#############################################################################

def check_nzb_status():
    """
    Checks to see if the NZB has already failed or been deleted.
    """
    status = get_nzb_status()
    status_total = get_nzb_status_total()

    if status_total in ['FAILURE', 'DELETED']:
        reason = 'Exiting due to total status of %s (%s).' % (status_total, status)
        exit(PROCESS_ERROR, reason)


def check_nzb_version(min_version):
    """
    Get the version from the server and determine if the script
    min_version is higher than or equal to what is running.
    """    
    try:
        version = float(os.environ['NZBOP_VERSION'])

        if version < min_version:
            reason = 'Requires version %s, but found %s.' % (min_version, version)
            exit(PROCESS_FAIL_RUNTIME, reason)

        log_debug('Running NZBGet %s on %s.' % (version, os.name))
    except Exception:
        traceback.print_exc()
        reason = 'Unable to determine server version. Requires version >= %s.' % min_version
        exit(PROCESS_FAIL_RUNTIME, reason)


def exit(exit_code, reason=None):
    if reason and exit_code == PROCESS_SUCCESS:
        log_info(reason)
    elif reason:
        log_error(reason)

    sys.exit(exit_code)


# Event helpers
#############################################################################

def get_nzb_event():
    """
    Parses the NZBNA_EVENT or NZBPP_EVENT and determines which mode it's
    actually running in. We expand the number of events so that event
    handlers can be created.
    """
    prefix = get_nzb_prefix()

    event = 'NONE'
    event_key = prefix + 'EVENT'

    if event_key in os.environ:
        event = os.environ[event_key]

    if event == 'NONE':
        if 'NZBPP_NZBNAME' in os.environ:
            event = 'POST_PROCESSING'
        elif 'NZBNP_NZBNAME' in os.environ:
            event = 'SCANNING'
        elif 'NZBNA_NZBNAME' in os.environ:
            event = 'QUEUEING'
        else:
            event = 'SCHEDULED'

    return event


def get_handler(event):
    """
    Attempts to find the associated event handler for the provided event.
    """
    if event in EVENTS:
        return EVENTS[event]


def set_handler(event, callback):
    """
    Sets a callback handler to associate with the event.
    """
    if event in EVENTS:
        EVENTS[event] = callback


def execute():
    """
    Executes the event handler associated with the current event.
    """
    event = get_nzb_event()
    handler = get_handler(event)

    if handler:
        log_info('Handler found for %s.' % event)
        handler()


# NZBGet helpers
#############################################################################

def get_nzb_age(nzbid):
    """
    Gets the age based on the first time an article was posted.
    """
    now = datetime.datetime.utcnow()
    groups = retry(lambda: proxy().listgroups(0))

    for group in groups:
        group_nzbid = int(group['NZBID'])
        if group_nzbid == nzbid:
            timestamp = int(group['MinPostTime'])
            last_post = datetime.datetime.fromtimestamp(timestamp)
            delta = now - last_post
            return int(delta.total_seconds() / 60 / 60)

    return 0


def set_nzb_bad():
    """
    Mark an NZB file as being bad. Note that the MarkAsBad in the XML RPC
    method doesn't seem to work.
    """
    print('[NZB] MARK=BAD')


def get_nzb_category():
    prefix = get_nzb_prefix()
    return os.environ[prefix + 'CATEGORY']


def get_nzb_directory():
    prefix = get_nzb_prefix()
    return os.environ[prefix + 'DIRECTORY']


def get_nzb_directory_final():
    key = get_nzb_prefix() + 'FINALDIR'
    return None if key not in os.environ else os.environ.get(key)


def set_nzb_directory_final(directory):
    print('[NZB] FINALDIR=%s' % directory)


def get_nzb_id():
    prefix = get_nzb_prefix()
    return int(os.environ[prefix + 'NZBID'])


def set_nzb_fail(nzbid):
    """
    There doesn't appear to be a way to set an NZB as having been failed for
    reasons other than internal ones. This forces the issue by deleting as
    much data as possible to force into into a FAILURE/PAR status.
    """
    client = proxy()
    nzb_files = retry(lambda: client.listfiles(0, 0, nzbid))
    
    for nzb_file in nzb_files:
        nzb_file_id = int(nzb_file['ID'])
        nzb_file_name = nzb_file['Filename']

        name, extension = os.path.splitext(nzb_file_name)
        delete_file = extension == '.par2' or extension != '.rar'

        # If the RAR is a part, we want to leave the first part alone.
        rar_number = get_rar_number(nzb_file_name)
        if rar_number > 1:
            delete_file = True

        if delete_file:
            log_warning('Deleting %s to force a failure.' % nzb_file_name)
            if not client.editqueue('FileDelete', 0, '', [nzb_file_id]):
                log_error('Failed to delete file %s.' % nzb_file_id)
                return False

    return True


def get_nzb_name():
    prefix = get_nzb_prefix()
    return os.environ[prefix + 'NZBNAME']


def get_nzb_prefix():
    """
    Depending on the mode in which the script was called (queue-script
    or post-processing-script) a different set of parameters (env. vars)
    is passed. They also have different prefixes:
      - NZBNA_ in queue-script mode;
      - NZBPP_ in pp-script mode.
    """
    return 'NZBNA_' if 'NZBNA_EVENT' in os.environ else 'NZBPP_'


def get_nzb_status():
    key = get_nzb_prefix() + 'STATUS'
    return 'UNKNOWN' if key not in os.environ else os.environ[key]


def get_nzb_status_total():
    key = get_nzb_prefix() + 'TOTALSTATUS'
    return 'UNKNOWN' if key not in os.environ else os.environ[key]


def get_nzb_tempfolder():
    return os.environ.get('NZBOP_TEMPDIR')


# Script helpers
##############################################################################

def get_script_option(name):
    return os.environ.get('NZBPO_' + name)


def get_script_option_dictionary(name, separator=':'):
    items = get_script_option(name).split(',')

    dictionary = []
    for item in items:
        parts = item.split(separator)
        key = parts[0]
        value = parts[1]
        dictionary.append({ 'key' : key, 'value' : value })

    return dictionary


def get_script_option_list(name, separator=','):
    return get_script_option(name).split(separator)


def get_script_state(script_name, filename, default={}):
    """
    Checks to see if a JSON file with state data exists on disk.
    If no file exists, it will use the provided default.
    """
    tempdir = get_script_tempfolder(script_name)
    filepath = os.path.join(tempdir, filename + '.state')

    if not os.path.isfile(filepath):
        return default
    else:
        return json.load(open(filepath, 'r'))

def set_script_state(script_name, filename, state):
    """
    Saves the state date to the state file.
    """
    tempdir = get_script_tempfolder(script_name)
    filepath = os.path.join(tempdir, filename + '.state')

    json.dump(state, open(filepath, 'w'))

    return state


def get_script_tempfolder(*args):
    tempdir = os.environ.get('NZBOP_TEMPDIR')

    for arg in args:
        tempdir = os.path.join(tempdir, arg)

    if not os.path.exists(tempdir):
        os.makedirs(tempdir)

    return tempdir


def get_script_tempfile(script_name, filename):
    tempdir = get_script_tempfolder(script_name)
    return os.path.join(tempdir, filename)


def get_script_variable(name, default=None):
    key = '[NZB] NZBPR_%s' % name.upper()
    return default if not key in os.environ else os.environ.get(key)


def set_script_variable(name, value):
    print('[NZB] NZBPR_%s=%s' % (name.upper(), value))


# Script locking functions
##############################################################################

def lock_create(name):
    tempdir = get_nzb_tempfolder()
    lockfile = os.path.join(tempdir, name + '.lock')

    if os.path.isfile(lockfile):
        log_warning('Lock file %s already exists.' % lockfile)
    else:
        file = open(lockfile, 'w')
        try:
            file.write(name)
            log_debug('Lock file %s created.' % lockfile)
        finally:
            file.close()


def lock_exists(name):
    tempdir = get_nzb_tempfolder()
    lockfile = os.path.join(tempdir, name + '.lock')

    return os.path.isfile(lockfile)


def lock_release(name):
    tempdir = get_nzb_tempfolder()
    lockfile = os.path.join(tempdir, name + '.lock')

    if os.path.isfile(lockfile):
        try:
            os.remove(lockfile)
            log_debug('Lock file %s released.' % lockfile)
        except Exception:
            traceback.print_exc()
            log_error('Failed to release lock file %s.' % lockfile)


def lock_reset(name, recreate=True):
    if lock_exists(name): lock_release(name)
    if recreate: lock_create(name)    


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
REGEX_RAR = re.compile('.*\.r(\d+)', re.IGNORECASE)
REGEX_RAR_PART = re.compile('.*\.part(\d+)\.rar', re.IGNORECASE)

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
        traceback.print_exc()
        log_error('Failed checking RAR contents for %s. Error was %s.' % (filepath, e))
        pass

def get_rar_xmlfiles(filelist):
    """
    Provided a filelist from XMLRPC, enumerate the files and determine the part
    number and return a list of parsed files.
    """
    files = []
    for file in filelist:
        file_id = int(file['ID'])
        file_name = file['Filename']
        file_nzbid = int(file['NZBID'])
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
    match = REGEX_RAR.match(filename) or REGEX_RAR_PART.match(filename)

    if match:
        return int(match.group(1))


def is_rar_file(filename):
    match = REGEX_RAR.match(filename) or REGEX_RAR_PART.match(filename)
    return True if match else False


def is_rar_password_error(text, error):
    log_debug(text.translate(None, '\r\n'))
    log_debug(error.translate(None, '\r\n'))

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

        return is_rar_password_error(text, error)
    except Exception as e:
        traceback.print_exc()
        log_error('Failed checking RAR %s for password. Error was %s.' % (filepath, e))
        return False


# Other helpers
##############################################################################

def retry(callback, max_retries=3, seconds=0.1, pushout=True):
    count = 0

    while count < max_retries:
        try:
            return callback()
        except Exception as e:
            log_error('Retry got exception %s (%s/%s).' % (count, retry_count, e))
            sleep_time = seconds * count if pushout else seconds
            time.sleep(sleep_time)
            count += 1

    raise IOError('Retry failed after %s tries.' % max_retries)


# Misc helpers
##############################################################################

def guess_filename(filename):
    try:
        import guessit
        return guessit.guess_file_info(filename)
    except Exception as e:
        name, extension = os.path.splitext(filename)
        log_error(e)
        return {'title' : name}

def is_video_invalid(filename):
    name, extension = os.path.splitext(filename)
    guess = guess_filename(filename)
    return guess['title'] == name


def is_video_file(filename):
    name, extension = os.path.splitext(filename)
    return extension in MEDIA_EXTENSIONS
