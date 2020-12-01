#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
#
# Copyright (c) 2020, Sine Nomine Associates
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
# OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

import errno
import json
import os.path
import subprocess
import time
import unittest

from vlaudit_stats import ignore_errno

COMMAND = ['./vlaudit-stats', '--quiet', '--force-time', '1607405378',
           '--top-limit', '100']

# AuditFile.TestCase is just our base class for running tests based on audit
# files. It's wrapped in the 'AuditFile' class so unittest doesn't try to run
# AuditFile.TestCase as a test to run; it'll only run the derived classes below
# that have actual data.
class AuditFile:
    class TestCase(unittest.TestCase):
        # Uncomment this when a test fails to see what actually is wrong in the
        # stats dict as a diff.
        maxDiff = None

        # overridden by the actual test cases
        audit_path = None

        fifo_path = 'test.fifo'
        sock_path = 'test.sock'
        server_proc = None

        def result_path(self, fmt):
            suffix = ".audit"

            if not self.audit_path.endswith(suffix):
                raise ValueError("audit path %s does not end in %s" % (self.audit_path, suffix))

            # strip off the trailing ".audit", and add ".<fmt>"
            return self.audit_path[:-len(suffix)] + "." + fmt

        # run 'stats-get' for each format, and compare to the expected output
        def check_stats(self, *extra_argv):
            base_argv = COMMAND + ['stats-get'] + list(extra_argv)

            for fmt in ['text', 'json']:
                res_path = self.result_path(fmt)

                argv = base_argv + ['--format', fmt]
                with self.subTest(audit_path=self.audit_path,
                                  res_path=res_path, argv=argv):
                    with open(res_path) as fh:
                        result = fh.read()
                    proc = subprocess.run(argv, stdout=subprocess.PIPE,
                                          check=True, universal_newlines=True,
                                          timeout=5)
                    if fmt == 'json':
                        self.assertEqual(json.loads(result), json.loads(proc.stdout))
                    else:
                        self.assertEqual(result, proc.stdout)

        def test_auditfile(self):
            self.check_stats('--from-auditlog', self.audit_path)

        def test_fifo(self):
            os.mkfifo(self.fifo_path)

            # Start the server proc
            argv = COMMAND + ['daemon', self.fifo_path,
                   '--socket', self.sock_path]
            self.server_proc = subprocess.Popen(argv)

            # Write our saved audit data to the pipe
            with open(self.fifo_path, 'w') as fifo_fh, \
                 open(self.audit_path) as audit_fh:
                fifo_fh.write(audit_fh.read())

            # Give the server a little time to process the data
            time.sleep(0.125)

            self.check_stats('--socket', self.sock_path)

        def tearDown(self):
            try:
                # shutdown the running server proc
                if self.server_proc is not None:
                    self.server_proc.terminate()
                    try:
                        self.server_proc.wait(1)
                    except subprocess.TimeoutExpired:
                        self.server_proc.kill()
                        raise
            finally:
                self.server_proc = None

                # remove our temporary files
                for path in [self.fifo_path, self.sock_path]:
                    with ignore_errno(errno.ENOENT):
                        os.unlink(path)

class AuditSimple(AuditFile.TestCase):
    audit_path = 'simple.audit'

class AuditGap(AuditFile.TestCase):
    audit_path = 'gap.audit'

class AuditBig(AuditFile.TestCase):
    audit_path = 'big.audit'

if __name__ == '__main__':
    unittest.main()
