# Copyright (c) 2016 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.md or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import logging

from multiprocessing.sharedctypes import Value

from .abstract_dd import AbstractDD

logger = logging.getLogger(__name__)


class AbstractParallelDD(AbstractDD):
    """Abstract super-class of the various parallel DD implementations."""

    def __init__(self, test, split, proc_num, max_utilization):
        """
        Initialize an AbstractParallelDD object.

        :param test: A callable tester object.
        :param split: Splitter method to break a configuration up to n parts.
        :param proc_num: The level of parallelization.
        :param max_utilization: The maximum CPU utilization accepted.
        """
        AbstractDD.__init__(self, test, split)

        self._proc_num = proc_num
        self._max_utilization = max_utilization
        self._fail_index = Value('i', -1, lock=False)

    def _loop_body(self, config, index, config_id):
        """
        The function that will be run in parallel.

        :param config: The list of entries of the current configuration.
        :param index: The index of the current configuration.
        :param config_id: The string representation of the current configuration.
        :return: True if the test is not interesting, False otherwise.
        """
        if self.test(config, config_id) == self.FAIL:
            self._fail_index.value = index
            return False

        return True
