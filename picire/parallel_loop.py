# Copyright (c) 2016-2019 Renata Hodovan, Akos Kiss.
#
# Licensed under the BSD 3-Clause License
# <LICENSE.rst or https://opensource.org/licenses/BSD-3-Clause>.
# This file may not be copied, modified, or distributed except
# according to those terms.

import logging
import multiprocessing
import os
import signal
import sys

import psutil

logger = logging.getLogger(__name__)
is_windows = sys.platform.startswith('win32')


# Beware! this is running in a new process now. state is shared with fork,
# but only changes to shared objects will be visible in parent.
def loop_body(shared_break, shared_slots, shared_lock, i, target, args):
    """
    Executes the given function in its own process group (on Windows: in its own
    process).

    :param shared_break: Loop-wide shared integer. Should be set to 1 if  the
        whole loop should be terminated.
    :param shared_slots: Loop-wide shared array of slots to keep track of status
        of loop bodies. The slot corresponding to a loop body should be set to 0
        once it has finished.
    :param shared_lock: Loop-wide shared lock. Should be notified when a loop
        body has finished.
    :param i: The index of the current slot.
    :param target: The function to run in parallel.
    :param args: The arguments that the target should run with.
    """
    if not is_windows:
        os.setpgrp()

    try:
        if not target(*args):
            shared_break.value = 1
    except Exception as e:
        logger.warning('', exc_info=e)
        shared_break.value = 1

    shared_slots[i] = 0

    with shared_lock:
        shared_lock.notify()


class Loop(object):
    """
    Parallel loop implementation based on multiprocessing module.
    """

    # TODO: could be None if we trusted that wait for infinity would not hang
    _timeout = 1

    def __init__(self, j=multiprocessing.cpu_count(), max_utilization=100):
        """
        Initialize a parallel loop object.

        :param j: The maximum number of parallel jobs.
        :param max_utilization: The maximum CPU utilization. Above this no more
            new jobs will be started.
        """
        self._j = j
        self._max_utilization = max_utilization
        # This gets initialized to 0, may be set to 1 anytime, but must not be reset to 0 ever;
        # thus, no locking is needed when accessing
        self._break = multiprocessing.sharedctypes.Value('i', 0, lock=False)
        self._lock = multiprocessing.Condition()
        self._slots = multiprocessing.sharedctypes.Array('i', j, lock=False)
        self._procs = [None] * j
        psutil.cpu_percent(None)

    def _abort(self):
        """
        Terminate all live jobs.
        """
        for i, (slot, proc) in enumerate(zip(self._slots, self._procs)):
            if slot:
                if not is_windows:
                    try:
                        os.killpg(proc.pid, signal.SIGTERM)
                    except OSError:
                        # If the process with pid did not have time to become a process group leader,
                        # then pgid does not exist and os.killpg could not kill the process,
                        # so re-try kill the process only.
                        try:
                            os.kill(proc.pid, signal.SIGTERM)
                        except OSError:
                            pass
                else:
                    root_proc = psutil.Process(proc.pid)
                    children = root_proc.children(recursive=True) + [root_proc]
                    for child_proc in children:
                        try:
                            # Would be easier to use proc.terminate() here but psutils
                            # (up to version 5.4.0) on Windows terminates processes with
                            # the 0 signal/code, making the outcome of the terminated
                            # process indistinguishable from a successful execution.
                            os.kill(child_proc.pid, signal.SIGTERM)
                        except OSError:
                            pass
                    psutil.wait_procs(children, timeout=1)
            self._slots[i], self._procs[i] = 0, None

    def _cleanup_slots(self):
        for i, (slot, proc) in enumerate(zip(self._slots, self._procs)):
            if slot:
                if not proc.is_alive() or not psutil.pid_exists(proc.pid):
                    self._slots[i], self._procs[i] = 0, None
            else:
                self._procs[i] = None

    # Target is expected to return True if loop shall continue and False if it
    # should break.
    def do(self, target, args):
        """
        Execute the target function if there is empty slot for it and the CPU
        utilization is suitable.

        :param target: The function to run in parallel.
        :param args: The parameters to run the target function with.
        :return: False if an interesting configuration was found. Otherwise
            returns True.
        """
        if self._break.value:
            logger.debug('do() called on a broken loop')
            self._abort()
            return False

        i = None
        while True:
            if psutil.cpu_percent(None) <= self._max_utilization:
                self._cleanup_slots()
                i = next((x for x, slot in enumerate(self._slots) if not slot), None)
                if i is not None:
                    break
            with self._lock:
                self._lock.wait(self._timeout)

        if self._break.value:
            self._abort()
            return False

        proc = multiprocessing.Process(target=loop_body, args=(self._break, self._slots, self._lock, i, target, args))
        proc.start()
        self._slots[i], self._procs[i] = 1, proc

        return True

    def join(self):
        """
        Wait until all the parallel child processes have finished.
        """
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
