# Copyright (c) 2016 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.md or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

from multiprocessing import Lock

from .outcome_cache import OutcomeCache


class SharedCache(OutcomeCache):
    """Thread-safe cache representation that stores the evaluated configurations and their outcome."""

    def __init__(self):
        OutcomeCache.__init__(self)
        self._lock = Lock()

    def add(self, config, result):
        """
        Add a new configuration to the cache.

        :param config: The configuration to save.
        :param result: The outcome of the added configuration.
        """
        with self._lock:
            OutcomeCache.add(self, config, result)

    def lookup(self, config):
        """
        Cache lookup to find out the outcome of a given configuration.

        :param config: The configuration we are looking for.
        :return: PASS or FAIL if config is in the cache; None, otherwise.
        """
        with self._lock:
            return OutcomeCache.lookup(self, config)

    def clear(self):
        """Thread-safe way of clearing cache."""
        with self._lock:
            OutcomeCache.clear(self)
