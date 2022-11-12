# Copyright (c) 2021-2022 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

from enum import Enum


class Outcome(Enum):

    PASS = 'PASS'
    FAIL = 'FAIL'

    def __repr__(self):
        return f'<{self.__class__.__name__}.{self.name}>'
