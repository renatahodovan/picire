# Copyright (c) 2016-2020 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import filecmp
import os
import pytest
import subprocess
import sys


is_windows = sys.platform.startswith('win32')
script_ext = '.bat' if is_windows else '.sh'

tests_dir = os.path.dirname(os.path.abspath(__file__))
resources_dir = os.path.join(tests_dir, 'resources')


@pytest.mark.parametrize('test, inp, exp, args_atom', [
    ('test-json-extra-comma', 'inp-extra-comma.json', 'exp-extra-comma.json', ('--atom=line', )),
    ('test-sumprod10-sum', 'inp-sumprod10.py', 'exp-sumprod10-sum.py', ('--atom=line', )),
    ('test-sumprod10-prod', 'inp-sumprod10.py', 'exp-sumprod10-prod.py', ('--atom=line', )),
    ('test-json-invalid-escape', 'inp-invalid-escape.json', 'exp-invalid-escape.json', ('--atom=char', )),
])
class TestCli:

    def _run_picire(self, test, inp, exp, tmpdir, args):
        out_dir = '%s' % tmpdir
        cmd = (sys.executable, '-m', 'picire') \
              + ('--test=' + test + script_ext, '--input=' + inp, '--out=' + out_dir) \
              + ('--log-level=TRACE', ) \
              + args
        proc = subprocess.Popen(cmd, cwd=resources_dir)
        proc.communicate()
        assert proc.returncode == 0
        assert filecmp.cmp(os.path.join(out_dir, inp), os.path.join(resources_dir, exp))

    @pytest.mark.parametrize('args', [
        ('--split=balanced', '--subset-iterator=forward', '--complement-iterator=forward', '--cache=none'),
        ('--split=zeller', '--subset-iterator=forward', '--complement-iterator=backward', '--cache=config'),
        ('--split=balanced', '--complement-first', '--subset-iterator=backward', '--complement-iterator=forward', '--cache=content'),
        ('--split=zeller', '--complement-first', '--subset-iterator=backward', '--complement-iterator=backward', '--cache=none'),
        ('--split=balanced', '--subset-iterator=skip', '--complement-iterator=forward', '--cache=config'),
        ('--split=zeller', '--subset-iterator=skip', '--complement-iterator=backward', '--cache=content'),
    ])
    def test_light(self, test, inp, exp, tmpdir, args_atom, args):
        self._run_picire(test, inp, exp, tmpdir, args_atom + args)

    @pytest.mark.parametrize('args', [
        ('--split=zeller', '--complement-first', '--subset-iterator=forward', '--complement-iterator=forward', '--cache=config'),
        ('--split=balanced', '--complement-first', '--subset-iterator=forward', '--complement-iterator=backward', '--cache=content'),
        ('--split=zeller', '--subset-iterator=backward', '--complement-iterator=forward', '--cache=none'),
        ('--split=balanced', '--subset-iterator=backward', '--complement-iterator=backward', '--cache=config'),
        ('--split=zeller', '--subset-iterator=skip', '--complement-iterator=forward', '--cache=content'),
        ('--split=balanced', '--subset-iterator=skip', '--complement-iterator=backward', '--cache=none'),
    ])
    def test_parallel(self, test, inp, exp, tmpdir, args_atom, args):
        self._run_picire(test, inp, exp, tmpdir, args_atom + ('--parallel', ) + args)

    @pytest.mark.parametrize('args', [
        ('--split=zeller', '--subset-iterator=forward', '--complement-iterator=forward', '--cache=content'),
        ('--split=balanced', '--subset-iterator=forward', '--complement-iterator=backward', '--cache=none'),
        ('--split=zeller', '--complement-first', '--subset-iterator=backward', '--complement-iterator=forward', '--cache=config'),
        ('--split=balanced', '--complement-first', '--subset-iterator=backward', '--complement-iterator=backward', '--cache=content'),
    ])
    def test_combined(self, test, inp, exp, tmpdir, args_atom, args):
        self._run_picire(test, inp, exp, tmpdir, args_atom + ('--parallel', '--combine-loops', ) + args)
