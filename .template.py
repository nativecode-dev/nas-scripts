#!/usr/bin/env python
#
# Template Script
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
### NZBGET POST-PROCESSING SCRIPT                                          ###

# Short description of script.
#
# Expanded description of script.
#

##############################################################################
### OPTIONS                                                                ###

# Enable or disable the script from executing (Enabled, Disabled, Debug).
#
# Allows global execution of the script to be disabled without removing the
# script from various events.
#
#ScriptAction=Enabled

### NZBGET POST-PROCESSING SCRIPT                                          ###
##############################################################################


import os
import sys
import base64
import urllib
import urllib2
import traceback

from xmlrpclib import ServerProxy


#############################################################################
# CONSTANTS (Don't change these values)
#############################################################################
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
# get_option
##############################################################################
def get_option(name):
    return os.environ['NZBPO_' + name]


#############################################################################
# get_script_option
#############################################################################
def get_script_option(name):
    return os.environ.get('NZBPR_' + name')


#############################################################################
# set_script_option
#############################################################################
def set_script_option(name, value):
    print('[NZB] NZBPR_' + name + '=' + value)


##############################################################################
# nzbget_command
##############################################################################
def nzbget_command(url_command):
    url = 'http://%s:%s/jsonrpc/%s' % (NZBGET_HOST, NZBGET_PORT, url_command)

    write_debug('[DETAIL] Command: %s.' % url)

    request = urllib2.Request(url)

    auth = base64.encodestring('%s:%s' % (NZBGET_USERNAME, NZBGET_PASSWORD)).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % auth)

    response = urllib2.urlopen(request)

    return response.read()


##############################################################################
# nzbget_proxy
##############################################################################
def nzbget_proxy():
    # Make sure we encode the username and password since it will be used in
    # the url we create.
    username = urllib.quote(NZBGET_USERNAME, safe='')
    password = urllib.quote(NZBGET_PASSWORD, safe='')
    url = 'http://%s:%s@%s:%s/xmlrpc' % (username, password, NZBGET_HOST, NZBGET_PORT)

    write_debug('[DETAIL] Proxy: %s.' % url)

    return ServerProxy(url)


#############################################################################
# check_nzb_environment
#############################################################################
def check_nzb_environment():
    # Check if the script is called from a compatible NZBGet version
    # (as queue-script or as pp-script)
    ArticleCacheDefined = 'NZBOP_ARTICLECACHE' in os.environ
    DirectoryDefined = 'NZBPP_DIRECTORY' in os.environ
    EventDefined = 'NZBNA_EVENT' in os.environ

    # TODO: This seems like a kind of retarded conditional.
    if not (DirectoryDefined or EventDefined) or not ArticleCacheDefined:
        print('[ERROR] *** NZBGet queue script ***')
        print('[ERROR] This script is supposed to be called from nzbget (14.0 or later).')
        sys.exit(PROCESS_FAIL_ENVIRONMENT)


#############################################################################
# check_nzb_status
#############################################################################
def check_nzb_status():
    # If nzb was already marked as bad, don't do any further detection.
    if os.environ.get('NZBPP_STATUS') == 'FAILURE/BAD':
        if os.environ.get('NZBPR_PPSTATUS_ARCHIVE_IGNORE') == 'yes':
            # Print the message again during post-processing to ad it into the
            # post-processing log (which is then used by notification scripts).
            print('[WARNING] Download has ignored files.')
        clean_up()
        sys.exit(PROCESS_SUCCESS)


#############################################################################
# check_nzb_reprocess
#############################################################################
def check_nzb_reprocess():
    # If nzb was reprocessed via the "Post-process again" action, the
    # download might not exist anymore.
    DirectoryDefined = 'NZBPP_DIRECTORY' in os.environ
    DirectoryExists = os.path.exists(os.environ.get('NZBPP_DIRECTORY'))
    if DirectoryDefined and not DirectoryExists:
        print('[WARNING] Destination directory does not exist.')
        clean_up()
        sys.exit(PROCESS_NONE)


#############################################################################
# check_nzb_failed
#############################################################################
def check_nzb_failed():
    # If nzb is already failed, don't do any further actions.
    if os.environ.get('NZBPP_TOTALSTATUS') == 'FAILURE':
        clean_up()
        sys.exit(PROCESS_NONE)


#############################################################################
# is_downloaded
#############################################################################
def is_downloaded():
    # Checks to see if the nzb file is still downloading or has finished.
    return os.environ.get('NZBNA_EVENT') == 'FILE_DOWNLOADED'


#############################################################################
# get_nzb_option
#############################################################################
def get_nzb_option(name):
    # Depending on the mode in which the script was called (queue-script
    # or post-processing-script) a different set of parameters (env. vars)
    # is passed. They also have different prefixes:
    #   - NZBNA_ in queue-script mode;
    #   - NZBPP_ in pp-script mode.
    Prefix='NZBNA_' if 'NZBNA_EVENT' in os.environ else 'NZBPP_'

    return os.environ[Prefix + name]


#############################################################################
# get_nzb_status
#############################################################################
def get_nzb_status():
    return get_nzb_option('STATUS')


#############################################################################
# get_nzb_status_total
#############################################################################
def get_nzb_status_total():
    return get_nzb_option('TOTALSTATUS')


#############################################################################
# write_debug
#############################################################################
def write_debug(message):
    if SCRIPT_DEBUG:
        print(message)


#############################################################################
# clean_up
#############################################################################
def clean_up():
    # Perform any cleanup operations required before exiting the script.
    return


#############################################################################
# main
#############################################################################
def main():
    # If the script is disabled, we need to just return with a success code
    # because the user globally disabled it.
    if SCRIPT_ACTION == 'Disabled':
        sys.exit(PROCESS_SUCCESS)

    check_nzb_environment()
    check_nzb_status()
    check_nzb_reprocess()
    check_nzb_failed()
    # Do your magic!


#############################################################################
# Define NZB options
#############################################################################
NzbCategory = get_nzb_option('CATEGORY')
NzbDirectory = get_nzb_option('DIRECTORY')
NzbFinalDirectory = get_nzb_option('FINALDIR')
NzbId = get_nzb_option('NZBID')
NzbName = get_nzb_option('NZBNAME')
#############################################################################


#############################################################################
# Define options
#############################################################################
SCRIPT_DEBUG=get_option('ScriptAction') == 'Debug'
#############################################################################


#############################################################################
# Execute the main script function.
#############################################################################
main()
#############################################################################


#############################################################################
# Assuming that we make it this far, we didn't encounter any
# errors so we can exit noting a value of success.
#############################################################################
sys.exit(PROCESS_SUCCESS)
#############################################################################
