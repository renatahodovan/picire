# Copyright (c) 2017 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import pytest
import sys


is_windows = sys.platform.startswith('win32')

pytest_mark_skipif_windows = pytest.mark.skipif(is_windows,
                                                reason='unsupported on Windows')

script_ext = '.bat' if is_windows else '.sh'
