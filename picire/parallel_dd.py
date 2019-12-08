# Copyright (c) 2016-2019 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import logging
import multiprocessing

from . import config_iterators
from . import config_splitters
from . import parallel_loop
from .abstract_parallel_dd import AbstractParallelDD

logger = logging.getLogger(__name__)


class ParallelDD(AbstractParallelDD):

    def __init__(self, test, cache=None, id_prefix=(), split=config_splitters.zeller,
                 proc_num=multiprocessing.cpu_count(), max_utilization=100,
                 subset_first=True, subset_iterator=config_iterators.forward, complement_iterator=config_iterators.forward):
        """
        Initialize a ParallelDD object.

        :param test: A callable tester object.
        :param cache: Cache object to use.
        :param id_prefix: Tuple to prepend to config IDs during tests.
        :param split: Splitter method to break a configuration up to n part.
        :param proc_num: The level of parallelization.
        :param max_utilization: The maximum CPU utilization accepted.
        :param subset_first: Boolean value denoting whether the reduce has to
            start with the subset-based approach or not.
        :param subset_iterator: Reference to a generator function that provides
            config indices in an arbitrary order.
        :param complement_iterator: Reference to a generator function that
            provides config indices in an arbitrary order.
        """
        AbstractParallelDD.__init__(self, test, split, proc_num, max_utilization, cache=cache, id_prefix=id_prefix)

        self._subset_iterator = subset_iterator
        self._complement_iterator = complement_iterator

        if subset_first:
            self._first_reduce, self._second_reduce = self._reduce_to_subset, self._reduce_to_complement
        else:
            self._first_reduce, self._second_reduce = self._reduce_to_complement, self._reduce_to_subset

    def _reduce_config(self, run, config, subsets, complement_offset):
        """
        Perform the reduce task using multiple processes.
        Subset and complement set tests are executed sequentially.

        :param run: The index of the current iteration.
        :param config: The current configuration under testing.
        :param subsets: List of sets that the current configuration is split to.
        :param complement_offset: A compensation offset needed to calculate the
            index of the first unchecked complement (optimization purpose only).
        :return: Tuple: (failing config or None, next n or None, next
            complement_offset).
        """
        next_config, next_n, complement_offset = self._first_reduce(run, config, subsets, complement_offset)
        if next_config is None:
            next_config, next_n, complement_offset = self._second_reduce(run, config, subsets, complement_offset)

        return next_config, next_n, complement_offset

    def _reduce_to_subset(self, run, config, subsets, complement_offset):
        """
        Perform a subset-based reduce task.

        :param run: The index of the current iteration.
        :param config: The current configuration under testing.
        :param subsets: List of sets that the current configuration is split to.
        :param complement_offset: A compensation offset needed to calculate the
            index of the first unchecked complement (optimization purpose only).
        :return: Tuple: (failing config or None, next n or None, next
            complement_offset).
        """
        # Looping through the subsets.
        n = len(subsets)
        self._fail_index.value = -1
        ploop = parallel_loop.Loop(self._proc_num, self._max_utilization)
        for i in self._subset_iterator(n):
            if i is None:
                continue

            config_id = ('r%d' % run, 's%d' % i)

            # If we had this test before, return the saved result.
            outcome = self._lookup_cache(subsets[i], config_id)
            if outcome == self.PASS:
                continue
            if outcome == self.FAIL:
                self._fail_index.value = i
                break

            if not ploop.do(self._loop_body, (subsets[i], i, config_id)):
                # if do() returned False, the test was not started
                break
        ploop.join()

        fvalue = self._fail_index.value
        if fvalue != -1:
            return subsets[fvalue], 2, 0

        return None, None, complement_offset

    def _reduce_to_complement(self, run, config, subsets, complement_offset):
        """
        Perform a complement-based reduce task.

        :param run: The index of the current iteration.
        :param config: The current configuration under testing.
        :param subsets: List of sets that the current configuration is split to.
        :param complement_offset: A compensation offset needed to calculate the
            index of the first unchecked complement (optimization purpose only).
        :return: Tuple: (failing config or None, next n or None, next
            complement_offset).
        """
        n = len(subsets)
        self._fail_index.value = -1
        ploop = parallel_loop.Loop(self._proc_num, self._max_utilization)
        for i in self._complement_iterator(n):
            if i is None:
                continue
            i = int((i + complement_offset) % n)

            complement = self._minus(config, subsets[i])
            config_id = ('r%d' % run, 'c%d' % i)

            # If we had this test before, return its result
            outcome = self._lookup_cache(complement, config_id)
            if outcome == self.PASS:
                continue
            if outcome == self.FAIL:
                self._fail_index.value = i
                break

            if not ploop.do(self._loop_body, (complement, i, config_id)):
                # If do() returned False, the test was not started.
                break
        ploop.join()

        fvalue = self._fail_index.value
        if fvalue != -1:
            # In next run, start removing the following subset.
            return self._minus(config, subsets[fvalue]), max(n - 1, 2), fvalue

        return None, None, complement_offset
