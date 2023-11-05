# Copyright (c) 2016-2023 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import codecs
import os
import shutil

from subprocess import run

from .outcome import Outcome


class SubprocessTest:

    def __init__(self, *, test_builder, command_pattern, work_dir, filename, encoding='utf-8', cleanup=True):
        """
        Wrapper around the script provided by the user. It decides about the
        interestingness based on the return code of executed script.

        :param test_builder: Callable object that creates test case from a
            configuration.
        :param command_pattern: The tester command as a sequence of arguments.
            If an element of the sequence contains %s, it is substituted with
            the path to the test case.
        :param work_dir: The work directory where test cases can be saved.
        :param filename: The file name to use for the test case.
        :param encoding: The encoding that will be used to save the tests.
        :param cleanup: Binary flag denoting whether the test directory should
            be removed after test execution or not.
        """
        self.test_builder = test_builder
        self.command_pattern = command_pattern
        self.work_dir = work_dir
        self.filename = filename
        self.encoding = encoding
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

        test_dir = os.path.join(self.work_dir, '_'.join(str(i) for i in config_id))
        test_path = os.path.join(test_dir, self.filename)

        os.makedirs(test_dir, exist_ok=True)

        with codecs.open(test_path, 'w', encoding=self.encoding, errors='ignore') as f:
            f.write(self.test_builder(config))

        args = []
        for arg in self.command_pattern:
            try:
                arg = arg % test_path
            except TypeError:
                pass
            args.append(arg)
        returncode = run(args, cwd=test_dir, check=False).returncode

        if self.cleanup:
            shutil.rmtree(test_dir)

        # Determine outcome.
        return Outcome.FAIL if returncode == 0 else Outcome.PASS


class ConcatTestBuilder:
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
