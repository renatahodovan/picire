======================
*Picire* Release Notes
======================

21.7
====

Summary of changes:

* Changed the API of algorithm classes and made them callable.
* Renamed LightDD algorithm class to DD.
* Changed the API of SubprocessTest to accept a sequence for command_pattern
  instead of a string.
* Added latin-1 as the default for encoding if it cannot be auto-detected.
* Made use of the *inators* package to unify CLI argument handling and logging.
* Moved to pyproject.toml & setup.cfg-based packaging.
* Improved logging.
* Various internal refactorings.
* Improved the testing infrastructure (testing Python 3.9, fixed Coveralls
  upload).
* Improved documentation.


20.12
=====

Summary of changes:

* Generalized ddmin algorithm to use split factor whenever configuration (test
  case) needs to be split or re-split.
* Changed the API of AbstractDD.ddmin by removing the split ratio argument (n).
* Changed config splitters from functions to classes.
* Extended API with OutcomeCache.set_test_builder.
* Changed the behavior of --cleanup CLI option to remove temporary files right
  after each test case execution (not only after the end of the reduction
  session).
* Improved log output.
* Bumped minimum Python requirement to 3.5.
* Adapted versioning to use setuptools_scm (included distance from latest
  release into non-released version strings).
* Added classification metadata to project.
* Improved documentation.
* Improved the testing infrastructure (linting, faster test suite, testing
  Python 3.8, testing macOS, migrated testing from Travis CI to GitHub Actions).
* Various internal refactorings and performance improvements.
* Minor bug fixes.


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
