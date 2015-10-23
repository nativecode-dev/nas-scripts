#!/usr/bin/env python
#
# Handles moving other video types.
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
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Handles moving video files from different categories.
#
# Based on the selected categories, will move just the largest video files
# to the specified location.

##############################################################################
### OPTIONS                                                                ###

# Enable or disable the script from executing (Enabled, Disabled, Debug).
#
# Allows global execution of the script to be disabled without removing the
# script from various events.
#
#ScriptState=Enabled

# Category and locations.
#
# Set the category and path to move files.
#
#CategoryLocations=Other:/share/Media/Other

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################


# Imports
##############################################################################
import nzb
import operator
import os
import shutil
import sys
import traceback


# Options
##############################################################################
SCRIPT_STATE=nzb.get_script_option('ScriptState')
CATEGORIES=nzb.get_script_option_dictionary('CategoryLocations')


# Constants
##############################################################################
MEDIA_EXTENSIONS=['.mkv', '.avi', '.divx', '.xvid', '.mov', '.wmv', '.mp4', '.mpg', '.mpeg', '.vob', '.iso', '.m4v']


# Handle post processing
##############################################################################
def on_post_processing():
    directory = nzb.get_nzb_directory()
    category = nzb.get_nzb_category()
    target = get_category_path(category)

    if os.path.isdir(directory):
        # We need to move the files, delete the directory, and hide the NZB
        # from history.
        file = get_largest_file(category, directory, target)

        source_path = os.path.join(directory, file)
        target_path = os.path.join(target, file)

        if os.path.isfile(target_path):
            nzb.log_warning('File %s already exists.' % target_path)
        else:
            shutil.copyfile(source_path, target_path)
            nzb.log_info('Copied %s to %s.' % (file, target_path))

        shutil.rmtree(directory)
        nzb.log_info('Deleted directory %s.' % directory)
    else:
        nzb.log_info('Directory %s does not exist.' % directory)

    nzbid = nzb.get_nzb_id()
    hide_nzb(nzbid, target)


def get_largest_file(category, directory, target):
    accepted_files = {}

    for file in os.listdir(directory):
        filepath = os.path.join(directory, file)
        filename, extension = os.path.splitext(file)
        if os.path.isfile(filepath) and extension in MEDIA_EXTENSIONS:
            if target:
                accepted_files[file] = os.path.getsize(filepath)

    accepted_files_by_size = sorted(accepted_files.items(), key=operator.itemgetter(1), reverse=True)
    largest = accepted_files_by_size[0]
    return largest[0]


def hide_nzb(nzbid, finaldir):
    nzb.set_nzb_directory_final(finaldir)
    nzbname = nzb.get_nzb_name()

    proxy = nzb.proxy()
    response = proxy.editqueue('HistoryDelete', 0, '', [int(nzbid)])

    if response:
        nzb.log_info('Marked %s (%s) as hidden.' % (nzbname, nzbid))
    else:
        nzb.log_warning('Failed to mark %s (%s) as hidden.' % (nzbname, nzbid))


def get_category_path(name):
    for category in CATEGORIES:
        if category['key'] == name:
            return category['value']

    return


# Cleanup script
##############################################################################
def clean_up():
    """
    Perform any script cleanup that is required here.
    """
    return


# Main entry-point
##############################################################################
def main():
    """
    We need to check to make sure the script can run in the provided
    environment and that certain status checks have occurred. All of the
    calls here will exit with an exit code if the check fails.
    """
    try:
        # If the script state was set to Disabledm, we don't need to run.
        if SCRIPT_STATE == 'Disabled':
            sys.exit(nzb.PROCESS_SUCCESS)

        # Check version of NZBGet to make sure we can run.
        nzb.check_nzb_version(13.0)

        # Wire up your event handlers before the call.
        # User the form nzb.set_handler(<event>, <function>)
        nzb.set_handler('POST_PROCESSING', on_post_processing)

        # Do not change this line, it checks the current event
        # and executes any event handlers.
        nzb.execute()
    except Exception:
        traceback.print_exc()
        sys.exit(nzb.PROCESS_ERROR)
    finally:
        clean_up()


# Main entry-point
##############################################################################
main()

# NZBGet is weird and doesn't use 0 to signal the successful execution of a
# script, so we use the PROCESS_SUCCESS code here.
sys.exit(nzb.PROCESS_SUCCESS)
