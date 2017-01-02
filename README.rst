======
Picire
======
*Parallel Delta Debugging Framework*

.. image:: https://badge.fury.io/py/picire.svg
   :target: https://badge.fury.io/py/picire
.. image:: https://travis-ci.org/renatahodovan/picire.svg?branch=master
   :target: https://travis-ci.org/renatahodovan/picire

Picire (pronounced as /pitsirE/) is a Python 3 implementation of the
`Delta Debugging`_ algorithm supporting parallelization and further
configuration options. It can be used either as a command line tool
or as a library.

Just like the original algorithm, *picire* automatically reduces "interesting"
tests while keeping their "interesting" behaviour. A common use case is
minimizing failing tests so that they still reproduce the original failure.

The tool (and the algorithm) works iteratively. As a first step, it splits up
the input into *n* chunks either by lines or characters. Then, iteratively,
it inspects smaller test cases composed of these chunks whether they are still
interesting. The selection of chunks can happen two ways: either a small subset
of the chunks is kept (subset-based reduce), or that small subset is removed
and everything else is kept (complement-based reduce). If a new interesting
test case is found, it becomes the input of the next iteration. The iterations
stop if removing any further chunks would make the test uninteresting (e.g. the
test is **1-minimal**).

.. _`Delta Debugging`: https://www.st.cs.uni-saarland.de/dd/


Requirements
============

* Python_ >= 3.4
* pip_ and setuptools Python packages (the latter is automatically installed by
  pip).

.. _Python: https://www.python.org
.. _pip: https://pip.pypa.io


Install
=======

The quick way::

    pip install picire

Alternatively, by cloning the project and running setuptools::

    python setup.py install


Usage
=====

*picire* has two mandatory command line arguments: one that defines the input
test case to be reduced (``--input``) and another describing an executable
tester script or program (``--test``) that can decide about the interestingness
of an arbitrary input. This will be run in every iteration to check a test case.

Common settings
---------------

* ``--parallel``: Enables *picire* to run in multiprocess mode. (Otherwise, the
  original single-process variant will run.)

* ``-j <num>``: Defines the maximum number of parallel jobs.

* ``--combine-loops``: The base algorithm had a dependency between subset and
  complement-based reduce loops, but because of the sequential nature of its
  implementation, it had no effect on efficiency. However, in parallel mode,
  this separation becomes a potential sub-optimality. With this option, the
  two reduce loops run combined for additional performance. Further details
  about the algorithm variants are available in the cited papers.

* ``--complement-first``: For some input types, subset-based reduce is not as
  effective as the complement-based one (sometimes, aggressively removing too
  big parts of the input eliminates the interestingness as well). By default,
  *picire* performs subset-based reduce before complement-based reduce, which
  can result in many superfluous checks for such inputs. This flag forces to
  start with complement checks.

* ``--subset-iterator`` / ``--complement-iterator``: Guide the iteration
  strategies of the subset and complement-based reduce loops.

  * ``forward``: Start investigating subsets (or complements) from the beginning
    of the input.

  * ``backward``: Start investigating subsets (or complements) from the end of
    the input. The goal is to reduce the number of semantic violations
    (assuming that definitions - like variable declarations - appear before
    uses).

  * ``skip``: Completely avoids the subset or complement checks (mostly used
    with ``--subset-iterator``).

For the detailed options, see ``picire --help``.

Tester script
-------------

The tester script is expected to take one command line argument, the path of a
test case, and it has to exit with 0 if the test is interesting and with
non-zero otherwise. An example tester script that runs an arbitrary target
application and checks if it fails on an assertion might look like the one
below::

    #! /bin/bash
    timeout --foreground 10 <path/to/the/target/application> $1 2>&1 | grep -q "Assertion failed";

**Remarks:**

* ``$1`` is the single and mandatory command line argument containing the path
  of a test case.
* If the target application is not guaranteed to exit, then it's worth running
  it with ``timeout`` to limit the amount of time waiting for producing the
  expected behaviour.
* If the target is run with timeout then the ``--foreground`` flag can also be
  useful as it allows forwarding the ``KILL`` signals (used by the parallel
  implementation) through the timeout's process group. This enables us to
  stop all alive parallel processes when a new interesting configuration
  is found already.
* If the interestingness decision is based on the content of the output then
  using ``grep`` (perhaps with ``-q`` or ``--quiet``) might be a right choice,
  since it returns 0 if the pattern was found and 1 if not. Exactly the
  return value *picire* expects.

A common form of *picire*'s usage::

    picire --input=<path/to/the/input> --test=<path/to/the/tester> \
    --parallel --subset-iterator=skip --complement-iterator=backward


Compatibility
=============

*picire* was tested on:

* Linux (Ubuntu 14.04 / 15.10)
* Mac OS X (OS X El Capitan - 10.11).


Acknowledgement and Citations
=============================

This software uses the delta debugging algorithm as described in (A. Zeller:
"Yesterday, my program worked", ESEC/FSE 1999) and (R. Hildebrandt, A. Zeller:
"Simplifying failure-inducing input", ISSTA 2000).

Further improvements are described in (R. Hodovan, A. Kiss: "Practical
Improvements to the Minimizing Delta Debugging Algorithm", ICSOFT-EA 2016).


Copyright and Licensing
=======================

See LICENSE_.

.. _LICENSE: LICENSE.rst
