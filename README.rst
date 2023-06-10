======
Picire
======
*Parallel Delta Debugging Framework*

.. image:: https://img.shields.io/pypi/v/picire?logo=python&logoColor=white
   :target: https://pypi.org/project/picire/
.. image:: https://img.shields.io/pypi/l/picire?logo=open-source-initiative&logoColor=white
   :target: https://pypi.org/project/picire/
.. image:: https://img.shields.io/github/actions/workflow/status/renatahodovan/picire/main.yml?branch=master&logo=github&logoColor=white
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

* Python_ >= 3.7

.. _Python: https://www.python.org


Install
=======

To use *Picire* in another project, it can be added to ``setup.cfg`` as an
install requirement (if using setuptools_ with declarative config):

.. code-block:: ini

    [options]
    install_requires =
        picire

To install *Picire* manually, e.g., into a virtual environment, use pip_::

    pip install picire

The above approaches install the latest release of *Picire* from PyPI_.
Alternatively, for the development version, clone the project and perform a
local install::

    pip install .

.. _setuptools: https://github.com/pypa/setuptools
.. _pip: https://pip.pypa.io
.. _PyPI: https://pypi.org/


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

* Linux (Ubuntu 14.04 / 16.04 / 18.04 / 20.04)
* OS X / macOS (10.11 / 10.12 / 10.13 / 10.14 / 10.15 / 11)
* Windows (Server 2012 R2 / Server version 1809 / Windows 10)


Acknowledgement and Citations
=============================

This software uses the delta debugging algorithm as described in:

* Andreas Zeller. Yesterday, My Program Worked. Today, It Does Not. Why?
  In Proceedings of the 7th European Software Engineering Conference Held
  Jointly with the 7th ACM SIGSOFT Symposium on the Foundations of Software
  Engineering (ESEC/FSE '99), volume 1687 of Lecture Notes in Computer Science
  (LNCS), pages 253-267, Toulouse, France, September 1999. Springer.
  https://doi.org/10.1007/3-540-48166-4_16
* Ralf Hildebrandt and Andreas Zeller. Simplifying Failure-Inducing Input.
  In Proceedings of the 2000 ACM SIGSOFT International Symposium on Software
  Testing and Analysis (ISSTA '00), pages 135-145, Portland, Oregon, USA, August
  2000. ACM.
  https://doi.org/10.1145/347324.348938

Further improvements are described in:

* Renata Hodovan and Akos Kiss. Practical Improvements to the Minimizing Delta
  Debugging Algorithm.
  In Proceedings of the 11th International Joint Conference on Software
  Technologies (ICSOFT 2016) - Volume 1: ICSOFT-EA, pages 241-248, Lisbon,
  Portugal, July 2016. SciTePress.
  https://doi.org/10.5220/0005988602410248
* Renata Hodovan, Akos Kiss, and Tibor Gyimothy. Tree Preprocessing and Test
  Outcome Caching for Efficient Hierarchical Delta Debugging.
  In Proceedings of the 12th IEEE/ACM International Workshop on Automation of
  Software Testing (AST 2017), pages 23-29, Buenos Aires, Argentina, May 2017.
  IEEE.
  https://doi.org/10.1109/AST.2017.4
* Akos Kiss. Generalizing the Split Factor of the Minimizing Delta Debugging
  Algorithm.
  IEEE Access, 8:219837-219846, December 2020. IEEE.
  https://doi.org/10.1109/ACCESS.2020.3043027
* Daniel Vince. Iterating the Minimizing Delta Debugging Algorithm.
  In Proceedings of the 13th International Workshop on Automating Test Case
  Design, Selection and Evaluation (A-TEST'22), pages 57-60, Singapore, November
  2022. ACM.
  https://doi.org/10.1145/3548659.3561314
* Daniel Vince and Akos Kiss. Cache Optimizations for Test Case Reduction.
  In Proceedings of the 22nd IEEE International Conference on Software Quality,
  Reliability, and Security (QRS 2022), pages 442-453, Guangzhou, China,
  December 2022. IEEE.
  https://doi.org/10.1109/QRS57517.2022.00052


Copyright and Licensing
=======================

Licensed under the BSD 3-Clause License_.

.. _License: LICENSE.rst
