# Copyright (c) 2016-2023 Renata Hodovan, Akos Kiss.
# Copyright (c) 2023 Daniel Vince.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import logging

from multiprocessing import Value

from . import parallel_loop
from .cache import ConfigCache
from .dd import DD
from .outcome import Outcome
from .shared_cache import shared_cache_decorator

logger = logging.getLogger(__name__)


class ParallelDD(DD):

    def __init__(self, test, *, split=None, cache=None, id_prefix=None,
                 config_iterator=None, dd_star=False,
                 proc_num=None, max_utilization=None):
        """
        Initialize a ParallelDD object.

        :param test: A callable tester object.
        :param split: Splitter method to break a configuration up to n parts.
        :param cache: Cache object to use.
        :param id_prefix: Tuple to prepend to config IDs during tests.
        :param config_iterator: Reference to a generator function that provides
            config indices in an arbitrary order.
        :param dd_star: Boolean to enable the DD star algorithm.
        :param proc_num: The level of parallelization.
        :param max_utilization: The maximum CPU utilization accepted.
        """
        cache = cache or shared_cache_decorator(ConfigCache)()
        super().__init__(test=test, split=split, cache=cache, id_prefix=id_prefix, config_iterator=config_iterator, dd_star=dd_star)

        self._proc_num = proc_num
        self._max_utilization = max_utilization
        self._fail_index = Value('i', 0, lock=False)

    def _loop_body(self, config, index, config_id):
        """
        The function that will be run in parallel.

        :param config: The list of entries of the current configuration.
        :param index: The index of the current configuration.
        :param config_id: The unique ID of the current configuration.
        :return: True if the test is not interesting, False otherwise.
        """
        if self._test_config(config, config_id) is Outcome.FAIL:
            self._fail_index.value = index
            return False

        return True

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
        self._fail_index.value = n
        ploop = parallel_loop.Loop(self._proc_num, self._max_utilization)
        for i in self._config_iterator(n):
            if i >= 0:
                config_id = (f'r{run}', f's{i}')
                config_set = subsets[i]
            else:
                i = int((-i - 1 + complement_offset) % n)
                config_id = (f'r{run}', f'c{i}')
                config_set = [c for si, s in enumerate(subsets) for c in s if si != i]
                i = -i - 1

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
        # which was found interesting. Otherwise it's n.
        fvalue = self._fail_index.value
        if fvalue < 0:
            # Interesting complement is found.
            # In next run, start removing the following subset
            fvalue = -fvalue - 1
            return subsets[:fvalue] + subsets[fvalue + 1:], fvalue
        if fvalue < n:
            # Interesting subset is found.
            return [subsets[fvalue]], 0

        return None, complement_offset
