# Copyright (c) 2016-2023 Renata Hodovan, Akos Kiss.
# Copyright (c) 2023 Daniel Vince.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import logging
import math
import pytest

import picire


def interesting_a(c):
    if 7 in c and 2 not in c:
        return False
    if 5 in c and 8 in c:
        return True
    return False

config_a = [1, 2, 3, 4, 5, 6, 7, 8]
expect_a = [5, 8]


def interesting_b(c):
    if not c:
        return False
    if 1 in c and 2 in c and 3 in c and 4 in c and \
                    5 in c and 6 in c and 7 in c and 8 in c:
        return True
    return False

config_b = [1, 2, 3, 4, 5, 6, 7, 8]
expect_b = [1, 2, 3, 4, 5, 6, 7, 8]


def interesting_c(c):
    if 1 in c and 2 in c and 3 in c and 4 in c and \
       6 in c and 8 in c:
        return True
    return False

config_c = [1, 2, 3, 4, 5, 6, 7, 8]
expect_c = [1, 2, 3, 4, 6, 8]


class CaseTest:

    def __init__(self, interesting, content):
        self.content = content
        self.interesting = interesting

    def __call__(self, config, config_id):
        return picire.Outcome.FAIL if self.interesting([self.content[x] for x in config]) else picire.Outcome.PASS


@pytest.mark.parametrize('interesting, config, expect', [
    (interesting_a, config_a, expect_a),
    (interesting_b, config_b, expect_b),
    (interesting_c, config_c, expect_c),
])
@pytest.mark.parametrize('granularity', [
    2,
    math.inf,
])
class TestApi:

    def _run_picire(self, interesting, config, expect, granularity, dd, split, subset_first, subset_iterator, complement_iterator, cache):
        if dd != picire.DD:
            cache = picire.shared_cache_decorator(cache)

        logging.basicConfig(format='%(message)s')
        logging.getLogger('picire').setLevel(logging.DEBUG)

        dd_obj = dd(CaseTest(interesting, config),
                    split=split(n=granularity),
                    cache=cache(),
                    config_iterator=picire.iterator.CombinedIterator(subset_first, subset_iterator, complement_iterator))
        output = [config[x] for x in dd_obj(list(range(len(config))))]

        assert output == expect

    @pytest.mark.parametrize('split, subset_first, subset_iterator, complement_iterator, cache', [
        (picire.splitter.BalancedSplit, True, picire.iterator.forward, picire.iterator.forward, picire.cache.NoCache),
        (picire.splitter.ZellerSplit, True, picire.iterator.forward, picire.iterator.backward, picire.cache.ConfigCache),
        (picire.splitter.BalancedSplit, False, picire.iterator.backward, picire.iterator.forward, picire.cache.NoCache),
        (picire.splitter.ZellerSplit, False, picire.iterator.backward, picire.iterator.backward, picire.cache.ConfigCache),
        (picire.splitter.BalancedSplit, True, picire.iterator.skip, picire.iterator.forward, picire.cache.NoCache),
        (picire.splitter.ZellerSplit, True, picire.iterator.skip, picire.iterator.backward, picire.cache.ConfigCache),
    ])
    def test_dd(self, interesting, config, expect, granularity, split, subset_first, subset_iterator, complement_iterator, cache):
        self._run_picire(interesting, config, expect, granularity, picire.DD, split, subset_first, subset_iterator, complement_iterator, cache)

    @pytest.mark.parametrize('split, subset_first, subset_iterator, complement_iterator, cache', [
        (picire.splitter.ZellerSplit, False, picire.iterator.forward, picire.iterator.forward, picire.cache.ConfigCache),
        (picire.splitter.BalancedSplit, False, picire.iterator.forward, picire.iterator.backward, picire.cache.NoCache),
        (picire.splitter.ZellerSplit, True, picire.iterator.backward, picire.iterator.forward, picire.cache.ConfigCache),
        (picire.splitter.BalancedSplit, True, picire.iterator.backward, picire.iterator.backward, picire.cache.NoCache),
        (picire.splitter.ZellerSplit, False, picire.iterator.skip, picire.iterator.forward, picire.cache.ConfigCache),
        (picire.splitter.BalancedSplit, False, picire.iterator.skip, picire.iterator.backward, picire.cache.NoCache),
    ])
    def test_parallel(self, interesting, config, expect, granularity, split, subset_first, subset_iterator, complement_iterator, cache):
        self._run_picire(interesting, config, expect, granularity, picire.ParallelDD, split, subset_first, subset_iterator, complement_iterator, cache)
