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


is_windows = sys.platform.startswith('win32')
script_ext = '.bat' if is_windows else '.sh'

tests_dir = os.path.dirname(os.path.abspath(__file__))
resources_dir = os.path.join(tests_dir, 'resources')


iterator_parameters_combined = [
    ('--subset-iterator=forward', '--complement-iterator=forward'),
    ('--subset-iterator=forward', '--complement-iterator=backward'),
    ('--subset-iterator=backward', '--complement-iterator=forward'),
    ('--subset-iterator=backward', '--complement-iterator=backward'),
    ('--complement-first', '--subset-iterator=forward', '--complement-iterator=forward'),
    ('--complement-first', '--subset-iterator=forward', '--complement-iterator=backward'),
    ('--complement-first', '--subset-iterator=backward', '--complement-iterator=forward'),
    ('--complement-first', '--subset-iterator=backward', '--complement-iterator=backward'),
]
iterator_parameters_noncombined = [
    ('--subset-iterator=skip', '--complement-iterator=forward'),
    ('--subset-iterator=skip', '--complement-iterator=backward'),
]


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
              + ('--log-level=DEBUG', ) \
              + args
        proc = subprocess.Popen(cmd, cwd=resources_dir)
        proc.communicate()
        assert proc.returncode == 0
        assert filecmp.cmp(os.path.join(out_dir, inp), os.path.join(resources_dir, exp))

    @pytest.mark.parametrize('args_parallel', [
        (),
    ])
    @pytest.mark.parametrize('args_split', [
        ('--split=balanced', ),
        ('--split=zeller', ),
    ])
    @pytest.mark.parametrize('args_it',
        iterator_parameters_combined + iterator_parameters_noncombined
    )
    @pytest.mark.parametrize('args_cache', [
        ('--cache=none', ),
        ('--cache=config', ),
        ('--cache=content', ),
    ])
    def test_light(self, test, inp, exp, tmpdir, args_atom, args_parallel, args_split, args_it, args_cache):
        self._run_picire(test, inp, exp, tmpdir,
                         args_atom + args_parallel + args_split + args_it + args_cache)

    @pytest.mark.parametrize('args_parallel', [
        ('--parallel', ),
    ])
    @pytest.mark.parametrize('args_split', [
        ('--split=zeller', ),
    ])
    @pytest.mark.parametrize('args_it',
        iterator_parameters_combined + iterator_parameters_noncombined
    )
    @pytest.mark.parametrize('args_cache', [
        ('--cache=none', ),
        ('--cache=config', ),
        ('--cache=content', ),
    ])
    def test_parallel(self, test, inp, exp, tmpdir, args_atom, args_parallel, args_split, args_it, args_cache):
        self._run_picire(test, inp, exp, tmpdir,
                         args_atom + args_parallel + args_split + args_it + args_cache)

    @pytest.mark.parametrize('args_parallel', [
        ('--parallel', '--combine-loops', ),
    ])
    @pytest.mark.parametrize('args_split', [
        ('--split=zeller', ),
    ])
    @pytest.mark.parametrize('args_it',
        iterator_parameters_combined
    )
    @pytest.mark.parametrize('args_cache', [
        ('--cache=config', ),
    ])
    def test_combined(self, test, inp, exp, tmpdir, args_atom, args_parallel, args_split, args_it, args_cache):
        self._run_picire(test, inp, exp, tmpdir,
                         args_atom + args_parallel + args_split + args_it + args_cache)
