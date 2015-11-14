#!/usr/bin/env python

import re
import sys

from pushover import init, Client

REGEX_LINK = re.compile('(.*)\s+Link encap:(.*)\s+HWaddr\s+(.*)')
REGEX_LINK_ADDR = re.compile('\s+inet addr:((\d{1,3}\.?){4})')
REGEX_LINK_MASK = re.compile('\s+Mask:((\d{1,3}\.?){4})')
REGEX_LINK_PTP = re.compile('\s+P-t-P:((\d{1,3}\.?){4})')

PUSHOVER_APP_KEY = 'a4eggo6VBoeibpQes1j8p9G5uTasMS'
PUSHOVER_USR_KEY = 'uMDKUJSBLFKEYgNJUWECx3hTU3Ax2W'

ifconfig = sys.stdin.read()


class NetLink(object):
    def __init__(self):
        self.addr = None
        self.hwaddr = None
        self.id = None
        self.mask = None
        self.name = None
        self.ptp = None


def get_interfaces(input):
    lines = input.split('\n')
    interfaces = []
    last_link = None
    for line in lines:
        link = get_interface_link(line)
        if link:
            last_link = link
            interfaces.append(link)

        if last_link:
            set_link_info(last_link, line)

    return interfaces


def get_interface_link(line):
    match_link = REGEX_LINK.match(line)
    if match_link:
        link = NetLink()
        link.id = match_link.group(1)
        link.name = match_link.group(2)
        link.hwaddr = match_link.group(3)
        return link
        


def set_link_info(link, line):
    match_addr = REGEX_LINK_ADDR.search(line)
    if match_addr:
        link.addr = match_addr.group(1)

    match_ptp = REGEX_LINK_PTP.search(line)
    if match_ptp:
        link.ptp = match_ptp.group(1)

    match_mask = REGEX_LINK_MASK.search(line)
    if match_mask:
        link.mask = match_mask.group(1)


interfaces = get_interfaces(ifconfig)

vpns = []
for interface in interfaces:
    if interface.ptp: vpns.append(interface)

if len(vpns) == 0:
    print('No VPN connections found.')
    try:
        init(PUSHOVER_APP_KEY)
        Client(PUSHOVER_USR_KEY).send_message('VPN on server is down.')
    except Exception as e:
        print(e)
