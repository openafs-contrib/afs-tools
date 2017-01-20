#!/usr/bin/env python
# Copyright (c) 2014-2017 Sine Nomine Associates
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THE SOFTWARE IS PROVIDED 'AS IS' AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#------------------------------------------------------------------------------
#
# Gather stats from OpenAFS file servers.
#
# This tool runs the OpenAFS rxdebug and xstat utilities to gather statisical
# information from running file servers and cache managers over the network.
#
# NOTE: This tool requires a patched version of xstat_fs_test and rxdebug which
#       provide a more regular output format.
#
# Example config file:
#
# cat ~/.xstat.conf
# [logging]
# level = info
# file = /tmp/xstat.log
#
# [collect]
# destdir = /tmp/xstats
# sleep = 60
# once = no
#
# [cell0]
# cellname = example.com
# fileservers =
#     172.16.50.143
#     172.16.50.144
#
#

import os
import sys
import errno
import re
import time
import logging
import pprint
import subprocess
import signal
import ConfigParser

LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}
LOG_CONSOLE_FORMAT = '%(levelname)s %(message)s'
LOG_FILE_FORMAT = '%(asctime)s %(levelname)s %(message)s'

# Log to stderr until the log file name is read from the config.
logging.basicConfig(level=LOG_LEVELS['info'], format=LOG_CONSOLE_FORMAT)

def debug(msg):
    logging.debug(msg)

def info(msg):
    logging.info(msg)

def warning(msg):
    logging.warning(msg)

def error(msg):
    logging.error(msg)

def fatal(msg):
    sys.stderr.write("ERROR: {}\n".format(msg))
    logging.critical(msg)
    sys.exit(1)

def setup_logging(filename, level):
    # Update the logger to log to a file instead of stderr now that we have
    # the log filename and level.
    logger = logging.getLogger()
    old_handler = logger.handlers[0]
    new_handler = logging.FileHandler(filename)
    new_handler.setLevel(LOG_LEVELS[level])
    new_handler.setFormatter(logging.Formatter(LOG_FILE_FORMAT))
    logger.addHandler(new_handler)
    logger.removeHandler(old_handler)
    logger.setLevel(LOG_LEVELS[level])

def read_config():
    """Read the config and set defaults.

    Read the config file and set defaults for any missing values.
    Create a config file with default values if not found."""
    filename = os.path.expanduser('~/.xstat.conf')
    c = ConfigParser.SafeConfigParser()
    debug("reading configuration file {}".format(filename))
    c.read(filename)

    if not c.has_section('logging'):
        c.add_section('logging')
    if not c.has_option('logging', 'level'):
        c.set('logging', 'level', 'info')
    if not c.has_option('logging', 'file'):
        c.set('logging', 'file', '/tmp/xstat.log')

    if not c.has_section('collect'):
        c.add_section('collect')
    if not c.has_option('collect', 'destdir'):
        c.set('collect', 'destdir', '/tmp/xstats')
    if not c.has_option('collect', 'sleep'):
        c.set('collect', 'sleep', '60')
    if not c.has_option('collect', 'once'):
        c.set('collect', 'once', 'no')

    if not c.has_section('cell0'):
        c.add_section('cell0')
    if not c.has_option('cell0', 'cellname'):
        c.set('cell0', 'cellname', detect_cellname())
    if not c.has_option('cell0', 'fileservers'):
        cellname = c.get('cell0', 'cellname')
        servers = detect_fileservers(cellname)   # returns a dict
        addrs = [a[0] for a in servers.values()] # use primary address
        c.set('cell0', 'fileservers', "\n"+"\n".join(addrs))

    if not os.path.exists(filename): # Dont clobber existing config.
        with open(filename, 'w') as f:
            info("writing config file {}".format(filename))
            c.write(f)
    return c

def mkdirp(path):
    """Make a directory with parents if it does not already exist."""
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def which(command):
    """Search for a command in the PATH."""
    for path in os.environ['PATH'].split(os.pathsep):
        filename = os.path.join(path, command)
        if os.path.isfile(filename) and os.access(filename, os.X_OK):
            return filename
    error("Could not find command '{}' in PATH {}".format(command, os.environ['PATH']))
    return None

def detect_cellname():
    """Detect the current cellname with the fs command.

    This assumes the current host is running an OpenAFS client."""
    info("searching for cellname")
    cellname = None
    cmd = [which('fs'), 'wscell']
    debug(subprocess.list2cmdline(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    with p.stdout:
        for line in iter(p.stdout.readline, ''):
            match = re.match(r"This workstation belongs to cell '([^']+)'", line)
            if match:
                cellname = match.group(1)
    info("cellname is {}".format(cellname))
    return cellname

def detect_fileservers(cellname):
    """Detect the file servers with the vos listaddrs command."""
    info("searching for file servers in cell {}".format(cellname))
    uuids = {}
    uuid = None
    cmd = [which('vos'), 'listaddrs', '-printuuid', '-noresolve', '-noauth', '-cell', cellname]
    debug(subprocess.list2cmdline(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    with p.stdout:
        for line in iter(p.stdout.readline, ''):
            match = re.match(r'UUID: (\S+)+', line)
            if match:
                uuid = match.group(1)
                uuids[uuid] = []
            match = re.match(r'([\d\.]+)', line)
            if match:
                addr = match.group(1)
                uuids[uuid].append(addr)
    return uuids

def get_usage(command):
    """Get the command usage as a string."""
    pathname = which(command)
    if pathname is None:
        fatal("Unable to find command '{}' in PATH.".format(command))
    cmd = [pathname, '-h']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    out,code = p.communicate()
    return out

def check_commands():
    """Check the required commands are available."""
    usage = get_usage('rxdebug')
    if not '-raw' in usage:
        fatal("rxdebug is missing the '-raw' option.")
    usage = get_usage('xstat_fs_test')
    for option in ['-format', '-delimiter']:
        if not option in usage:
            fatal("xstat_fs_test is missing the '{}' option.".format(option))

def xstat_fs(host, collection, out):
    """Retrieve xstats from a server and write them to the stream."""
    cmd = [which('xstat_fs_test'), host, '-once', '-co', collection, '-format', 'dsv', '-delimiter', ' ']
    cmdline = subprocess.list2cmdline(cmd)
    debug(cmdline)
    p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.PIPE)
    with p.stderr:
        for line in iter(p.stderr.readline, ''):
            line = line.rstrip()
            warning("xstat_fs_test: {}".format(line))
    code = p.wait()
    if code:
        error("xstat_fs_test failed ({}): {}".format(code, cmdline))

def rxstats(host, port, out):
    """Retrieve rxstats from a server and write them to the stream."""
    cmd = [which('rxdebug'), host, port, '-rxstats', '-noconns', '-raw']
    cmdline = subprocess.list2cmdline(cmd)
    timestamp = int(time.time())
    debug(cmdline)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    with p.stdout:
        for line in iter(p.stdout.readline, ''):
            line = line.rstrip()
            match = re.match(r'(\S+)\s(\S+)', line)
            if match:
                name = match.group(1)
                value = match.group(2)
                out.write("{} {} {} {} {}\n".format(timestamp, host, port, name, value))
            else:
                warning("rxdebug: {}".format(line))
    code = p.wait()
    if code:
        error("rxdebug failed ({}): {}".format(code, cmdline))


running = True
def sigint_handler(signal, frame):
    global running
    sys.stdout.write("\nquitting...\n")
    info("SIGINT caught, quitting")
    running = False

def main():
    global running

    config = read_config()
    setup_logging(config.get('logging','file'), config.get('logging','level'))
    destdir = os.path.expanduser(config.get('collect', 'destdir'))
    mkdirp(destdir)
    check_commands() # Exits if the required commands are missing.

    info('Starting main loop.')
    signal.signal(signal.SIGINT, sigint_handler)
    while running:
        for section in config.sections():
            if section.startswith('cell'):
                cellname = config.get(section, 'cellname')
                servers = config.get(section, 'fileservers').strip().split()
                timestamp = time.strftime('%Y-%m-%d')
                filename = os.path.join(destdir, "{}-{}.dat".format(cellname, timestamp))
                for server in servers:
                    info("Writing stats for server {} to file {}".format(server, filename))
                    with open(filename, 'a') as out:
                        try:
                            rxstats(server, '7000', out)
                            xstat_fs(server, '2', out)
                            xstat_fs(server, '3', out)
                        except Exception as e:
                            error("Exception: {}".format(e))
        if running:
            if config.getboolean('collect', 'once'):
                info("once option set, quitting")
                running = False
            else:
                sleep = int(config.get('collect', 'sleep'))
                debug('sleep {}'.format(sleep))
                time.sleep(sleep)
    info('Done.')

if __name__ == "__main__":
    main()
