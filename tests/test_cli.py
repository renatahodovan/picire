# Copyright (c) 2016-2017 Renata Hodovan, Akos Kiss.
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


tests_dir = os.path.dirname(os.path.abspath(__file__))
resources_dir = os.path.join(tests_dir, 'resources')


@pytest.mark.parametrize('args_parallel', [
    (),
    ('--parallel', ),
    ('--parallel', '--combine-loops', ),
])
@pytest.mark.parametrize('args_split', [
    ('--split=balanced', ),
    ('--split=zeller', ),
])
@pytest.mark.parametrize('args_first', [
    (),
    ('--complement-first', ),
])
@pytest.mark.parametrize('args_subsit', [
    ('--subset-iterator=forward', ),
    ('--subset-iterator=backward', ),
    ('--subset-iterator=skip', ),
])
@pytest.mark.parametrize('args_complit', [
    ('--complement-iterator=forward', ),
    ('--complement-iterator=backward', ),
])
@pytest.mark.parametrize('args_cache', [
    ('--cache=none', ),
    ('--cache=config', ),
    ('--cache=content', ),
])
class TestCli:

    def _run_picire(self, test, inp, exp, tmpdir, args):
        out_dir = '%s' % tmpdir
        cmd = (sys.executable, '-m', 'picire') \
              + ('--test=' + test, '--input=' + inp, '--out=' + out_dir) \
              + ('--log-level=DEBUG', ) \
              + args
        proc = subprocess.Popen(cmd, cwd=resources_dir)
        proc.communicate()
        assert proc.returncode == 0
        assert filecmp.cmp(os.path.join(out_dir, inp), os.path.join(resources_dir, exp))

    @pytest.mark.parametrize('test, inp, exp', [
        ('test-json-extra-comma.sh', 'inp-extra-comma.json', 'exp-extra-comma.json'),
        ('test-sumprod10-sum.sh', 'inp-sumprod10.py', 'exp-sumprod10-sum.py'),
        ('test-sumprod10-prod.sh', 'inp-sumprod10.py', 'exp-sumprod10-prod.py'),
    ])
    def test_line(self, test, inp, exp, tmpdir, args_parallel, args_split, args_first, args_subsit, args_complit, args_cache):
        self._run_picire(test, inp, exp, tmpdir,
                         ('--atom=line', ) + args_parallel + args_split + args_first + args_subsit + args_complit + args_cache)

    @pytest.mark.parametrize('test, inp, exp', [
        ('test-json-invalid-escape.sh', 'inp-invalid-escape.json', 'exp-invalid-escape.json'),
    ])
    def test_char(self, test, inp, exp, tmpdir, args_parallel, args_split, args_first, args_subsit, args_complit, args_cache):
        self._run_picire(test, inp, exp, tmpdir,
                         ('--atom=char', ) + args_parallel + args_split + args_first + args_subsit + args_complit + args_cache)
