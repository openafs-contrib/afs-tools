#!/usr/bin/python3
#
# Copyright (c) 2019, Sine Nomine Associates ("SNA")
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND SNA DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS. IN NO EVENT SHALL SNA BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR
# CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE,
# DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS
# SOFTWARE.
#

"""
OpenAFS sysid file encoder/decoder for debugging and troubleshooting.

This module provides a utility to convert OpenAFS sysid files to and from yaml
formatted text to check sysid values. Normally you should let the fileserver
create sysid file contents.

Example python interactive usage:

    >>> from sysidutil import Sysid
    >>>
    >>> # Decode a sysid file.
    >>> sysid = Sysid('sysid')
    >>> print(sysid)
    ---
    magic: 0x88aabbcc
    version: 1
    uuid: 0076d7e8-0e62-1dd8-8aa0-f801a8c0aa77
    addresses:
    - 192.168.1.248
    - 192.168.122.1
    - 192.168.123.1
    - 192.168.250.234
    - 192.168.123.123
    >>> print(sysid.uuid)
    '0076d7e8-0e62-1dd8-8aa0-f801a8c0aa77'
    >>>
    >>> # Export to a yaml file.
    >>> sysid.export('sysid.yaml')
    >>>
    >>> # Import from yaml file.
    >>> sysid = Sysid.from_yaml('sysid.yaml')
    >>>
    >>> # Add a server address and write to the binary sysid.
    >>> sysid.addrs.append('1.2.3.4')
    >>> sysid.write('sysid')

"""

import argparse
import sys
import struct
import socket
import re

def _quad_dotted(unpacked_address):
    packed_address = struct.pack('!I', unpacked_address)
    return socket.inet_ntoa(packed_address)

class UUID:
    """
    UUID encoder/decoder.
    """
    _s = struct.Struct('!I H H B B 6B')
    size = _s.size

    def __init__(self):
        self.time_low = 0
        self.time_mid = 0
        self.time_hi = 0
        self.clock_hi = 0
        self.clock_low = 0
        self.node = (0, 0, 0, 0, 0, 0)

    @classmethod
    def from_bytes(cls, data):
        """
        Create a uuid from packed bytes.

        Args:
            data (bytes): packed uuid bytes
        Returns:
            new UUID object
        """
        uuid = cls()
        uuid.decode(data)
        return uuid

    @classmethod
    def from_str(cls, uuid_str):
        """
        Create a uuid from string representation.

        Args:
            uuid_str (str): UUID string representation
        Returns:
            new UUID object
        Notes: Supports old and new style UUID strings.
        """
        uuid = cls()
        uuid.parse(uuid_str)
        return uuid

    def decode(self, data):
        """
        Decode packed bytes into uuid.

        Args:
            data (bytes): packed uuid bytes
        Returns:
            UUID: self
        """
        vals = self._s.unpack(data)
        self.time_low = vals[0]
        self.time_mid = vals[1]
        self.time_hi = vals[2]
        self.clock_hi = vals[3]
        self.clock_low = vals[4]
        self.node = vals[5:11]
        return self

    def encode(self):
        """
        Return uuid as packed bytes.

        Returns:
            bytes: packed uuid data
        """
        data = self._s.pack(
            self.time_low,
            self.time_mid,
            self.time_hi,
            self.clock_hi,
            self.clock_low,
            *self.node)
        return data

    def parse(self, uuid_str):
        """
        Parse uuid string representation.

        Note: Accepts standard UUID 5-group format 8-4-4-4-12 and OpenAFS
        6-group UUID format 8-4-4-2-2-12.

        Args:
            uuid_str (str): string reprentation of UUID
        Returns:
            UUID: self
        Raises:
            ValueError: uuid_str is not formatted as a uuid string
        """
        r = r'^([0-9a-fA-F]{8})-([0-9a-fA-F]{4})-([0-9a-fA-F]{4})-'\
            '([0-9a-fA-F]{2})-?([0-9a-fA-F]{2})-([0-9a-fA-F]{12})$'
        m = re.search(r, uuid_str)
        if m:
            g = m.groups()
            self.time_low = int(g[0], base=16)
            self.time_mid = int(g[1], base=16)
            self.time_hi = int(g[2], base=16)
            self.clock_hi = int(g[3], base=16)
            self.clock_low = int(g[4], base=16)
            self.node = tuple([int(g[5][i:i+2], base=16) for i in range(0,12,2)])
        else:
            raise ValueError('Not a UUID string: {0}'.format(uuid_str))
        return self

    def __str__(self):
        """
        Return string representation of the UUID.
        """
        sep = ''
        return "{:08x}-{:04x}-{:04x}-{:02x}{}{:02x}-{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}"\
            .format(self.time_low, self.time_mid, self.time_hi,
                    self.clock_hi, sep, self.clock_low, *self.node)

    def __repr__(self):
        return \
            "<UUID:"\
            " time_low={s.time_low}"\
            " time_mid={s.time_mid}"\
            " time_hi={s.time_hi}"\
            " clock_hi={s.clock_hi}"\
            " clock_low={s.clock_low}"\
            " node={s.node}"\
            ">".format(s=self)

class Sysid:
    MAGIC = 0x88aabbcc
    VERSION = 1

    def __init__(self, filename=None):
        self.magic = self.MAGIC
        self.version = self.VERSION
        self.uuid = UUID()
        self.addrs = []
        if filename:
            with open(filename, 'rb') as f:
                data = f.read()
            self.decode(data)

    @classmethod
    def from_yaml(cls, filename='sysid.yaml'):
        """
        Import the sysid data from a yaml file.

        Args:
            filename (str): yaml file pathname (default: sysid.yaml)
        Returns:
            new Sysid object initialized from the file.
        """
        sysid = cls()
        if filename == '-':
            fh = sys.stdin
        else:
            fh = open(filename, 'r')
        text = fh.read()
        if fh is not sys.stdin:
            fh.close()
        sysid.parse_yaml(text)
        return sysid

    def write(self, filename='sysid'):
        """
        Write the sysid file to the native format.

        Args:
            filename (str): file pathname (default: sysid)
        """
        with open(filename, 'wb') as f:
            f.write(self.encode())

    def export(self, filename='sysid.yaml', fmt='yaml'):
        """
        Save the sysid data in a non-native file format.

        Args:
            filename (str): yaml file pathname (default: 'sysid.yaml')
            fmt (str): file format name. (default: 'yaml')
                       must be one of: 'yaml'
        Raises:
            ValueError on unsupported format name.
        """
        if fmt != 'yaml':
            raise ValueError('Unsupported export format: {}'.format(fmt))
        if filename == '-':
            fh = sys.stdout
        else:
            fh = open(filename, 'w')
        fh.write(self.as_yaml())
        fh.write('\n')
        if fh is not sys.stdout:
            fh.close()

    def decode(self, data):
        """Decode the packed binary sysid data.

        Args:
            data (bytes): packed sysid data

        Returns:
            Sysid: self
        """
        magic,version = struct.unpack('=I I', data[0:8])
        if magic != self.MAGIC:
            raise ValueError('Bad magic value: 0x%0x' % magic)
        if version != self.VERSION:
            raise ValueError('Bad version value: %d' % version)
        uuid = UUID.from_bytes(data[8:24])
        num_addrs, = struct.unpack('=I', data[24:28])
        if not 0 <= num_addrs <= 255:
            raise ValueError('Bad number of addresses: 0x%s' % data[24:28].hex())
        expected = 28 + (4 * num_addrs)
        if len(data) != expected:
            raise ValueError('Bad data length: expected=%d, found=%d' % (expected, len(data)))
        unpacked_addrs = struct.unpack('!{0}I'.format(num_addrs), data[28:])
        self.magic = magic
        self.version = version
        self.uuid = uuid
        self.addrs = [_quad_dotted(ua) for ua in unpacked_addrs]
        return self

    def encode(self):
        """
        Encode the sysid data into a packed binary.

        Returns:
            bytes: packed sysid data
        """
        hdr = struct.pack('=I I', self.magic, self.version)
        uuid = self.uuid.encode()
        num_addrs = struct.pack('=I', len(self.addrs))
        data = hdr + uuid + num_addrs
        for addr in self.addrs:
            pa = socket.inet_aton(addr)
            data += pa
        return data

    def parse_yaml(self, text):
        """
        Parse a yaml string containing the sysid data.

        Args:
            text (str): yaml string
        """
        in_addrs = False
        self.addrs = []
        for line in text.splitlines():
            if line == '---':
                continue
            if not in_addrs:
                m = re.match(r'\s*magic:\s+0x([0-9a-fA-F]+)', line)
                if m:
                    self.magic = int(m.group(1), base=16)
                    continue
                m = re.match(r'\s*version:\s+([0-9]+)', line)
                if m:
                    self.version = int(m.group(1))
                    continue
                m = re.match(r'\s*uuid:\s+(.*)', line)
                if m:
                    self.uuid = UUID.from_str(m.group(1))
                    continue
                m = re.match(r'\s*addresses:\s*$', line)
                if m:
                    in_addrs = True
            else:
                m = re.match(r'\s*-\s+([0-9\.]+)', line)
                if m:
                    self.addrs.append(m.group(1))
                else:
                    in_addrs = False

    def as_yaml(self):
        """
        Format the sysid info as a yaml string.

        Returns:
            str: sysid data as a yaml string.
        """
        if self.magic is None:
            magic = 'null'
        else:
            magic = '0x{0:x}'.format(self.magic)
        if self.version is None:
            version = 'null'
        else:
            version = self.version
        if self.uuid is None:
            uuid = 'null'
        else:
            uuid = '{0}'.format(self.uuid)
        if self.addrs is None:
            addrs = ''
        else:
            addrs = '\n' + '\n'.join(['- ' + a for a in self.addrs])
        yaml = """\
---
magic: {0}
version: {1}
uuid: {2}
addresses:{3}""".format(magic, version, uuid, addrs)
        return yaml

    def __str__(self):
        """
        Return a yaml string representation of the sysid data.
        """
        return self.as_yaml()

    def __repr__(self):
        return \
            "<Sysid:"\
            " magic={self.magic}"\
            " version={self.version}"\
            " uuid={self.uuid}"\
            " addrs={self.addrs}"\
            ">".format(self=self)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', help='command to run',
                        choices=('sysid2yaml', 'yaml2sysid'))
    parser.add_argument('-s', '--sysid', help='sysid filename', default='sysid')
    parser.add_argument('-f', '--filename', help='yaml file', default='-')
    args = parser.parse_args()

    if args.command == 'sysid2yaml':
        sysid = Sysid(args.sysid)
        sysid.export(args.filename, fmt='yaml')
    elif args.command == 'yaml2sysid':
        sysid = Sysid.from_yaml(args.filename)
        sysid.write(args.sysid)
    else:
        raise AssertionError('bad command')

if __name__ == '__main__':
    sys.exit(main())
