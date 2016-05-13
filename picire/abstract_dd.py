# Copyright (c) 2016 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.md or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import logging

from . import global_structures

logger = logging.getLogger(__name__)


class AbstractDD(object):
    """Abstract super-class of the parallel and non-parallel DD classes."""

    # Test outcomes.
    PASS = 'PASS'
    FAIL = 'FAIL'

    def __init__(self, test, split):
        """
        Initialise an abstract DD class. Not to be called directly,
        only by super calls in subclass initializers.

        :param test: A callable tester object.
        :param split: Splitter method to break a configuration up to n parts.
        """
        self._test = test
        self._split = split

    @staticmethod
    def config_id(run, dir, i):
        """
        Create identifier for the current task.

        :param run: The index of the current iteration.
        :param dir: The direction of reduce: either s(ubest) or c(omplement).
        :param i: The index of the current test in the iteration.
        :return: Config id in (run)_(dir)_(i) format.
        """
        return '%d_%s_%d' % (run, dir, i)

    @staticmethod
    def pretty_config_id(config_id):
        """
        Create beautified identifier for the current task.

        :param config_id: Config ID in form (run)_(dir)_(i).
        :return: Config ID in form (run) / (dir) / (i).
        """
        return config_id.replace('_', ' / ')

    @staticmethod
    def lookup_cache(config, config_id):
        """
        Perform a cache lookup if caching is enabled.

        :param config: The configuration we are looking for.
        :param config_id: The ID describing the configuration (only for debug message).
        :return: None if caching is disabled, PASS or FAIL otherwise.
        """
        if not global_structures.outcome_cache:
            return None

        cached_result = global_structures.outcome_cache.lookup(config)
        if cached_result is not None:
            logger.debug('\t\t-- [ %s ]: %s' % (AbstractDD.pretty_config_id(config_id), cached_result))

        return cached_result

    @staticmethod
    def minus(c1, c2):
        """Return a list of all elements of C1 that are not in C2."""
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

        logger.debug('dd(%s) ...' % (repr(config)))

        outcome = self._dd(config)

        logger.debug('dd(%s) = %s' % (repr(config), repr(outcome)))

        return outcome

    def test(self, config, config_id):
        """
        Test a single configuration and save the result in cache.

        :param config: The current configuration to test.
        :param config_id: Unique ID that will be used to save tests to easily identifiable directories.
        :return: PASS or FAIL
        """

        logger.debug('\t[ %s ]: test...' % AbstractDD.pretty_config_id(config_id))

        outcome = self._test(config, config_id)

        logger.debug('\t[ %s ]: test = %s' % (AbstractDD.pretty_config_id(config_id), repr(outcome)))

        if global_structures.outcome_cache and config_id != 'assert':
            global_structures.outcome_cache.add(config, outcome)
            logger.debug('\t\t++ [ %s ]' % AbstractDD.pretty_config_id(config_id))

        return outcome
