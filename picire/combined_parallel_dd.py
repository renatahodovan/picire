# Copyright (c) 2016-2018 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import logging
import os

from . import config_iterators
from . import config_splitters
from . import parallel_loop
from .abstract_dd import AbstractDD
from .abstract_parallel_dd import AbstractParallelDD

logger = logging.getLogger(__name__)


class CombinedParallelDD(AbstractParallelDD):

    def __init__(self, test, *, cache=None, split=config_splitters.zeller,
                 proc_num=os.cpu_count(), max_utilization=100,
                 config_iterator=config_iterators.forward):
        """
        Initialize a CombinedParallelDD object.

        :param test: A callable tester object.
        :param cache: Cache object to use.
        :param split: Splitter method to break a configuration up to n part.
        :param proc_num: The level of parallelization.
        :param max_utilization: The maximum CPU utilization accepted.
        :param config_iterator: Reference to a generator function that provides config indices in an arbitrary order.
        """
        AbstractParallelDD.__init__(self, test, split, proc_num, max_utilization, cache=cache)

        self._config_iterator = config_iterator

    def _reduce_config(self, run, config, subsets, complement_offset):
        """
        Perform the reduce task using multiple processes.
        Subset and complement set tests are mixed and don't wait for each other.

        :param run: The index of the current iteration.
        :param config: The current configuration under testing.
        :param subsets: List of sets that the current configuration is split to.
        :param complement_offset: A compensation offset needed to calculate the index
               of the first unchecked complement (optimization purpose only).
        :return: Tuple: (failing config or None, next n or None, next complement_offset).
        """
        n = len(subsets)
        self._fail_index.value = -1
        ploop = parallel_loop.Loop(self._proc_num, self._max_utilization)
        for i in self._config_iterator(2 * n):
            if i is None:
                continue

            if i < n:
                config_id = (run, 's', i)
                config_set = subsets[i]
            else:
                j = int((i - n + complement_offset) % n)
                config_id = (run, 'c', j)
                config_set = self.minus(config, subsets[j])

            # If we checked this test before, return its result
            outcome = self.lookup_cache(config_set, config_id)
            if outcome == self.PASS:
                continue
            elif outcome == self.FAIL:
                self._fail_index.value = i
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
                return subsets[fvalue], 2, 0
            # Complement fail.
            else:
                j = int((fvalue - n + complement_offset) % n)
                complement = self.minus(config, subsets[j])
                return complement, max(n - 1, 2), j

        return None, None, complement_offset
