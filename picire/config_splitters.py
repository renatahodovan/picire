# Copyright (c) 2016-2019 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.


def zeller(config, n):
    """
    Splits up the input config into n pieces as used by Zeller in the original
    reference implementation. The approach works iteratively in n steps, first
    slicing off a chunk sized 1/n-th of the original config, then slicing off
    1/(n-1)-th of the remainder, and so on, until the last piece is halved
    (always using integers division).

    :param config: The configuration to split.
    :param n: The number of sets the configuration will be split up to.
    :return: List of the split sets.
    """
    subsets = []
    start = 0
    for i in range(n):
        subset = config[start:start + (len(config) - start) // (n - i)]
        subsets.append(subset)
        start += len(subset)
    return subsets


def balanced(config, n):
    """
    Slightly different version of Zeller's split. This version keeps the split
    balanced by distributing the residuals of the integer division among all
    chunks. This way, the size of the chunks in the resulting split is not
    monotonous.

    :param config: The configuration to split.
    :param n: The number of sets the configuration will be split up to.
    :return: List of the split sets.
    """
    return [config[len(config) * i // n: len(config) * (i + 1) // n] for i in range(n)]
