# Copyright (c) 2016-2023 Renata Hodovan, Akos Kiss.
# Copyright (c) 2023 Daniel Vince.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import logging

from concurrent.futures import ALL_COMPLETED, FIRST_COMPLETED, ThreadPoolExecutor, wait
from os import cpu_count
from threading import Lock

from .cache import OutcomeCache
from .dd import DD
from .outcome import Outcome

logger = logging.getLogger(__name__)


class SharedCache(OutcomeCache):
    """
    Thread-safe cache representation that stores the evaluated configurations
    and their outcome.
    """

    def __init__(self, cache):
        self._cache = cache
        self._lock = Lock()

    def set_test_builder(self, test_builder):
        with self._lock:
            self._cache.set_test_builder(test_builder)

    def add(self, config, result):
        with self._lock:
            self._cache.add(config, result)

    def lookup(self, config):
        with self._lock:
            return self._cache.lookup(config)

    def clear(self):
        with self._lock:
            self._cache.clear()

    def __str__(self):
        with self._lock:
            return self._cache.__str__()


class ParallelDD(DD):

    def __init__(self, test, *, split=None, cache=None, id_prefix=None,
                 config_iterator=None, dd_star=False, stop=None,
                 proc_num=None):
        """
        Initialize a ParallelDD object.

        :param test: A callable tester object.
        :param split: Splitter method to break a configuration up to n parts.
        :param cache: Cache object to use.
        :param id_prefix: Tuple to prepend to config IDs during tests.
        :param config_iterator: Reference to a generator function that provides
            config indices in an arbitrary order.
        :param dd_star: Boolean to enable the DD star algorithm.
        :param stop: A callable invoked before the execution of every test.
        :param proc_num: The level of parallelization.
        """
        super().__init__(test=test, split=split, cache=cache, id_prefix=id_prefix, config_iterator=config_iterator, dd_star=dd_star, stop=stop)
        self._cache = SharedCache(self._cache)

        self._proc_num = proc_num or cpu_count()

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
        fvalue = n
        tests = set()
        with ThreadPoolExecutor(self._proc_num) as pool:
            for i in self._config_iterator(n):
                results, tests = wait(tests, timeout=0 if len(tests) < self._proc_num else None, return_when=FIRST_COMPLETED)
                for result in results:
                    index, outcome = result.result()
                    if outcome is Outcome.FAIL:
                        fvalue = index
                        break
                if fvalue < n:
                    break

                if i >= 0:
                    config_id = (f'r{run}', f's{i}')
                    config_set = subsets[i]
                else:
                    i = (-i - 1 + complement_offset) % n
                    config_id = (f'r{run}', f'c{i}')
                    config_set = [c for si, s in enumerate(subsets) for c in s if si != i]
                    i = -i - 1

                # If we checked this test before, return its result
                outcome = self._lookup_cache(config_set, config_id)
                if outcome is Outcome.PASS:
                    continue
                if outcome is Outcome.FAIL:
                    fvalue = i
                    break

                self._check_stop()
                tests.add(pool.submit(self._test_config_with_index, i, config_set, config_id))

            results, _ = wait(tests, return_when=ALL_COMPLETED)
            if fvalue == n:
                for result in results:
                    index, outcome = result.result()
                    if outcome is Outcome.FAIL:
                        fvalue = index
                        break

        # fvalue contains the index of the cycle in the previous loop
        # which was found interesting. Otherwise it's n.
        if fvalue < 0:
            # Interesting complement is found.
            # In next run, start removing the following subset
            fvalue = -fvalue - 1
            return subsets[:fvalue] + subsets[fvalue + 1:], fvalue
        if fvalue < n:
            # Interesting subset is found.
            return [subsets[fvalue]], 0

        return None, complement_offset

    def _test_config_with_index(self, index, config, config_id):
        return index, self._test_config(config, config_id)
