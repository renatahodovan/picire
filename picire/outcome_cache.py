# Copyright (c) 2016 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.md or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.


class OutcomeCache(object):

    class _Entry(object):
        """
        This class holds test outcomes for configurations. This avoids
        running the same test twice.

        The outcome cache is implemented as a tree.  Each node points
        to the outcome of the remaining list.

        Example: ([1, 2, 3], PASS), ([1, 2], FAIL), ([1, 4, 5], FAIL):

             (2, FAIL)--(3, PASS)
            /
        (1, None)
            \
             (4, None)--(5, FAIL)
        """

        def __init__(self):
            self.result = None  # Result so far
            self.tail = {}  # Points to outcome of tail

        def add(self, config, result):
            """
            Add (config, RESULT) to the cache. config must be a list of scalars.

            :param config: Config to add to the cache.
            :param result: The outcome of the added config.
            """
            p = self
            for cs in config:
                if cs not in p.tail:
                    p.tail[cs] = OutcomeCache._Entry()
                p = p.tail[cs]
            p.result = result

        def lookup(self, config):
            """
            Performs a cache lookup.

            :param config: The configuration we are looking for.
            :return: PASS or FAIL if config is in the cache, None otherwise.
            """
            p = self
            for cs in config:
                if cs not in p.tail:
                    return None
                p = p.tail[cs]

            return p.result

    def __init__(self):
        self._root = OutcomeCache._Entry()

    def add(self, config, result):
        """
        Add a new configuration to the cache.

        :param config: The configuration to save.
        :param result: The outcome of the added configuration.
        """
        self._root.add(config, result)

    def lookup(self, config):
        """
        Cache lookup to find out the outcome of a given configuration.

        :param config: The configuration we are looking for.
        :return: PASS or FAIL if config is in the cache; None, otherwise.
        """
        return self._root.lookup(config)

    def clear(self):
        """Clear the cache."""
        self._root = OutcomeCache._Entry()
