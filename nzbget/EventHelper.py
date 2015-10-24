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
### NZBGET SCHEDULER/FEED/SCAN/QUEUE/POST-PROCESSING SCRIPT                ###

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
#PrefixFilters=NZBNA,NZBNP,NZBOP,NZBPO,NZBPP,NZBPR

### NZBGET SCHEDULER/FEED/SCAN/QUEUE/POST-PROCESSING SCRIPT                ###
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


# Handle scheduled
##############################################################################
def on_scheduled():
    log_environment()
    return

# Handle NZB added
##############################################################################
def on_nzb_added():
    log_environment()
    return


# Handle NZB downloaded
##############################################################################
def on_nzb_downloaded():
    log_environment()
    return


# Handle file downloaded
##############################################################################
def on_file_downloaded():
    log_environment()
    return


# Handle post processing
##############################################################################
def on_post_processing():
    log_environment()
    return


# Handle queueing
##############################################################################
def on_queueing():
    log_environment()
    return


# Handle scanning
##############################################################################
def on_scanning():
    log_environment()
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

        # Check the version NZBGet we're running on.
        nzb.check_nzb_version(13.0)

        nzb.log_info('CURRENT EVENT: %s' % nzb.get_nzb_event())

        # Wire up your event handlers before the call.
        # User the form nzb.set_handler(<event>, <function>)
        nzb.set_handler('FILE_DOWNLOADED', on_file_downloaded)
        nzb.set_handler('NZB_ADDED', on_nzb_added)
        nzb.set_handler('NZB_DOWNLOADED', on_nzb_downloaded)
        nzb.set_handler('POST_PROCESSING', on_post_processing)
        nzb.set_handler('QUEUEING', on_queueing)
        nzb.set_handler('SCANNING', on_scanning)
        nzb.set_handler('SCHEDULED', on_scheduled)

        # Do not change this line, it checks the current event
        # and executes any event handlers.
        nzb.execute()
    except Exception:
        nzb.exit(nzb.PROCESS_ERROR)

    nzb.exit(nzb.PROCESS_SUCCESS)


# Main entry-point
##############################################################################
main()

# NZBGet is weird and doesn't use 0 to signal the successful execution of a
# script, so we use the PROCESS_SUCCESS code here.
nzb.exit(nzb.PROCESS_SUCCESS)
