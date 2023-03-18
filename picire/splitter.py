# Copyright (c) 2016-2023 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

class SplitterRegistry(object):
    registry = {}

    @classmethod
    def register(cls, split_name):
        def decorator(split_class):
            cls.registry[split_name] = split_class
            return split_class
        return decorator


@SplitterRegistry.register('zeller')
class ZellerSplit(object):
    """
    Splits up the input config into n pieces as used by Zeller in the original
    reference implementation. The approach works iteratively in n steps, first
    slicing off a chunk sized 1/n-th of the original config, then slicing off
    1/(n-1)-th of the remainder, and so on, until the last piece is halved
    (always using integers division).
    """

    def __init__(self, n=2):
        """
        :param n: The split ratio used to determine how many parts (subsets) the
            config to split to (both initially and later on whenever config
            subsets needs to be re-split).
        """
        self._n = n

    def __call__(self, subsets):
        """
        :param subsets: List of sets that the current configuration is split to.
        :return: List of newly split sets.
        """
        config = [c for s in subsets for c in s]
        length = len(config)
        n = min(length, len(subsets) * self._n)

        next_subsets = []
        start = 0
        for i in range(n):
            stop = start + (length - start) // (n - i)
            next_subsets.append(config[start:stop])
            start = stop
        return next_subsets

    def __str__(self):
        cls = self.__class__
        return f'{cls.__module__}.{cls.__name__}(n={self._n})'


@SplitterRegistry.register('balanced')
class BalancedSplit(object):
    """
    Slightly different version of Zeller's split. This version keeps the split
    balanced by distributing the residuals of the integer division among all
    chunks. This way, the size of the chunks in the resulting split is not
    monotonous.
    """

    def __init__(self, n=2):
        """
        :param n: The split ratio used to determine how many parts (subsets) the
            config to split to (both initially and later on whenever config
            subsets needs to be re-split).
        """
        self._n = n

    def __call__(self, subsets):
        """
        :param subsets: List of sets that the current configuration is split to.
        :return: List of newly split sets.
        """
        config = [c for s in subsets for c in s]
        length = len(config)
        n = min(length, len(subsets) * self._n)

        return [config[length * i // n:length * (i + 1) // n] for i in range(n)]

    def __str__(self):
        cls = self.__class__
        return f'{cls.__module__}.{cls.__name__}(n={self._n})'
