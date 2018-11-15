#!/usr/bin/python3
#
# Copyright (c) 2018, Sine Nomine Associates ("SNA")
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
# vldbutil.py
#
# Just a simple module for interpreting some data in an openafs ubik .DB0 file
# containing a vldb version 4 database. Useful when debugging issues with the
# actual database parts of the vldb.
#
# Example usage in main() below, but intended more to be used interactively
# from a python prompt, e.g.:
#
# $ python3
# >>> import vldbutil
# >>> vldb = vldbutil.DB0('foo.DB0')
# >>> vldb.lookup_name('root.cell')

import argparse
import struct
import sys

class UbikHeader:
    # 4-byte int
    magic = None
    # 2-byte int
    pad1 = None
    # 2-byte int
    size = None
    # 4-byte int
    v_epoch = None
    # 4-byte int
    v_counter = None

    _s = struct.Struct('>I2H2I')

    def __init__(self, buf=None, fh=None):
        if fh is not None:
            fh.seek(0)
            buf = fh.read(self._s.size)
        if buf is not None:
            vals = self._s.unpack(buf)
            self.magic = vals[0]
            self.pad1 = vals[1]
            self.size = vals[2]
            self.v_epoch = vals[3]
            self.v_counter = vals[4]

    def __str__(self):
        return "<UbikHeader: version %u.%u (0x%x 0x%x 0x%x)>" % ( \
               self.v_epoch, self.v_counter,
               self.magic, self.pad1, self.size)

class VLHeader:
    # 4-byte ints
    vldbversion = None
    headersize = None
    freePtr = None
    eofPtr = None
    allocs = None
    frees = None
    MaxVolumeId = None
    totalRW = None
    totalRO = None
    totalBK = None

    # array of 4-byte ints, length 255
    IpMappedAddr = None

    # arrays of 4-byte ints, length 8191
    VolnameHash = None
    VolidHashRW = None
    VolidHashRO = None
    VolidHashRW = None

    # 4 byte int
    SIT = None

    _s = struct.Struct('>10I'+'255I'+'8191I'+'8191I'+'8191I'+'8191I'+'I')

    def __init__(self, buf):
        vals = self._s.unpack(buf)
        self.vldbversion = vals[0]
        self.headersize = vals[1]
        self.freePtr = vals[2]
        self.eofPtr = vals[3]
        self.allocs = vals[4]
        self.frees = vals[5]
        self.MaxVolumeId = vals[6]
        self.totalRW = vals[7]
        self.totalRO = vals[8]
        self.totalBK = vals[9]

        self.IpMappedAddr = vals[10:265]
        self.VolnameHash = vals[265:8456]
        self.VolidHashRW = vals[8456:16647]
        self.VolidHashRO = vals[16647:24838]
        self.VolidHashBK = vals[24838:33029]

        self.SIT = vals[33029]

    def __str__(self):
        ret = "<VLHeader:"
        for field in "vldbversion headersize freePtr eofPtr allocs frees MaxVolumeId totalRW totalRO totalBK SIT".split():
            ret += " %s: %u" % (field, getattr(self, field))
        return ret+">"

class VLEntry:
    # virtual fields, not on disk
    address = None
    offset = None

    # 4-byte ints
    rwid = None
    roid = None
    bkid = None
    flags = None
    LockAfsId = None
    LockTimestamp = None
    cloneId = None
    nextIdHashRW = None
    nextIdHashRO = None
    nextIdHashBK = None
    nextNameHash = None

    # fixed-size string, 65 bytes
    name = None

    # arrays of 1-byte ints, length 13
    serverNumber = None
    serverPartition = None
    serverFlags = None

    _s = struct.Struct('>11I65s13B13B13B')

    def __init__(self, buf, address):
        self.address = address
        self.offset = address + VLDB0.DBASE_OFFSET

        vals = self._s.unpack(buf)
        self.rwid = vals[0]
        self.roid = vals[1]
        self.bkid = vals[2]
        self.flags = vals[3]
        self.LockAfsId = vals[4]
        self.LockTimestamp = vals[5]
        self.cloneId = vals[6]
        self.nextIdHashRW = vals[7]
        self.nextIdHashRO = vals[8]
        self.nextIdHashBK = vals[9]
        self.nextNameHash = vals[10]
        self.name = vals[11].decode('ascii').rstrip('\x00')
        self.serverNumber = vals[12:25]
        self.serverPartition = vals[25:38]
        self.serverFlags = vals[38:51]

    def __str__(self):
        return "<VLEntry: name '%s' address: %u volid %u %u %u>" % ( \
               self.name, self.address, self.rwid, self.roid, self.bkid)

    def __repr__(self):
        ret = "<VLEntry: name: '%s'" % self.name
        for field in "address offset rwid roid bkid flags LockAfsId LockTimestamp cloneId nextIdHashRW nextIdHashRO nextIdHashBK nextNameHash".split():
            ret += " %s: %u" % (field, getattr(self, field))
        return ret+">"

class VLDB0:
    HASHSIZE = 8191
    DBASE_OFFSET = 64

    @classmethod
    def hash_name(cls, volname):
        ret = 0
        for c in reversed(volname):
            val = ord(c)
            if val > 255:
                raise TypeError("Non-ascii char '%s'", val)
            ret = (ret * 63 + (val - 63)) % (2**32)
        ret = ret % cls.HASHSIZE
        return ret

    @classmethod
    def hash_id(cls, volid):
        return volid % cls.HASHSIZE

    def __init__(self, filename):
        self.fh = open(filename, 'rb')
        self.ubik_header = UbikHeader(fh=self.fh)
        self.vl_header = VLHeader(self.vlread(0, VLHeader._s.size))

    def vlread(self, address, size):
        self.fh.seek(address + self.DBASE_OFFSET)
        return self.fh.read(size)

    def vlreadentry(self, address):
        buf = self.vlread(address, VLEntry._s.size)
        return VLEntry(buf, address)

    def _walk_hash(self, field_name, addr):
        while addr != 0:
            vlentry = self.vlreadentry(addr)
            yield vlentry
            addr = getattr(vlentry, field_name)
            #print("%s is %u" % (field_name, addr))

    def walk_namehash(self, addr):
        for entry in self._walk_hash('nextNameHash', addr):
            yield entry

    def walk_rwidhash(self, addr):
        for entry in self._walk_hash('nextIdHashRW', addr):
            yield entry

    def walk_freelist(self):
        for entry in self.walk_rwidhash(self.vl_header.freePtr):
            yield entry

    def walk_entries(self, start=None):
        addr = start
        if addr is None:
            addr = self.vl_header.headersize
        while True:
            #print("trying address %u" % addr)
            entry = self.vlreadentry(addr)
            #print("entry: %s" % str(entry))
            yield entry

            if entry.flags == 0x8:
                # sizeof mh entry
                addr += 8192
            else:
                # sizeof(vlentry)
                addr += 148

    def lookup_name(self, volname):
        idx = self.hash_name(volname)
        addr = self.vl_header.VolnameHash[idx]
        print("Initial hash index %u, address %u" % (idx, addr))

        for entry in self.walk_namehash(addr):
            #print("entry: %s" % str(entry))
            if entry.name == volname:
                return entry

        return None

    def search_name(self, volname):
        addr = self.vl_header.headersize
        for entry in self.walk_entries():
            if entry.name == volname:
                return entry

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('filename')

    args = parser.parse_args(argv[1:])

    # Example usage of some simple functionality:

    vldb = VLDB0(args.filename)
    print("ubik header: %s" % vldb.ubik_header)
    print("vlheader: %s" % vldb.vl_header)

    entry = vldb.lookup_name('root.cell')
    print("root.cell: %s" % entry)

    #entry = vldb.search_name('root.cell')
    #print("foo: %s" % entry)

    print("free entries:")
    for entry in vldb.walk_freelist():
        print("free entry: %r" % entry)

if __name__ == '__main__':
    main(sys.argv)
