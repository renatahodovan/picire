======
Picire
======
*Parallel Delta Debugging Framework*

.. image:: https://img.shields.io/pypi/v/picire?logo=python&logoColor=white
   :target: https://pypi.org/project/picire/
.. image:: https://img.shields.io/pypi/l/picire?logo=open-source-initiative&logoColor=white
   :target: https://pypi.org/project/picire/
.. image:: https://img.shields.io/github/workflow/status/renatahodovan/picire/main/master?logo=github&logoColor=white
   :target: https://github.com/renatahodovan/picire/actions
.. image:: https://img.shields.io/coveralls/github/renatahodovan/picire/master?logo=coveralls&logoColor=white
   :target: https://coveralls.io/github/renatahodovan/picire


*Picire* (pronounced as /pitsirE/) is a Python implementation of the
`Delta Debugging`_ algorithm supporting parallelization and further
configuration options. It can be used either as a command line tool
or as a library.

Just like the original algorithm, *Picire* automatically reduces "interesting"
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

* Python_ ~= 2.7 or >= 3.5
* pip_ and setuptools Python packages (the latter is automatically installed by
  pip).

.. _Python: https://www.python.org
.. _pip: https://pip.pypa.io


Install
=======

The quick way (to install the latest official release)::

    pip install picire

Or clone the project and run setuptools (to install the freshest development
revision)::

    python setup.py install


Usage
=====

*Picire* has two mandatory command line arguments: one that defines the input
test case to be reduced (``--input``) and another describing an executable
tester script or program (``--test``) that can decide about the interestingness
of an arbitrary input. This will be run in every iteration to check a test case.

Common settings
---------------

* ``--parallel``: Enables *Picire* to run in multiprocess mode. (Otherwise, the
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
  *Picire* performs subset-based reduce before complement-based reduce, which
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

* The ``<path/to/the/target/application>`` should either be an absolute path to
  the target application or the application should be on the search path (i.e.,
  ``$PATH``).
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
  return value *Picire* expects.

A common form of *Picire*'s usage::

    picire --input=<path/to/the/input> --test=<path/to/the/tester> \
           --parallel --subset-iterator=skip --complement-iterator=backward


Compatibility
=============

*Picire* was tested on:

* Linux (Ubuntu 14.04 / 16.04 / 18.04)
* Mac OS X (El Capitan 10.11 / Sierra 10.12 / High Sierra 10.13 / Mojave 10.14 / Catalina 10.15)
* Windows (Server 2012 R2 / Server version 1809 / Windows 10)


Acknowledgement and Citations
=============================

This software uses the delta debugging algorithm as described in (A. Zeller:
"Yesterday, my program worked", ESEC/FSE 1999) and (R. Hildebrandt, A. Zeller:
"Simplifying failure-inducing input", ISSTA 2000).

Further improvements are described in (R. Hodovan, A. Kiss: "Practical
Improvements to the Minimizing Delta Debugging Algorithm", ICSOFT-EA 2016)
and (R. Hodovan, A. Kiss, T. Gyimothy: "Tree Preprocessing and Test Outcome
Caching for Efficient Hierarchical Delta Debugging", AST 2017).


Copyright and Licensing
=======================

Licensed under the BSD 3-Clause License_.

.. _License: LICENSE.rst
