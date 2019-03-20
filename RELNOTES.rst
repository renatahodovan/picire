======================
*Picire* Release Notes
======================

19.3
====

Summary of changes:

* Made code Python 2 compatible.
* Fixed diagnostic messages.
* Improved parallelism internals.
* Improved the testing infrastructure (testing Python 2.7 and 3.7 on Travis CI;
  maintenance changes to various CI configurations).


18.10
=====

Summary of changes:

* Changed test configuration IDs from strings to tuples, changed how config IDs
  encode DD execution information, and extended API to enable prefixing of
  config IDs (resulting changes both in API and in working directory layout).
* Better separation of public and subclass APIs.
* Various internal refactorings.


18.1
====

Summary of changes:

* Added support for custom initial granularity.
* Improved logging (added support for filtering out really high volume logs by
  introducing a new log level).
* Improved the testing infrastructure (by using the Coveralls online service).


17.10
=====

Summary of changes:

* Windows became a first-class citizen: both sequential and parallel ddmin
  implementations are supported on the platform.


17.6
====

Summary of changes:

* Added CLI support for running character-based reduction after line-based
  reduction.
* Improved the testing infrastructure (support for Python 3.6 and code coverage
  measurement).
* Minor bug fixes and improvements.


17.1
====

Summary of changes:

* Changed the working directory of each test subprocess from $CWD to the
  corresponding test directory.
* Added support for content-based result caching (in addition to the
  configuration-based approach).
* Minor bug fixes and improvements.


16.7
====

Summary of changes:

* Added py.test-based testing, and support for tox and Travis CI.
* API refactoring to allow better code reuse, especially by the *Picireny*
  project.
* Minor bug fixes and improvements.


16.5
====

First public release of the *Picire* Parallel Delta Debugging Framework.

Summary of main features:

* One sequential ("light") and two process-based parallel ("parallel" and
  "combined parallel") ddmin implementations.
* "Subset checks first" and "complement checks first" modes.
* "Forward", "backward", "random" (and "skip") iteration strategies for both
  subset and complement checks.
* "Zeller" and "balanced" split modes.
* Python 3 API and CLI.
