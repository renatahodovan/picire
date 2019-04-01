# Copyright (c) 2016-2019 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import logging

from multiprocessing.sharedctypes import Value

from .abstract_dd import AbstractDD
from .outcome_cache import ConfigCache
from .shared_cache import shared_cache_decorator

logger = logging.getLogger(__name__)


class AbstractParallelDD(AbstractDD):
    """
    Abstract super-class of the various parallel DD implementations.
    """

    def __init__(self, test, split, proc_num, max_utilization, cache=None, id_prefix=()):
        """
        Initialize an AbstractParallelDD object.

        :param test: A callable tester object.
        :param split: Splitter method to break a configuration up to n parts.
        :param proc_num: The level of parallelization.
        :param max_utilization: The maximum CPU utilization accepted.
        :param cache: Cache object to use.
        :param id_prefix: Tuple to prepend to config IDs during tests.
        """
        cache = cache or shared_cache_decorator(ConfigCache)()
        AbstractDD.__init__(self, test, split, cache=cache, id_prefix=id_prefix)

        self._proc_num = proc_num
        self._max_utilization = max_utilization
        self._fail_index = Value('i', -1, lock=False)

    def _loop_body(self, config, index, config_id):
        """
        The function that will be run in parallel.

        :param config: The list of entries of the current configuration.
        :param index: The index of the current configuration.
        :param config_id: The unique ID of the current configuration.
        :return: True if the test is not interesting, False otherwise.
        """
        if self._test_config(config, config_id) == self.FAIL:
            self._fail_index.value = index
            return False

        return True
