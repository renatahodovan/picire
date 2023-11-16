# Copyright (c) 2016-2023 Renata Hodovan, Akos Kiss.
# Copyright (c) 2023 Daniel Vince.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import itertools
import logging

from .cache import ConfigCache
from .exception import ReductionError, ReductionStopped
from .iterator import CombinedIterator
from .outcome import Outcome
from .splitter import ZellerSplit

logger = logging.getLogger(__name__)


class DD:
    """
    Single process version of the Delta Debugging algorithm.
    """

    def __init__(self, test, *, split=None, cache=None, id_prefix=None,
                 config_iterator=None, dd_star=False, stop=None):
        """
        Initialize a DD object.

        :param test: A callable tester object.
        :param split: Splitter method to break a configuration up to n parts.
        :param cache: Cache object to use.
        :param id_prefix: Tuple to prepend to config IDs during tests.
        :param config_iterator: Reference to a generator function that provides
            config indices in an arbitrary order.
        :param dd_star: Boolean to enable the DD star algorithm.
        :param stop: A callable invoked before the execution of every test.
        """
        self._test = test
        self._split = split or ZellerSplit()
        self._cache = cache or ConfigCache()
        self._id_prefix = id_prefix or ()
        self._iteration_prefix = ()
        self._config_iterator = config_iterator or CombinedIterator()
        self._dd_star = dd_star
        self._stop = stop

    def __call__(self, config):
        """
        Return a 1-minimal failing subset of the initial configuration.

        :param config: The initial configuration that will be reduced.
        :return: 1-minimal failing configuration.
        :raises ReductionException: If reduction could not run until completion.
            The ``result`` attribute of the exception contains the smallest,
            potentially non-minimal, but failing configuration found during
            reduction.
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

                try:
                    next_subsets, complement_offset = self._reduce_config(run, subsets, complement_offset)
                except ReductionStopped as e:
                    logger.info('\tStopped')
                    e.result = config
                    raise
                except Exception as e:
                    logger.info('\tErrored')
                    raise ReductionError(str(e), result=config) from e

                if next_subsets is not None:
                    changed = True
                    # Interesting configuration is found, continue reduction with this configuration.
                    subsets = next_subsets
                    config = [c for s in subsets for c in s]

                    logger.info('\tReduced')

                elif len(subsets) < len(config):
                    # No interesting configuration is found but it is still not the finest splitting, start new iteration.
                    next_subsets = self._split(subsets)
                    complement_offset = (complement_offset * len(next_subsets)) // len(subsets)
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
        Perform the reduce task of ddmin.

        :param run: The index of the current iteration.
        :param subsets: List of sets that the current configuration is split to.
        :param complement_offset: A compensation offset needed to calculate the
            index of the first unchecked complement (optimization purpose only).
        :return: Tuple: (list of subsets composing the failing config or None,
            next complement_offset).
        """
        n = len(subsets)
        fvalue = n
        for i in self._config_iterator(n):
            if i >= 0:
                config_id = (f'r{run}', f's{i}')
                config_set = subsets[i]
            else:
                i = (-i - 1 + complement_offset) % n
                config_id = (f'r{run}', f'c{i}')
                config_set = [c for si, s in enumerate(subsets) for c in s if si != i]
                i = -i - 1

            # Get the outcome either from cache or by testing it.
            outcome = self._lookup_cache(config_set, config_id)
            if outcome is None:
                self._check_stop()
                outcome = self._test_config(config_set, config_id)
            if outcome is Outcome.FAIL:
                fvalue = i
                break

        # fvalue contains the index of the cycle in the previous loop
        # which was found interesting. Otherwise it's n.
        if fvalue < 0:
            # Interesting complement is found.
            # In next run, start removing the following subset
            fvalue = -fvalue - 1
            return subsets[:fvalue] + subsets[fvalue + 1:], fvalue
        if fvalue < n:
            # Interesting subset is found.
            return [subsets[fvalue]], 0

        return None, complement_offset

    def _check_stop(self):
        """
        Check whether reduction shall continue with executing the next test or
        stop.

        :raises ReductionStopped: If reduction shall not continue.
        """
        if self._stop:
            self._stop()

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

        if cached_result is not None and logger.isEnabledFor(logging.DEBUG):
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

        if logger.isEnabledFor(logging.DEBUG):
            pretty_config_id = self._pretty_config_id(config_id)
            logger.debug('\t[ %s ]: test...', pretty_config_id)

        outcome = self._test(config, config_id)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('\t[ %s ]: test = %r', pretty_config_id, outcome.name)

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
