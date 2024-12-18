# Copyright (c) 2016-2024 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

from random import shuffle


class IteratorRegistry:
    registry = {}

    @classmethod
    def register(cls, iter_name):
        def decorator(iter_fn):
            cls.registry[iter_name] = iter_fn
            return iter_fn
        return decorator


forward = IteratorRegistry.register('forward')(range)  #: Generator returning numbers from 0 to n-1.


@IteratorRegistry.register('backward')
def backward(n):
    """
    Generator returning numbers from n - 1 to 0 decreasing by 1.

    :param n: Upper bound of the interval.
    :return: Decreasing numbers from n - 1 to 0.
    """
    yield from range(n - 1, -1, -1)


@IteratorRegistry.register('skip')
def skip(n):
    """
    Do not return anything. Used to skip subset (or, less often, complement)
    checks.

    :param n: Anything. It won't ever be used. It's added only for consistency
        reasons.
    :return: None
    """
    yield from ()


@IteratorRegistry.register('random')
def random(n):
    """
    Returns numbers 0..n-1 in random order.

    :param n: Upper bound of the interval.
    :return: Numbers in random order from 0 to n - 1.
    """
    lst = list(range(n))
    shuffle(lst)
    yield from lst


class CombinedIterator:
    """
    Callable iterator class that acts as generator when subset and complement
    check loops are combined.
    """

    def __init__(self, subset_first=True, subset_iterator=forward, complement_iterator=forward):
        """
        Initialize CombinedIterator with the basic settings describing the order
        of subset and complement checks together with the certain iterators.

        :param subset_first: Boolean value denoting whether the reduce has to
            start with the subset-based approach or not.
        :param subset_iterator: Reference to a generator function that provides
            config indices in an arbitrary order.
        :param complement_iterator: Reference to a generator function that
            provides config indices in an arbitrary order.
        """
        self._subset_first = subset_first
        self._subset_iterator = subset_iterator
        self._complement_iterator = complement_iterator

    def __call__(self, n):
        """
        Provide the index of the next configuration according to the settings.

        :param n: The number of subsets in the configuration.
        :return: The index of the next configuration (i=0..n-1 to keep subset i,
            i=-1..-n to remove subset -i-1).
        """
        if self._subset_first:
            yield from self._subset_iterator(n)
            for i in self._complement_iterator(n):
                yield -i - 1
        else:
            for i in self._complement_iterator(n):
                yield -i - 1
            yield from self._subset_iterator(n)

    def __str__(self):
        def _str(a):
            if hasattr(a, '__name__'):
                return '.'.join(([a.__module__] if hasattr(a, '__module__') else []) + [a.__name__])
            return str(a)

        return f'{_str(self.__class__)}(subset_first={self._subset_first}, subset_iterator={_str(self._subset_iterator)}, complement_iterator={_str(self._complement_iterator)})'
