# Copyright (c) 2016-2023 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import logging

from . import parallel_loop
from .abstract_parallel_dd import AbstractParallelDD
from .iterator import forward
from .outcome import Outcome

logger = logging.getLogger(__name__)


class CombinedIterator(object):
    """
    Callable iterator class that acts as generator when subset and complement
    check loops are combined.
    """

    def __init__(self, subset_first=True, subset_iterator=forward, complement_iterator=forward):
        """
        Initialize CombinedIterator with the basic settings describing the order
        of subset and complement checks together with the certain iterators.

        :param subset_first: Boolean value denoting whether the reduce has to
            start with the subset based approach or not.
        :param subset_iterator: Reference to a generator function that provides
            config indices in an arbitrary order.
        :param complement_iterator: Reference to a generator function that
            provides config indices in an arbitrary order.
        """
        self._subset_first = subset_first
        self._subset_iterator = subset_iterator
        self._complement_iterator = complement_iterator

    def __call__(self, n):
        """
        Provide the index of the next configuration according to the settings.

        :param n: The number of configurations (subset and combined configs
            altogether).
        :return: The index of the next configuration.
        """
        if self._subset_first:
            for i in self._subset_iterator(n // 2):
                yield i
            for i in self._complement_iterator(n // 2):
                yield i + n // 2
        else:
            for i in self._complement_iterator(n // 2):
                yield i + n // 2
            for i in self._subset_iterator(n // 2):
                yield i


class CombinedParallelDD(AbstractParallelDD):

    def __init__(self, test, *, split=None, cache=None, id_prefix=None,
                 proc_num=None, max_utilization=None,
                 config_iterator=None):
        """
        Initialize a CombinedParallelDD object.

        :param test: A callable tester object.
        :param split: Splitter method to break a configuration up to n part.
        :param cache: Cache object to use.
        :param id_prefix: Tuple to prepend to config IDs during tests.
        :param proc_num: The level of parallelization.
        :param max_utilization: The maximum CPU utilization accepted.
        :param config_iterator: Reference to a generator function that provides
            config indices in an arbitrary order.
        """
        super().__init__(test=test, split=split, cache=cache, id_prefix=id_prefix, proc_num=proc_num, max_utilization=max_utilization)

        self._config_iterator = config_iterator or forward

    def _reduce_config(self, run, subsets, complement_offset):
        """
        Perform the reduce task using multiple processes. Subset and complement
        set tests are mixed and don't wait for each other.

        :param run: The index of the current iteration.
        :param subsets: List of sets that the current configuration is split to.
        :param complement_offset: A compensation offset needed to calculate the
            index of the first unchecked complement (optimization purpose only).
        :return: Tuple: (list of subsets composing the failing config or None,
            next complement_offset).
        """
        n = len(subsets)
        self._fail_index.value = -1
        ploop = parallel_loop.Loop(self._proc_num, self._max_utilization)
        for i in self._config_iterator(2 * n):
            if i is None:
                continue

            if i < n:
                config_id = (f'r{run}', f's{i}')
                config_set = subsets[i]
            else:
                i = int((i - n + complement_offset) % n) + n
                config_id = (f'r{run}', f'c{i - n}')
                config_set = [c for si, s in enumerate(subsets) for c in s if si != i - n]

            # If we checked this test before, return its result
            outcome = self._lookup_cache(config_set, config_id)
            if outcome is Outcome.PASS:
                continue
            if outcome is Outcome.FAIL:
                self._fail_index.value = i
                ploop.brk()
                break

            # Break if we found a FAIL either in the cache or be testing it now.
            if not ploop.do(self._loop_body, (config_set, i, config_id)):
                # if do() returned False, the test was not started
                break
        ploop.join()

        # fvalue contains the index of the cycle in the previous loop
        # which was found interesting. Otherwise it's -1.
        fvalue = self._fail_index.value
        if fvalue != -1:
            # Subset fail.
            if fvalue < n:
                return [subsets[fvalue]], 0
            # Complement fail.
            return subsets[:fvalue - n] + subsets[fvalue - n + 1:], fvalue - n

        return None, complement_offset
