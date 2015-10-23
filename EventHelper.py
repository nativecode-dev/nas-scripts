#!/usr/bin/env python
#
# EventHelper
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
### NZBGET FEED/SCAN/QUEUE/POST-PROCESSING SCRIPT                          ###

# Provides output to help with debugging scripts.
#
# Provides some help to determine what environment variables are available
# to scripts at different events.

##############################################################################
### OPTIONS                                                                ###

# Enable or disable the script from executing (Enabled, Disabled, Debug).
#
# Allows global execution of the script to be disabled without removing the
# script from various events.
#
#ScriptState=Enabled

# Enable or disable logging of environment keys (Disabled, Keys, Pairs).
#
# Turns writing to the info log the keys for environment variables.
#ScriptOutput=Disabled

# Filters environment variables based on prefix.
#
# Comma-separated list of environment prefixes to check.
#PrefixFilters=NZBNA,NZBPR,NZBPP

### NZBGET FEED/SCAN/QUEUE/POST-PROCESSING SCRIPT                          ###
##############################################################################


# Imports
##############################################################################
import nzb
import os
import sys
import traceback

# Options
##############################################################################
SCRIPT_STATE=nzb.get_script_option('ScriptState')
SCRIPT_OUTPUT=nzb.get_script_option('ScriptOutput')
PREFIX_FILTERS=nzb.get_script_option('PrefixFilters').strip().split(',')


# Constants
##############################################################################
IGNORED_KEYS=['NZBPR_CnpNZBFileName']


# Handle no event
##############################################################################
def on_none():
    return


# Handle NZB added
##############################################################################
def on_nzb_added():
    return


# Handle NZB downloaded
##############################################################################
def on_nzb_downloaded():
    return


# Handle file downloaded
##############################################################################
def on_file_downloaded():
    return


# Handle post processing
##############################################################################
def on_post_processing():
    return


# Handle scan
##############################################################################
def on_scan():
    return


# Log environment
##############################################################################
def log_environment():
    if SCRIPT_OUTPUT == 'Disabled':
        return
    elif SCRIPT_OUTPUT == 'Keys':
        keys = []

        for key in os.environ.keys():
            if not key_filtered(key):
                for prefix in PREFIX_FILTERS:
                    if key.startswith(prefix):
                        keys.append(key)

        nzb.log_info(' '.join(keys))
    elif SCRIPT_OUTPUT == 'Pairs':
        variables = []

        for key in os.environ.keys():
            if not key_filtered(key):
                for prefix in PREFIX_FILTERS:
                    if key.startswith(prefix):
                        variables.append('%s = %s' % (key, os.environ[key]))

        variables.sort()

        for variable in variables:
            nzb.log_info(variable)


# Determines if environment key is filtered
##############################################################################
def key_filtered(key):
    if key.endswith('_') or key.endswith(':'):
        return True
    elif key in IGNORED_KEYS:
        return True
    else:
        return False


# Script entry-point
##############################################################################
def execute():
    """
    Start executing script-specific logic here.
    """
    try:
        event = nzb.get_nzb_event()

        if event == 'NONE':
            # An event with NONE could mean we are in scan or post.
            if 'NZBPP_NZBID' in os.environ:
                event = 'POST_PROCESSING'
                on_post_processing()
            elif 'NZBPR__UNPACK_' in os.environ:
                event = 'SCAN'
                on_scan()
            else:
                on_none()
        elif event == 'FILE_DOWNLOADED':
            on_file_downloaded()
        elif event == 'NZB_ADDED':
            on_nzb_added()
        elif event == 'NZB_DOWNLOADED':
            on_nzb_downloaded()

        nzb.log_info('EVENT: %s' % event)
        log_environment()
    except Exception:
        nbz.log_error('Something bad happened.')
        clean_up()
        sys.exit(nzb.PROCESS_ERROR)

    sys.exit(nzb.PROCESS_SUCCESS)


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
        # If the script state was set to Disabled, we don't need to run.
        if SCRIPT_STATE == 'Disabled':
            sys.exit(nzb.PROCESS_SUCCESS)

        # Check the version NZBGet we're running on.
        nzb.check_nzb_version(13.0)

        # Call our execute code.
        execute()
    except Exception:
        sys.exit(nzb.PROCESS_ERROR)

    sys.exit(nzb.PROCESS_SUCCESS)


# Main entry-point
##############################################################################
main()

# NZBGet is weird and doesn't use 0 to signal the successful execution of a
# script, so we use the PROCESS_SUCCESS code here.
sys.exit(nzb.PROCESS_SUCCESS)
