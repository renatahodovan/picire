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


class ParallelDD(AbstractParallelDD):

    def __init__(self, test, *, split=None, cache=None, id_prefix=None,
                 proc_num=None, max_utilization=None,
                 subset_first=True, subset_iterator=None, complement_iterator=None):
        """
        Initialize a ParallelDD object.

        :param test: A callable tester object.
        :param split: Splitter method to break a configuration up to n part.
        :param cache: Cache object to use.
        :param id_prefix: Tuple to prepend to config IDs during tests.
        :param proc_num: The level of parallelization.
        :param max_utilization: The maximum CPU utilization accepted.
        :param subset_first: Boolean value denoting whether the reduce has to
            start with the subset-based approach or not.
        :param subset_iterator: Reference to a generator function that provides
            config indices in an arbitrary order.
        :param complement_iterator: Reference to a generator function that
            provides config indices in an arbitrary order.
        """
        super().__init__(test=test, split=split, cache=cache, id_prefix=id_prefix, proc_num=proc_num, max_utilization=max_utilization)

        self._subset_iterator = subset_iterator or forward
        self._complement_iterator = complement_iterator or forward

        if subset_first:
            self._first_reduce, self._second_reduce = self._reduce_to_subset, self._reduce_to_complement
        else:
            self._first_reduce, self._second_reduce = self._reduce_to_complement, self._reduce_to_subset

    def _reduce_config(self, run, subsets, complement_offset):
        """
        Perform the reduce task using multiple processes.
        Subset and complement set tests are executed sequentially.

        :param run: The index of the current iteration.
        :param subsets: List of sets that the current configuration is split to.
        :param complement_offset: A compensation offset needed to calculate the
            index of the first unchecked complement (optimization purpose only).
        :return: Tuple: (list of subsets composing the failing config or None,
            next complement_offset).
        """
        next_subsets, complement_offset = self._first_reduce(run, subsets, complement_offset)
        if next_subsets is None:
            next_subsets, complement_offset = self._second_reduce(run, subsets, complement_offset)

        return next_subsets, complement_offset

    def _reduce_to_subset(self, run, subsets, complement_offset):
        """
        Perform a subset-based reduce task.

        :param run: The index of the current iteration.
        :param subsets: List of sets that the current configuration is split to.
        :param complement_offset: A compensation offset needed to calculate the
            index of the first unchecked complement (optimization purpose only).
        :return: Tuple: (list of subsets composing the failing config or None,
            next complement_offset).
        """
        # Looping through the subsets.
        n = len(subsets)
        self._fail_index.value = -1
        ploop = parallel_loop.Loop(self._proc_num, self._max_utilization)
        for i in self._subset_iterator(n):
            if i is None:
                continue

            config_id = (f'r{run}', f's{i}')
            subset = subsets[i]

            # If we had this test before, return the saved result.
            outcome = self._lookup_cache(subset, config_id)
            if outcome is Outcome.PASS:
                continue
            if outcome is Outcome.FAIL:
                self._fail_index.value = i
                ploop.brk()
                break

            if not ploop.do(self._loop_body, (subset, i, config_id)):
                # if do() returned False, the test was not started
                break
        ploop.join()

        fvalue = self._fail_index.value
        if fvalue != -1:
            return [subsets[fvalue]], 0

        return None, complement_offset

    def _reduce_to_complement(self, run, subsets, complement_offset):
        """
        Perform a complement-based reduce task.

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
        for i in self._complement_iterator(n):
            if i is None:
                continue
            i = int((i + complement_offset) % n)

            config_id = (f'r{run}', f'c{i}')
            complement = [c for si, s in enumerate(subsets) for c in s if si != i]

            # If we had this test before, return its result
            outcome = self._lookup_cache(complement, config_id)
            if outcome is Outcome.PASS:
                continue
            if outcome is Outcome.FAIL:
                self._fail_index.value = i
                ploop.brk()
                break

            if not ploop.do(self._loop_body, (complement, i, config_id)):
                # If do() returned False, the test was not started.
                break
        ploop.join()

        fvalue = self._fail_index.value
        if fvalue != -1:
            # In next run, start removing the following subset.
            return subsets[:fvalue] + subsets[fvalue + 1:], fvalue

        return None, complement_offset
