# Copyright (c) 2016 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import pytest

import picire


class CaseA(object):

    config = [1, 2, 3, 4, 5, 6, 7, 8]
    expect = [5, 8]

    @staticmethod
    def interesting(c):
        if 7 in c and 2 not in c:
            return False
        if 5 in c and 8 in c:
            return True
        return False


class CaseB(object):

    config = [1, 2, 3, 4, 5, 6, 7, 8]
    expect = [1, 2, 3, 4, 5, 6, 7, 8]

    @staticmethod
    def interesting(c):
        if not c:
            return False
        if 1 in c and 2 in c and 3 in c and 4 in c and \
           5 in c and 6 in c and 7 in c and 8 in c:
            return True
        return False


class CaseC(object):

    config = [1, 2, 3, 4, 5, 6, 7, 8]
    expect = [1, 2, 3, 4, 6, 8]

    @staticmethod
    def interesting(c):
        if 1 in c and 2 in c and 3 in c and 4 in c and \
           6 in c and 8 in c:
            return True
        return False


class CaseTest:

    def __init__(self, interesting, content):
        self.content = content
        self.interesting = interesting

    def __call__(self, config, config_id):
        return picire.AbstractDD.FAIL if self.interesting([self.content[x] for x in config]) else picire.AbstractDD.PASS


@pytest.mark.parametrize('dd', [
    picire.LightDD,
    picire.ParallelDD,
    picire.CombinedParallelDD,
])
@pytest.mark.parametrize('split', [
    picire.config_splitters.balanced,
    picire.config_splitters.zeller,
])
@pytest.mark.parametrize('subset_first', [
    True,
    False,
])
@pytest.mark.parametrize('subset_iterator', [
    picire.config_iterators.forward,
    picire.config_iterators.backward,
    picire.config_iterators.skip,
])
@pytest.mark.parametrize('complement_iterator', [
    picire.config_iterators.forward,
    picire.config_iterators.backward,
])
class TestApi:

    @pytest.mark.parametrize('case', [
        CaseA,
        CaseB,
        CaseC,
    ])
    def test_case(self, case, dd, split, subset_first, subset_iterator, complement_iterator):
        picire.global_structures.init(parallel=dd != picire.LightDD, disable_cache=False)

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

        dd_obj = dd(CaseTest(case.interesting, case.config), split=split, **it_kwargs)
        output = [case.config[x] for x in dd_obj.ddmin(list(range(len(case.config))))]

        assert output == case.expect
