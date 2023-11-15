# Copyright (c) 2023 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.


class ReductionException(Exception):
    """
    Base class of reduction-related exceptions. In addition to signal the
    premature termination of a reduction process, exception instances contain
    the intermediate result of the reduction.

    :ivar result: A representation of the smallest, potentially non-minimal, but
        failing test case found during reduction.
    """

    def __init__(self, *args, result=None):
        super().__init__(*args)
        self.result = result


class ReductionStopped(ReductionException):
    """
    Exception to signal that reduction has been stopped, e.g., because some time
    limit or test count limit has been reached.
    """


class ReductionError(ReductionException):
    """
    Exception to signal that an unexpected error occured during reduction.
    """
