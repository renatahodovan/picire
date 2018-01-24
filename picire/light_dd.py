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

    def _reduce_config(self, run, config, subsets, complement_offset):
        """
        Perform the reduce task in single process mode.

        :param run: The index of the current iteration.
        :param config: The current configuration under testing.
        :param subsets: List of sets that the current configuration is split to.
        :param complement_offset: A compensation offset needed to calculate the index
               of the first unchecked complement (optimization purpose only).
        :return: Tuple: (failing config or None, next n or None, next complement_offset).
        """
        if self._subset_first:
            first_reduce, second_reduce = self._reduce_to_subset, self._reduce_to_complement
        else:
            first_reduce, second_reduce = self._reduce_to_complement, self._reduce_to_subset

        next_config, next_n, complement_offset = first_reduce(run, config, subsets, complement_offset)
        if next_config is None:
            next_config, next_n, complement_offset = second_reduce(run, config, subsets, complement_offset)

        return next_config, next_n, complement_offset

    def _reduce_to_subset(self, run, config, subsets, complement_offset):
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

    def _reduce_to_complement(self, run, config, subsets, complement_offset):
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
        for i in self._complement_iterator(n):
            if i is None:
                continue
            i = int((i + complement_offset) % n)

            config_id = (run, 'c', i)
            complement = self.minus(config, subsets[i])

            outcome = self.lookup_cache(complement, config_id) or self.test(complement, config_id)
            if outcome == self.FAIL:
                # Interesting complement is found.
                # In next run, start removing the following subset
                return complement, max(n - 1, 2), i

        return None, None, complement_offset
