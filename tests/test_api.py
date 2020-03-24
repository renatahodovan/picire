# Copyright (c) 2016-2020 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import logging
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
        return picire.AbstractDD.FAIL if self.interesting([self.content[x] for x in config]) else picire.AbstractDD.PASS


@pytest.mark.parametrize('interesting, config, expect', [
    (interesting_a, config_a, expect_a),
    (interesting_b, config_b, expect_b),
    (interesting_c, config_c, expect_c),
])
@pytest.mark.parametrize('granularity', [
    2,
    float('inf'),
])
class TestApi:

    def _run_picire(self, interesting, config, expect, granularity, dd, split, subset_first, subset_iterator, complement_iterator, cache):
        if dd != picire.CombinedParallelDD:
            it_kwargs = {
                'subset_first': subset_first,
                'subset_iterator': subset_iterator,
                'complement_iterator': complement_iterator,
            }
        else:
            it_kwargs = {
                'config_iterator': picire.CombinedIterator(subset_first, subset_iterator, complement_iterator)
            }

        if dd != picire.LightDD:
            cache = picire.shared_cache_decorator(cache)

        logging.basicConfig(format='%(message)s')
        logging.getLogger('picire').setLevel(logging.DEBUG)

        dd_obj = dd(CaseTest(interesting, config),
                    split=split,
                    cache=cache(),
                    **it_kwargs)
        output = [config[x] for x in dd_obj.ddmin(list(range(len(config))), n=granularity)]

        assert output == expect

    @pytest.mark.parametrize('split, subset_first, subset_iterator, complement_iterator, cache', [
        (picire.config_splitters.balanced, True, picire.config_iterators.forward, picire.config_iterators.forward, picire.OutcomeCache),
        (picire.config_splitters.zeller, True, picire.config_iterators.forward, picire.config_iterators.backward, picire.ConfigCache),
        (picire.config_splitters.balanced, False, picire.config_iterators.backward, picire.config_iterators.forward, picire.OutcomeCache),
        (picire.config_splitters.zeller, False, picire.config_iterators.backward, picire.config_iterators.backward, picire.ConfigCache),
        (picire.config_splitters.balanced, True, picire.config_iterators.skip, picire.config_iterators.forward, picire.OutcomeCache),
        (picire.config_splitters.zeller, True, picire.config_iterators.skip, picire.config_iterators.backward, picire.ConfigCache),
    ])
    def test_light(self, interesting, config, expect, granularity, split, subset_first, subset_iterator, complement_iterator, cache):
        self._run_picire(interesting, config, expect, granularity, picire.LightDD, split, subset_first, subset_iterator, complement_iterator, cache)

    @pytest.mark.parametrize('split, subset_first, subset_iterator, complement_iterator, cache', [
        (picire.config_splitters.zeller, False, picire.config_iterators.forward, picire.config_iterators.forward, picire.ConfigCache),
        (picire.config_splitters.balanced, False, picire.config_iterators.forward, picire.config_iterators.backward, picire.OutcomeCache),
        (picire.config_splitters.zeller, True, picire.config_iterators.backward, picire.config_iterators.forward, picire.ConfigCache),
        (picire.config_splitters.balanced, True, picire.config_iterators.backward, picire.config_iterators.backward, picire.OutcomeCache),
        (picire.config_splitters.zeller, True, picire.config_iterators.skip, picire.config_iterators.forward, picire.ConfigCache),
        (picire.config_splitters.balanced, True, picire.config_iterators.skip, picire.config_iterators.backward, picire.OutcomeCache),
    ])
    def test_parallel(self, interesting, config, expect, granularity, split, subset_first, subset_iterator, complement_iterator, cache):
        self._run_picire(interesting, config, expect, granularity, picire.ParallelDD, split, subset_first, subset_iterator, complement_iterator, cache)

    @pytest.mark.parametrize('split, subset_first, subset_iterator, complement_iterator, cache', [
        (picire.config_splitters.zeller, True, picire.config_iterators.forward, picire.config_iterators.forward, picire.OutcomeCache),
        (picire.config_splitters.balanced, True, picire.config_iterators.forward, picire.config_iterators.backward, picire.ConfigCache),
        (picire.config_splitters.zeller, False, picire.config_iterators.backward, picire.config_iterators.forward, picire.OutcomeCache),
        (picire.config_splitters.balanced, False, picire.config_iterators.backward, picire.config_iterators.backward, picire.ConfigCache),
    ])
    def test_combined(self, interesting, config, expect, granularity, split, subset_first, subset_iterator, complement_iterator, cache):
        self._run_picire(interesting, config, expect, granularity, picire.CombinedParallelDD, split, subset_first, subset_iterator, complement_iterator, cache)
