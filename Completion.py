#!/usr/bin/env python
#
# Completion.py script for NZBGet
#
# Copyright (C) 2014, 2015 kloaknet.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
### NZBGET SCAN/QUEUE/SCHEDULER SCRIPT                                     ###

# Verifies that enough articles are available before starting the download.
#
# This script should be added as:
# - Scan script: to pause incoming NZBs.
# - Queue script: to check a newly added and by the script paused NZB, resume 
#   when OK.
# - Scheduler script: to regularly check completeness of by the script paused 
#   NZB in the queue, will resume when OK or mark as BAD after file is X hours 
#   old. 
#
# NOTE: To stop the script when checking, reload NZBget.
#
# Info about the NZBGet Completion.py script:
# Author: kloaknet.
# Support and updates: http://nzbget.net/forum/viewtopic.php?f=8&t=1736.
# Date: Aug 15th, 2015.
# License: GPLv3 (http://www.gnu.org/licenses/gpl.html).
# PP-script Version: 0.2.3.
#
# NOTE: This script requires NZBget 13.0+ and Python 2.7.9+ to be installed on 
# your system.

##############################################################################
### OPTIONS                                                                ###

# NZB max age.
# Max age of the NZB file in hours till the scheduler script stops checking 
# the NZB, moves it to the history and marks it BAD.
# Age limit is also used for the Prioritize option.
#AgeLimit=4

# Prioritize NZBs older than AgeLimit(yes, no).
# NZBs with the highest priority will be checked first. For NZBs with equal 
# priority the oldest NZBs will be checked first. With this option on NO, NZB
# files older than AgeLimit will be the last checked with equal priority.
#Prioritize=no

# Check duplicate NZBs stored in the history(yes, SameScore, no).
# NZBs with the DUPE status in the history will be checked, note that the
# NZBGet option DupeCheck needs to be enabled for this to work. The option 
# SameScore will only check the dupes that have the same DUPE score as the item 
# in the queue. This means that only when the file in the queue is older than 
# AgeLimit and marked BAD, a lower score DUPE could be moved back to the queue.
#CheckDupes=SameScore

# Force FAILURE instead of BAD(yes, no).
# The mark BAD option might not be supported by programs like Sonarr. Therefore
# this option forces a failure, so Sonarr will know that it has to push an
# other nzb, because this one failed.
# NOTE: This option will result in multiple warning messages and at least one
# error from NZBget to force the FAILURE status.
#ForceFailure=no

# Percentage of archive articles to check. 
# A higher percentage will be more accurate, but will increase the duration of 
# the check.
#CheckLimit=25

# Check all archives when no pars(yes,no).
# Force a full check on all the archives articles in the release when no or 
# only 1 par file is included. This to garantee all articles are there and you
# don't waste bandwidth because just 1 article is missing.
#FullCheckNoPars=yes

# Categories to check for completion.
# Comma separated list like 'TV, Movies, etc'. Leave blank for all categories.
#Categories=TV

# Print more info to the log for debugging(yes, no).
#Verbose=no

# Print even more info to the log(yes, no). 
# (e.g. tons of OK NNTP server response messages).
#Extreme=no

### NZBGET SCAN/QUEUE/SCHEDULER SCRIPT                                     ###
##############################################################################

import os
import urllib
import urllib2
import base64
import json
import time
import subprocess
import sys
import socket
import ssl
import inspect
import traceback
import HTMLParser
import errno
import datetime
from threading import Thread
from xmlrpclib import ServerProxy
from os.path import dirname
from operator import itemgetter

# Check if the script is called from nzbget 13.0 or later.
# Queue Script uses 'NZBNA_EVENT, introduced in nzbget 13
if not 'NZBOP_SCANSCRIPT' in os.environ:  # new variable since nzbget 13.0
    print ('[ERROR] This script is supposed to be called from nzbget ', 
        '(13.0 or later), stopping')
    sys.exit(0)
AGE_LIMIT = int(os.environ.get('NZBPO_AgeLimit', 4))
AGE_LIMIT_SEC = 3600 * AGE_LIMIT
PRIORITIZE_OLD = os.environ.get('NZBPO_Prioritize', 'no') == 'yes'
CHECK_DUPES = os.environ.get('NZBPO_CheckDupes', 'no')
if CHECK_DUPES != 'no' and os.environ.get('NZBOP_DUPECHECK') == 'no':
    print ('[WARNING] DupeCheck should be enabled in NZBGet, otherwise ' + 
        'enabling the CheckDupes option of this script that you enabled ' +
        'will not work')
FORCE_FAILURE = os.environ.get('NZBPO_ForceFailure', 'no') == 'yes'
CATEGORIES = os.environ['NZBPO_Categories'].lower().split(',')
CATEGORIES = [c.strip(' ') for c in CATEGORIES] 
VERBOSE = os.environ.get('NZBPO_Verbose', 'yes') == 'yes'  ##
EXTREME = os.environ.get('NZBPO_Extreme', 'yes') == 'yes'  ##
CHECK_LIMIT = int(os.environ.get('NZBPO_CheckLimit', 5))  ##
FULL_CHECK_NO_PARS = os.environ.get('NZBPO_FullCheckNoPars', 'yes') == 'yes'
NNTP_TIME_OUT = 2  # low, but should be sufficient for connection check
HOST = os.environ['NZBOP_CONTROLIP']  # NZBget host
if HOST == '0.0.0.0':
    HOST = '127.0.0.1'  # fix to local
PORT = os.environ['NZBOP_CONTROLPORT']  # NZBget port
USERNAME = os.environ['NZBOP_CONTROLUSERNAME']  # NZBget username
PASSWORD = urllib.quote(os.environ['NZBOP_CONTROLPASSWORD'], safe='')  # NZBget password

#if EXTREME:
#    print '[E] AGE_LIMIT: ' + str(AGE_LIMIT)
#    print '[E] PRIORITIZE_OLD: ' + str(PRIORITIZE_OLD)
#    print '[E] CHECK_DUPES: ' + str(CHECK_DUPES)
#    print '[E] FORCE_FAILURE: ' + str(FORCE_FAILURE)
#    print '[E] CHECK_LIMIT: ' + str(CHECK_LIMIT)
#    print '[E] FULL_CHECK_NO_PARS: ' + str(FULL_CHECK_NO_PARS)
#    print '[E] CATEGORIES: ' + str(CATEGORIES)
#    print '[E] VERBOSE: ' + str(VERBOSE)
#    print '[E] EXTREME: ' + str(EXTREME)

def unpause_nzb(nzb_id):
    '''
        resume the nzb with NZBid in the NZBGet queue via RPC-API
        '''
    NZBget = connect_to_nzbget()
    NZBget.editqueue('GroupResume', 0, '', [int(nzb_id)])  # Resume nzb
    NZBget.editqueue('GroupPauseExtraPars', 0, '', [int(nzb_id)])  # Pause pars

def unpause_nzb_dupe(dupe_nzb_id, nzb_id):
    '''
        resume the nzb with NZBid in the NZBGet history via RPC-API, move the 
        other one to history.
        '''
    NZBget = connect_to_nzbget()
    # Return item from history (before deleting, to avoid NZBget automatically
    # returning a DUPE instead of the script).
    NZBget.editqueue('HistoryRedownload', 0, '', [int(dupe_nzb_id)])  # Return 
    NZBget.editqueue('GroupResume', 0, '', [int(dupe_nzb_id)])  # Resume nzb
    # Pause pars
    NZBget.editqueue('GroupPauseExtraPars', 0, '', [int(dupe_nzb_id)])
    # Remove item in queue, send back to history as DUPE
    NZBget.editqueue('GroupDupeDelete', 0, '', [int(nzb_id)])

def mark_bad(nzb_id):
    '''
        mark the nzb with NZBid BAD in the NZBGet queue via RPC-API
        '''
    NZBget = connect_to_nzbget()
    NZBget.editqueue('GroupDelete', 0, '', [int(nzb_id)])  # need to delete
    NZBget.editqueue('HistoryMarkBad', 0, '', [int(nzb_id)])  # mark bad

def mark_bad_dupe(dupe_nzb_id):
    '''
        mark the nzb with NZBid BAD in the NZBGet history via RPC-API, item is
        already in history, so no moving.
        '''
    NZBget = connect_to_nzbget()
    NZBget.editqueue('HistoryMarkBad', 0, '', [int(dupe_nzb_id)])  # mark bad

def force_failure(nzb_id):
    '''
        mark BAD doesn't do the trick for FailureLink, Sonarr, SickBeard
        Forces failure, removes all files but one .par2
        sending deleted nzb back to queue will restore the deleted files.
        TODO: replace temp variable etc, and sent a missing article to the 
            queue
        '''
    if VERBOSE:
        print '[V] force_failure(nzb_id=' + str(nzb_id) + ')'
    NZBget = connect_to_nzbget()
    data = NZBget.listfiles(0, 0, [int(nzb_id)])
    id_list = []
    file_size_prev = 100000000000  # 100 Gb, file size will never occur.
    id_prev = -1
    temp = 1
    for f in data:
        file_name = f.get('Filename')
        file_paused = f.get('Paused')
        id = int(f.get('ID'))
        if file_name.find('.par2') == -1:
            # not a .par2 file, list for deletion
            if temp != 1:
                #let the first rar pass, temp
                id_list.append(id)
            else:
                temp += 1
        else:
            # .par2 file, search for smallest file
            file_size_lo = f.get('FileSizeLo')
            # checking for smallest par2 file to minimize download
            if file_size_lo > file_size_prev:
                # not the smallest .par2 file, list for deletion
                id_list.append(id)
            else:
                # maybe the smallest .par2 file, store ID, redefine prev
                if id_prev != -1:
                    # list id_prev for deletion
                    id_list.append(id_prev)
                    id_prev = id
                else:
                    # first occurrence
                    id_prev = id
                file_size_prev = file_size_lo
    if id_prev == -1: 
        # no par files in this release
            # leave last file intact to avoid deleted status
                # id_list.pop()
        print id_list
        NZBget.editqueue('FileDelete', 0, '', id_list)
        print '[WARNING] Forcing failure of release:'
        sys.stdout.flush()
    else:
    # at least 1 par file in release
        print '[WARNING] Forcing failure of release:'
        sys.stdout.flush()
        
        NZBget.editqueue('FileDelete', 0, '', id_list)
    # Resume nzb in queue
    NZBget.editqueue('GroupResume', 0, '', nzb_id)

def force_failure_dupe(dupe_nzb_id):
    '''
        mark BAD doesn't do the trick for FailureLink, Sonarr, SickBeard
        Forces failure, removes all files but one .par2
        sending deleted nzb back to queue will restore the deleted files.
        although no dupes are expected from Sonarr and the likes, maybe a RSS
        feed for movies or other stuff is used that might produce dupes.
        '''
    print 'force failure dupe' #
    NZBget = connect_to_nzbget()
    if VERBOSE:
        print '[V] pause files before returning to queue' 
    # pause all files before returning to queue
    NZBget.editqueue('GroupPause', 0, '', dupe_nzb_id)
    if VERBOSE:
        print '[V] returning nzb to queue' 
    # return item back to queue to be able to force a failure
    NZBget.editqueue('HistoryReturn', 0, '', dupe_nzb_id)
    data = NZBget.listfiles(0, 0, [int(dupe_nzb_id)])
    id_list = []
    file_size_prev = 100000000000  # 100 Gb, file size will never occur.
    id_prev = -1
    for f in data:
        file_name = f.get('Filename')
        file_paused = f.get('Paused')
        id = int(f.get('ID'))
        if file_name.find('.par2') == -1:
            # not a .par2 file, list for deletion
            if temp != 1:       ##
                #let the first rar pass, temp
                id_list.append(id)
            else:
                temp += 1
        else:
            # .par2 file, search for smallest file
            file_size_lo = f.get('FileSizeLo')
            # checking for smallest par2 file to minimize download
            if file_size_lo > file_size_prev:
                # not the smallest .par2 file, list for deletion
                id_list.append(id)
            else:
                # maybe the smallest .par2 file, store ID, redefine prev
                if id_prev != -1:
                    # list id_prev for deletion
                    id_list.append(id_prev)
                    id_prev = id
                else:
                    # first occurrence
                    id_prev = id
                file_size_prev = file_size_lo
    if id_prev == -1:
        # no par files in this release
        # leave last file intact to avoid deleted status
            #id_list.pop()
        print '[WARNING] Forcing failure of release, leaving 1 rar intact:'
        NZBget.editqueue('FileDelete', 0, '', id_list)
        sys.stdout.flush()
    else:
    # at least 1 par file in release
        print '[WARNING] Forcing failure of release:'
        sys.stdout.flush()
        NZBget.editqueue('FileDelete', 0, '', id_list)
    # Resume nzb in queue
    NZBget.editqueue('GroupResume', 0, '', dupe_nzb_id)

def connect_to_nzbget():
    '''
        Establish connection to NZBGet via RPC-API using HTTP.
        '''
    # Build an URL for XML-RPC requests:
    xmlRpcUrl = 'http://%s:%s@%s:%s/xmlrpc' % (USERNAME, PASSWORD, HOST, PORT)
    # Create remote server object
    nzbget = ServerProxy(xmlRpcUrl)
    return nzbget

def call_nzbget_direct(url_command):
    '''
        Connect to NZBGet and call an RPC-API-method without using of python's 
        XML-RPC. XML-RPC is easy to use but it is slow for large amounts of 
        data.
        '''
    # Building http-URL to call the method
    http_url = 'http://%s:%s/jsonrpc/%s' % (HOST, PORT, url_command)
    request = urllib2.Request(http_url)
    base_64_string = base64.encodestring('%s:%s' % (USERNAME, 
        PASSWORD)).replace('\n','')
    request.add_header("Authorization", "Basic %s" % base_64_string)
    response = urllib2.urlopen(request)  # get some data from NZBGet
    # data is a JSON raw-string, contains ALL properties each NZB in queue
    data = response.read()
    return data

def get_nzb_filename(parameters):
    '''
        get the real nzb_filename from the added parameter CnpNZBFileName
        '''
    # extracting filename from job the hard way
    s = str(parameters)
    loc = s.rfind("u'CnpNZBFileName', u'Value': u'")
    s = s[loc+31:]
    loc = s.find("'}")
    return s[:loc]

def get_nzb_status(nzb):
    ''' 
        check if amount of failed articles is not too much. If too much keep
        paused, if too old and too much failure mark bad / force failure,
        otherwise resume. When an -1 or -2 is returned from check_nzb(), the 
        nzb is unpaused, hoping NZBget can still process the file, while the 
        script can't.
        '''
    if VERBOSE:
        print '[V] get_nzb_status(nzb=' + str(nzb) + ')'
    print 'Checking: "' + nzb[1] + '"'
    # collect rar msg ids that need to be checked
    rar_msg_ids = get_nzb_data(os.environ['NZBOP_NZBDIR'] + os.sep + nzb[1])
    if rar_msg_ids == -1:  # no such NZB file
        succes = True  # file send back to queue
        if VERBOSE:
            print '[WARNING] [V] No such NZB file, resuming NZB'
        unpause_nzb(nzb[0])  # unpause based on NZBget ID
    elif rar_msg_ids == -2:  # empty NZB or no group
        succes = True  # file send back to queue
        if VERBOSE:
            print '[WARNING] [V] NZB appears invalid, resuming NZB'
        unpause_nzb(nzb[0])  # unpause based on NZBget ID
    else:
        failed_limit = 100 - nzb[3] / 10.0
        print '[V] Maximum failed articles limit: ' + str(failed_limit) + '%'
        failed_ratio = check_failure_status(rar_msg_ids, failed_limit)
        if VERBOSE:
            print '[V] Total failed ratio: ' + str(round(failed_ratio,1)) + '%'
        if failed_ratio < failed_limit or failed_ratio == 0:
            succes = True
            print 'Resuming: "' + nzb[1] + '"'
            sys.stdout.flush()
            unpause_nzb(nzb[0])  # unpause based on NZBget ID
        elif (failed_ratio >= failed_limit and 
            nzb[2] < (int(time.time()) - int(AGE_LIMIT_SEC))):
            succes = False
            if VERBOSE:
                if not FORCE_FAILURE:
                    print '[V] Marked as bad: "' + nzb[1] + '"'
                else:
                    print '[V] Forcing failure of: "' + nzb[1] + '"'
                sys.stdout.flush()  # otherwise NZBGet sends message first
                
            if FORCE_FAILURE:
                force_failure(nzb[0])  #
            else:
                mark_bad(nzb[0])
        else:
            succes = False
            # dupekey should not be '', that would mean it is not added by RSS
            if CHECK_DUPES != 'no' and nzb[4] != '':
                if get_dupe_nzb_status(nzb):
                    print ('"' + nzb[1] + '" moved to history as DUPE, ' + 
                        'complete DUPE returned to queue.')
                else:
                    print ('[WARNING]"' + nzb[1] + 
                        '", remains paused for next check, ' + 
                        'no suitable/complete DUPEs found in history')
            elif CHECK_DUPES != 'no' and nzb[4] == '' and VERBOSE:
                print ('[V] ' + nzb[1] + ' is not added via RSS, therefore ' + 
                'the dupekey is empty and checking for DUPEs in the history ' +
                'is skipped.')
    return succes 

def get_dupe_nzb_status(nzb):
    '''
        check dupes in the history on their possible completion when the item
        in the queue is not yet complete. When complete DUPE item, move it 
        back into the queue, and move the otherone to history.
        '''
    if VERBOSE:
        print '[V] get_dupe_nzb_status(nzb=' + str(nzb) + ')'
    # get the data from the active history
    data = call_nzbget_direct('history')
    jobs = json.loads(data)
    duplicate = False
    num_duplicates = 0
    list_duplicates = []
    for job in jobs['result']:
        if (job['Status'] == 'DELETED/DUPE' and job['DupeKey'] == nzb[4] and
            'CnpNZBFileName' in str(job)):
            if CHECK_DUPES == 'yes':
                duplicate = True
                num_duplicates += 1
                list_duplicates.append(job)
            elif CHECK_DUPES == 'SameScore' and job['DupeScore'] == nzb[5]:
                duplicate = True
                num_duplicates += 1
                list_duplicates.append(job)
            else:
                print 'different dupescore?'  #
    if duplicate and VERBOSE:
        print ('[V] ' + str(num_duplicates) +  ' duplicate of ' + 
            nzb[1] + ' found in history')
        # sort on nzb age, then on dupescore. Higher score items will be on 
        # top. Oldest file has lowest maxposttime
        t = sorted(list_duplicates, key=itemgetter('MaxPostTime'))
        sorted_duplicates = (sorted(t, key=itemgetter('DupeScore'), 
            reverse=True))
        i = 0
        # loop through all DUPE items (with optional matching DUPEscore)
        for job in sorted_duplicates:
            i += 1
            nzb_id = job['NZBID']
            nzb_filename = get_nzb_filename(job['Parameters'])
            nzb_age = job['MaxPostTime']  # nzb age
            nzb_critical_health = job['CriticalHealth']
            print ('Checking DUPE: "' + nzb_filename + '" [' + str(i) + '/' + 
                str(num_duplicates) + ']')

            rar_msg_ids = get_nzb_data(os.environ['NZBOP_NZBDIR'] + os.sep + 
                nzb_filename)
            if failed_ratio == -1:  # no such NZB file
                success = False  # file marked BAD
                if VERBOSE:
                    print '[WARNING] [V] No such DUPE NZB file, marking BAD'
                if FORCE_FAILURE:
                    force_failure_dupe(nzb_id)  #
                else:
                    mark_bad_dupe(nzb_id)
            elif failed_ratio == -2:  # empty NZB or no group
                success = False  # file marked BAD
                if VERBOSE:
                    print '[WARNING] [V] DUPE NZB appears invalid, marking BAD'
                if FORCE_FAILURE:
                    force_failure_dupe(nzb_id)  #
                else:
                    mark_bad_dupe(nzb_id)
            else: ##
                failed_limit = 100 - nzb_critical_health / 10.0
                print ('[V] Maximum failed articles limit: ' + 
                    str(failed_limit) + '%')
                failed_ratio = check_failure_status(rar_msg_ids, failed_limit)
                if VERBOSE:
                    print ('[V] Total failed ratio: ' + 
                        str(round(failed_ratio,1)) + '%')
                if failed_ratio < failed_limit or failed_ratio == 0:
                    success = True
                    print 'Resuming DUPE: "' + nzb_filename + '"'
                    sys.stdout.flush()
                    unpause_nzb_dupe(nzb_id, nzb[0])  # resume on NZBget ID
                    break
                elif (failed_ratio >= failed_limit and 
                    nzb_age < (int(time.time()) - int(AGE_LIMIT_SEC))):
                    success = False
                    if VERBOSE:
                        if not FORCE_FAILURE:
                            print '[V] Marked as bad: "' + nzb[1] + '"'
                        else:
                            print '[V] Forcing failure of: "' + nzb[1] + '"'
                        sys.stdout.flush()
                    if FORCE_FAILURE:
                        force_failure_dupe(nzb_id)
                    else:
                        mark_bad_dupe(nzb_id)
                else:
                    success = False
    elif VERBOSE:
        print '[V] No duplicates of ' + nzb[1] + ' found in history'
        success = False
    return success

def is_number(s):
    '''
        Checks if the string can be converted to a number
        '''
#    if VERBOSE:
#        print '[V] is_number(s= ' + str(s) + ' )'
    try:
        float(s)
        return True
    except ValueError:
        return False

def check_send_server_reply(sock, t, group, id, i, host, username, password):
    '''
        Check NNTP server messages, send data for next recv.
        After connecting, there will be a 200 message, after each message, a 
        reply (t) will be send to get a next message.
    
        More info on NNTP server responses:
        The first digit of the response broadly indicates the success,
        failure, or progress of the previous command:
           1xx - Informative message
           2xx - Command completed OK
           3xx - Command OK so far; send the rest of it
           4xx - Command was syntactically correct but failed for some reason
           5xx - Command unknown, unsupported, unavailable, or syntax error
        The next digit in the code indicates the function response category:
           x0x - Connection, setup, and miscellaneous messages
           x1x - Newsgroup selection
           x2x - Article selection
           x3x - Distribution functions
           x4x - Posting
           x8x - Reserved for authentication and privacy extensions
           x9x - Reserved for private use (non-standard extensions
        '''
    global logged_in  ## also defined in other def!! can it be removed here?
    global entered_group  ## also defined in other def!!
#    if EXTREME:
#        print ('[E] check_send_server_reply(sock= ' + str(sock) + ', t= ' + str(t) +
#            ' ,group= ' + str(group) + ' , id= ' + str(id) + ' , i= ' + 
#            str(i) + ' )')
    try:
        id_used = False  # is id used via HEAD / STAT request to NNTP server
        msg_id_used = None
        error = False
        server_reply = t[:3] # only first 3 chars are relevant
        # no correct NNTP server code received, most likely still propagating?
        if not is_number(server_reply):
            if VERBOSE:
                print ('[WARNING] [V] Socket: ' + str(i) + ' ' + str(host) +
                    ', NNTP reply incorrect:' + str(t.split()))
            server_reply = 'NNTP reply incorrect'
            error = True  # pass these vars so that next article will be sent
            id_used = True  # pass these vars so that next article will be sent
            return (error, id_used, server_reply, msg_id_used)
        # checking NNTP server server_replies
        if server_reply in ('411', '412', '420', '423', '430'):
            # 411 no such group
            # 412 no newsgroup has been selected
            # 420 no current article has been selected
            # 423 no such article number in this group
            # 430 no such article found
            if VERBOSE:
                print ('[WARNING] [V] Socket: ' + str(i) + ' ' + str(host) +
                    ', NNTP reply: ' + str(t.split()))
                sys.stdout.flush()
            error = True  # article is not there
        elif server_reply in ('220', '221', '222', '223'):
            # 220 article retrieved - head and body follow
            # 221 article retrieved - head follows (reply on HEAD)
            # 222 article retrieved - body follows
            # 223 article retrieved - request text separately (reply on STAT)
            msg_id_used = t.split()[2][1:-1]  # get msg id to identify ok article
            if EXTREME:
                print ('[E] Socket: ' + str(i) + ' ' + str(host) + 
                    ', NNTP reply: ' + str(t.split()))
        elif server_reply in ('200', '201'):
            # 200 service available, posting permitted
            # 201 service available, posting prohibited
            if EXTREME:
                print ('[INFO] [E] Socket: ' + str(i) + ' ' + str(host) + 
                    ', NNTP reply: ' + str(t.split()))
            # Sending username:
            text = 'AUTHINFO USER %s\r\n' % (username)
            if EXTREME:
                print ('[E] Socket: ' + str(i) + ' ' + str(host) + ', Send: ' + 
                    str(text))
                sys.stdout.flush()
            sock.send(text)
        elif server_reply in ('381'):
            # 381 Password required
            text = 'AUTHINFO PASS %s\r\n' % (password)
            if EXTREME:
                print ('[E] Socket: ' + str(i) + ' ' + str(host) + 
                    ', NNTP reply: ' + str(t.split()))
                print ('[E] Socket: ' + str(i) + ' ' + str(host) + ', Send: ' + 
                    str(text))
                sys.stdout.flush()
            sock.send(text)
        elif server_reply in ('281'):
            # 281 Authentication accepted
            if EXTREME:
                print ('[E] Socket: ' + str(i) + ' ' + str(host) + 
                    ', NNTP reply: ' + str(t.split()))
            logged_in[i] = True
        elif server_reply in ('211'):
            # 211 group selected (group)
            # joined_group[i] = t.split()[4]
            if EXTREME:
                print ('[INFO] [E] Socket: ' + str(i) + ' ' + str(host) + 
                    ', NNTP reply: ' + str(t.split()))
            entered_group[i] = True
        elif server_reply[:2] in ('48'):
            # 48X incorrect news server account settings
            print ('[ERROR] Socket: ' + str(i) + ' ' + str(host) +
                ', Incorrect news server account settings: ' + str(t) + 'Exit')
            sys.exit(94)
        else:
            if VERBOSE:
                print ('[WARNING] [V] Socket: ' + str(i) + ' ' + str(host) +
                    ', Not covered NNTP server reply code: ' + str(t.split()))
        if logged_in[i] == True and entered_group[i] == False: # and join_group[i] == True
            text = 'group ' + group + '\r\n'
            if EXTREME:
                print ('[E] Socket: ' + str(i) + ' ' + str(host) + ', Send: ' + 
                    str(text))
                sys.stdout.flush()
            sock.send(text)
        # end_loop is used to not send a stat msg when receiving last replies
        if entered_group[i] == True and end_loop == False: # or join_group[i] == False
            text = 'STAT <' + id + '>\r\n'
            id_used = True
            if EXTREME:
                print ('[E] Socket: ' + str(i) + ' ' + str(host) + ', Send: ' + 
                    str(text))
                sys.stdout.flush()
            sock.send(text)
        return (error, id_used, server_reply, msg_id_used)
    except:
        print ('Exception LINE: ' + 
            str(traceback.tb_lineno(sys.exc_info()[2])) + ': ' +
            str(sys.exc_info()[1]))
        return (False, False, server_reply, -1)

def fix_nzb(nzb_lines):
    '''
        some nzbs may contain all data on 1 single line, to handle this 
        correctly in check_nzb(), the single line is splitted on the >< mark
        '''
    if VERBOSE:
        print '[V] fix_nzb(nzb_lines=' + str(nzb_lines) + ')'
        print '[V] Repairing data in NZB'
        sys.stdout.flush()
    nzb_lines = str(nzb_lines)
    positions = [n for n in xrange(len(nzb_lines)) 
        if nzb_lines.find('><', n) == n]
    first = 0
    last = 0
    corrected_lines = []
    for n in positions:
        last = n + 1
        corrected_lines.append(nzb_lines[first:last])
        first = last
    if VERBOSE:
        print '[V] Data in NZB repaired'
    return corrected_lines

def get_nzb_data(fname):
    '''
        extract the nzb info from the NZB file, and return data set of articles
        to be checked
        '''
    if VERBOSE:
        print '[V] get_nzb_data(fname=' + str(fname) + ')'
    try:  # check if NZB exists
        fd = open(fname)
        lines = fd.readlines()
        fd.close()
    except:
        print '[ERROR] no such nzb file'
        return -1
    if len(lines) == 1:  # single line NZB
        lines = fix_nzb(lines)
    all_msg_ids = []  # list of message ids for NNTP server
    group = None
    # maybe read from bottom towards top, so that the subject will be the 
    # last line of the file, so the num of articles can be stored with 
    # the subject?
    for line in lines:
        if line.lower().find('<file') != -1:  # look for par2 files
            if line.lower().find('.par2') != -1:
                par = 1  # found a par file, next msg_ids of par2s
            else:
                par = 0  # not a par file, next msg ids of files
        if line.lower().find('subject="') != -1:  # look for subject
            ##CouldDo:
            # each file has its own subject, needed for matching bad 
            # segments with file in NZBget for successfull ForceFailure
            # without wasting some 100 Mb.
            subject = line.split('subject="')[1].split('">')[0]
            subject = HTMLParser.HTMLParser().unescape(subject)
#                print 'subject=' + subject
        if line.lower().find('<groups>') != -1:
            # Start of list of groups found, clear possible previous group
            groups = []
        if line.lower().find('<group>') != -1:  # look for group name
            group = line.split('>')[1].split('<')[0]
            groups.append(group) # store all groups per file
        if line.lower().find('<segment bytes') != -1:  # look for msg ids
            message_id = line.split('>')[1].split('<')[0]
            message_id = HTMLParser.HTMLParser().unescape(message_id)
            ok = -1
            all_msg_ids.append([subject, par, groups, message_id, ok])
            #ok 0 = not checked/ 1,2,3,4, ok for each server num, -1 failed
            # Could Do:
            # subject included for each article, filter on subject, count
            # num of articles in file, compare with num of failed articles
            # so that the one with 1 - ratio of failures times size will give
            # the smallest file to download for force failure option.
    if not group or len(all_msg_ids) == 0:
        print '[ERROR] empty nzb or no group'
        return -2
    rar_msg_ids = []
    par_msg_ids = []
    for msg_id in all_msg_ids:  # split par2 from other files  ##2
        if msg_id[1] == 0:
            # print msg_id
            rar_msg_ids.append(msg_id)
        else:
            par_msg_ids.append(msg_id)
    all_articles = len(all_msg_ids)
    rar_articles = len(rar_msg_ids)
    par_articles = len(par_msg_ids)
    # check if more than 1 pars are available or not.
    if FULL_CHECK_NO_PARS and par_articles < 1:
        each = 1  # check each article
        if VERBOSE:
            print ('[V] No par files in release, all articles will be ' + 
                'checked')
    elif FULL_CHECK_NO_PARS and par_articles == 1:
        each = 1  # check each article
        if VERBOSE:
            print ('[V] 1 par file in release, all articles will be ' + 
                'checked')
    else:
        each = int(100 / CHECK_LIMIT)  # check each Xth article only
    t = rar_msg_ids[::each]
    rar_msg_ids = t
    articles_to_check = len(rar_msg_ids)
    if VERBOSE:
        print ('[V] NZB contains ' + str(all_articles) + ' articles, ' +
            str(rar_articles) + ' rar articles, ' + str(par_articles) +
            ' par2 articles')
        print '[V] ' + str(articles_to_check) + ' articles will be checked'
    return rar_msg_ids

def get_server_settings():
    '''
        Get the settings for all the active news-servers in NZBGet, and store
        them in a list. Filter out all but 1 server in same group.
        '''
    # get news server settings for each server
    NZBget = connect_to_nzbget()
    nzbget_status = NZBget.status()
    servers_status = nzbget_status['NewsServers']
    servers = []
    i = 0
    for server_status in servers_status:
        # Use only enabled servers in NZBget
        if server_status['Active'] == True:
            s = str(server_status['ID'])
            level = os.environ['NZBOP_Server' + s + '.Level']            # 0
            group = os.environ['NZBOP_Server' + s + '.Group']            # 1
            host = os.environ['NZBOP_Server' + s + '.Host']              # 2
            port = os.environ['NZBOP_Server' + s + '.Port']              # 3
            username = os.environ['NZBOP_Server' + s + '.Username']      # 4
            password = os.environ['NZBOP_Server' + s + '.Password']      # 5
            encryption = (os.environ['NZBOP_Server' + s + '.Encryption'] == 
                'yes')                                                   # 6
            connections = os.environ['NZBOP_Server' + s + '.Connections']# 7
            servers.append([level, group, host, port, username, password,
                encryption, connections])
    if VERBOSE:
        print ('[V] all active news servers BEFORE filtering on NZBGet ' + 
            'ServerX.Group: ' + str(servers))
    # sort on groups, followed by lvl, so that all identical group numbers > 0
    # can be removed
    servers.sort(key=itemgetter(1,0))
    a = None
    c = []
    # remove all identical groups from server:
    for server in servers:
        b = int(server[1])
        # only allow 1 server per group
        if a != b:
            c.append(server)
        # garantee that all group 0 (no group) servers remain
        if b > 0:
            a = b
    servers = c
    if VERBOSE:
        print ('[V] all active news servers AFTER filtering on NZBGet ' + 
            'ServerX.Group: ' + str(servers))
    return servers

def create_sockets(servers):
    '''
        create the sockets that will be used to send in 
        check_send_server_reply() and receive in check_failure_status()
        server dependent sockets, ssl / non ssl
        '''
    tot_num_conn = 0
    # get total number of connections
    for server in servers:
        tot_num_conn = tot_num_conn + int(server[7])
    global logged_in  # connections status
    global entered_group  # connections status
    logged_in = [False] * tot_num_conn
    entered_group = [False] * tot_num_conn
    sockets = [None] * tot_num_conn  ## all connections!
    start_sock = 0  # counting already created sockets
    server_no = -1
    conn_err = [0] * len(servers)
    for server in servers:
        server_no += 1
        host = server[2]
        port = int(server[3])
        username = server[4]
        password = server[5]
        encryption = server[6]  # ssl
        num_conn = int(server[7])
        end_sock = start_sock + num_conn
        try:
            # create connections
            if encryption:
                # SSL
                if VERBOSE:
                    print '[V] Using SSL connection for server: ' + host
                # build ssl socket, but without certificate requirement
                context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
                context.verify_mode = ssl.CERT_NONE 
                context.options |= ssl.OP_NO_SSLv2 
                context.options |= ssl.OP_NO_SSLv3
                for i in range(start_sock, end_sock):
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sockets[i] = context.wrap_socket(s)
            else:
                # Non SSL
                if VERBOSE:
                    print '[V] Using Non SSL connection for server: ' + host
                for i in range(start_sock, end_sock):
                    sockets[i] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            for i in range(start_sock, end_sock):
                # set timeout for trying to connect (e.g. wrong port config)
                sockets[i].settimeout(NNTP_TIME_OUT)
                try:
                    sockets[i].connect((host, port))
                    # remove time out, so socket is closed after complete message
                    sockets[i].settimeout(0)
                except Exception, e:
                    print ('[ERROR] ' + str(e) + 
                        ', check host and port settings for server ' + host )
                    conn_err[server_no] += 1
                    continue
            start_sock = start_sock + num_conn
            if conn_err[server_no] >= num_conn:
                print ('[ERROR] All connections for server ' + host +
                    ' failed')
                for i in range(start_sock, end_sock):
                    sockets[i].shutdown(2)
                    sockets[i].close()
                #sys.exit(94)
        except SystemExit:  # stop script when all connections fail
            print 'stopping script bla'
            nzbget_resume()
            del_lock_file()
            sys.exit(94)
        except:
            print ('Exception LINE: ' + 
                str(traceback.tb_lineno(sys.exc_info()[2])) + ': ' +
                str(sys.exc_info()[1]))
    return sockets, conn_err

def check_failure_status(rar_msg_ids, failed_limit):
    '''
        Get the failed_ratio for each news server, if n th server failed_ratio
        below failed_limit, return ok failure ratio for resuming
        '''
    if EXTREME:
        print('[E] check_failure_status(rar_msg_ids=' + str(rar_msg_ids) + 
            ', failed_limit=' + str(failed_limit) + ')')
    articles_to_check = len(rar_msg_ids)
    # message on each 25 %
    message_on = ([0, int(articles_to_check * failed_limit * 0.01),
        int(articles_to_check * 0.25), int(articles_to_check * 0.50), 
        int(articles_to_check * 0.75), int(articles_to_check)])
    servers = get_server_settings()  # get news server provider settings
    # build the (non) ssl sockets per server
    (sockets, conn_err) = create_sockets(servers)
    num_server = 0
    end_sock = 0  # counting already created sockets
    global end_loop
    # looping through servers, until limited failure
    for server in servers:
        host = server[2]
        username = server[4]
        password = server[5]
        num_conn = int(server[7])
        start_sock = end_sock
        end_sock = start_sock + num_conn
        failed_ratio = 0
        failed_articles = 0
        send_articles = 0
        end_loop = False
        if conn_err[num_server] >= num_conn:
            print '[WARNING] Skipping server: ' + host
            num_server += 1
            continue
        num_server += 1
        print 'Using server: ' + host
        # loop through all rar_msg_ids, check each one if available
        # if to much failed for server, skip check and move to next
        # send_articles has range 0 to x-1, while articles to check = x
        while (send_articles < articles_to_check and 
                (failed_ratio < failed_limit or failed_ratio == 0)):
            # check each connection for data receive
            for i in range(start_sock, end_sock):
                reply = None
                # break looping through sockets when already finished
                if send_articles >= articles_to_check:
                    break
                try:
                    reply = sockets[i].recv(4096)
                except:
                    # when nothing received wait 200 ms for each complete loop
                    # avoiding continuous looping on fast machines
                    time.sleep(0.20 / num_conn) 
                    if EXTREME:
                        print ('[E] Slow reply from server, waiting ' + 
                            str(200 / num_conn) + ' ms to avoid looping')
                            
                    continue  # reply will be empty string when error
                if  reply != None and rar_msg_ids[send_articles][4] > -1:
                    # loop over ok articles on previous servers
                    while (send_articles < articles_to_check and 
                            rar_msg_ids[send_articles][4] > -1):
                        if EXTREME:
                            print ('[E] Article already checked and ' + 
                                'available on server ' + 
                                servers[rar_msg_ids[send_articles][4]-1][2] )
                        send_articles += 1
                # msg received, and msg not checked/ok yet, and not all 
                # articles send:
                if reply != None and rar_msg_ids[send_articles][4] == -1:
                    id = rar_msg_ids[send_articles][3]
                    groups = rar_msg_ids[send_articles][2]
                    group = groups[0] 
                 ## current socket group needs to be checked for each article 
                 ## call otherwise set entered_group[i] = False, groups don't 
                 ## work atm
                    (error, id_used, server_reply, msg_id_used) = \
                        check_send_server_reply(sockets[i], reply, group, id, 
                        i, host, username, password)  ##
                    if id_used and error:
                        # ID of missing article is not returned by server
                        failed_articles += 1
                    # found ok article on server, store success:
                    if id_used and not error and server_reply == '223':
                        # find row index for successfully send article 
                        # (with reply)
                        for j, rar_msg_id in enumerate(rar_msg_ids):
                            if msg_id_used == rar_msg_id[3]:
                                # store success serv num
                                rar_msg_ids[j][4] = num_server
                                break
                    if id_used:  # avoids removing ids send before AUTH etc
                        # rar_msg_ids starts with base 0
                        if send_articles + 1 in message_on:
                            # msg on only each 25%
                            print ('Requested [' + str(send_articles + 1) + 
                                '/' +  str(articles_to_check) + 
                                '] articles, ' + str(failed_articles) + 
                                ' failed')
                            sys.stdout.flush()
                        if send_articles < articles_to_check - 1:
                            send_articles += 1
                        elif send_articles < articles_to_check:
                            send_articles += 1
                            if EXTREME:
                                print '[E] Receiving remaining replies'
                # python 2.X issue, int * float, otherwise no division
                failed_ratio = failed_articles * 100.0 / articles_to_check
        # loop through all sockets, to catch the last server replies
        # without sending new STAT messages, and allowing sockets to close
        end_loop = True
        end_count = 0
        #loop twice over all sockets to try to catch all remaining replies
        for k in range(0,2):
            for i in range(start_sock, end_sock):
                reply = None
                try:
                    reply = sockets[i].recv(4096)
                except:
                    # when nothing received wait 200 ms for each complete loop
                    # avoiding continuous looping on fast machines
                    time.sleep(0.20 / num_conn) 
                    if EXTREME:
                        print ('[E] Slow reply from server, waiting ' + 
                            str(200 / num_conn) + ' ms to avoid looping')
                    continue  # reply will be empty string when error
                if reply != None:
                    logged_in[i] = False  # circumvents sending other STAT msg 
                    (error, id_used, server_reply, msg_id_used) = \
                        check_send_server_reply(sockets[i], reply, group, id, 
                        i, host, username, password)  ##
                    if error:
                        # ID of missing article is not returned by server
                        failed_articles += 1
                        end_count += 1
                        if end_count >= num_conn:
                            print ('All requested replies received, ' +
                                str(failed_articles) + ' failed')
                            break
                    # found ok article on server, store success:
                    if not error and server_reply == '223':
                        # find row index for successfully send article 
                        # (with recv reply)
                        for j, rar_msg_id in enumerate(rar_msg_ids):
                            if msg_id_used == rar_msg_id[3]:
                                # store success serv num
                                rar_msg_ids[j][4] = num_server
                                break
                        end_count += 1
                        if end_count >= num_conn:
                            print ('All requested replies received, ' +
                                str(failed_articles) + ' failed')
                            break
                # python 2.X issue, int * float, otherwise no division
                failed_ratio = failed_articles * 100.0 / articles_to_check
            if end_count >= num_conn:
                break
        print ('Failed ratio for server: ' + host + ': ' + 
            str(round(failed_ratio,1))) + '%'
        if failed_ratio < failed_limit:  # ok on the last provider
            break
    return failed_ratio

def lock_file():
    '''
        This function checks if the .lock file is there, if it is created 
        before or after a restart of NZBget. This prevents the script from
        running twice at the same time. It returns True when there is a valid
        .lock file, otherwise it will return false and create one.
        '''
    if VERBOSE:
        print '[V] lock_file()'
    NZBget = connect_to_nzbget()
    nzbget_status = NZBget.status() # Get NZB status info XML-RPC
    server_time = nzbget_status['ServerTime']
    up_time = nzbget_status['UpTimeSec']
    tmp_path = os.environ['NZBOP_TEMPDIR'] + os.sep + 'completion'
    try:
        os.makedirs(tmp_path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(tmp_path):
            pass
        else: raise
    f_name = tmp_path + os.sep + 'completion.lock'
    file_exists = os.path.isfile(f_name)
    if file_exists:
        fd = open(f_name)
        time_stamp = int(fd.readline())
        fd.close()
        # Check if the .lock file was created before or after the last restart
        if server_time - up_time > time_stamp:  
            # .lock created before restart, overwrite .lock file time_stamp
            fd = open(f_name,'w')
            fd.write(str(server_time))
            fd.close()
            if VERBOSE:
                print '[V] Old completion.lock file overwritten'
            return False
        else:
            # .lock created after restart, script is running at this moment
            # don't start script
            if VERBOSE:
                print '[V] Script is already running, check canceled'
            return True
    else:
        fd = open(f_name,'w')
        fd.write(str(server_time))
        fd.close()
        if VERBOSE:
            print '[INFO] [V] completion.lock file created'
        return False

def del_lock_file():
    '''
        Delete the .lock file
        '''
    if VERBOSE:
        print '[V] del_lock_file()'
    f_name = os.path.join( os.environ['NZBOP_TEMPDIR'], 'completion','completion.lock' )
    os.remove(f_name)
    if VERBOSE:
        print '[V] completion.lock file deleted'

def nzbget_paused():
    '''
        Pause NZBget if not already paused, when paused don't start the check.
        give the NZBGet sockets some time to close the connections, and avoid
        48X warnings on number of connections.
        '''
    if VERBOSE:
        print '[V] nzbget_paused()'
    NZBget = connect_to_nzbget()
    nzbget_status = NZBget.status()
    nzbget_paused = nzbget_status['DownloadPaused']
    if nzbget_paused:
        paused = True
    else:
        paused = False
        nzbget_status = NZBget.status()
        download_rate = nzbget_status['DownloadRate']
        NZBget.pausedownload()  # pause downloading in nzbget
        if VERBOSE:
            print '[V] Waiting for NZBGet to end downloading'
            sys.stdout.flush()
        while download_rate > 0:  # avoid double use of connections
            if VERBOSE:
                print ('[V] Download rate: ' +
                    round(download_rate / 1000.0 ,2) + 
                    ' kB/s, waiting 10 sec to stop downloading')
                sys.stdout.flush()
            time.sleep(10) # let the connections cool down 10 sec
            nzbget_status = NZBget.status()
            download_rate = nzbget_status['DownloadRate']
        if VERBOSE:
            print '[V] Downloading for NZBGet paused'
            sys.stdout.flush()
    return paused

def nzbget_resume():
    '''
        Resume NZBget
        '''
    if VERBOSE:
        print '[V] nzbget_resume()'
    NZBget = connect_to_nzbget()
    NZBget.resumedownload()  # resume downloading in nzbget
    if VERBOSE:
        print '[V] Downloading for NZBGet resumed'

def get_prio_nzb(jobs):
    '''
        Get queue data from nzbget, check if not downloading a release, check
        if item is in the specified categories to be checked, sort data based
        on priority and age (oldest first, less chance of propagation, bigger 
        chance it will be DMCAed. Check the first item in sorted queue, if file
        is incomplete, check next item etc. Only resume first succesfull file.
        '''
    if EXTREME:
        print '[E] get_prio_nzb(jobs='
        for job in jobs:
            print '[E] ' + str(job)
        print ')'
    do_check = False
    #check if there is something downloading, loop through jobs
    for job in jobs:
        nzb_category = job['Category']
        if (CATEGORIES[0] == '' or nzb_category.lower() in CATEGORIES):
            nzb_filename = get_nzb_filename(job['Parameters'])
            if job['Status'] in ('DOWNLOADING', 'QUEUED'):
                # no check, active download / unpaused items
                do_check = False
                if VERBOSE:
                    print ('[V] Found active item in queue: "' + nzb_filename +
                        '", skipping check')
                break
            elif job['Status'] in ('PAUSED'):
                # valid item for a check
                do_check = True
                if VERBOSE:
                    print ('[V] Found paused item in queue: "' + nzb_filename +
                        '"')
            else:  # post-process / par / rar action active
                if VERBOSE:
                    print ('[V] Found processing item in queue: "' + 
                        nzb_filename + '"')
    if do_check:
        paused = nzbget_paused()  # check if NZBget is paused, +pause nzbget
        if paused:  # nzbget is paused by user, no check
            if VERBOSE:
                print '[V] Not started because download is paused'
    if do_check and not paused:
        if PRIORITIZE_OLD:
            # sort on nzb age, then on priority. Priority items will be on top.
            # oldest file has lowest maxposttime
            if VERBOSE:
                print ('[V] Maintaining priority of items older than'+ 
                    'AgeLimit of '+ str(AGE_LIMIT) + ' hours')
            t = sorted(jobs, key=itemgetter('MaxPostTime'))
            jobs_sorted = (sorted(t, key=itemgetter('MaxPriority'), 
                reverse=True))
        else:
            # sort on nzb age, but move older than max-age to bottom, then
            # sort of priority. Priority items will be on top.
            if VERBOSE:
                print ('[V] Ignoring priority of items older than AgeLimit ' +
                    'of '+ str(AGE_LIMIT) + ' hours')
            max_age = int(time.time()) - int(AGE_LIMIT_SEC)
            t1 = sorted((j for j in jobs if 
                float(j['MaxPostTime']) >= max_age), 
                key=itemgetter('MaxPostTime'))
            t2 = sorted((j for j in jobs if 
                float(j['MaxPostTime']) < max_age), 
                key=itemgetter('MaxPostTime'))
            for t in t2:
                t1.append(t)
            jobs_sorted = (sorted(t1, key=itemgetter('MaxPriority'), 
                reverse=True))
        for job in jobs_sorted:
            nzb_category = job['Category']
            if (CATEGORIES[0] == '' or nzb_category.lower() in CATEGORIES):
                nzb_filename = get_nzb_filename(job['Parameters'])
                if job['Status'] == 'PAUSED':
                    nzb_id = job['NZBID']
                    nzb_age = job['MaxPostTime']  # nzb age
                    nzb_critical_health = job['CriticalHealth']
                    nzb_dupe_key = job['DupeKey']
                    nzb_dupe_score = job['DupeScore']
                    nzb = [nzb_id, nzb_filename, nzb_age, nzb_critical_health,
                        nzb_dupe_key, nzb_dupe_score]
                    # do a completion check, returns true if ok and resumed
                    if get_nzb_status(nzb):
                        break
                else:
                    if VERBOSE:
                        print ('[V] Skipping: "' + nzb_filename +
                            '": not paused')
            else:
                if VERBOSE:
                    print ('[V] Skipping: "' + nzb_filename +
                        '": Category "' + str(job['Category'].lower()) +
                        '" not in Categories ' + str(CATEGORIES))
        nzbget_resume()

def scheduler_call():
    '''
        Script is called as scheduler script
        check if files in the queue should be checked by the completion script
        '''
#    if VERBOSE:
#        print '[V] scheduler_call()'
    # data contains ALL properties each NZB in queue
    data = call_nzbget_direct('listgroups')
    jobs = json.loads(data)
    # check if nzb in queue, and check if paused by this script
    if len(jobs['result']) > 0 and 'CnpNZBFileName' in str(jobs):
        if not lock_file():  # check if script is not already running
            paused_jobs = []
            for job in jobs['result']:
                # send only nzbs paused by the script
                if 'CnpNZBFileName' in str(job):
                    paused_jobs.append(job)
            get_prio_nzb(paused_jobs)
            del_lock_file()
    elif VERBOSE:
            print '[V] Empty queue'

def queue_call():
    '''
        Script is called as queue script
        check if new files in queue should be checked by the completion script
        '''
#    if VERBOSE:
#        print '[V] queue_call()'
    # check if NZB is added, otherwise it will call on each downloaded part
    event = os.environ['NZBNA_EVENT']
    if event == 'NZB_ADDED' or event == 'NZB_DOWNLOADED':
        # when NZB_DOWNLOADED occurs, the NZB is still in queue, with the 
        # paused par2 etc.
        # data contains ALL properties each NZB in queue
        data = call_nzbget_direct('listgroups')
        jobs = json.loads(data)
        # check if nzb in queue, and check if paused by this script
        if len(jobs['result']) > 0 and 'CnpNZBFileName' in str(jobs):
            if not lock_file():  # check if script is not already running
                paused_jobs = []
                for job in jobs['result']:
                    # send only nzbs paused by the script
                    if 'CnpNZBFileName' in str(job):
                        paused_jobs.append(job)
                get_prio_nzb(paused_jobs)
                del_lock_file()

def scan_call():
    '''
        Script is called as scan script. This part of the script pauses the NZB
        and marks the file as paused by the script. Files not paused by the 
        script won't be checked on completion.
        NZBGet doesn't provide the actual name of the file when in the queue.
        if 2 same filename items appear at the same time the 2nd file wiil be
        _2.nzb.queued and if 2 items are added after eachoter, they will be
        nzb.queued and nzb.2.queued. NZBget does not provide the _2. or .2. in 
        e.g. queue, scheduler calls, 'listgroups' or 'history'. The scan script
        adds the NZBPR_CnpNZBFileName variable to know the exact file name, and 
        uses it to recognize if a nzb is paused by the script.
        '''
#    if VERBOSE:
#        print '[V] scan_call()'
    # Check if NZB should be paused.
    if (os.environ['NZBNP_CATEGORY'].lower() in CATEGORIES or 
            CATEGORIES[0] == ''):
        # NZBNP_FILENAME needs to be written to other NZBPR_var for later use.
        nzb_filename = os.environ['NZBNP_FILENAME']
        nzb_dir = os.environ['NZBOP_NZBDIR']
        nzb_filename = nzb_filename.replace(nzb_dir + os.sep, '')
        l_nzb = len(nzb_filename)  # length for file matching, with .nzb ext
        c = 0
        dupe_list_num = []
        for file in os.listdir(nzb_dir):
            if file.endswith(".queued") and file[:l_nzb] == nzb_filename:
                # found file with same file name + .nzb
                # count identical files
                c += 1
                # extract possible number between .nzb. and .queued
                dupe_num = file[file.rfind('.nzb.')+5:-7]
                dupe_list_num.append(dupe_num)
        if c > 0:  # already 1 file with same name in queue/history
            if VERBOSE:
                print ('[V] Found ' + str(c) + 
                    ' queued / history nzb with identical name: ' + 
                    nzb_filename )
            # num between .nzb. .queued is lowest num not in dupe_list_num
            for x in range(1, c + 1):
                if x == 1:
                    t = ''
                else:
                    t = str(x)
                if t not in dupe_list_num:
                    if t == '':
                        nzb_filename = nzb_filename + '.queued'
                    else:
                        nzb_filename = nzb_filename + '.' + t + '.queued'
                    break
                elif c == 1 or c == x:
                    t = str(x + 1)
                    nzb_filename = nzb_filename + '.' + t + '.queued'
                # else: nothing
        else:  # no identical file names
            nzb_filename = nzb_filename + '.queued'
        if VERBOSE:
            print '[V] Expected queued file name: "' + nzb_filename + '"'
        print '[NZB] NZBPR_CnpNZBFileName=' + nzb_filename
        # pausing NZB
        if VERBOSE:
            print '[V] Pausing: "' + os.environ['NZBNP_NZBNAME'] + '"'
        print '[NZB] PAUSED=1'

def main():
    '''
        Check for which script type the script is called
        '''
    # check if the script is called as Scheduler Script
    if 'NZBSP_TASKID' in os.environ: scheduler_call()
    # Check if the script is called as Queue Script.
    if 'NZBNA_NZBNAME' in os.environ: queue_call()
    # check if the script is called as Scan Script
    if 'NZBNP_NZBNAME' in os.environ: scan_call()

main()

''' 
TODO:
    - When 2 NZBs are added together, the check sometimes doesn't start, try
      to block queue script when scan script is active?
    - When the JOIN GROUP nntp command is required for one of the news servers,
      the script doesn't work, and never has (note that this is barely used 
      anymore).
ADDED/FIXED:
    - When other scripts also added a parameter to a NZB, the script couldn't
      extract the file name of the nzb to be checked, causing a move to the 
      queue without checking. Typically happened for Sonarr.


Script structure:

- main() -> scan / queue / schedule script
- scan -> pause typical incoming NZBs
- queue / schedule -> start whole completion check loop, get queue data list
    - lock_file() -> check if not running, otherwise create lock file
    - get_prio_nzb() -> sent highest prio / oldest within to check
        - nzbget_paused() -> check if NZBGet not paused, pause NZBGet for check
        - get_nzb_status() -> handle results of article check: resume / keep
          paused / mark bad / mark failed
            - get_nzb_data() -> extract the data from the nzb
                - fix_nzb() -> fix 1 line nzbs
            - check_failure_status() -> recv messages
                - get_server_settings() -> extract NZBGet server info
                - create_sockets() -> build sockets
                - check_send_server_reply() -> check recv messages, article 
                  ok/nok,
                    login, send messages.
                    - is_number() -> check if a str is a number
            - unpause_nzb() -> resume nzb if requested
            - mark_bad() -> mark nzb bad
            - force_failure() -> force a failure of nzb
            - get_dupe_nzb_status()
                - unpause_nzb_dupe() return dupe into queue
                - mark_bad_dupe() mark dupe nzb bad
                - force_failure_dupe() force nzb bad while returning to queue
        - nzbget_resume() -> resume NZBget if paused by nzbget_paused()
    - del_lock_file -> delete created lock file.

- connect_to_nzbget() -> connection to get data from NZBget
- call_nzbget_direct() -> connect and get data from NZBget
'''
