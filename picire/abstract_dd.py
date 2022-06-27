# Copyright (c) 2016-2023 Renata Hodovan, Akos Kiss.
# Copyright (c) 2023 Daniel Vince.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import itertools
import logging

from .cache import OutcomeCache
from .outcome import Outcome
from .splitter import ZellerSplit

logger = logging.getLogger(__name__)


class AbstractDD(object):
    """
    Abstract super-class of the parallel and non-parallel DD classes.
    """

    def __init__(self, test, *, split=None, cache=None, id_prefix=None, dd_star=False):
        """
        Initialise an abstract DD class. Not to be called directly, only by
        super calls in subclass initializers.

        :param test: A callable tester object.
        :param split: Splitter method to break a configuration up to n parts.
        :param cache: Cache object to use.
        :param id_prefix: Tuple to prepend to config IDs during tests.
        :param dd_star: Boolean to enable the DD star algorithm.
        """
        self._test = test
        self._split = split or ZellerSplit()
        self._cache = cache or OutcomeCache()
        self._id_prefix = id_prefix or ()
        self._iteration_prefix = ()
        self._dd_star = dd_star

    def __call__(self, config):
        """
        Return a 1-minimal failing subset of the initial configuration.

        :param config: The initial configuration that will be reduced.
        :return: 1-minimal failing configuration.
        """
        for iter_cnt in itertools.count():
            logger.info('Iteration #%d', iter_cnt)
            self._iteration_prefix = self._id_prefix + (f'i{iter_cnt}',)
            changed = False
            subsets = [config]
            complement_offset = 0

            for run in itertools.count():
                logger.info('Run #%d', run)
                logger.info('\tConfig size: %d', len(config))
                assert self._test_config(config, (f'r{run}', 'assert')) is Outcome.FAIL

                # Minimization ends if the configuration is already reduced to a single unit.
                if len(config) < 2:
                    logger.info('\tGranularity: %d', len(subsets))
                    logger.debug('\tConfig: %r', subsets)
                    break

                if len(subsets) < 2:
                    assert len(subsets) == 1
                    subsets = self._split(subsets)

                logger.info('\tGranularity: %d', len(subsets))
                logger.debug('\tConfig: %r', subsets)

                next_subsets, complement_offset = self._reduce_config(run, subsets, complement_offset)

                if next_subsets is not None:
                    changed = True
                    # Interesting configuration is found, continue reduction with this configuration.
                    subsets = next_subsets
                    config = [c for s in subsets for c in s]

                    logger.info('\tReduced')

                elif len(subsets) < len(config):
                    # No interesting configuration is found but it is still not the finest splitting, start new iteration.
                    next_subsets = self._split(subsets)
                    complement_offset = (complement_offset * len(next_subsets)) / len(subsets)
                    subsets = next_subsets

                    logger.info('\tIncreased granularity')

                else:
                    # Current iteration ends if no interesting configuration was found by the finest splitting.
                    break

            if not self._dd_star or not changed:
                break

        logger.info('\tDone')
        return config

    def _reduce_config(self, run, subsets, complement_offset):
        """
        Perform the reduce task of ddmin. To be overridden by subclasses.

        :param run: The index of the current iteration.
        :param subsets: List of sets that the current configuration is split to.
        :param complement_offset: A compensation offset needed to calculate the
            index of the first unchecked complement (optimization purpose only).
        :return: Tuple: (list of subsets composing the failing config or None,
            next complement_offset).
        """
        raise NotImplementedError()

    def _lookup_cache(self, config, config_id):
        """
        Perform a cache lookup if caching is enabled.

        :param config: The configuration we are looking for.
        :param config_id: The ID describing the configuration (only for debug
            message).
        :return: None if outcome is not found for config in cache or if caching
            is disabled, PASS or FAIL otherwise.
        """
        cached_result = self._cache.lookup(config)
        if cached_result is not None:
            logger.debug('\t[ %s ]: cache = %r', self._pretty_config_id(self._iteration_prefix + config_id), cached_result.name)

        return cached_result

    def _test_config(self, config, config_id):
        """
        Test a single configuration and save the result in cache.

        :param config: The current configuration to test.
        :param config_id: Unique ID that will be used to save tests to easily
            identifiable directories.
        :return: PASS or FAIL
        """
        config_id = self._iteration_prefix + config_id

        logger.debug('\t[ %s ]: test...', self._pretty_config_id(config_id))
        outcome = self._test(config, config_id)
        logger.debug('\t[ %s ]: test = %r', self._pretty_config_id(config_id), outcome.name)

        if 'assert' not in config_id:
            self._cache.add(config, outcome)

        return outcome

    @staticmethod
    def _pretty_config_id(config_id):
        """
        Create beautified identifier for the current task from the argument.
        The argument is typically a tuple in the form of ('rN', 'DM'), where N
        is the index of the current iteration, D is direction of reduce (either
        s(ubset) or c(omplement)), and M is the index of the current test in the
        iteration. Alternatively, argument can also be in the form of
        (rN, 'assert') for double checking the input at the start of an
        iteration.

        :param config_id: Config ID tuple.
        :return: Concatenating the arguments with slashes, e.g., "rN / DM".
        """
        return ' / '.join(str(i) for i in config_id)
