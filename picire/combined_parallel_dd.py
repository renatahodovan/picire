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

    def _dd(self, config):
        """
        Calculates a 1-minimal subset of the config that is still interesting using multiple processes.
        Subset and complement based blocks are mixed and don't wait for each other.

        :param config: The input configuration.
        :return: A minimal subset of the current configuration what is still interesting (if any).
        """
        n = 2
        run = 1
        complement_offset = 0

        while True:
            assert self.test(config, AbstractDD.config_id(run, 'assert')) == self.FAIL

            subsets = self._split(config, n)

            logger.info('Run #%d: trying %s.', run, ' + '.join([str(len(subsets[i])) for i in range(n)]))

            # Reset fail index.
            self._fail_index.value = -1

            ploop = parallel_loop.Loop(self._proc_num, self._max_utilization)
            for i in self._config_iterator(2 * n):
                if i is None:
                    continue

                if i < n:
                    config_id = AbstractDD.config_id(run, 's', i)
                    config_set = subsets[i]
                else:
                    j = int((i - n + complement_offset) % n)
                    config_id = AbstractDD.config_id(run, 'c', j)
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
                    logger.info('Reduced to %d units.', len(subsets[fvalue]))
                    logger.debug('New config: %r.', subsets[fvalue])

                    next_config = subsets[fvalue]
                    next_n = 2
                    complement_offset = 0
                # Complement fail.
                else:
                    j = int((fvalue - n + complement_offset) % n)
                    complement = self.minus(config, subsets[j])
                    logger.info('Reduced to %d units.', len(complement))
                    logger.debug('New config: %r.', complement)

                    next_config = complement
                    next_n = max(n - 1, 2)

                    # In next run, start removing the following subset.
                    complement_offset = j
            else:
                next_config = config
                next_n = min(len(config), n * 2)
                logger.info('Increase granularity to %d.', next_n)
                complement_offset = (complement_offset * next_n) / n

            # Minimization ends if no interesting configuration was found by the finest splitting or
            # if the configuration is already reduced to a single unit.
            if fvalue == -1 and n == len(config):
                # No further minimizing.
                logger.info('Done.')
                return config

            if fvalue != -1 and len(next_config) == 1:
                # No further minimizing.
                logger.info('Done.')
                return next_config

            config = next_config
            n = next_n
            run += 1
