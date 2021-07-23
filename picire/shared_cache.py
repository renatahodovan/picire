# Copyright (c) 2016-2021 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import inspect

from multiprocessing import Lock
from multiprocessing.managers import BaseManager

from .outcome_cache import OutcomeCache


class SharedCacheManager(BaseManager):
    """
    Manager to share the cache object between parallel processes.
    """

    _managers = {}


class SharedCacheConstructor(object):
    """
    Wrapper for cache classes to instantiate them as shared.
    """

    _exposed = []

    @classmethod
    def exposed(cls, fn):
        cls._exposed.append(fn.__name__)
        return fn

    def __init__(self, cache_class):
        self._cache_class = cache_class

    def __call__(self, *args, **kwargs):
        return SharedCache(self._cache_class(*args, **kwargs))


class SharedCache(OutcomeCache):
    """
    Thread-safe cache representation that stores the evaluated configurations
    and their outcome.
    """

    def __init__(self, cache):
        self._cache = cache
        self._lock = Lock()

    @SharedCacheConstructor.exposed
    def set_test_builder(self, test_builder):
        with self._lock:
            self._cache.set_test_builder(test_builder)

    @SharedCacheConstructor.exposed
    def add(self, config, result):
        with self._lock:
            self._cache.add(config, result)

    @SharedCacheConstructor.exposed
    def lookup(self, config):
        with self._lock:
            return self._cache.lookup(config)

    @SharedCacheConstructor.exposed
    def clear(self):
        with self._lock:
            self._cache.clear()

    @SharedCacheConstructor.exposed
    def __str__(self):
        with self._lock:
            return self._cache.__str__()


def shared_cache_decorator(cache_class):
    name = cache_class.__name__

    if not hasattr(SharedCacheManager, name):
        SharedCacheManager.register(name, SharedCacheConstructor(cache_class), None, SharedCacheConstructor._exposed)
        getattr(SharedCacheManager, name).__signature__ = inspect.signature(cache_class)

        SharedCacheManager._managers[name] = SharedCacheManager()
        SharedCacheManager._managers[name].start()

    return getattr(SharedCacheManager._managers[name], name)
