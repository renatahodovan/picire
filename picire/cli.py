# Copyright (c) 2016-2021 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import argparse
import codecs
import os
import time

from multiprocessing import cpu_count
from os.path import basename, exists, join, realpath
from shutil import rmtree

import chardet
import inators
import pkg_resources

from inators import log as logging

from . import config_iterators, config_splitters, outcome_cache
from .combined_iterator import CombinedIterator
from .combined_parallel_dd import CombinedParallelDD
from .dd import DD
from .parallel_dd import ParallelDD
from .shared_cache import shared_cache_decorator
from .subprocess_test import ConcatTestBuilder, SubprocessTest

logger = logging.getLogger('picire')
__version__ = pkg_resources.get_distribution(__package__).version


def create_parser():
    def int_or_inf(value):
        if value == 'inf':
            return float('inf')
        value = int(value)
        if value < 2:
            raise argparse.ArgumentTypeError('invalid value: {value!r} (must be at least 2)'.format(value=value))
        return value

    parser = argparse.ArgumentParser(description='Command line interface of the "picire" test case reducer')
    parser.add_argument('-i', '--input', metavar='FILE', required=True,
                        help='test case to be reduced')

    # Base reduce settings.
    parser.add_argument('--cache', metavar='NAME',
                        choices=[i for i in dir(outcome_cache) if not i.startswith('_') and i.islower()], default='config',
                        help='cache strategy (%(choices)s; default: %(default)s)')
    parser.add_argument('--split', metavar='NAME',
                        choices=[i for i in dir(config_splitters) if not i.startswith('_') and i.islower()], default='zeller',
                        help='split algorithm (%(choices)s; default: %(default)s)')
    parser.add_argument('--test', metavar='FILE', required=True,
                        help='test command that decides about interestingness of an input')
    parser.add_argument('--granularity', metavar='N', type=int_or_inf, default=2,
                        help='initial granularity and split factor (integer or \'inf\'; default: %(default)d)')
    parser.add_argument('--encoding', metavar='NAME',
                        help='test case encoding (default: autodetect)')

    # Extra settings for parallel reduce.
    parser.add_argument('-p', '--parallel', action='store_true', default=False,
                        help='run DD in parallel')
    parser.add_argument('-c', '--combine-loops', action='store_true', default=False,
                        help='combine subset and complement check loops for more parallelization (has effect in parallel mode only)')
    parser.add_argument('-j', '--jobs', metavar='N', type=int, default=cpu_count(),
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
    inators.arg.add_log_level_argument(parser)
    parser.add_argument('-o', '--out', metavar='DIR',
                        help='working directory (default: input.timestamp)')
    parser.add_argument('--disable-cleanup', dest='cleanup', default=True, action='store_false',
                        help='disable the removal of generated temporary files')
    return parser


def process_args(parser, args):
    args.input = realpath(args.input)
    if not exists(args.input):
        parser.error('Test case does not exist: %s' % args.input)

    with open(args.input, 'rb') as f:
        args.src = f.read()

    if args.encoding:
        try:
            codecs.lookup(args.encoding)
        except LookupError:
            parser.error('The given encoding (%s) is not known.' % args.encoding)
    else:
        args.encoding = chardet.detect(args.src)['encoding'] or 'latin-1'

    args.src = args.src.decode(args.encoding)

    args.out = realpath(args.out if args.out else '%s.%s' % (args.input, time.strftime('%Y%m%d_%H%M%S')))

    args.test = realpath(args.test)
    if not exists(args.test) or not os.access(args.test, os.X_OK):
        parser.error('Tester program does not exist or isn\'t executable: %s' % args.test)

    args.tester_class = SubprocessTest
    args.tester_config = {
        'command_pattern': [args.test, '%s'],
        'work_dir': join(args.out, 'tests'),
        'filename': basename(args.input),
        'encoding': args.encoding,
        'cleanup': args.cleanup,
    }

    args.cache = getattr(outcome_cache, args.cache)
    if args.parallel:
        args.cache = shared_cache_decorator(args.cache)

    split_class = getattr(config_splitters, args.split)
    subset_iterator = getattr(config_iterators, args.subset_iterator)
    complement_iterator = getattr(config_iterators, args.complement_iterator)

    # Choose the reducer class that will be used and its configuration.
    args.reduce_config = {'split': split_class(n=args.granularity)}
    if not args.parallel:
        args.reduce_class = DD
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


def log_args(title, args):
    def _log_args(args):
        if not args:
            return repr(args)
        if isinstance(args, dict):
            log = []
            for k, v in sorted(args.items()):
                k_log = _log_args(k)
                v_log = _log_args(v)
                if isinstance(v_log, list):
                    log += ['%s:' % k_log]
                    for line in v_log:
                        log += ['\t' + line]
                else:
                    log += ['%s: %s' % (k_log, v_log)]
            return log if len(log) > 1 else log[0]
        if isinstance(args, list):
            v_logs = [_log_args(v) for v in args]
            if any(isinstance(v_log, list) for v_log in v_logs):
                log = []
                for v_log in v_logs:
                    if not isinstance(v_log, list):
                        v_log = [v_log]
                    for i, line in enumerate(v_log):
                        log += ['%s %s' % ('-' if i == 0 else ' ', line)]
            else:
                log = ', '.join(v_log for v_log in v_logs)
            return log
        if hasattr(args, '__name__'):
            return '.'.join(([args.__module__] if hasattr(args, '__module__') else []) + [args.__name__])
        return str(args)
    logger.info('%s\n\t%s\n', title, '\n\t'.join(_log_args(args)))


def reduce(src, *,
           reduce_class, reduce_config,
           tester_class, tester_config,
           atom='line',
           cache_class=None):
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
    :return: The contents of the minimal test case.
    """

    # Get the parameters in a dictionary so that they can be pretty-printed
    # (minus src, as that parameter can be arbitrarily large)
    args = locals().copy()
    del args['src']
    log_args('Reduce session starts', args)

    cache = cache_class() if cache_class else None

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
                          id_prefix=('a%d' % atom_cnt,),
                          **reduce_config)
        min_set = dd(list(range(len(src))))
        src = test_builder(min_set)

        logger.trace('The cached results are: %s', cache)
        logger.debug('A minimal config is: %r', min_set)

    return src


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
    process_args(parser, args)

    logging.basicConfig(format='%(message)s')
    inators.arg.process_log_level_argument(args, logger)

    logger.info('Input loaded from %s', args.input)

    out_src = reduce(args.src,
                     reduce_class=args.reduce_class,
                     reduce_config=args.reduce_config,
                     tester_class=args.tester_class,
                     tester_config=args.tester_config,
                     atom=args.atom,
                     cache_class=args.cache)

    if args.cleanup:
        rmtree(join(args.out, 'tests'))

    out_file = join(args.out, basename(args.input))
    with codecs.open(out_file, 'w', encoding=args.encoding, errors='ignore') as f:
        f.write(out_src)
    logger.info('Output saved to %s', out_file)
