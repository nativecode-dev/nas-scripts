#!/usr/bin/env python
#
# Rejector
#
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


##############################################################################
### NZBGET QUEUE/POST-PROCESSING SCRIPT                                    ###

#
# Inspects RAR archives to protect against downloading unwanted files.
#
# Validates that RAR archives that contain disc images, are password
# protected, and/or are fake releases are rejected before the whole archive
# is downloaded.
#
# NOTE: This script requires Python 2.7 to be installed on your system.
#

##############################################################################
### OPTIONS                                                                ###

# Enable or disable the script from executing (Enabled, Disabled, Debug).
#
# Allows global execution of the script to be disabled without removing the
# script from various events.
#
#ScriptState=Enabled

# Determine which type(s) of disc images should be rejected
# (All, Image, Rip, Disabled).
#
# If the largest file that ends in .iso or .img appears to be a disc image,
# the archive is rejected based on the RejectAction.
#
#RejectDiscImages=All

# List of disc image extensions to ignore.
#
# If any of the files contains one of the following comma-separated
# extensions, the file is considered as a disc image.
#
#RejectDiscImageExtensions=.iso,.bdmv,.ifo,.vob

# Enable or disable fake archive validation (Enabled, Disabled).
#
# Checks archive files to ensure that they are not fakes seeded to NNTP
# servers.
#
#RejectFakes=Enabled

# Enable or disable password-protected achives (Enabled, Disabled).
#
# Performs a check on archives by checking if a password is required.
#
#RejectPassword=Enabled

# Specifies a regex pattern to use when file matching.
#
# You can specify multiple regular expressions by separating them with
# a comma and double-quoting each expression.
#RejectPatterns=

# Determines action to take when an archive is rejected (Pause, Fail, Bad).
#
# By default, archives are marked as failed to be compatible with Sonarr
# and other systems that don't understand NZB's marked as Bad. You can also
# set to Pause in order to perform a manual action.
#
#RejectAction=Fail

# List of black-listed strings that potentially indicate the archive
# is a fake.
#
# Comma-separated list of strings that should be searched and to mark
# the archive as being fake.
#
# NOTE: All strings should be lowercase.
#
#FakeBlacklist=.exe,.bat,.sh

# List of white-listed strings that should be excluded from checking.
#
# Comman-separated list of strings that should be searched and override
# any black-listed strings.
#
# NOTE: All strings should be lowercase.
#
#FakeWhitelist=rename

### NZBGET QUEUE/POST-PROCESSING SCRIPT                                    ###
##############################################################################


# Imports
##############################################################################
import nzb
import operator
import os
import re
import shutil
import sys
import traceback


# Options
##############################################################################
SCRIPT_STATE=nzb.get_script_option('ScriptState')
FAKE_BLACKLIST=nzb.get_script_option_list('FakeBlacklist')
FAKE_WHITELIST=nzb.get_script_option_list('FakeWhitelist')
REJECT_ACTION=nzb.get_script_option('RejectAction')
REJECT_DISC_IMAGES=nzb.get_script_option('RejectDiscImages')
REJECT_DISC_IMAGE_EXTENSIONS=nzb.get_script_option_list('RejectDiscImageExtensions')
REJECT_FAKES=nzb.get_script_option('RejectFakes')
REJECT_PASSWORD=nzb.get_script_option('RejectPassword')
REJECT_PATTERNS=nzb.get_script_option_list('RejectPatterns')


# Constants
##############################################################################
SCRIPT_NAME='Rejector'
LOCK_FILELIST='RejectorFileList'


# Handles when a file from the NZB has completed downloading.
##############################################################################
def on_file_downloaded():
    nzbid = nzb.get_nzb_id()

    # Update the file caches and run the inspection methods.
    update_filelist(nzbid)


# Handles when an NZB is added to the queue.
##############################################################################
def on_nzb_added():
    # Clean up any previous runs.
    clean_up()

    # Lock the script from running again.
    nzb.lock_create(SCRIPT_NAME)
    nzbid = nzb.get_nzb_id()

    # Move the last RAR file to the top.
    reorder_queued_items(nzbid)


# Handles when an NZB is finished downloading all files.
##############################################################################
def on_nzb_downloaded():
    if nzb.lock_exists(SCRIPT_NAME):
        # Only clean up once we're done downloading.
        clean_up()


# Moves the last RAR file to the top of the queue list.
##############################################################################
def reorder_queued_items(nzbid):
    """
    Finds the last part of the RAR archive and moves to the top of the queue.
    """
    # If another script already sorted, then we can skip sorting.
    if bool(nzb.get_script_variable('RAR_SORTED')):
        nzb.log_info('Last RAR file was already sorted.')
        return

    # Get the list of files for this NZB.
    proxy = nzb.proxy()
    filelist = proxy.listfiles(0, 0, nzbid)

    # Enumerate the RAR files from the NZB and try to parse the part number.
    files = nzb.get_rar_xmlfiles(filelist)

    # If we found RAR files, we need to sort so that the last RAR file is the first
    # item in the list.
    if files:
        files_sorted = sorted(files, key=operator.itemgetter('number'), reverse=True)
        filename = files_sorted[0]['filename']
        fileid = int(files_sorted[0]['fileid'])

        if proxy.editqueue('FileMoveTop', 0, '', [fileid]):
            nzb.log_detail('Moved last RAR file %s to the top.' % filename)
            nzb.set_script_variable('RAR_SORTED', True)
        else:
            nzb.log_warning('Failed to move the last RAR file %s.' % filename)
    else:
        nzb.log_warning('Failed to get list of files to sort.')


# Updates the cached filelist on disk.
##############################################################################
def update_filelist(nzbid):
    # If a lock already exists in updating the cache file, bail out.
    if nzb.lock_exists(LOCK_FILELIST):
        return

    # Get the list of files from cache and from disk.
    nzb.lock_create(LOCK_FILELIST)

    try:
        cache_filepath = get_cache_filepath(nzbid)
        directory = nzb.get_nzb_directory()

        if not os.path.isdir(directory):
            nzb.log_warning('Directory %s does not appear valid.' % directory)

        filelist = nzb.get_new_files(os.listdir(directory), cache_filepath)

        # Cache the files that we've found that we just processed.
        with open(cache_filepath, 'a') as cachefile:
            for filename in filelist:
                name, extension = os.path.splitext(filename)
                if extension != '.tmp':
                    cachefile.write(filename + '\n')
                    process_download(directory, filename)
            cachefile.close()
    except Exception as e:
        traceback.print_exc()
        nzb.log_error(e)
        raise
    finally:
        nzb.lock_release(LOCK_FILELIST)


# Gets the full path to the cache file.
##############################################################################
def get_cache_filepath(name):
    tempdir = get_temp_path()
    filename = 'cached-%s.filelist' % name

    return os.path.join(tempdir, filename)


# Processes a file that has been downloaded.
##############################################################################
def process_download(directory, filename):
    if not os.path.isdir(directory):
        nzb.log_warning('Directory %s does not appear valid.' % directory)

    filepath = os.path.join(directory, filename)
    cache_filepath = get_cache_filepath('%s-contents' % nzb.get_nzb_id())
    contentlist = nzb.get_rar_filelist(filepath)
    filelist = nzb.get_new_files(contentlist, cache_filepath)

    with open(cache_filepath, 'a') as cachefile:
        for file in filelist:
            inspect_rar_content(directory, file)
            cachefile.write(file + '\n')
        cachefile.close()


# Inspects the specified file from inside a RAR archive.
##############################################################################
def inspect_rar_content(directory, filename):
    nzb.log_detail('Checking RAR content file %s.' % filename)

    if REJECT_DISC_IMAGES != 'Disabled':
        check_disc_image(filename)

    if REJECT_FAKES != 'Disabled':
        check_fake(filename)

    if REJECT_PASSWORD != 'Disabled':
        check_protected(directory, filename)


# Checks if the file looks like a disc image.
##############################################################################
def check_disc_image(filename):
    name, extension = os.path.splitext(filename)

    if REJECT_DISC_IMAGES == 'All' or REJECT_DISC_IMAGES == 'Image':
        if extension in REJECT_DISC_IMAGE_EXTENSIONS:
            reject('Contains a disc image file (%s).' % filename)

    if REJECT_DISC_IMAGES == 'All' or REJECT_DISC_IMAGES == 'Rip':
        if extension == '.vob' or extension == '.ifo':
            reject('Contains a file (%s) indicating it was a rip.' % filename)


# Checks if the file is considered part of being fake.
##############################################################################
def check_fake(filename):
    name, extension = os.path.splitext(filename)

    if name.lower() in FAKE_WHITELIST or extension.lower() in FAKE_WHITELIST:
        return

    blacklisted = name.lower() in FAKE_BLACKLIST or extension.lower() in FAKE_BLACKLIST
    invalid = False if extension in nzb.MEDIA_EXTENSIONS else nzb.is_video_invalid(filename)

    if blacklisted or invalid:
        reject('Contains a file (%s) that appears to indicate a fake.' % filename)


# Checks if the file is password protected.
def check_protected(directory, filename):
    filepath = os.path.join(directory, filename)
    if nzb.is_rar_protected(filepath):
        reject('Requires a password to extract.')


# Rejects the archive and marks the NZB according to the REJECT_ACTION.
##############################################################################
def reject(reason):
    nzbid = nzb.get_nzb_id()
    nzbname = nzb.get_nzb_name()
    nzb.log_error('Rejecting %s. %s.' % (nzbname, reason))

    response = None

    if REJECT_ACTION == 'Pause':
        nzb.log_error('File %s was rejected, pausing download.' % nzbname)
        response = nzb.proxy().editqueue('GroupPause', 0, '', [nzbid])
    elif REJECT_ACTION == 'Bad':
        nzb.log_error('File %s was rejected, marking as bad.' % nzbname)
        nzb.set_nzb_bad()
        response = True
    elif REJECT_ACTION == 'Fail':
        nzb.log_error('File %s was rejected, marking as failed.' % nzbname)
        response = nzb.set_nzb_fail(nzbid)

    if not response:
        nzb.log_error('Failed to apply the reject action.')
        nzb.exit(nzb.PROCESS_ERROR)

    nzb.exit(nzb.PROCESS_ERROR)


# Gets the temp folder for the script.
##############################################################################
def get_temp_path():
    return nzb.get_script_tempfolder(SCRIPT_NAME)


# Cleanup script
##############################################################################
def clean_up():
    """
    Perform any script cleanup that is required here.
    """
    if nzb.lock_exists(SCRIPT_NAME):
        nzb.lock_release(SCRIPT_NAME)

    if nzb.lock_exists(LOCK_FILELIST):
        nzb.lock_release(LOCK_FILELIST)

    tempdir = get_temp_path()
    if len(os.listdir(tempdir)) == 0:
        if os.path.exists(tempdir):
            shutil.rmtree(tempdir)


# Main entry-point
##############################################################################
def main():
    """
    We need to check to make sure the script can run in the provided
    environment and that certain status checks have occurred. All of the
    calls here will exit with an exit code if the check fails.
    """
    try:
        # If the script state was set to Disabled, we don't need to run.
        if SCRIPT_STATE == 'Disabled':
            nzb.exit(nzb.PROCESS_SUCCESS)

        # Determine if we have features enabled.
        DiscImageEnabled = REJECT_DISC_IMAGES != 'Disabled'
        FakeCheckEnabled = REJECT_FAKES != 'Disabled'
        PasswordCheckEnabled = REJECT_PASSWORD != 'Disabled'
        if not (DiscImageEnabled and FakeCheckEnabled and PasswordCheckEnabled):
            nzb.log_info('No features enabled. Skipping script execution.')
            nzb.exit(nzb.PROCESS_SUCCESS)

        # Check version of NZBGet to make sure we can run.
        nzb.check_nzb_version(13.0)

        # Wire up your event handlers before the call.
        # Use the form nzb.set_handler(<event>, <function>)
        nzb.set_handler('FILE_DOWNLOADED', on_file_downloaded)
        nzb.set_handler('NZB_ADDED', on_nzb_added)
        nzb.set_handler('NZB_DOWNLOADED', on_nzb_downloaded)

        # Do not change this line, it checks the current event
        # and executes any event handlers.
        nzb.execute()
    except Exception as e:
        traceback.print_exc()
        nzb.exit(nzb.PROCESS_ERROR, e)
        clean_up()


# Main entry-point
##############################################################################
main()

# NZBGet is weird and doesn't use 0 to signal the successful execution of a
# script, so we use the PROCESS_SUCCESS code here.
nzb.exit(nzb.PROCESS_SUCCESS)
