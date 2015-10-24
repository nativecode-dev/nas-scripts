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
import json
import os
import re
import shlex
import subprocess
import sys
import traceback
import urllib
import urllib2


# Import aliases
#############################################################################

from xmlrpclib import ServerProxy


# Constants
#############################################################################

PROCESS_FAIL_RUNTIME=0
PROCESS_FAIL_ENVIRONMENT=1
PROCESS_SUCCESS=93
PROCESS_ERROR=94
PROCESS_NONE=95

NZBGET_HOST=os.environ['NZBOP_CONTROLIP']
NZBGET_PORT=os.environ['NZBOP_CONTROLPORT']
NZBGET_USERNAME=os.environ['NZBOP_CONTROLUSERNAME']
NZBGET_PASSWORD=os.environ['NZBOP_CONTROLPASSWORD']

# If the IP address has no real value, set to localhost.
if NZBGET_HOST == '0.0.0.0': NZBGET_HOST = '127.0.0.1'

MEDIA_EXTENSIONS=['.mkv', '.avi', '.divx', '.xvid', '.mov', '.wmv', '.mp4', '.mpg', '.mpeg', '.m4v']

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
    print '[%s] %s' % (type, message)


# API
#############################################################################

def command(url_command):
    url = 'http://%s:%s/jsonrpc/%s' % (NZBGET_HOST, NZBGET_PORT, url_command)
    log_debug('Command: %s.' % url)

    auth = '%s:%s' % (NZBGET_USERNAME, NZBGET_PASSWORD)
    auth_token = base64.encodestring(auth).replace('\n', '')

    request = urllib2.Request(url)
    request.add_header('Authorization', 'Basic %s' % auth_token)

    response = urllib2.urlopen(request)

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
    status = get_nzb_status_total()
    if status in ['FAILURE', 'DELETED']:
        log_warning('Exiting due to status of %s.' % status)
        sys.exit(PROCESS_ERROR)


def check_nzb_version(min_version):
    """
    Get the version from the server and determine if the script
    min_version is higher than or equal to what is running.
    """    
    try:
        version = float(os.environ['NZBOP_VERSION'])

        if version < min_version:
            log_info('Requires version %s, but found %s.' % (min_version, version))
            sys.exit(PROCESS_FAIL_RUNTIME)

        log_debug('Running NZBGet %s on %s.' % (version, os.name))
    except Exception:
        log_error('Unable to determine server version. Requires version >= %s.' % min_version)
        sys.exit(PROCESS_FAIL_RUNTIME)


# Event helpers
#############################################################################

def get_nzb_event():
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
    if event in EVENTS:
        return EVENTS[event]


def set_handler(event, callback):
    if event in EVENTS:
        EVENTS[event] = callback


def execute():
    event = get_nzb_event()
    handler = get_handler(event)

    if handler:
        log_info('Handler found for %s.' % event)
        handler()


# Helpers
#############################################################################

def get_nzb_category():
    prefix = get_nzb_prefix()
    return os.environ[prefix + 'CATEGORY']


def get_nzb_data(nzbid):
    url = 'listfiles?1=0&2=0&3=%s' % nzbid
    return command(url)


def get_nzb_directory():
    prefix = get_nzb_prefix()
    return os.environ[prefix + 'DIRECTORY']


def get_nzb_directory_final():
    prefix = get_nzb_prefix()
    key = prefix + 'FINALDIR'
    if key in os.environ:
        return os.environ[key]
    else:
        return None


def set_nzb_directory_final(directory):
    print '[NZB] FINALDIR=%s' % directory


def set_nzb_bad():
    print '[NZB] MARK=BAD'


def set_nzb_fail(nzbid):
    client = proxy()
    nzb_files = client.listfiles(0, 0, nzbid)
    
    for nzb_file in nzb_files:
        nzb_file_id = int(nzb_file['ID'])
        nzb_file_name = nzb_file['Filename']
        name, extension = os.path.splitext(nzb_file_name)

        if extension == '.par2' or extension != '.rar':
            log_warning('Deleting %s to force a failure.' % nzb_file_name)
            if not client.editqueue('FileDelete', 0, '', [nzb_file_id]):
                log_error('Failed to delete file %s.' % nzb_file_id)
                return False

    return True


def get_nzb_id():
    prefix = get_nzb_prefix()
    return int(os.environ[prefix + 'NZBID'])


def get_nzb_files(nzbid):
    data = json.loads(get_nzb_data(nzbid))

    files = []
    for item in data['result']:
        files.append({ 'filename' : item['Filename'], 'id' : item['ID'] })

    return files

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


def get_script_state(name):
    return os.environ.get('NZBPR_' + name)


def set_script_state(name, value):
    print '[NZB] NZBPR_%s=%s' % (name, value)


def get_script_tempfolder(*args):
    tempdir = os.environ.get('NZBOP_TEMPDIR')

    for arg in args:
        tempdir = os.path.join(tempdir, arg)

    if not os.path.exists(tempdir):
        os.makedirs(tempdir)

    return tempdir


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


def lock_release(name):
    tempdir = get_nzb_tempfolder()
    lockfile = os.path.join(tempdir, name + '.lock')

    if os.path.isfile(lockfile):
        try:
            os.remove(lockfile)
            log_debug('Lock file %s released.' % lockfile)
        except Exception:
            log_error('Failed to release lock file %s.' % lockfile)


def lock_exists(name):
    tempdir = get_nzb_tempfolder()
    lockfile = os.path.join(tempdir, name + '.lock')

    return os.path.isfile(lockfile)


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
