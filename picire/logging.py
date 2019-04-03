# Copyright (c) 2018-2019 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

from __future__ import absolute_import

from logging import *


TRACE = DEBUG // 2
DISABLE = CRITICAL + 1


levels = {
    'TRACE': TRACE,
    'DEBUG': DEBUG,
    'INFO': INFO,
    'WARNING': WARNING,
    'ERROR': ERROR,
    'CRITICAL': CRITICAL,
    'DISABLE': DISABLE,
}


__getLogger = getLogger


def getLogger(name=None):
    logger = __getLogger(name)
    logger.trace = lambda msg, *args, **kwargs: logger.log(TRACE, msg, *args, **kwargs)
    return logger
