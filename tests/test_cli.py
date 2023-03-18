# Copyright (c) 2016-2023 Renata Hodovan, Akos Kiss.
# Copyright (c) 2023 Daniel Vince.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import os
import platform
import pytest
import subprocess
import sys


is_windows = sys.platform.startswith('win32')
script_ext = '.bat' if is_windows else '.sh'

is_cpython = platform.python_implementation() == 'CPython'

tests_dir = os.path.dirname(os.path.abspath(__file__))
resources_dir = os.path.join(tests_dir, 'resources')


@pytest.mark.parametrize('test, inp, exp, args_atom', [
    pytest.param('test-json-extra-comma', 'inp-extra-comma.json', 'exp-extra-comma.json', ('--atom=line', ),
                 marks=pytest.mark.skipif(not is_cpython, reason='json error messages are implementation-specific')),
    ('test-sumprod10-sum', 'inp-sumprod10.py', 'exp-sumprod10-sum.py', ('--atom=line', )),
    ('test-sumprod10-prod', 'inp-sumprod10.py', 'exp-sumprod10-prod.py', ('--atom=line', )),
    pytest.param('test-json-invalid-escape', 'inp-invalid-escape.json', 'exp-invalid-escape.json', ('--atom=char', ),
                 marks=pytest.mark.skipif(not is_cpython, reason='json error messages are implementation-specific')),
    pytest.param('test-json-invalid-escape', 'inp-invalid-escape.json', 'exp-invalid-escape.json', ('--atom=both', ),
                 marks=pytest.mark.skipif(not is_cpython, reason='json error messages are implementation-specific')),
])
class TestCli:

    def _run_picire(self, test, inp, exp, tmpdir, args):
        out_dir = str(tmpdir)
        cmd = (sys.executable, '-m', 'picire') \
              + (f'--test={test}{script_ext}', f'--input={inp}', f'--out={out_dir}') \
              + ('--log-level=TRACE', ) \
              + args
        subprocess.run(cmd, cwd=resources_dir, check=True)

        with open(os.path.join(out_dir, inp), 'rb') as outf:
            outb = outf.read()
        with open(os.path.join(resources_dir, exp), 'rb') as expf:
            expb = expf.read()
        assert outb == expb

    @pytest.mark.parametrize('args', [
        ('--split=balanced', '--subset-iterator=forward', '--complement-iterator=forward', '--cache=config'),
        ('--split=zeller', '--subset-iterator=forward', '--complement-iterator=backward', '--cache=content'),
        ('--split=balanced', '--complement-first', '--subset-iterator=backward', '--complement-iterator=forward', '--cache=content-hash'),
        ('--split=zeller', '--complement-first', '--subset-iterator=backward', '--complement-iterator=backward', '--cache=config-tuple', '--cache-fail', '--no-cache-evict-after-fail'),
        ('--split=balanced', '--subset-iterator=skip', '--complement-iterator=forward', '--cache=content', '--cache-fail', '--no-cache-evict-after-fail'),
        ('--split=zeller', '--subset-iterator=skip', '--complement-iterator=backward', '--cache=content-hash', '--cache-fail', '--no-cache-evict-after-fail'),
    ])
    def test_dd(self, test, inp, exp, tmpdir, args_atom, args):
        self._run_picire(test, inp, exp, tmpdir, args_atom + args)

    @pytest.mark.parametrize('args', [
        ('--split=zeller', '--complement-first', '--subset-iterator=forward', '--complement-iterator=forward', '--cache=config-tuple'),
        ('--split=balanced', '--complement-first', '--subset-iterator=forward', '--complement-iterator=backward', '--cache=content'),
        ('--split=zeller', '--subset-iterator=backward', '--complement-iterator=forward', '--cache=content-hash'),
        ('--split=balanced', '--subset-iterator=backward', '--complement-iterator=backward', '--cache=config', '--cache-fail', '--no-cache-evict-after-fail'),
        ('--split=zeller', '--subset-iterator=skip', '--complement-iterator=forward', '--cache=content', '--cache-fail', '--no-cache-evict-after-fail'),
        ('--split=balanced', '--subset-iterator=skip', '--complement-iterator=backward', '--cache=content-hash', '--cache-fail', '--no-cache-evict-after-fail'),
    ])
    def test_parallel(self, test, inp, exp, tmpdir, args_atom, args):
        self._run_picire(test, inp, exp, tmpdir, args_atom + ('--parallel',) + args)
