#!/usr/bin/env python
#
# <script_name>
#
# Copyright (C) 2015 <name> <<email>>
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

# <description_short>
#
# <description_long>

##############################################################################
### OPTIONS                                                                ###

# Enable or disable the script from executing (Enabled, Disabled, Debug).
#
# Allows global execution of the script to be disabled without removing the
# script from various events.
#
#ScriptState=Enabled

### NZBGET QUEUE/POST-PROCESSING SCRIPT                                    ###
##############################################################################


# Imports
##############################################################################
import nzb
import os
import sys


# Options
##############################################################################
SCRIPT_STATE=nzb.get_script_option('ScriptState')


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


# Handle queuing
##############################################################################
def on_queueing():
    return


# Handle scan
##############################################################################
def on_scan():
    return


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
            if 'NZBPP_NZBNAME' in os.environ:
                on_post_processing()
            elif 'NZBNP_NZBNAME' in os.environ:
                on_scanning()
            elif 'NZBNA_NZBNAME' in os.environ:
                on_queueing()
            else:
                on_none()
        elif event == 'FILE_DOWNLOADED':
            on_file_downloaded()
        elif event == 'NZB_ADDED':
            on_nzb_added()
        elif event == 'NZB_DOWNLOADED':
            on_nzb_downloaded()
    except:
        clean_up()

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
        # If the script state was set to Disabledm, we don't need to run.
        if SCRIPT_STATE == 'Disabled':
            sys.exit(nzb.PROCESS_SUCCESS)

        nzb.check_nzb_version(13.0)

        # nzb.check_nzb_environment()
        # nzb.check_nzb_failed()
        # nzb.check_nzb_reprocess()
        # nzb.check_nzb_status()

        execute()
    except:
        sys.exit(nzb.PROCESS_ERROR)


# Main entry-point
##############################################################################
main()

# NZBGet is weird and doesn't use 0 to signal the successful execution of a
# script, so we use the PROCESS_SUCCESS code here.
sys.exit(nzb.PROCESS_SUCCESS)
