# Copyright (c) 2016-2020 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.


def zeller(length, n):
    """
    Splits up the input config into n pieces as used by Zeller in the original
    reference implementation. The approach works iteratively in n steps, first
    slicing off a chunk sized 1/n-th of the original config, then slicing off
    1/(n-1)-th of the remainder, and so on, until the last piece is halved
    (always using integers division).

    :param length: The length of the configuration to split.
    :param n: The number of sets the configuration will be split up to.
    :return: List of slices marking the boundaries of the split sets.
    """
    slices = []
    start = 0
    for i in range(n):
        stop = start + (length - start) // (n - i)
        slices.append(slice(start, stop))
        start = stop
    return slices


def balanced(length, n):
    """
    Slightly different version of Zeller's split. This version keeps the split
    balanced by distributing the residuals of the integer division among all
    chunks. This way, the size of the chunks in the resulting split is not
    monotonous.

    :param length: The length of the configuration to split.
    :param n: The number of sets the configuration will be split up to.
    :return: List of slices marking the boundaries of the split sets.
    """
    return [slice(length * i // n, length * (i + 1) // n) for i in range(n)]
