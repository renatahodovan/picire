# Copyright (c) 2016 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.md or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

from multiprocessing.managers import BaseManager

from .outcome_cache import OutcomeCache
from .shared_cache import SharedCache


class SharedDataManager(BaseManager):
    """Data manager to share the cache object between parallel processes."""
    pass


def init(parallel, disable_cache):
    global outcome_cache

    outcome_cache = None

    if not parallel:
        if not disable_cache:
            outcome_cache = OutcomeCache()
    else:
        if not disable_cache:
            SharedDataManager.register('cacheManager', SharedCache)
            data_manager = SharedDataManager()
            data_manager.start()
            outcome_cache = data_manager.cacheManager()
