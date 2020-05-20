# Copyright (c) 2016-2020 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import codecs
import os
import shlex
import shutil
import sys

from subprocess import Popen

from .abstract_dd import AbstractDD


class SubprocessTest(object):

    def __init__(self, command_pattern, test_builder, test_pattern, encoding, cleanup):
        """
        Wrapper around the script provided by the user. It decides about the
        interestingness based on the return code of executed script.

        :param command_pattern: The command as the tester script should be ran.
            Except that the path of the test is substituted with %s.
        :param test_builder: Callable object that creates test case from a
            configuration.
        :param test_pattern: The patter of the test's path. It contains one %s
            part that will be replaced with the ID of the certain
            configurations.
        :param encoding: The encoding that will be used to save the tests.
        :param cleanup: Binary flag denoting whether the test directory should
            be removed after test execution or not.
        """
        self.command_pattern = command_pattern
        self.encoding = encoding
        self.test_builder = test_builder
        self.test_pattern = test_pattern
        self.cleanup = cleanup

    def __call__(self, config, config_id):
        """
        Saving and evaluating of the current configuration.

        :param config: The list of units (chars or lines) that have to be
            compiled into a single test.
        :param config_id: Unique ID of the current configuration. It's used to
            name the containing folder of the current test.
        :return: The evaluation of the current test. It's either FAIL or PASS.
        """

        test_path = self.test_pattern % '_'.join(str(i) for i in config_id)
        test_dir = os.path.dirname(test_path)

        if not os.path.isdir(test_dir):
            os.makedirs(test_dir)

        with codecs.open(test_path, 'w', encoding=self.encoding, errors='ignore') as f:
            f.write(self.test_builder(config))

        proc = Popen(shlex.split(self.command_pattern % test_path,
                                 posix=not sys.platform.startswith('win32')),
                     cwd=test_dir)
        proc.wait()

        if self.cleanup:
            shutil.rmtree(test_dir)

        # Determine outcome.
        return AbstractDD.FAIL if proc.returncode == 0 else AbstractDD.PASS


class ConcatTestBuilder(object):
    """
    Callable class that builds test case from a configuration.
    """

    def __init__(self, content):
        """
        Initialize a test builder with the atoms (e.g. chars or lines) of the
        original test case.

        :param content: Atoms of the original test case.
        """
        self._content = content

    def __call__(self, config):
        """
        Builds test case from the given config.

        :param config: Configuration to build a test case from.
        :return: Test case described by the config.
        """
        return ''.join(self._content[x] for x in config)
