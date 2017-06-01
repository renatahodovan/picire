# Copyright (c) 2016-2017 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import argparse
import chardet
import codecs
import logging
import os
import pkgutil
import time

from os.path import abspath, basename, exists, join, relpath
from shutil import rmtree

from . import config_splitters, config_iterators, outcome_cache
from .combined_iterator import CombinedIterator
from .combined_parallel_dd import CombinedParallelDD
from .light_dd import LightDD
from .parallel_dd import ParallelDD
from .shared_cache import shared_cache_decorator
from .subprocess_test import ConcatTestBuilder, SubprocessTest

logger = logging.getLogger('picire')
__version__ = pkgutil.get_data(__package__, 'VERSION').decode('ascii').strip()


def create_parser():
    parser = argparse.ArgumentParser(description='Command line interface of the "picire" test case reducer')
    parser.add_argument('-i', '--input', metavar='FILE', required=True,
                        help='test case to be reduced')

    # Base reduce settings.
    parser.add_argument('--cache', metavar='NAME',
                        choices=[i for i in dir(outcome_cache) if not i.startswith('_') and i.islower()], default='config',
                        help='cache strategy (%(choices)s; default: %(default)s)')
    parser.add_argument('--split', metavar='NAME', dest='split_method',
                        choices=[i for i in dir(config_splitters) if not i.startswith('_')], default='zeller',
                        help='split algorithm (%(choices)s; default: %(default)s)')
    parser.add_argument('--test', metavar='FILE', required=True,
                        help='test command that decides about interestingness of an input')
    parser.add_argument('--encoding', metavar='NAME',
                        help='test case encoding (default: autodetect)')

    # Extra settings for parallel reduce.
    parser.add_argument('-p', '--parallel', action='store_true', default=False,
                        help='run DD in parallel')
    parser.add_argument('-c', '--combine-loops', action='store_true', default=False,
                        help='combine subset and complement check loops for more parallelization (has effect in parallel mode only)')
    parser.add_argument('-j', '--jobs', metavar='N', type=int, default=os.cpu_count(),
                        help='maximum number of test commands to execute in parallel (has effect in parallel mode only; default: %(default)s)')
    parser.add_argument('-u', '--max-utilization', metavar='N', type=int, default=100,
                        help='maximum CPU utilization allowed; don\'t start new parallel jobs until utilization is higher (has effect in parallel mode only; default: %(default)s)')

    # Tweaks how to walk through the chunk lists.
    parser.add_argument('--complement-first', dest='subset_first', action='store_false', default=True,
                        help='check complements first')
    parser.add_argument('--subset-iterator', metavar='NAME',
                        choices=[i for i in dir(config_iterators) if not i.startswith('_')], default='forward',
                        help='ordering strategy for looping through subsets (%(choices)s; default: %(default)s)')
    parser.add_argument('--complement-iterator', metavar='NAME',
                        choices=[i for i in dir(config_iterators) if not i.startswith('_')], default='forward',
                        help='ordering strategy for looping through complements (%(choices)s; default: %(default)s)')

    # Additional settings.
    parser.add_argument('-l', '--log-level', metavar='LEVEL',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'DISABLE'], default='INFO',
                        help='verbosity level of diagnostic messages (%(choices)s; default: %(default)s)')
    parser.add_argument('-v', '--verbose', dest='log_level', action='store_const', const='DEBUG', default=argparse.SUPPRESS,
                        help='verbose mode (alias for -l %(const)s)')
    parser.add_argument('-q', '--quiet', dest='log_level', action='store_const', const='DISABLE', default=argparse.SUPPRESS,
                        help='quiet mode (alias for -l %(const)s)')
    parser.add_argument('-o', '--out', metavar='DIR',
                        help='working directory (default: input.timestamp)')
    parser.add_argument('--disable-cleanup', dest='cleanup', default=True, action='store_false',
                        help='disable the removal of generated temporary files')
    return parser


def process_args(parser, args):
    if args.log_level == 'DISABLE':
        args.log_level = logging.CRITICAL + 1

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

    args.cache = getattr(outcome_cache, args.cache)
    if args.parallel:
        args.cache = shared_cache_decorator(args.cache)

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
            args.reduce_config['config_iterator'] = CombinedIterator(args.subset_first,
                                                                     subset_iterator,
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
         atom='line',
         cache_class=None, cleanup=True):
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
    :param atom: Input granularity to work with during reduce ('char', 'line', or 'both'; default: 'line').
    :param cache_class: Reference to the cache class to use.
    :param cleanup: Binary flag denoting whether removing auxiliary files at the end is enabled (default: True).
    :return: The path to the minimal test case.
    """

    # Get the parameters in a dictionary so that they can be pretty-printed
    # (minus src, as that parameter can be arbitrarily large)
    args = locals().copy()
    del args['src']
    logger.info('Reduce session starts for %s\n%s',
                input, ''.join(['\t%s: %s\n' % (k, v) for k, v in sorted(args.items())]))

    tests_dir = join(out, 'tests')
    # Split source to the chosen atoms.
    if atom in ['line', 'both']:
        content = src.decode(encoding).splitlines(keepends=True)
        tests_dir = join(tests_dir, 'line')
    elif atom == 'char':
        content = src.decode(encoding)
        tests_dir = join(tests_dir, 'char')
    os.makedirs(tests_dir, exist_ok=True)
    logger.info('Initial test contains %d %ss', len(content), atom)

    test_builder = ConcatTestBuilder(content)
    cache = cache_class() if cache_class else None
    if hasattr(cache, 'set_test_builder'):
        cache.set_test_builder(test_builder)

    dd = reduce_class(tester_class(test_builder=test_builder,
                                   test_pattern=join(tests_dir, '%s', basename(input)),
                                   **tester_config),
                      cache=cache,
                      **reduce_config)
    min_set = dd.ddmin(list(range(len(content))))

    logger.debug('The cached results are: %s', cache)
    logger.debug('A minimal config is: %r', min_set)

    out_file = join(out, basename(input))
    out_src = test_builder(min_set)
    with codecs.open(out_file, 'w', encoding=encoding, errors='ignore') as f:
        f.write(out_src)
    logger.info('Result is saved to %s.', out_file)

    if cleanup:
        rmtree(tests_dir)

    if atom == 'both':
        out_file = call(reduce_class=reduce_class, reduce_config=reduce_config,
                        tester_class=tester_class, tester_config=tester_config,
                        input=out_file, src=out_src.encode(encoding=encoding), encoding=encoding, out=out,
                        atom='char',
                        cache_class=cache_class, cleanup=cleanup)

    return out_file


def execute():
    """
    The main entry point of picire.
    """

    parser = create_parser()
    # Implementation specific CLI options that are not needed to be part of the core parser.
    parser.add_argument('-a', '--atom', metavar='NAME', choices=['char', 'line', 'both'], default='line',
                        help='atom (i.e., granularity) of input (%(choices)s; default: %(default)s)')
    parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))

    args = parser.parse_args()
    process_args(parser, args)

    logging.basicConfig(format='%(message)s')
    logger.setLevel(args.log_level)

    call(reduce_class=args.reduce_class,
         reduce_config=args.reduce_config,
         tester_class=args.tester_class,
         tester_config=args.tester_config,
         input=args.input,
         src=args.src,
         encoding=args.encoding,
         out=args.out,
         atom=args.atom,
         cache_class=args.cache,
         cleanup=args.cleanup)
