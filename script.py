#!/usr/bin/env python

# Imports
##############################################################################
import nzb
import os
import sys


# Script entry-point
##############################################################################
def execute():
    """
    Start executing script-specific logic here.
    """
    try:
        # YOUR CODE HERE
        return
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
        nzb.check_nzb_environment()
        nzb.check_nzb_failed()
        nzb.check_nzb_reprocess()
        nzb.check_nzb_status()

        execute()
    except:
        sys.exit(nzb.PROCESS_ERROR)


# Main entry-point
##############################################################################
main()

# NZBGet is weird and doesn't use 0 to signal the successful execution of a
# script, so we use the PROCESS_SUCCESS code here.
sys.exit(nzb.PROCESS_SUCCESS)
