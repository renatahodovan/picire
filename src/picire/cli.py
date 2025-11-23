# Copyright (c) 2016-2025 Renata Hodovan, Akos Kiss.
# Copyright (c) 2023 Daniel Vince.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import argparse
import codecs
import os
import sys
import time

from datetime import timedelta
from importlib import metadata
from math import inf
from multiprocessing import cpu_count
from os.path import basename, exists, join, realpath
from shutil import rmtree
from textwrap import indent

import chardet
import inators

from inators import log as logging

from .cache import CacheRegistry
from .dd import DD
from .exception import ReductionException, ReductionStopped
from .iterator import CombinedIterator, IteratorRegistry
from .limit_reduction import LimitReduction
from .parallel_dd import ParallelDD
from .splitter import SplitterRegistry
from .subprocess_test import ConcatTestBuilder, SubprocessTest

logger = logging.getLogger('picire')
__version__ = metadata.version(__package__)


def create_parser():
    def int_or_inf(value):
        if value == 'inf':
            return inf
        value = int(value)
        if value < 2:
            raise argparse.ArgumentTypeError(f'invalid value: {value!r} (must be at least 2)')
        return value

    parser = argparse.ArgumentParser(description='Command line interface of the "picire" test case reducer')
    parser.add_argument('-i', '--input', metavar='FILE', required=True,
                        help='test case to be reduced')

    # Base reduce settings.
    parser.add_argument('--cache', metavar='NAME',
                        choices=sorted(CacheRegistry.registry.keys()), default='config',
                        help='cache strategy (%(choices)s; default: %(default)s)')
    parser.add_argument('--split', metavar='NAME',
                        choices=sorted(SplitterRegistry.registry.keys()), default='zeller',
                        help='split algorithm (%(choices)s; default: %(default)s)')
    parser.add_argument('--test', metavar='FILE', required=True,
                        help='test command that decides about interestingness of an input')
    parser.add_argument('--granularity', metavar='N', type=int_or_inf, default=2,
                        help='initial granularity and split factor (integer or \'inf\'; default: %(default)d)')
    parser.add_argument('--encoding', metavar='NAME',
                        help='test case encoding (default: autodetect)')
    parser.add_argument('--no-dd-star', dest='dd_star', default=True, action='store_false',
                        help='run the ddmin algorithm only once')

    # Extra settings for parallel reduce.
    parser.add_argument('-p', '--parallel', action='store_true', default=False,
                        help='run DD in parallel')
    parser.add_argument('-j', '--jobs', metavar='N', type=int, default=cpu_count(),
                        help='maximum number of test commands to execute in parallel (has effect in parallel mode only; default: %(default)s)')

    # Tweaks how to walk through the chunk lists.
    parser.add_argument('--complement-first', dest='subset_first', action='store_false', default=True,
                        help='check complements first')
    parser.add_argument('--subset-iterator', metavar='NAME',
                        choices=sorted(IteratorRegistry.registry.keys()), default='forward',
                        help='ordering strategy for looping through subsets (%(choices)s; default: %(default)s)')
    parser.add_argument('--complement-iterator', metavar='NAME',
                        choices=sorted(IteratorRegistry.registry.keys()), default='forward',
                        help='ordering strategy for looping through complements (%(choices)s; default: %(default)s)')

    # Tweaks for caching.
    parser.add_argument('--cache-fail', action='store_true', default=False,
                        help='store failing, i.e., interesting test cases in the cache')
    parser.add_argument('--no-cache-evict-after-fail', dest='evict_after_fail', action='store_false', default=True,
                        help='disable the eviction of larger test cases from the cache when a failing, i.e., interesting test case is found')

    # Limits on the reduction.
    parser.add_argument('--limit-time', metavar='SEC', type=int,
                        help='limit the execution time of reduction (in seconds; may result in non-minimal output)')
    parser.add_argument('--limit-tests', metavar='N', type=int,
                        help='limit the number of test command executions (may result in non-minimal output)')

    # Logging settings.
    inators.arg.add_log_level_argument(parser)
    parser.add_argument('--log-format', metavar='FORMAT', default='%(message)s',
                        help='printf-style format string of diagnostic messages (default: %(default)s)')
    parser.add_argument('--log-datefmt', metavar='FORMAT', default='%Y-%m-%d %H:%M:%S',
                        help='strftime-style format string of timestamps in diagnostic messages (default: %(default)s)')

    # Additional settings.
    parser.add_argument('-o', '--out', metavar='DIR',
                        help='working directory (default: input.timestamp)')
    parser.add_argument('--no-cleanup', dest='cleanup', default=True, action='store_false',
                        help='disable the removal of generated temporary files')
    return parser


def config_logging(args):
    logging.basicConfig(format=args.log_format, datefmt=args.log_datefmt)
    inators.arg.process_log_level_argument(args, logger)


def process_args(args):
    args.input = realpath(args.input)
    if not exists(args.input):
        raise ValueError(f'Test case does not exist: {args.input}')

    with open(args.input, 'rb') as f:
        args.src = f.read()

    if args.encoding:
        try:
            codecs.lookup(args.encoding)
        except LookupError as e:
            raise ValueError(f'The given encoding ({args.encoding}) is not known.') from e
    else:
        args.encoding = chardet.detect(args.src)['encoding'] or 'latin-1'

    args.src = args.src.decode(args.encoding)

    args.out = realpath(args.out if args.out else f'{args.input}.{time.strftime("%Y%m%d_%H%M%S")}')

    args.test = realpath(args.test)
    if not exists(args.test) or not os.access(args.test, os.X_OK):
        raise ValueError(f'Tester program does not exist or isn\'t executable: {args.test}')

    args.tester_class = SubprocessTest
    args.tester_config = {'command_pattern': [args.test, '%s'],
                          'work_dir': join(args.out, 'tests'),
                          'filename': basename(args.input),
                          'encoding': args.encoding,
                          'cleanup': args.cleanup}

    args.cache_class = CacheRegistry.registry[args.cache]
    args.cache_config = {'cache_fail': args.cache_fail,
                         'evict_after_fail': args.evict_after_fail}

    if args.limit_time is not None or args.limit_tests is not None:
        stop = LimitReduction(deadline=timedelta(seconds=args.limit_time) if args.limit_time is not None else None,
                              max_tests=args.limit_tests)
    else:
        stop = None

    # Choose the reducer class that will be used and its configuration.
    args.reduce_config = {'config_iterator': CombinedIterator(args.subset_first,
                                                              IteratorRegistry.registry[args.subset_iterator],
                                                              IteratorRegistry.registry[args.complement_iterator]),
                          'split': SplitterRegistry.registry[args.split](n=args.granularity),
                          'dd_star': args.dd_star,
                          'stop': stop}
    if not args.parallel:
        args.reduce_class = DD
    else:
        args.reduce_class = ParallelDD
        args.reduce_config.update(proc_num=args.jobs)

    logger.info('Input loaded from %s', args.input)


def pretty_str(obj):
    """
    Return the "pretty-string" representation of a data structure. Explicitly
    handles dicts and lists arbitrarily nested in each other, and objects with
    ``__name__`` (typically functions and classes). Everything else is handled
    with :func:`str` as a fallback. The output is YAML-like, but with no intent
    to be conforming. The goal is to be informative when logging.
    """
    def _pretty_str(obj):
        if not obj:
            return repr(obj)
        if isinstance(obj, dict):
            log = []
            for k, v in sorted(obj.items()):
                k_log = _pretty_str(k)
                v_log = _pretty_str(v)
                if isinstance(v_log, list):
                    log += [f'{k_log}:']
                    for line in v_log:
                        log += [f'\t{line}']
                else:
                    log += [f'{k_log}: {v_log}']
            return log if len(log) > 1 else log[0]
        if isinstance(obj, list):
            v_logs = [_pretty_str(v) for v in obj]
            if any(isinstance(v_log, list) for v_log in v_logs):
                log = []
                for v_log in v_logs:
                    if not isinstance(v_log, list):
                        v_log = [v_log]
                    for i, line in enumerate(v_log):
                        log += [f'{"-" if i == 0 else " "} {line}']
            else:
                log = ', '.join(v_log for v_log in v_logs)
            return log
        if hasattr(obj, '__name__'):
            return '.'.join(([obj.__module__] if hasattr(obj, '__module__') else []) + [obj.__name__])
        return str(obj)
    return '\n'.join(_pretty_str(obj))


def reduce(src, *,
           reduce_class, reduce_config,
           tester_class, tester_config,
           atom='line',
           cache_class=None, cache_config=None):
    """
    Execute picire as if invoked from command line, however, control its
    behaviour not via command line arguments but function parameters.

    :param src: Contents of the test case to reduce.
    :param reduce_class: Reference to the reducer class.
    :param reduce_config: Dictionary containing information to initialize the
        reduce_class.
    :param tester_class: Reference to a runnable class that can decide about the
        interestingness of a test case.
    :param tester_config: Dictionary containing information to initialize the
        tester_class.
    :param atom: Input granularity to work with during reduce ('char', 'line',
        or 'both'; default: 'line').
    :param cache_class: Reference to the cache class to use.
    :param cache_config: Dictionary containing information to initialize the
        cache_class.
    :return: The contents of the minimal test case.
    :raises ReductionException: If reduction could not run until completion. The
        ``result`` attribute of the exception contains the contents of the
        smallest, potentially non-minimal, but failing test case found during
        reduction.
    """

    # Get the parameters in a dictionary so that they can be pretty-printed
    # (minus src, as that parameter can be arbitrarily large)
    args = locals().copy()
    del args['src']
    if logger.isEnabledFor(logging.INFO):
        logger.info('Reduce session starts\n%s', indent(pretty_str(args), '\t'))

    cache = cache_class(**cache_config) if cache_class else None

    for atom_cnt, atom_name in enumerate(['line', 'char'] if atom == 'both' else [atom]):
        # Split source to the chosen atoms.
        if atom_name == 'line':
            src = src.splitlines(True)
        logger.info('Initial test contains %d %ss', len(src), atom_name)

        test_builder = ConcatTestBuilder(src)
        if cache:
            cache.clear()
            cache.set_test_builder(test_builder)

        dd = reduce_class(tester_class(test_builder=test_builder, **tester_config),
                          cache=cache,
                          id_prefix=(f'a{atom_cnt}',),
                          **reduce_config)
        try:
            min_set = dd(list(range(len(src))))
            src = test_builder(min_set)

            logger.trace('The cached results are: %s', cache)
            logger.debug('A minimal config is: %r', min_set)
        except ReductionException as e:
            logger.trace('The cached results are: %s', cache)
            logger.debug('The reduced config is: %r', e.result)
            logger.warning('Reduction stopped prematurely, the output may not be minimal: %s', e, exc_info=None if isinstance(e, ReductionStopped) else e)

            e.result = test_builder(e.result)
            raise

    return src


def postprocess(args, out_src):
    if args.cleanup:
        rmtree(join(args.out, 'tests'))

    output = join(args.out, basename(args.input))
    with open(output, 'w', encoding=args.encoding, errors='ignore', newline='') as f:
        f.write(out_src)

    logger.info('Output saved to %s', output)


def execute():
    """
    The main entry point of picire.
    """
    parser = create_parser()
    # Implementation specific CLI options that are not needed to be part of the core parser.
    parser.add_argument('-a', '--atom', metavar='NAME', choices=['char', 'line', 'both'], default='line',
                        help='atom (i.e., granularity) of input (%(choices)s; default: %(default)s)')
    inators.arg.add_version_argument(parser, version=__version__)
    args = parser.parse_args()

    config_logging(args)
    try:
        process_args(args)
    except ValueError as e:
        parser.error(e)

    try:
        out_src = reduce(args.src,
                         reduce_class=args.reduce_class,
                         reduce_config=args.reduce_config,
                         tester_class=args.tester_class,
                         tester_config=args.tester_config,
                         atom=args.atom,
                         cache_class=args.cache_class,
                         cache_config=args.cache_config)
        postprocess(args, out_src)
    except ReductionException as e:
        postprocess(args, e.result)
        if not isinstance(e, ReductionStopped):
            sys.exit(1)
