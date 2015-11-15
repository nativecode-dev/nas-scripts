#!/usr/bin/env python

# IMPORTS
# -----------------------------------------------------------------------------
import argparse
import json
import logging
import logging.handlers
import sys
import urllib2

from python_nas.core import conf, http
from python_nas.notifications import email, pushover


# CONSTANTS
# -----------------------------------------------------------------------------
CONFIG_NAME='monitor.conf'
PROCESS_SUCCESS=0
PROCESS_WARNING=1
PROCESS_MISCONFIGURED=100
PROCESS_CATASTROPHIC=666


# GLOBALS
# ----------------------------------------------------------------------------
log = None


# FUNCTIONS
# -----------------------------------------------------------------------------
def main():
    initialize_loggers()
    initialize_arguments()


def initialize_loggers():
    global log
    log = logging.Logger('monitor')
    create_console_logger()
    create_syslog_logger()


def create_console_logger():
    console = logging.StreamHandler(stream=sys.stdout)
    console.setLevel(logging.DEBUG)
    log.addHandler(console)


def create_syslog_logger():
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    syslog = logging.handlers.SysLogHandler(address='/dev/log')
    syslog.setLevel(logging.ERROR)
    syslog.setFormatter(formatter)
    log.addHandler(syslog)


def initialize_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--command')
    subparsers = parser.add_subparsers()

    # Define subcommand for checking configured sites.
    initialize_arguments_check(subparsers)

    # Define subcommand for showing configuration options.
    initialize_arguments_config(subparsers)

    # Define subcommand for checking connections.
    initialize_arguments_connection(subparsers)

    # Define subcommand for adding/removing notifications.
    initialize_arguments_notification(subparsers)

    # Define subcommand for adding/removing sites.
    initialize_arguments_site(subparsers)

    # Perform command action.
    try:
        config = conf.read_json(CONFIG_NAME)
        args = parser.parse_args()
        args.func(args, config)
    except Exception as e:
        log.exception(e)
        sys.exit(PROCESS_CATASTROPHIC)


def initialize_arguments_check(subparsers):
    parser = subparsers.add_parser('check', help='Perform checks on configured targets.')
    parser.add_argument('--monitor', choices=['all', 'connections', 'sites'], default='all', type=str)
    parser.set_defaults(func=perform_checks)


def initialize_arguments_config(subparsers):
    parser = subparsers.add_parser('config', help='Show configuration options.')
    parser.set_defaults(func=show_config)


def initialize_arguments_connection(subparsers):
    help_options = 'Comma-separated list of values or key/value pairs.'

    parser = subparsers.add_parser('connection', help='Manage connections to monitor.')
    parser.add_argument('--action', choices=['add', 'remove'], default='add', type=str)
    parser.add_argument('--options', required=True, type=str, help=help_options)
    parser.add_argument('--type', choices=['interface', 'ipmatch', 'vpn'], default='interface', type=str)
    parser.set_defaults(func=modify_connection)


def initialize_arguments_notification(subparsers):
    help_options = 'Comma-separated list of values or key/value pairs.'

    parser = subparsers.add_parser('notification', help='Manage notification targets.')
    parser.add_argument('--action', choices=['add', 'remove'], default='add', type=str)
    parser.add_argument('--options', required=True, type=str, help=help_options)
    parser.add_argument('--type', choices=['email', 'pushover'], required=True, type=str)
    parser.set_defaults(func=modify_notification)


def initialize_arguments_site(subparsers):
    parser = subparsers.add_parser('site', help='Manage sites to monitor.')
    parser.add_argument('--action', choices=['add', 'remove'], default='add', type=str)
    parser.add_argument('--url', required=True, type=str)
    parser.add_argument('--auth', choices=['basic', 'none', 'url'], default='none', type=str)
    parser.add_argument('--username', default=None, type=str)
    parser.add_argument('--password', default=None, type=str)
    parser.set_defaults(func=modify_site)


def perform_checks(args, config):
    monitored = ['connections', 'sites'] if args.monitor  == 'all' else [args.monitor]

    if 'connections' in monitored:
        perform_check_connections(args, config)

    if 'sites' in monitored:
        perform_check_sites(args, config)


def perform_check_connections(args, config):
    if not 'connections' in config:
        log.warning("No connections have been configured.")
        return

    connections = config['connections']

    for connection in connections:
        pass


def perform_check_sites(args, config):
    if not 'sites' in config:
        log.warning("No sites have been configured.")
        return

    sites = config['sites']

    for url in sites:
        log.info("Checking site '%s'." % url)
        site = sites[url]

        try:
            if site['auth'] == 'none':
                response = http.get(url)
            elif site['auth'] == 'basic':
                headers = http.get_basic_auth_header(site['username'], site['password'])
                response = http.get(url, headers)

            if response and response.code == 200:
                log.info("Site %s returned a 200 OK status." % url)
        except urllib2.HTTPError as e:
            message = "Site %s returned a '%s (%s)' status." % (url, e.reason, e.code)
            log.debug(message)
            send_notifications(config, message, url)


def send_notifications(config, message, url):
    notifiers = None if 'notifiers' not in config else config['notifiers']

    if notifiers:
        for type in notifiers.keys():
            log.info("Sending notification via %s." % type)
            try:
                if type == 'email':
                    email.send_multiple(notifiers[type], message)
                elif type == 'pushover':
                    pushover.send_multiple(notifiers[type], message, title="Site Monitor (%s)" % url)
            except Exception as e:
                log.exception(e)


def modify_connection(args, config):
    connections = {} if not 'connections' in config else config['connections']
    conf.write_json(CONFIG_NAME, config)


def modify_notification(args, config):
    notifiers = {} if not 'notifiers' in config else config['notifiers']

    if args.action == 'add':
        notifier = notifiers[args.type] = {} if not args.type in notifiers else notifiers[args.type]
        if args.type == 'email':
            conf.list_add(notifier, 'recipients', conf.list_split(args.options))
            log.info("Added email recipients %s." % args.options)
        elif args.type == 'pushover':
            conf.dict_addstring(notifier, args.options, ['apikey', 'clientkey'])
            log.info("Added pushover options %s." % args.options)
    elif args.action == 'remove':
        if args.type in notifiers:
            notifier = notifiers[args.type]
            if args.type == 'email':
                conf.list_remove(notifier, 'recipients', conf.list_split(args.options))
                log.info("Removed email recipients %s." % args.options)
            elif args.type == 'pushover':
                conf.dict_remove(notifier, args.options)
                log.info("Removed pushover channel %s." % args.options)

    conf.write_json(CONFIG_NAME, config)


def modify_site(args, config):
    sites = {} if not 'sites' in config else config['sites']

    if args.action == 'add':
        site = sites[args.url] = {} if not args.url in sites else sites[args.url]
        site['auth'] = args.auth
        site['username'] = args.username
        site['password'] = args.password

        log.info("Added or updated site %s." % args.url)
    elif args.action == 'remove':
        if args.url in sites:
            del sites[args.url]
            log.info("Removed site %s." % args.url)

    conf.write_json(CONFIG_NAME, config)


def show_config(args, config):
    print(json.dumps(config, sort_keys=True, indent=2, separators=(',', ': ')))


if __name__ == '__main__':
    main()
