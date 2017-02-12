# Copyright (c) 2016-2017 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import logging

from .outcome_cache import OutcomeCache

logger = logging.getLogger(__name__)


class AbstractDD(object):
    """Abstract super-class of the parallel and non-parallel DD classes."""

    # Test outcomes.
    PASS = 'PASS'
    FAIL = 'FAIL'

    def __init__(self, test, split, *, cache=None):
        """
        Initialise an abstract DD class. Not to be called directly,
        only by super calls in subclass initializers.

        :param test: A callable tester object.
        :param split: Splitter method to break a configuration up to n parts.
        :param cache: Cache object to use.
        """
        self._test = test
        self._split = split
        self._cache = cache or OutcomeCache()

    @staticmethod
    def config_id(*args):
        """
        Create a task identifier from the arguments. The arguments are typically
        in the form of (run, dir, i), where run is the index of the current
        iteration, dir is direction of reduce (either s(ubest) or c(omplement)),
        and i is the index of the current test in the iteration. Alternatively,
        arguments can also be in the form of (run, 'assert') for double checking
        the input at the start of an iteration.

        :return: Config ID by concatenating the arguments with underscores.
        """
        return '_'.join([str(arg) for arg in args])

    @staticmethod
    def pretty_config_id(config_id):
        """
        Create beautified identifier for the current task.

        :param config_id: Config ID as returned by config_id.
        :return: Config ID separated by slashes, e.g., "(run) / (dir) / (i)".
        """
        return config_id.replace('_', ' / ')

    def lookup_cache(self, config, config_id):
        """
        Perform a cache lookup if caching is enabled.

        :param config: The configuration we are looking for.
        :param config_id: The ID describing the configuration (only for debug message).
        :return: None if caching is disabled, PASS or FAIL otherwise.
        """
        cached_result = self._cache.lookup(config)
        if cached_result is not None:
            logger.debug('\t[ %s ]: cache = %r', AbstractDD.pretty_config_id(config_id), cached_result)

        return cached_result

    @staticmethod
    def minus(c1, c2):
        """Return a list of all elements of C1 that are not in C2."""
        c2 = set(c2)
        return [c for c in c1 if c not in c2]

    def _dd(self, config):
        """
        To be overridden by subclasses.

        :param config: The input configuration.
        :return: A minimal subset of the current configuration what is still interesting (if any).
        """
        pass

    def ddmin(self, config):
        """
        Return a 1-minimal failing subset of the initial configuration.

        :param config: The initial configuration that will be reduced.
        :return: 1-minimal failing configuration.
        """

        if len(config) < 2:
            assert self.test(config, 'assert') == self.FAIL
            logger.info('Test case is minimal already.')
            return config

        logger.debug('dd(%r) ...', config)

        outcome = self._dd(config)

        logger.debug('dd(%r) = %r', config, outcome)

        return outcome

    def test(self, config, config_id):
        """
        Test a single configuration and save the result in cache.

        :param config: The current configuration to test.
        :param config_id: Unique ID that will be used to save tests to easily identifiable directories.
        :return: PASS or FAIL
        """

        logger.debug('\t[ %s ]: test...', AbstractDD.pretty_config_id(config_id))

        outcome = self._test(config, config_id)

        logger.debug('\t[ %s ]: test = %r', AbstractDD.pretty_config_id(config_id), outcome)

        if 'assert' not in config_id:
            self._cache.add(config, outcome)

        return outcome
