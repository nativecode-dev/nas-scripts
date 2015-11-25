#!/usr/bin/env python

# IMPORTS
# -----------------------------------------------------------------------------
import argparse
import json
import logging
import logging.handlers
import sys
import urllib2

from python_nas import Enum
from python_nas.core import conf, http
from python_nas.networking import interfaces
from python_nas.notifications import email, pushover


# ENUMERATIONS
# -----------------------------------------------------------------------------
ENUM_ACTIONS=Enum({'add': 0, 'remove': 1})
ENUM_CONNECTIONS=Enum({'interface': 0, 'ping': 1})
ENUM_MONITORS=Enum({'all': 0, 'connections': 1, 'notifiers': 1, 'sites': 2})
ENUM_NOTIFIERS=Enum({'email': 0, 'pushover': 1})
ENUM_RULES=Enum({'exists': 0, 'not_exists': 1})


# CONSTANTS
# -----------------------------------------------------------------------------
CONFIG_NAME='monitor.conf'

LIST_ACTIONS=ENUM_ACTIONS.get_names()
LIST_CONNECTIONS=ENUM_CONNECTIONS.get_names()
LIST_MONITORS=ENUM_MONITORS.get_names()
LIST_NOTIFIERS=ENUM_NOTIFIERS.get_names()
LIST_RULES=ENUM_RULES.get_names()

PROCESS_SUCCESS=0
PROCESS_WARNING=1
PROCESS_MISCONFIGURED=100
PROCESS_CATASTROPHIC=666


# GLOBALS
# -----------------------------------------------------------------------------
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
    parser.add_argument('--list', choices=LIST_MONITORS, default='all', type=str)
    parser.set_defaults(func=show_config)


def initialize_arguments_connection(subparsers):
    parser = subparsers.add_parser('connection', help='Manage connections to monitor.')
    parser.add_argument('--action', choices=LIST_ACTIONS, default='add', type=str)
    parser.add_argument('--rule', choices=LIST_RULES, default='exists', type=str)
    parser.add_argument('--type', choices=LIST_CONNECTIONS, default='interface', type=str)
    parser.add_argument('--value', required=True, type=str)
    parser.set_defaults(func=modify_connection)


def initialize_arguments_notification(subparsers):
    help_options = 'Comma-separated list of values or key/value pairs.'

    parser = subparsers.add_parser('notification', help='Manage notification targets.')
    parser.add_argument('--action', choices=LIST_ACTIONS, default='add', type=str)
    parser.add_argument('--options', required=True, type=str, help=help_options)
    parser.add_argument('--type', choices=LIST_NOTIFIERS, required=True, type=str)
    parser.set_defaults(func=modify_notification)


def initialize_arguments_site(subparsers):
    parser = subparsers.add_parser('site', help='Manage sites to monitor.')
    parser.add_argument('--action', choices=LIST_ACTIONS, default='add', type=str)
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

    for connection_type in connections:
        try:
            if connection_type == 'interface':
                interface = connections[connection_type]
                perform_check_connections_interface(args, config, interface)
            elif connection_type == 'ping':
                pings = connections[connection_type]
                perform_check_connections_ping(args, config, pings)
        except Exception as e:
            log.exception(e)


def perform_check_connections_interface(args, config, interface):
    for device_key in interface.keys():
        log.info("Checking connection %s." % device_key)
        device = interface[device_key]
        rule = device['rule']
        if rule == 'exists':
            if not interfaces.exists(device_key):
                message = "Device %s does not exist." % device_key
                log.info(message)
                send_notifications(config, message, device_key)
            else:
                log.info("Connection %s is active." % device_key)
        elif rule == 'not_exists':
            if interfaces.exists(device_key):
                message = "Device %s exists" % device_key
                send_notifications(config, message, device_key)


def perform_check_connections_ping(args, config, ping):
    for host in ping.keys():
        log.info("Checking ping to %s." % host)
        rule = ping[host]['rule']

        if rule == 'exists':
            if not interfaces.can_ping(host):
                message = "Can't ping host %s." % host
                send_notifications(config, message, host)
            else:
                message = "Was able to ping %s." % host
        elif rule == 'not_exists':
            if interfaces.can_ping(host):
                message = "Can ping host %s." % host
                send_notifications(config, message, host)

        log.info(message)


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
                log.info("Site '%s' returned a '200 OK' status." % url)
        except urllib2.HTTPError as e:
            log.error(e)
            message = "Site %s returned a '%s (%s)' status." % (url, e.reason, e.code)
            log.debug(message)
            send_notifications(config, message, url)


def send_notifications(config, message, identifier):
    notifiers = None if 'notifiers' not in config else config['notifiers']

    if notifiers:
        for type in notifiers.keys():
            log.info("Sending notification via %s." % type)
            try:
                if type == 'email':
                    recipients = notifiers[type]['recipients']
                    email.send_multiple(recipients, message)
                    log.info("Sent '%s' to recipients %s." % (message, ', '.join(recipients)))
                elif type == 'pushover':
                    pushover.send_multiple(notifiers[type], message, title="Monitor (%s)" % identifier)
                    log.info("Sent '%s' to pushover." % message)
            except Exception as e:
                log.exception(e)


def modify_connection(args, config):
    connections = config['connections'] = {} if not 'connections' in config else config['connections']

    if args.action == 'add': modify_connection_add(args, connections)
    elif args.action == 'remove': modify_connection_remove(args, connections)

    conf.write_json(CONFIG_NAME, config)


def modify_connection_add(args, connections):
    type = connections[args.type] = {} if not args.type in connections else connections[args.type]
    interface = type[args.value] = {} if not args.value in type else type[args.value]
    interface['rule'] = args.rule
    log.info("Added or updated %s." % args.type)


def modify_connection_remove(args, connections):
    if args.type in connections:
        connection = connections[args.type]
        if args.value in connection:
            del connection[args.value]
            log.info("Removed %s named %s." % (args.type, args.value))


def modify_notification(args, config):
    notifiers = config['notifiers'] = {} if not 'notifiers' in config else config['notifiers']

    if args.action == 'add': modify_notification_add(args, notifiers)
    elif args.action == 'remove': modify_notification_remove(args, notifiers)

    conf.write_json(CONFIG_NAME, config)


def modify_notification_add(args, notifiers):
    notifier = notifiers[args.type] = {} if not args.type in notifiers else notifiers[args.type]
    if args.type == 'email':
        conf.list_add(notifier, 'recipients', conf.list_split(args.options))
        log.info("Added email recipients %s." % args.options)
    elif args.type == 'pushover':
        conf.dict_addstring(notifier, args.options, ['apikey', 'clientkey'])
        log.info("Added pushover options %s." % args.options)


def modify_notification_remove(args, notifiers):
    if args.type in notifiers:
        notifier = notifiers[args.type]
        if args.type == 'email':
            conf.list_remove(notifier, 'recipients', conf.list_split(args.options))
            log.info("Removed email recipients %s." % args.options)
        elif args.type == 'pushover':
            conf.dict_remove(notifier, args.options)
            log.info("Removed pushover channel %s." % args.options)


def modify_site(args, config):
    sites = config['sites'] = {} if not 'sites' in config else config['sites']

    if args.action == 'add': modify_site_add(args, sites)
    elif args.action == 'remove': modify_site_remove(args, sites)

    conf.write_json(CONFIG_NAME, config)


def modify_site_add(args, sites):
    site = sites[args.url] = {} if not args.url in sites else sites[args.url]
    site['auth'] = args.auth
    site['username'] = args.username
    site['password'] = args.password

    log.info("Added or updated site %s." % args.url)


def modify_site_remove(args, sites):
    if args.url in sites:
        del sites[args.url]
        log.info("Removed site %s." % args.url)


def show_config(args, config):
    showables = ['connections', 'notifiers', 'sites'] if 'all' == args.list else [args.list]

    for showable in showables:
        if not showable in config:
            log.info("No %s configured." % showable)
            continue

        section = config[showable]
        log.info("List of %s." % showable)

        if showable == 'connections': show_config_connections(section)
        elif showable == 'notifiers': show_config_notifiers(section)
        elif showable == 'sites': show_config_sites(section)


def show_config_connections(section):
    for connection_type in sorted(section.keys()):
        connection = section[connection_type]
        if connection_type == 'interface':
            for value in sorted(connection.keys()):
                rule = connection[value]['rule']
                log.info("\t[INTERFACE] %s : %s" % (value, rule))
        elif connection_type == 'ping':
            for value in sorted(connection.keys()):
                rule = connection[value]['rule']
                log.info("\t[PING] %s : %s" % (value, rule))


def show_config_notifiers(section):
    for notifier_type in sorted(section.keys()):
        notifier = section[notifier_type]
        if notifier_type == 'email':
            for recipient in sorted(notifier['recipients']):
                log.info("\t[EMAIL] %s." % recipient)
        elif notifier_type == 'pushover':
            for pushover in sorted(notifier.keys()):
                log.info("\t[PUSHOVER] %s." % pushover)


def show_config_sites(section):
    for url in sorted(section.keys()):
        site = section[url]
        log.info("\t[SITE] '%s' (%s)." % (url, site['auth']))


if __name__ == '__main__':
    main()
