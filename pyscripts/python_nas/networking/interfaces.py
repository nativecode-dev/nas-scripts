import os
import re
import subprocess
import urllib2

# Returns 3 groups: 1) Name 2) Link 3) Loopback or HWaddr
REGEX_INTERFACE=re.compile('(.*)\s+Link encap:(.*)\s+(Loopback|HWaddr\s.*)')
REGEX_ADDR_INET=re.compile('inet addr:((\d{1,3}\.?){4})')
REGEX_ADDR_MASK=re.compile('Mask:((\d{1,3}\.?){4})')
REGEX_ADDR_PTP=re.compile('P-t-P:((\d{1,3}\.?){4})')


class NetInterface(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def exists(name):
    try:
        get_ifconfig(name)
        return True
    except Exception:
        return False


def get_ifconfig(name=None):
    command = ['ifconfig']
    if name: command.append(name)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()

    if error or not output:
        raise Exception("Could not retrieve ifconfig output.")

    return output


def get_interface_info(interface, name):
    output = get_ifconfig(name).split('\n')
    for line in output:
        # Match the inet_addr.
        match_addr_inet = REGEX_ADDR_INET.search(line)
        if match_addr_inet:
            interface.addr_inet = match_addr_inet.group(1)

        # Match the mask.
        match_addr_mask = REGEX_ADDR_MASK.search(line)
        if match_addr_mask:
            interface.addr_mask = match_addr_mask.group(1)

        # Match the ptp.
        match_addr_ptp = REGEX_ADDR_PTP.search(line)
        if match_addr_ptp:
            interface.addr_ptp = match_addr_ptp.group(1)


def get_interfaces(full=False):
    output = get_ifconfig().split('\n')
    interfaces = []

    for line in output:
        match = REGEX_INTERFACE.search(line)
        if match:
            name = match.group(1).strip()
            link = match.group(2).strip()
            hwaddr = match.group(3).strip()
            interface = NetInterface()
            interface.name = name
            interface.link = link
            interface.hwaddr = hwaddr.replace('HWaddr ', '')
            interfaces.append(interface)

            if full: get_interface_info(interface, name)

    return interfaces


def get_public_address(type='ipv4'):
    if not type in ['ipv4', 'ipv6']:
        raise Exception("Type must be either 'ipv4' or 'ipv6'.")

    return urllib2.urlopen('http://%s.icanhazip.com' % type).read().replace('\n', '')
