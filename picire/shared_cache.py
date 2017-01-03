# Copyright (c) 2016-2017 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import inspect

from multiprocessing import Lock
from multiprocessing.managers import BaseManager

shared_manager_store = dict()


def shared_cache_decorator(cache_class):
    global shared_manager_store

    if cache_class in shared_manager_store:
        return shared_manager_store[cache_class].SharedCache

    class SharedDataManager(BaseManager):
        """Data manager to share the cache object between parallel processes."""
        pass

    class SharedCache(cache_class):
        """Thread-safe cache representation that stores the evaluated configurations and their outcome."""

        def __init__(self, *args, **kwargs):
            cache_class.__init__(self, *args, **kwargs)
            self._lock = Lock()

        def add(self, config, result):
            with self._lock:
                cache_class.add(self, config, result)

        def lookup(self, config):
            with self._lock:
                return cache_class.lookup(self, config)

        def clear(self):
            with self._lock:
                cache_class.clear(self)

    SharedDataManager.register('SharedCache', SharedCache, None,
                               [nv[0] for nv in inspect.getmembers(cache_class, lambda m: inspect.isfunction(m) and m.__name__ != '__init__')])
    getattr(SharedDataManager, 'SharedCache').__signature__ = inspect.signature(cache_class)
    data_manager = SharedDataManager()
    data_manager.start()
    shared_manager_store[cache_class] = data_manager

    return data_manager.SharedCache
