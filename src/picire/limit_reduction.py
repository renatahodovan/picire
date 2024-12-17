# Copyright (c) 2023 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

from datetime import datetime, timedelta
from time import time

from .exception import ReductionStopped


class LimitReduction:
    """
    Limit the execution time and/or the number of performed tests during a
    reduction.
    """

    def __init__(self, *, deadline=None, max_tests=None):
        """
        :param deadline: A soft limit on the execution time of the reduction.
            The deadline may be given as a :class:`datetime` object, as a
            :class:`timedelta` object (relative to :meth:`~datetime.now`), or as
            a ``float`` POSIX timestamp (as returned by :meth:`time.time`).
        :param max_tests: A hard limit on the maximum number of tests that may
            be executed.
        """
        self._deadline = deadline
        self._max_tests = max_tests

        if isinstance(deadline, timedelta):
            deadline = datetime.now() + deadline
        if isinstance(deadline, datetime):
            deadline = deadline.timestamp()
        self._deadline_timestamp = deadline
        self._tests_left = max_tests

    def __call__(self):
        if self._deadline is not None:
            if time() >= self._deadline_timestamp:
                raise ReductionStopped('deadline expired')
        if self._max_tests is not None:
            if self._tests_left <= 0:
                raise ReductionStopped('maximum number of tests performed')
            self._tests_left -= 1

    def __str__(self):
        cls = self.__class__
        params = []
        if self._deadline is not None:
            params.append(f'deadline={self._deadline}')
        if self._max_tests is not None:
            params.append(f'max_tests={self._max_tests}')
        return f'{cls.__module__}.{cls.__name__}({", ".join(params)})'
