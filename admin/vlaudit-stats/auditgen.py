#!/usr/bin/env python3

# A simple script to generate the contents of "big.audit".

import os.path
import time

class AuditGen:
    def __init__(self, fh):
        self.audit_fh = fh
        self.audit_counter = 0
        self.audit_time = 1600000000

    def emit_line(self, evdata):
        counter = self.audit_counter
        self.audit_counter += 1

        ts = time.ctime(self.audit_time)
        self.audit_time += 1

        self.audit_fh.write("[%d] %s EVENT %s \n" % (counter, ts, evdata))

    def aud_off(self):
        self.emit_line("AFS_Aud_Off CODE 0")

    def vl_regadd(self, code, host, uuid):
        self.emit_line("AFS_VL_RegAdd CODE %d NAME afs HOST %s UUID %s" % (
                       code, host, uuid))

    def vl_getbyid(self, code, host, req_id, volid, volname):
        self.emit_line("AFS_Aud_Unauth CODE -1 STR AFS_VL_GetEnt")
        self.emit_line("AFS_VL_GetEnt CODE %d NAME --UnAuth-- HOST %s LONG %d LONG %d STR %s" % (
                       code, host, req_id, volid, volname))

    def vl_getbyname(self, code, host, req_name, volid, volname):
        self.emit_line("AFS_Aud_Unauth CODE -1 STR AFS_VL_GetEnt")
        self.emit_line("AFS_VL_GetEnt CODE %d NAME --UnAuth-- HOST %s STR %s LONG %d STR %s" % (
                       code, host, req_name, volid, volname))

    def host_str(self, idx):
        if idx < 0:
            raise RuntimeError("Bad host idx %d" % idx)
        if idx <= 254:
            return '192.0.2.%d' % (idx+1)
        if idx <= 509:
            return '198.51.100.%d' % (idx - 255 + 1)
        raise RuntimeError("Bad host idx %d" % idx)

    def hit_vol(self, n_hits, volname, rwid=0, rwname='', code=0):
        for host_i in range(1, n_hits+1):
            self.vl_getbyname(code, self.host_str(host_i), volname, rwid, rwname)

    def hit_host(self, n_hits, host_i, byname=False):
        host = self.host_str(host_i)
        for hit_i in range(1, n_hits+1):
            rwid = 546870912 + hit_i*3
            rwname = 'vol.%x' % hit_i

            if byname:
                volname = '%s.readonly' % rwname
            else:
                volname = '%d' % (rwid+1)
            self.vl_getbyname(0, host, volname, rwid, rwname)

    def gen(self):
        self.aud_off()
        self.vl_regadd(0, self.host_str(0), '000c4b94-8644-1d3a-90-fa-e71011acaa77')

        self.hit_host(1000, 1)
        self.hit_host(1000, 2)
        self.hit_host(1000, 3)

        self.hit_vol(5, '536870913', 536870912, 'root.cell')
        self.hit_vol(20, 'root.cell.readonly', 536870912, 'root.cell')
        self.hit_vol(30, '536870913', 536870912, 'root.cell')
        self.hit_vol(40, '536870915', 536870915, 'vol.foo')
        self.hit_host(50, 205, byname=True)

        self.hit_vol(60, 'vol.bogus', code=363524)


if __name__ == '__main__':
    fname = "foo.audit"
    print("Generating audit messages to %s" % fname)
    with open(fname, 'w') as fh:
        gen = AuditGen(fh)
        gen.gen()
