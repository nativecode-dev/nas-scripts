# Imports
##############################################################################
import json
import nzb
import os
import re


# Rar functions
##############################################################################

def rar_search_init(script_name):
    """
    Initialize temporary file to contain filenames.
    """
    global rar_temp_filename

    nzbid = nzb.get_nzb_id()
    tempfolder = nzb.get_script_tempfolder(script_name)
    rar_temp_filename = '%s/%s' % (tempfolder, nzbid)
    nzb.log_debug('' % rar_temp_filename)

    return rar_temp_filename


def rar_sort_last_to_top():
    nzbid = nzb.get_nzb_id()
    nzbfiles = nzb.get_nzb_files(nzbid)

    re_filename = re.compile('.*\.part(\d+)\.rar', re.IGNORECASE)
    re_extension = re.compile('.*\.r(\d+)', re.IGNORECASE)

    file_id = None
    file_name = None
    file_number = None

    for nzbfile in nzbfiles:
        id = nzbfile['id']
        filename = nzbfile['filename']
        
        match = re_filename.match(filename) or re_extension.match(filename)
        if match:
            number = int(match.group(1))
            if not file_number or number > file_number:
                file_id = id
                file_name = filename
                file_number = number

    if file_id:
        nzb.log_info('Moving last rar-file to the top: %s.' % file_name)
        proxy = nzb.proxy()
        proxy.editqueue('FileMoveTop', 0, '', [file_id])
    else:
        nzb.log_info('Skipping sorting since no rar-files found.')
