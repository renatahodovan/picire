# Copyright (c) 2016-2023 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

class IteratorRegistry(object):
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
    from random import shuffle

    lst = list(range(n))
    shuffle(lst)
    yield from lst
