#!/usr/bin/env python
#
# Archive Filter
#
# Copyright (C) 2015 NativeCode Development <reginfo@nativecode.com>
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
### NZBGET QUEUE/POST-PROCESSING SCRIPT                                    ###

# Provides pre-filtering of archives if they contain specific file types.
#
# If the file list of an archive contains a file with one of the filtered
# extensions, the NZB will be marked as FAILURE/BAD.
#

##############################################################################
### OPTIONS                                                                ###

# Enable or disable the script from executing (Enabled, Disabled, Debug).
#
# Allows global execution of the script to be disabled without removing the
# script from various events.
#
#ScriptAction=Enabled

# Ignored extensions.
#
# List of extensions to ignore if they exist in the archive separated by a
# comma.
#IgnoredExtensions=.iso

### NZBGET QUEUE/POST-PROCESSING SCRIPT                                    ###
##############################################################################


import os
import sys
import subprocess
import re
import base64
import urllib
import urllib2
import shlex
import traceback

from xmlrpclib import ServerProxy


#############################################################################
# CONSTANTS (Don't change these values)
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


##############################################################################
# option
##############################################################################
def option(name):
    return os.environ.get('NZBPO_' + name)


##############################################################################
# nzbget_http
##############################################################################
def nzbget_http():
    # Make sure we encode the username and password since it will be used in
    # the url we create.
    username = urllib.quote(NZBGET_USERNAME, safe='')
    password = urllib.quote(NZBGET_PASSWORD, safe='')
    url = 'http://%s:%s@%s:%s/xmlrpc' % (username, password, NZBGET_HOST, NZBGET_PORT)

    if SCRIPT_DEBUG:
        print('[DETAIL] HTTP: %s.' % url)

    return ServerProxy(url)


##############################################################################
# nzbget_xmlrpc
##############################################################################
def nzbget_xmlrpc(url_command):
    url = 'http://%s:%s/jsonrpc/%s' % (NZBGET_HOST, NZBGET_PORT, url_command)

    if SCRIPT_DEBUG:
        print('[DETAIL] XMLRPC: %s.' % url)

    request = urllib2.Request(url)

    auth = base64.encodestring('%s:%s' % (NZBGET_USERNAME, NZBGET_PASSWORD)).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % auth)

    response = urllib2.urlopen(request)

    return response.read()


##############################################################################
# start_check
##############################################################################
def start_check():
    # Check if the script is called from a compatible NZBGet version
    # (as queue-script or as pp-script)
    HasEvent = 'NZBNA_EVENT' in os.environ
    HasDirectory = 'NZBPP_DIRECTORY' in os.environ
    HasArticleCache = 'NZBOP_ARTICLECACHE' in os.environ
    if not (HasEvent or HasDirectory) or not HasArticleCache:
        print('[ERROR] *** NZBGet queue script ***')
        print('[ERROR] This script is supposed to be called from nzbget (14.0 or later).')
        sys.exit(PROCESS_FAIL_ENVIRONMENT)


    # This script processes only certain queue events.
    # For compatibility with newer NZBGet versions, it ignores event types
    # it doesn't know.
    KnownEvents = ['NBZ_ADDED', 'FILE_DOWNLOADED', 'NZB_DOWNLOADED', None]
    if os.environ.get('NZBNA_EVENT') not in KnownEvents:
        sys.exit(PROCESS_FAIL_RUNTIME)


    # If nzb was already marked as bad, don't do any further detection.
    if os.environ.get('NZBPP_STATUS') == 'FAILURE/BAD':
        if os.environ.get('NZBPR_PPSTATUS_ARCHIVE_IGNORE') == 'yes':
            # Print the message again during post-processing to ad it into the
            # post-processing log (which is then used by notification scripts).
            print('[WARNING] Download has ignored files.')
        clean_up()
        sys.exit(PROCESS_SUCCESS)


    # if called via "Post-process again" from history details dialog, the
    # download may not exist anymore.
    if HasDirectory and not os.path.exists(os.environ.get('NZBPP_DIRECTORY')):
        print('[WARNING] Destination directory does not exist.')
        clean_up()
        sys.exit(PROCESS_NONE)


    # If nzb is already failed, don't do any further detection.
    if os.environ.get('NZBPP_TOTALSTATUS') == 'FAILURE':
        clean_up()
        sys.exit(PROCESS_NONE)


##############################################################################
# sort_inner_files
##############################################################################
def sort_inner_files():
    nzb_id = int(os.environ.get('NZBNA_NZBID'))

    # Building command-URL to call method "listfiles", passing in three
    # parameters: (0, 0, nzb_id)
    url_command = 'listfiles?1=0&2=0&3=%i' % nzb_id
    data = nzbget_xmlrpc(url_command)

    # Iterate through the list of files to find the last rar-file.
    # The last is the one with the highest XX in ".partXX.rar" or ".rXX"
    re_primary = re.compile('.*\.part(\d+)\.rar', re.IGNORECASE)
    re_parts = re.compile('.*\.r(\d+)', re.IGNORECASE)
    file_index = None
    file_id = None
    file_name = None

    for line in data.splitlines():
        if line.startswith('"ID" : '):
            id = int(line[7:len(line)-1])
        if line.startswith('"Filename" : "'):
            name = line[14:len(line)-2]
            match = re_primary.match(name) or re_parts.match(name)
            if match:
                index = int(match.group(1))
                if not file_index or index > file_index:
                    file_index = index
                    file_id = id
                    file_name = name

    # Move the last rar-file to the top of the file list
    if file_id:
        print('[INFO] Moving last rar-file to the top: %s.' % file_name)
        nzbget = nzbget_http()
        nzbget.editqueue('FileMoveTop', 0, '', [file_id])
    else:
        print('[INFO] Skipping sorting since could not find any rar-files.')


##############################################################################
# clean_up
##############################################################################
def clean_up():
    nzb_id = os.environ.get('NZBPP_NZBID')
    temp_folder = os.environ.get('NZBOP_TEMPDIR') + '/ArchiveFilter'

    nzbids = []
    files = os.listdir(temp_folder)

    if len(files) > 1:
        # Create the list of nzbs in download queue.
        data = nzbget_xmlrpc('listgroups?1=0')

        for line in data.splitlines():
            if line.startswith('"NZBID" : '):
                id = int(line[10:len(line)-1])
                nzbids.append(str(id))

    old_temp_files = list(set(files)-set(nzbids))
    if nzb_id in files and nzb_id not in old_temp_files:
        old_temp_files.append(nzb_id)

    for temp_id in old_temp_files:
        temp_file = temp_folder + '/' + str(temp_id)
        try:
            print('[DETAIL] Removing temp file %s.' % temp_file)
        except:
            print('[ERROR] Could not remove temp file %s.' % temp_file)


##############################################################################
# contains_ignored_files
##############################################################################
def contains_ignored_files(list):
    for item in list:
        if os.path.splitext(item)[1] in IGNORED_EXTENSIONS:
            return True
        else:
            continue

    return False


##############################################################################
# detect_ignored_files
##############################################################################
def detect_ignored_files(name, directory):
    # Ignored file detection:
    #   If download contains ignored files, we want to mark the download
    #   as being bad.
    #
    #   QUEUE:
    #     - If directory contains other archives, list their content and use
    #       the file names for detection.
    #   POST:
    #     - Scan directory content and use the file names for detection.
    #
    # It's actually not necessary to check the mode since it's already
    # verified which event the script is running at.
    filelist = []
    dir = os.path.normpath(directory)
    filelist.extend([ o for o in os.listdir(dir) if os.path.isfile(os.path.join(dir, o)) ])
    dirlist = [ os.path.join(dir, o) for o in os.listdir(dir) if os.path.isdir(os.path.join(dir, o)) ]
    filelist.extend(list_all_rars(dir))

    for subdir in dirlist:
        filelist.extend(list_all_rars(subdir))

    ignored = contains_ignored_files(filelist)

    if ignored:
        print('[WARNING] Download has ignored files.')

    return ignored


##############################################################################
# list_all_rars
##############################################################################
def list_all_rars(directory):
    files = get_file_list(directory)
    tested = ''
    out = ''
    for file in files:
        # Avoid .tmp files as corrupt.
        if not "tmp" in file:
            try:
                command = [unrar(), "vb", directory + '/' + file]

                if SCRIPT_DEBUG:
                    print('[INFO] Command: %s.' % command)

                proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out_temp, err = proc.communicate()
                out += out_temp
                result = proc.returncode

                if SCRIPT_DEBUG:
                    print('[INFO] Out: %s.' % out_temp)
            except Exception as e:
                print('[ERROR] Failed %s: %s' % (file, e))

                if SCRIPT_DEBUG:
                    traceback.print_exc()
        
        tested += file + '\n'

    save_tested(tested)

    return out.splitlines()


##############################################################################
# get_file_list
##############################################################################
def get_file_list(directory):
    try:
        with open(temp_file_name) as temp_file:
            tested = temp_file.read().splitlines()
            files = os.listdir(directory)

            return list(set(files)-set(tested))
    except:
        # temp_file doesn't exist, all files need testing
        temp_folder = os.path.dirname(temp_file_name)
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)
            print('[DETAIL] Created folder %s.' % temp_folder)
        with open(temp_file_name, "w") as temp_file:
            temp_file.write('')
            print('[DETAIL] Created temp file: %s.' % temp_file_name)

        return os.listdir(directory)

##############################################################################
# save_tested
##############################################################################
def save_tested(data):
    with open(temp_file_name, "a") as temp_file:
        temp_file.write(data)


##############################################################################
# unrar
##############################################################################
def unrar():
    exe_name = 'unrar.exe' if os.name == 'nt' else 'unrar'
    cmd_unrar = os.environ['NZBOP_UNRARCMD']
    if os.path.isfile(cmd_unrar) and cmd_unrar.lower().endswith(exe_name):
        return cmd_unrar

    args = shlex.split(cmd_unrar)
    for arg in args:
        if arg.lower().endswith(exe_name):
            return arg

    return exe_name


##############################################################################
# main
##############################################################################
def main():
    if SCRIPT_DEBUG:
        print('[INFO] ScriptAction set to %s.' % option('ScriptAction'))

    # Make sure we can execute the script before continuing. Otherwise,
    # we'll skip running the script and just exit with a success.
    if option('ScriptAction') == 'Enabled' or SCRIPT_DEBUG:
        # Globally define directory for storing list of tested files.
        global temp_file_name

        # Do start up check.
        start_check()

        # Determine if the file is still downloading or has finished.
        Downloading = os.environ.get('NZBNA_EVENT') == 'FILE_DOWNLOADED'

        # Depending on the mode in which the script was called (queue-script
        # or post-processing-script) a different set of parameters (env. vars)
        # is passed. They also have different prefixes:
        #   - NZBNA_ in queue-script mode;
        #   - NZBPP_ in pp-script mode.
        Prefix='NZBNA_' if 'NZBNA_EVENT' in os.environ else 'NZBPP_'

        # Read context (what nzb is currently being processed)
        Category = os.environ[Prefix + 'CATEGORY']
        Directory = os.environ[Prefix + 'DIRECTORY']
        NzbName = os.environ[Prefix + 'NZBNAME']

        # Directory for storing list of tested files
        temp_file_name = os.environ.get('NZBOP_TEMPDIR') + '/ArchiveFilter/' + os.environ.get(Prefix + 'NZBID')

        # When nzb is added to queue - reorder inner files for earlier ignore list detection.
        # Also it is possible that nzb was added with a category which doesn't have
        # ArchiveFilter listed in the PostScript. In this case ArchiveFilter was not called
        # when adding nzb to queue but it is being called now and we can reorder
        # files now.
        OnAdded = os.environ.get('NZBNA_EVENT') == 'NZB_ADDED'
        OnFileDownloaded = os.environ.get('NZBNA_EVENT') == 'FILE_DOWNLOADED'
        OnSorted = os.environ.get('NZBPR_ARCHIVEFILTER_SORTED') <> 'yes'

        if SCRIPT_DEBUG:
            print('[INFO] OnAdded=%s, OnFileDownloaded=%s, OnSorted=%s.' % (OnAdded, OnFileDownloaded, OnSorted))

        if OnAdded or (OnFileDownloaded and OnSorted):
            print('[INFO] Sorting inner files for earlier file list detection for %s' % NzbName)
            sys.stdout.flush()
            sort_inner_files()
            print('[NZB] NZBPR_ARCHIVEFILTER_SORTED=yes')

        if OnAdded:
            sys.exit(PROCESS_NONE)

        print('[DETAIL] Detecting ignored files for %s.' % NzbName)
        sys.stdout.flush()

        if detect_ignored_files(NzbName, Directory):
            # An ignored file was found, so we need to mark that the archive is ignored.
            print('[NZB] NZBPR_PPSTATUS_ARCHIVEFILTER_IGNORED=yes')

            # Special command telling NZBGet to mark nzb as bad. The nzb will
            # be removed from queue and become status "FAILURE/BAD".
            print('[NZB] MARK=BAD')
        else:
            if os.environ.get('NZBPR_PPSTATUS_ARCHIVEFILTER_IGNORED') == 'yes':
                print('[NZB] NZBPR_PPSTATUS_ARCHIVEFILTER_IGNORED=')

        print('[DETAIL] Detection completed for %s.' % NzbName)
        sys.stdout.flush()

        # Remove temp files in PP.
        if Prefix == 'NZBPP_':
            clean_up()

# Define options
SCRIPT_DEBUG=option('ScriptAction') == 'Debug'
IGNORED_EXTENSIONS=option('IgnoredExtensions')

# Execute the main script function.
main()

# Assuming that we make it this far, we didn't encounter any
# errors so we can exit noting a value of success.
sys.exit(PROCESS_SUCCESS)
