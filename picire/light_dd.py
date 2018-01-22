# Copyright (c) 2016-2018 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import logging

from . import config_iterators
from . import config_splitters
from .abstract_dd import AbstractDD
from .outcome_cache import ConfigCache

logger = logging.getLogger(__name__)


class LightDD(AbstractDD):
    """Single process version of the Delta Debugging algorithm."""

    def __init__(self, test, *, cache=None, split=config_splitters.zeller,
                 subset_first=True, subset_iterator=config_iterators.forward, complement_iterator=config_iterators.forward):
        """
        Initialize a LightDD object.

        :param test: A callable tester object.
        :param cache: Cache object to use.
        :param split: Splitter method to break a configuration up to n parts.
        :param subset_first: Boolean value denoting whether the reduce has to start with the subset-based approach or not.
        :param subset_iterator: Reference to a generator function that provides config indices in an arbitrary order.
        :param complement_iterator: Reference to a generator function that provides config indices in an arbitrary order.
        """
        cache = cache or ConfigCache()
        AbstractDD.__init__(self, test, split, cache=cache)

        self._subset_first = subset_first
        self._subset_iterator = subset_iterator
        self._complement_iterator = complement_iterator

    def _dd(self, config, *, n):
        """
        Calculates a 1-minimal subset of the config that is still interesting in single process mode.

        :param config: The input configuration.
        :param n: The number of sets that the config is initially split to.
        :return: A minimal subset of the current configuration what is still interesting (if any).
        """
        run = 1
        complement_offset = 0

        if self._subset_first:
            first_test = self._test_subsets
            second_test = self._test_complements
        else:
            first_test = self._test_complements
            second_test = self._test_subsets

        while True:
            assert self.test(config, (run, 'assert')) == self.FAIL

            subsets = self._split(config, n)

            logger.info('Run #%d: trying %s.', run, ' + '.join([str(len(subsets[i])) for i in range(n)]))

            next_config, next_n, complement_offset = first_test(run, config, subsets, complement_offset)
            if next_config is None:
                next_config, next_n, complement_offset = second_test(run, config, subsets, complement_offset)

            if next_config is None:
                # Minimization ends if no interesting configuration was found by the finest splitting.
                if n == len(config):
                    logger.info('Done.')
                    return config

                next_config = config
                next_n = min(len(config), n * 2)
                complement_offset = (complement_offset * next_n) / n
                logger.info('Increase granularity to %d.', next_n)

            else:
                # Interesting configuration is found.
                logger.info('Reduced to %d units.', len(next_config))
                logger.debug('New config: %r.', next_config)

                # Minimization ends if the configuration is already reduced to a single unit.
                if len(next_config) == 1:
                    logger.info('Done.')
                    return next_config

            config = next_config
            n = next_n
            run += 1

    def _test_subsets(self, run, config, subsets, complement_offset):
        """
        Perform a subset-based reduce task.

        :param run: The index of the current iteration.
        :param config: The current configuration under testing.
        :param subsets: List of sets that the current configuration is split to.
        :param complement_offset: A compensation offset needed to calculate the index
               of the first unchecked complement (optimization purpose only).
        :return: Tuple: (failing config or None, next n or None, next complement_offset).
        """
        n = len(subsets)
        for i in self._subset_iterator(n):
            if i is None:
                continue

            config_id = (run, 's', i)

            # Get the outcome either from cache or by testing it.
            outcome = self.lookup_cache(subsets[i], config_id) or self.test(subsets[i], config_id)
            if outcome == self.FAIL:
                # Interesting subset is found.
                return subsets[i], 2, 0

        return None, None, complement_offset

    def _test_complements(self, run, config, subsets, complement_offset):
        """
        Perform a complement-based reduce task.

        :param run: The index of the current iteration.
        :param config: The current configuration under testing.
        :param subsets: List of sets that the current configuration is split to.
        :param complement_offset: A compensation offset needed to calculate the index
               of the first unchecked complement (optimization purpose only).
        :return: Tuple: (failing config or None, next n or None, next complement_offset).
        """
        n = len(subsets)
        for j in self._complement_iterator(n):
            if j is None:
                continue

            i = int((j + complement_offset) % n)
            config_id = (run, 'c', i)
            complement = self.minus(config, subsets[i])

            outcome = self.lookup_cache(complement, config_id) or self.test(complement, config_id)
            if outcome == self.FAIL:
                # Interesting complement is found.
                # In next run, start removing the following subset
                return complement, max(n - 1, 2), i

        return None, None, complement_offset
