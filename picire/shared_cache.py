# Copyright (c) 2016-2019 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import inspect

from multiprocessing import Lock
from multiprocessing.managers import BaseManager

shared_cache_class_store = dict()


class SharedDataManager(BaseManager):
    """
    Data manager to share the cache object between parallel processes.
    """
    pass


class SharedCacheTrampoline(object):
    """
    Thread-safe wrapper for SharedCache methods.
    """

    def __init__(self, shared_cache, fn):
        self._shared_cache = shared_cache
        self._fn = fn

    def __call__(self, *args, **kwargs):
        with self._shared_cache._lock:
            return getattr(self._shared_cache._cache, self._fn)(*args, **kwargs)


class SharedCache(object):
    """
    Thread-safe cache representation that stores the evaluated configurations
    and their outcome.
    """

    def __init__(self, cache):
        self._cache = cache
        self._lock = Lock()

        for fn, _ in inspect.getmembers(cache.__class__, lambda m: (inspect.isfunction(m) or inspect.ismethod(m)) and m.__name__ != '__init__'):
            setattr(self, fn, SharedCacheTrampoline(self, fn))


class SharedCacheConstructor(object):
    """
    Wrapper for cache classes to instantiate them as shared.
    """

    def __init__(self, cache_class):
        self._cache_class = cache_class

    def __call__(self, *args, **kwargs):
        return SharedCache(self._cache_class(*args, **kwargs))


def shared_cache_decorator(cache_class):
    if cache_class not in shared_cache_class_store:
        SharedDataManager.register(cache_class.__name__, SharedCacheConstructor(cache_class), None,
                                   [fn for fn, _ in inspect.getmembers(cache_class, lambda m: (inspect.isfunction(m) or inspect.ismethod(m)) and m.__name__ != '__init__')])
        try:
            getattr(SharedDataManager, cache_class.__name__).__signature__ = inspect.signature(cache_class)
        except AttributeError:
            pass  # no signatures in Python < 3.3

        data_manager = SharedDataManager()
        data_manager.start()

        shared_cache_class_store[cache_class] = getattr(data_manager, cache_class.__name__)

    return shared_cache_class_store[cache_class]
