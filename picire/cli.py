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
from os.path import abspath, basename, exists, join, relpath
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


def process_args(parser, args):
    args.input = abspath(relpath(args.input))
    if not exists(args.input):
        parser.error('Input file does not exits: %s' % args.input)

    with open(args.input, 'rb') as f:
        args.src = f.read()

    if args.encoding:
        try:
            codecs.lookup(args.encoding)
        except LookupError:
            parser.error('The given encoding (%s) is not known.' % args.encoding)
    else:
        args.encoding = chardet.detect(args.src)['encoding']
        if not args.encoding:
            parser.error('The encoding of the test is not recognized.'
                         'Please define it with the --encoding command line option.')

    args.test = abspath(relpath(args.test))
    if not exists(args.test) or not os.access(args.test, os.X_OK):
        parser.error('Tester program does not exist or isn\'t executable: %s' % args.test)

    args.tester_class = SubprocessTest
    args.tester_config = {
        'encoding': args.encoding,
        'command_pattern': '%s %%s' % args.test
    }

    args.jobs = 1 if not args.parallel else args.jobs if args.jobs else os.cpu_count()

    split_method = getattr(config_splitters, args.split_method)
    subset_iterator = getattr(config_iterators, args.subset_iterator)
    complement_iterator = getattr(config_iterators, args.complement_iterator)

    # Choose the reducer class that will be used and its configuration.
    args.reduce_config = {'split': split_method}
    if not args.parallel:
        args.reduce_class = LightDD
        args.reduce_config['subset_iterator'] = subset_iterator
        args.reduce_config['complement_iterator'] = complement_iterator
        args.reduce_config['subset_first'] = args.subset_first
    else:
        args.reduce_config['proc_num'] = args.jobs
        args.reduce_config['max_utilization'] = args.max_utilization

        if args.combine_loops:
            args.reduce_class = CombinedParallelDD
            args.reduce_config['config_iterator'] = CombinedIterator(args.subset_first, subset_iterator,
                                                                     complement_iterator)
        else:
            args.reduce_class = ParallelDD
            args.reduce_config['subset_iterator'] = subset_iterator
            args.reduce_config['complement_iterator'] = complement_iterator
            args.reduce_config['subset_first'] = args.subset_first

    args.out = abspath(relpath(args.out if args.out else '%s.%s' % (args.input, time.strftime('%Y%m%d_%H%M%S'))))


def call(*,
         reduce_class, reduce_config,
         tester_class, tester_config,
         input, src, encoding, out,
         atom,
         parallel=False, disable_cache=False, cleanup=True):
    """
    Execute picire as if invoked from command line, however, control its
    behaviour not via command line arguments but function parameters.

    :param reduce_class: Reference to the reducer class.
    :param reduce_config: Dictionary containing information to initialize the reduce_class.
    :param tester_class: Reference to a runnable class that can decide about the interestingness of a test case.
    :param tester_config: Dictionary containing information to initialize the tester_class.
    :param input: Path to the test case to reduce (only used to determine the name of the output file).
    :param src: Contents of the test case to reduce.
    :param encoding: Encoding of the input test case.
    :param out: Path to the output directory.
    :param atom: Input granularity to work with during reduce ('char' or 'line').
    :param parallel: Boolean to enable parallel mode (default: False).
    :param disable_cache: Boolean to disable cache (default: False).
    :param cleanup: Binary flag denoting whether removing auxiliary files at the end is enabled (default: True).
    :return: The path to the minimal test case.
    """

    # Get the parameters in a dictionary so that they can be pretty-printed later
    # (minus src, as that parameter can be arbitrarily large)
    args = locals().copy()
    del args['src']

    tests_dir = join(out, 'tests')
    os.makedirs(tests_dir, exist_ok=True)

    global_structures.init(parallel, disable_cache)

    # Split source to the chosen atoms.
    if atom == 'line':
        content = src.decode(encoding).splitlines(keepends=True)
    elif atom == 'char':
        content = src.decode(encoding)

    if len(content) < 2:
        logger.info('Test case is minimal already.')
        sys.exit(0)

    logger.info('Reduce session starts for %s\n%s' % (
        input, reduce(lambda x, y: x + y, ['\t%s: %s\n' % (k, v) for k, v in sorted(args.items())], '')))
    logger.info('Initial test contains %s %ss' % (len(content), atom))

    dd = reduce_class(tester_class(test_builder=ConcatTestBuilder(content),
                                   test_pattern=join(tests_dir, '%s', basename(input)),
                                   **tester_config),
                      **reduce_config)
    min_set = dd.ddmin(list(range(len(content))))

    logger.debug('A minimal config is: %s' % min_set)
    out_file = join(out, basename(input))
    with codecs.open(out_file, 'w', encoding=encoding, errors='ignore') as f:
        f.write(ConcatTestBuilder(content)(min_set))
    logger.info('Result is saved to %s.' % out_file)

    if cleanup:
        rmtree(tests_dir)

    return out_file


def execute():
    """
    The main entry point of picire.
    """

    parser = create_parser()
    # Implementation specific CLI options that are not needed to be part of the core parser.
    parser.add_argument('-a', '--atom', choices=['char', 'line'], default='line',
                        help='The atom (i.e., input granularity) to work with.')
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))

    args = parser.parse_args()

    logging.basicConfig(format='%(message)s')
    logger.setLevel(args.log_level)

    process_args(parser, args)

    call(reduce_class=args.reduce_class,
         reduce_config=args.reduce_config,
         tester_class=args.tester_class,
         tester_config=args.tester_config,
         input=args.input,
         src=args.src,
         encoding=args.encoding,
         out=args.out,
         atom=args.atom,
         parallel=args.parallel,
         disable_cache=args.disable_cache,
         cleanup=args.cleanup)
