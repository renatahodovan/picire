# Copyright (c) 2016-2017 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import logging
import multiprocessing
import os
import psutil
import signal

logger = logging.getLogger(__name__)


class Loop(object):
    """Parallel loop implementation based on multiprocessing module."""

    # TODO: could be None if we trusted that wait for infinity would not hang
    _timeout = 1

    def __init__(self, j=os.cpu_count(), max_utilization=100):
        """
        Initialize a parallel loop object.

        :param j: The maximum number of parallel jobs.
        :param max_utilization: The maximum CPU utilization. Above this no more new jobs
                                will be started.
        """
        self._j = j
        self._max_utilization = max_utilization
        # This gets initialized to 0, may be set to 1 anytime, but must not be reset to 0 ever;
        # thus, no locking is needed when accessing
        self._break = multiprocessing.sharedctypes.Value('i', 0, lock=False)
        self._lock = multiprocessing.Condition()
        self._slots = multiprocessing.sharedctypes.Array('i', j, lock=False)
        psutil.cpu_percent(None)

    # Beware! this is running in a new process now. state is shared with fork,
    # but only changes to shared objects will be visible in parent.
    def _body(self, i, target, args):
        """
        Executes the given function in its own process group.

        :param i: The index of the current configuration.
        :param target: The function to run in parallel.
        :param args: The arguments that the target should run with.
        """
        os.setpgrp()
        try:
            if not target(*args):
                self._break.value = 1
        except:
            logger.warning('', exc_info=True)
            self._break.value = 1

        self._slots[i] = 0

        with self._lock:
            self._lock.notify()

    def _abort(self):
        """Terminate all live jobs."""
        for i, pid in enumerate(self._slots):
            if pid != 0:
                try:
                    os.killpg(pid, signal.SIGTERM)
                except OSError:
                    # If the process with pid did not have time to become a process group leader,
                    # then pgid does not exist and os.killpg could not kill the process,
                    # so re-try kill the process only.
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except OSError:
                        pass
            self._slots[i] = 0

    def _cleanup_slots(self):
        for i, pid in enumerate(self._slots):
            if pid != 0:
                try:
                    os.kill(pid, 0)
                except OSError:
                    self._slots[i] = 0

    # Target is expected to return True if loop shall continue and False if it
    # should break.
    def do(self, target, args):
        """
        Execute the target function if there is empty slot for it and
        the CPU utilization is suitable.

        :param target: The function to run in parallel.
        :param args: The parameters to run the target function with.
        :return: False if an interesting configuration was found. Otherwise returns True.
        """
        if self._break.value:
            logger.debug('do() called on a broken loop')
            self._abort()
            return False

        i = None
        while True:
            if psutil.cpu_percent(None) <= self._max_utilization:
                self._cleanup_slots()
                i = next((x for x in range(self._j) if self._slots[x] == 0), None)
                if i is not None:
                    break
            with self._lock:
                self._lock.wait(self._timeout)

        if self._break.value:
            self._abort()
            return False

        proc = multiprocessing.Process(target=self._body, args=(i, target, args))
        proc.start()
        self._slots[i] = proc.pid

        return True

    def join(self):
        """Wait until all the parallel child processes have finished."""
        if self._break.value:
            self._abort()
            return

        while True:
            self._cleanup_slots()
            # Return if all the jobs are done, that's there isn't any non-zero value in self._slots.
            if not any(self._slots):
                return

            with self._lock:
                self._lock.wait(self._timeout)

            if self._break.value:
                self._abort()
