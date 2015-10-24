#!/usr/bin/env python
#
# HealthCheck
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
### NZBGET SCHEDULER/POST-PROCESSING SCRIPT                                ###

# Checks for completion of NZB files that fail due to FAILURE/HEALTH.
#
# When downloading NZB files where the news server has not completed getting
# all articles propagated to the server, NZBGet will be unable to repair the
# archive or the health will be too low. In these cases, NZBGet will set the
# status to FAILURE/HEALTH. This script will wait to requeue and pause the
# NZB until either it is completed or a wait limit has been reached.

##############################################################################
### OPTIONS                                                                ###

# Enable or disable the script from executing (Enabled, Disabled, Debug).
#
# Allows global execution of the script to be disabled without removing the
# script from various events.
#
#ScriptState=Enabled

# Sets the max age of a file before considering it a lost cause (hours).
#
# NOTE: Default is an extremely conservative value.
#
#AgeLimit=12

# Sets the number of times it will attempt to requeue the file before
# giving up (count).
#
#RetryLimit=10

# Sets the amount of time to multiple each retry before trying to unpause
# the file and resume (minutes).
#
# NOTE: The algorithm is based on a push-out timer. The first retry will
# wait 10 (default) minutes. Each subsequent retry will be (X * count);
# so for example, the third retry will wait 30 minutes before resuming.
#
#RetryMinutes=10

### NZBGET SCHEDULER/POST-PROCESSING SCRIPT                                ###
##############################################################################


# Imports
##############################################################################
import datetime
import json
import nzb
import os
import sys
import time
import traceback


# Options
##############################################################################
SCRIPT_STATE=nzb.get_script_option('ScriptState')
SCRIPT_NAME='HealthCheck'
AGE_LIMIT=int(nzb.get_script_option('AgeLimit'))
RETRY_LIMIT=int(nzb.get_script_option('RetryLimit'))
RETRY_MINUTES=int(nzb.get_script_option('RetryMinutes'))


# Handles post-processing of the NZB file.
##############################################################################
def on_post_processing():
    # Create a lock so that the scheduler also doesn't try to run.
    nzb.lock_create(SCRIPT_NAME)

    status = nzb.get_nzb_status()

    if status != 'FAILURE/HEALTH':
        nzb.log_detail('Nothing to do, status was %s.' % status)
        nzb.exit(nzb.PROCESS_SUCCESS)

    try:
        nzbid = nzb.get_nzb_id()
        nzbname = nzb.get_nzb_name()

        nzb.log_detail('Performing health check on %s (%s).' % (nzbname, status))

        check_limit_age(nzbid, nzbname)
        check_limit_retries(nzbid, nzbname)

        # Stop all other post-processing because we need to requeue the file.
        nzb.log_warning('Pausing %s due to status of %s.' % (nzbname, status))
        proxy = nzb.proxy()

        # Pause the file group.
        if not proxy.editqueue('GroupPause', 0, '', [nzbid]):
            reason = 'Failed to pause %s (%s).' % (nzbname, nzbid)
            nzb.exit(nzb.PROCESS_FAIL_PROXY, reason)

        # Send the file back to the queue.
        if not proxy.editqueue('HistoryReturn', 0, '', [nzbid]):
            reason = 'Failed to requeue %s (%s).' % (nzbname, nzbid)
            nzb.exit(nzb.PROCESS_FAIL_PROXY, reason)
    except Exception as e:
        traceback.print_exc()
        nzb.exit(nzb.PROCESS_ERROR, e)
    finally:
        nzb.lock_release(SCRIPT_NAME)
        clean_up()


# Handles scheduled tasks.
##############################################################################
def on_scheduled():
    # Bail out if a lock exists, because post-processing is running.
    if nzb.lock_exists(SCRIPT_NAME):
        nzb.exit(nzb.PROCESS_SUCESS)

    groups = nzb.proxy().listgroups(0)

    for group in groups:
        nzbid = int(group['NZBID'])
        update_filepath = get_update_filepath(nzbid)

        # Look at the next group if we couldn't find it here.
        if not os.path.isfile(update_filepath): 
            continue

        nzb.log_detail('Found state file at %s.' % update_filepath)
        timestamp = int(time.mktime(datetime.datetime.utcnow().timetuple()))
        state = json.load(open(update_filepath, 'r'))
        state_nzbname = state['nzbname']
        state_lastcheck = int(state['lastcheck'])
        state_retries = int(state['retries'])
        wait_minutes = state_retries * RETRY_MINUTES
        elapsed_minutes = (timestamp - state_lastcheck) / 60 / 60

        # If the wait time has elapsed, we need to unpause the file.
        if elapsed_minutes >= wait_minutes:
            nzb.log_detail('Resuming download for %s (%s).' % (state_nzbname, nzbid))
            if not nzb.proxy().editqueue('GroupResume', 0, '', [nzbid]):
                reason = 'Failed to resume %s (%s).' % (state_nzbname, nzbid)
                nzb.exit(nzb.PROCESS_FAIL_PROXY, reason)
        else:
            nzb.log_detail('Waiting for %s minutes, %s minutes elapsed.' % (wait_minutes, elapsed_minutes))


# Checks if the file is likely to already have been propagated.
##############################################################################
def check_limit_age(nzbid, nzbname):
    """
    Checks if the age of the NZB is older than our limit. We assume that
    anything older must be fairly complete and if the health check fails,
    it's because the files are gone.
    """
    nzbage = nzb.get_nzb_age(nzbid)
    nzbage_hours = int(nzbage / 60)
    if nzbage > AGE_LIMIT:
        clean_up()
        reason = 'File %s is %s hours old, but limit was %s.' % (nzbname, nzbage_hours, AGE_LIMIT)
        nzb.exit(nzb.PROCESS_SUCCESS, reason)


# Checks the number of times file was already requeued.
##############################################################################
def check_limit_retries(nzbid, nzbname):
    """
    Checks to see how many retries have already been performed and exits
    if we are the limit.
    """
    # Update the state so we can determine how long we should wait.
    state = update_state(nzbid, nzbname)
    retries = int(state['retries'])
    wait_minutes = retries * RETRY_MINUTES

    # If we already reached the limit, we'll bail.
    if retries >= RETRY_LIMIT:
        clean_up()
        reason = 'Number of retries has been reached (%s) for %s (%s).' % (retries, nzbid, nzbname)
        nzb.exit(nzb.PROCESS_SUCCESS)


# Updates the state of the script to track things like retries.
##############################################################################
def update_state(nzbid, nzbname):
    filepath = get_update_filepath(nzbid)
    timestamp = int(time.mktime(datetime.datetime.utcnow().timetuple()))

    if not os.path.exists(filepath):
        state = { 'nzbid' : nzbid, 'nzbname' : nzbname, 'retries' : 1, 'lastcheck' : timestamp }
    else:
        state = json.load(open(filepath, 'r'))
        retries = int(state['retries'])
        state['retries'] = retries + 1
        state['lastcheck'] = timestamp

    json.dump(state, open(filepath, 'w'))

    return state


# Gets the path to the state file.
##############################################################################
def get_update_filepath(nzbid):
    return nzb.get_script_tempfile(SCRIPT_NAME, 'nzb-%s.state' % nzbid)


# Cleanup script
##############################################################################
def clean_up():
    """
    Perform any script cleanup that is required here.
    """
    nzbid = nzb.get_nzb_id()

    # Remove the state file.
    update_filepath = get_update_filepath(nzbid)
    if os.path.isfile(update_filepath):
        os.remove(update_filepath)

    if SCRIPT_ACTION == 'Debug':
        # Check if the script path has no other files and delete it.
        # NOTE: We can't blindly remove the directory because there might be
        #       other instances waiting for their retries and need the state.
        tempdir = nzb.get_script_tempfolder(SCRIPT_NAME)
        if len(os.path.listdir(tempdir)) == 0:
            os.rmdirs(tempdir)


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

        # Check version of NZBGet to make sure we can run.
        nzb.check_nzb_version(13.0)

        # Wire up your event handlers before the call.
        # Use the form nzb.set_handler(<event>, <function>)
        nzb.set_handler('POST_PROCESSING', on_post_processing)
        nzb.set_handler('SCHEDULED', on_scheduled)

        # Do not change this line, it checks the current event
        # and executes any event handlers.
        nzb.execute()
    except Exception as e:
        traceback.print_exc()
        nzb.exit(nzb.PROCESS_ERROR, e)


# Main entry-point
##############################################################################
main()

# NZBGet is weird and doesn't use 0 to signal the successful execution of a
# script, so we use the PROCESS_SUCCESS code here.
nzb.exit(nzb.PROCESS_SUCCESS)
