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

# Filters environment variables based on prefix.
#
# Comma-separated list of environment prefixes to check.
#EnvironmentPrefix=NZBNA,NZBPR

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
ENVIRONMENT_PREFIXES=nzb.get_script_option('EnvironmentPrefix').split(',')


# Handle no event
##############################################################################
def on_none():
    variables = []

    for key in os.environ.keys():
        for prefix in ENVIRONMENT_PREFIXES:
            if key.startswith(prefix):
                variables.append('%s=%s' % (key, os.environ[key]))

    variables.sort()

    for variable in variables:
        nzb.log_info(variable)


# Handle NZB added
##############################################################################
def on_nzb_added():
    nzb.log_info('on_nzb_added')


# Handle NZB downloaded
##############################################################################
def on_nzb_downloaded():
    nzb.log_info('on_nzb_downloaded')


# Handle file downloaded
##############################################################################
def on_file_downloaded():
    nzb.log_info('on_file_downloaded')


# Handle post processing
##############################################################################
def on_post_processing():
    nzb.log_info('on_post_processing')


# Handle scan
##############################################################################
def on_scan():
    nzb.log_info('on_scan')


# Script entry-point
##############################################################################
def execute():
    """
    Start executing script-specific logic here.
    """
    try:
        event = nzb.get_nzb_event()
        nzb.log_info('EVENT: %s' % event)

        if event == 'NONE':
            # An event with NONE could mean we are in scan or post.
            if 'NZBPR_CNPNZBFILENAME' in os.environ:
                on_post_processing()
            elif 'NZBPR__UNPACK_' in os.environ:
                on_scan()
            else:
                on_none()
        elif event == 'FILE_DOWNLOADED':
            on_file_downloaded()
        elif event == 'NZB_ADDED':
            on_nzb_added()
        elif event == 'NZB_DOWNLOADED':
            on_nzb_downloaded()
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
