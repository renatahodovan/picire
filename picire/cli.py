# Copyright (c) 2016 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.md or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import chardet
import codecs
import logging
import os
import pkgutil
import sys
import time

from argparse import ArgumentParser
from functools import reduce
from os.path import abspath, basename, exists, join, realpath
from shutil import rmtree

from . import config_splitters, config_iterators, global_structures
from .combined_iterator import CombinedIterator
from .combined_parallel_dd import CombinedParallelDD
from .light_dd import LightDD
from .parallel_dd import ParallelDD
from .subprocess_test import ConcatTestBuilder, SubprocessTest

logger = logging.getLogger('picire')
__version__ = pkgutil.get_data(__package__, 'VERSION').decode('ascii').strip()


def create_parser():
    parser = ArgumentParser(description='Command line interface of the "picire" test case reducer.',
                            prog='Picire', add_help=True)
    parser.add_argument('-i', '--input', required=True,
                        help='The test case to be reduced.')

    # Base reduce settings.
    parser.add_argument('--disable-cache', action='store_true', default=False,
                        help='Turn off caching.')
    parser.add_argument('--split', dest='split_method',
                        choices=[i for i in dir(config_splitters) if not i.startswith('_')], default='zeller',
                        help='The split algorithm to use.')
    parser.add_argument('--test', required=True,
                        help='The test command to execute to decide whether an input is interesting or not.')
    parser.add_argument('--encoding',
                        help='The encoding of the input test.')

    # Extra settings for parallel reduce.
    parser.add_argument('-p', '--parallel', action='store_true', default=False,
                        help='Run dd in parallel.')
    parser.add_argument('-c', '--combine-loops', action='store_true', default=False,
                        help='Combine subset and complement check loops for more parallelization (has effect in parallel mode only).')
    parser.add_argument('-j', '--jobs', type=int,
                        help='The maximum number of test commands to execute in parallel (has effect in parallel mode only).')
    parser.add_argument('-u', '--max-utilization', type=int, default=100,
                        help='Maximum CPU utilization allowed; don\'t start new parallel jobs if utilization is higher (has effect in parallel mode only).')

    # Tweaks how to walk through the chunk lists.
    parser.add_argument('--complement-first', dest='subset_first', action='store_false', default=True,
                        help='Check complements first.')
    parser.add_argument('--subset-iterator',
                        choices=[i for i in dir(config_iterators) if not i.startswith('_')], default='forward',
                        help='The ordering strategy for looping through subsets.')
    parser.add_argument('--complement-iterator',
                        choices=[i for i in dir(config_iterators) if not i.startswith('_')], default='forward',
                        help='The ordering strategy for looping through complements.')

    # Additional settings.
    parser.add_argument('-l', '--log-level',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
                        help='The verbosity level of diagnostic messages.')
    parser.add_argument('-o', '--out',
                        help='The path of the working directory.')
    parser.add_argument('--disable-cleanup', dest='cleanup', default=True, action='store_false',
                        help='Disable the removal of generated temporary files.')
    return parser


def execute():

    parser = create_parser()
    # Implementation specific CLI options that are not needed to be part of the core parser.
    parser.add_argument('-a', '--atom', choices=['char', 'line'], default='line',
                        help='The atom (i.e., input granularity) to work with.')
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))

    args = parser.parse_args()

    logging.basicConfig(format='%(message)s')
    logger.setLevel(args.log_level)

    args.input = abspath(realpath(args.input))
    if not exists(args.input):
        parser.error('Input file does not exits: %s' % args.input)

    args.test = abspath(realpath(args.test))
    if not exists(args.test) or not os.access(abspath(args.test), os.X_OK):
        parser.error('Tester program does not exist or isn\'t executable: %s' % args.test)

    if args.encoding:
        try:
            codecs.lookup(args.encoding)
        except LookupError:
            parser.error('The given encoding (%s) is not known.' % args.encoding)

    split_method = getattr(config_splitters, args.split_method)
    subset_iterator = getattr(config_iterators, args.subset_iterator)
    complement_iterator = getattr(config_iterators, args.complement_iterator)

    args.out = abspath(realpath(args.out if args.out else '%s.%s' % (args.input, time.strftime('%Y%m%d_%H%M%S'))))
    tests_dir = join(args.out, 'tests')
    args.jobs = 1 if not args.parallel else args.jobs if args.jobs else os.cpu_count()

    with open(args.input, 'rb') as f:
        src = f.read()

    if not args.encoding:
        args.encoding = chardet.detect(src)['encoding']
        if not args.encoding:
            parser.error('The encoding of the test is not recognized.'
                         'Please define it with the --encoding command line option.')

    if not exists(abspath(args.out)):
        os.makedirs(args.out)
        os.makedirs(tests_dir)

    if args.atom == 'line':
        content = src.decode(args.encoding).splitlines(keepends=True)
    elif args.atom == 'char':
        content = src.decode(args.encoding)

    if len(content) < 2:
        parser.info('Test case is minimal already.')
        sys.exit(0)

    logger.info('Reduce session starts for %s\n%s' % (
        args.input, reduce(lambda x, y: x + y, ['\t%s: %s\n' % (k, v) for k, v in sorted(vars(args).items())], '')))
    logger.info('Initial test contains %s %ss' % (len(content), args.atom))

    test_path_pattern = join(tests_dir, '%s', basename(args.input))
    command_pattern = '%s %%s' % abspath(args.test)

    global_structures.init(args.parallel, args.disable_cache)

    test = SubprocessTest(command_pattern, ConcatTestBuilder(content), test_path_pattern, args.encoding)
    if not args.parallel:
        dd = LightDD(test,
                     split=split_method,
                     subset_first=args.subset_first,
                     subset_iterator=subset_iterator,
                     complement_iterator=complement_iterator)
    elif not args.combine_loops:
        dd = ParallelDD(test,
                        split=split_method,
                        proc_num=args.jobs,
                        max_utilization=args.max_utilization,
                        subset_first=args.subset_first,
                        subset_iterator=subset_iterator,
                        complement_iterator=complement_iterator)
    else:
        dd = CombinedParallelDD(test,
                                split=split_method,
                                proc_num=args.jobs,
                                max_utilization=args.max_utilization,
                                config_iterator=CombinedIterator(args.subset_first, subset_iterator, complement_iterator))

    min_set = dd.ddmin(list(range(len(content))))

    logger.debug('A minimal config is: %s' % min_set)
    out_file = join(args.out, basename(args.input))
    with codecs.open(out_file, 'w', encoding=args.encoding) as f:
        f.write(''.join(content[x] for x in min_set))
    logger.info('Result is saved to %s.' % out_file)

    if args.cleanup:
        rmtree(tests_dir)
