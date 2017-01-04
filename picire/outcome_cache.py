# Copyright (c) 2016-2017 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.


class OutcomeCache(object):
    """
    Base class for configuration outcome caching strategies. It does not
    implement a caching strategy itself (or, it implements the disable-cache
    strategy) but leaves the implementation of real strategies to subclasses.
    """

    def add(self, config, result):
        """
        Add a new configuration to the cache.

        :param config: The configuration to save.
        :param result: The outcome of the added configuration.
        """
        pass

    def lookup(self, config):
        """
        Cache lookup to find out the outcome of a given configuration.

        :param config: The configuration we are looking for.
        :return: PASS or FAIL if config is in the cache; None, otherwise.
        """
        return None

    def clear(self):
        """Clear the cache."""
        pass


class ConfigCache(OutcomeCache):

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
                    p.tail[cs] = ConfigCache._Entry()
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

        def _str(self, config=None):
            config = config or []
            s = ''
            if self.result is not None:
                s += '\t[%s]: %r,\n' % (', '.join([repr(c) for c in config]), self.result)
            for c, e in sorted(self.tail.items()):
                config.append(c)
                s += e._str(config)
                config.pop()
            return s

    def __init__(self):
        self._root = ConfigCache._Entry()

    def add(self, config, result):
        self._root.add(config, result)

    def lookup(self, config):
        return self._root.lookup(config)

    def clear(self):
        self._root = ConfigCache._Entry()

    def __str__(self):
        return '{\n%s}' % self._root._str()


class ContentCache(OutcomeCache):
    """
    Class that can cache the outcome of test cases by their content.
    """

    def __init__(self):
        self.container = dict()
        self.test_builder = None

    def set_test_builder(self, test_builder):
        self.test_builder = test_builder

    def add(self, config, result):
        self.container[self.test_builder(config)] = result

    def lookup(self, config):
        return self.container.get(self.test_builder(config), None)

    def clear(self):
        pass

    def __str__(self):
        from functools import reduce
        return '{\n%s}' % reduce(lambda x, y: x + y,
                                 ['\t%r: %r,\n' % (k, v)
                                  for k, v in sorted(self.container.items())],
                                 '')


# Aliases for cache classes to help their identification in CLI.
none = OutcomeCache
config = ConfigCache
content = ContentCache
