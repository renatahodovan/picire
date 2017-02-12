# Copyright (c) 2016-2017 Renata Hodovan, Akos Kiss.
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


class ParallelDD(AbstractParallelDD):

    def __init__(self, test, *, cache=None, split=config_splitters.zeller,
                 proc_num=os.cpu_count(), max_utilization=100,
                 subset_first=True, subset_iterator=config_iterators.forward, complement_iterator=config_iterators.forward):
        """
        Initialize a ParallelDD object.

        :param test: A callable tester object.
        :param cache: Cache object to use.
        :param split: Splitter method to break a configuration up to n part.
        :param proc_num: The level of parallelization.
        :param max_utilization: The maximum CPU utilization accepted.
        :param subset_first: Boolean value denoting whether the reduce has to start with the subset based approach or not.
        :param subset_iterator: Reference to a generator function that provides config indices in an arbitrary order.
        :param complement_iterator: Reference to a generator function that provides config indices in an arbitrary order.
        """
        AbstractParallelDD.__init__(self, test, split, proc_num, max_utilization, cache=cache)

        self._subset_first = subset_first
        self._subset_iterator = subset_iterator
        self._complement_iterator = complement_iterator

    def _dd(self, config):
        """
        Calculates an 1-minimal subset of the config that is still interesting using multiple processes.
        Subset and complement based blocks are executed sequentially.

        :param config: The input configuration.
        :return: A minimal subset of the current configuration what is still interesting (if any).
        """
        n = 2
        run = 1
        complement_offset = 0

        if self._subset_first:
            first_test = self._test_subsets
            second_test = self._test_complements
        else:
            first_test = self._test_complements
            second_test = self._test_subsets

        while True:
            assert self.test(config, AbstractDD.config_id(run, 'assert')) == self.FAIL

            subsets = self._split(config, n)

            logger.info('Run #%d: trying %s.', run, ' + '.join([str(len(subsets[i])) for i in range(n)]))

            # Reset fail index.
            self._fail_index.value = -1

            next_config, next_n, complement_offset = first_test(n, run, config, subsets, complement_offset)
            if self._fail_index.value == -1:
                next_config, next_n, complement_offset = second_test(n, run, config, subsets, complement_offset)

            # If findex is still -1 then no interesting configuration was found in either loops.
            if self._fail_index.value == -1:
                next_config = config
                next_n = min(len(config), n * 2)
                logger.info('Increase granularity to %d.', next_n)
                complement_offset = (complement_offset * next_n) / n

            # Minimization ends if no interesting configuration was found by the finest splitting or
            # if the configuration is already reduced to a single unit.
            if self._fail_index.value == -1 and n == len(config):
                # No further minimizing.
                logger.info('Done.')
                return config

            if self._fail_index.value != -1 and len(next_config) == 1:
                # No further minimizing.
                logger.info('Done.')
                return next_config

            config = next_config
            n = next_n
            run += 1

    def _test_subsets(self, n, run, config, subsets, complement_offset):
        """
        Perform a subset based reduce task.

        :param n: The number of sets that the config is split to.
        :param run: The index of the current iteration.
        :param config: The current configuration under testing.
        :param subsets: List of sets that the current configuration is split to.
        :param complement_offset: A compensation offset need to calculate the index
               of the first unchecked complement (optimization purpose only).
        :return: Tuple: (failing config or None, next n or None, next complement_offset).
        """
        # Looping through the subsets.
        ploop = parallel_loop.Loop(self._proc_num, self._max_utilization)
        for i in self._subset_iterator(n):
            if i is None:
                continue
            config_id = AbstractDD.config_id(run, 's', i)

            # If we had this test before, return the saved result.
            outcome = self.lookup_cache(subsets[i], config_id)
            if outcome == self.PASS:
                continue
            elif outcome == self.FAIL:
                self._fail_index.value = i
                break

            if not ploop.do(self._loop_body, (subsets[i], i, config_id)):
                # if do() returned False, the test was not started
                break
        ploop.join()

        fvalue = self._fail_index.value
        if fvalue != -1:
            logger.info('Reduced to %d units.', len(subsets[fvalue]))
            logger.debug('New config: %r.', subsets[fvalue])

            return subsets[fvalue], 2, 0

        return None, None, complement_offset

    def _test_complements(self, n, run, config, subsets, complement_offset):
        """
        Perform a complement based reduce task.

        :param n: The number of sets that the config is split to.
        :param run: The index of the current iteration.
        :param config: The current configuration under testing.
        :param subsets: List of sets that the current configuration is split to.
        :param complement_offset: A compensation offset need to calculate the index
               of the first unchecked complement (optimization purpose only).
        :return: Tuple: (failing config or None, next n or None, next complement_offset).
        """
        ploop = parallel_loop.Loop(self._proc_num, self._max_utilization)
        for j in self._complement_iterator(n):
            if j is None:
                continue

            i = int((j + complement_offset) % n)
            complement = self.minus(config, subsets[i])
            config_id = AbstractDD.config_id(run, 'c', i)

            # If we had this test before, return its result
            outcome = self.lookup_cache(complement, config_id)
            if outcome == self.PASS:
                continue
            elif outcome == self.FAIL:
                self._fail_index.value = i
                break

            if not ploop.do(self._loop_body, (complement, i, config_id)):
                # If do() returned False, the test was not started.
                break
        ploop.join()

        fvalue = self._fail_index.value
        if fvalue != -1:
            complement = self.minus(config, subsets[fvalue])
            logger.info('Reduced to %d units.', len(complement))
            logger.debug('New config: %r.', complement)

            # In next run, start removing the following subset.
            return complement, max(n - 1, 2), fvalue

        return None, None, complement_offset
