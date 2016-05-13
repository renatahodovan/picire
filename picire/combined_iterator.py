# Copyright (c) 2016 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.md or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.


class CombinedIterator(object):
    """Callable iterator class that acts as generator when subset and complement check loops are combined."""

    def __init__(self, subset_first, sub_it, compl_it):
        """
        Initialize CombinedIterator with the basic settings describing the order of subset and complement checks
        together with the certain iterators.

        :param subset_first: Boolean value denoting whether the reduce has to start with the subset based approach or not.
        :param sub_it: Reference to a generator function that provides config indices in an arbitrary order.
        :param compl_it: Reference to a generator function that provides config indices in an arbitrary order.
        """
        self._subset_first = subset_first
        self._subset_iterator = sub_it
        self._complement_iterator = compl_it

    def __call__(self, n):
        """
        Provide the index of the next configuration according to the settings.

        :param n: The number of configurations (subset and combined configs altogether).
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
