Development
=================

Install and test from the repository root::

    python -m venv .venv
    . .venv/bin/activate
    pip install -e '.[dev]'
    make test

All tests run through pytest. ``tests/unit`` contains fast offline checks,
``tests/pdf`` contains offline LaTeX compilation checks, and ``tests/live``
contains checks using external services. Shared fixtures live in ``tests/fixtures``.
Plain ``python -m pytest`` has the same selection as ``make test``.

Run ``make test-pdf`` to include PDF checks (requires ``latexmk``, ``lualatex``,
and ``biber``; missing tools are reported as skips). Run ``make test-live`` for
live checks, which also require those tools and the example dependencies.
Live failures are reported as failures, including unavailable services.

Pass pytest options with ``PYTEST_ARGS``, for example::

    make test PYTEST_ARGS='-k catalog'
    make test-live PYTEST_ARGS='-k full_catalog'
    make test-all

The last command runs every group and saves successfully compiled catalog PDFs
for manual review:

* ``build/test-reports/biso/main.pdf``
* ``build/test-reports/pubpart/main.pdf``

Override the destination with ``make test-all TEST_REPORTS_DIR=/tmp/reports``.
Each report is compiled in a fresh temporary project before its PDF is copied,
so existing ``main.tex`` files cannot hide template changes. Other test outputs
remain temporary; use pytest's ``--basetemp`` option to choose their location.
Direct pytest runs can opt in with ``--report-output-dir=build/test-reports``.
The current live catalog fixture supplies BiSO data; the pubpart PDF therefore
shows missing-figure notices until a PubPart/OpenAlex producer is supplied.

The GitHub Actions ``Tests`` workflow runs ``make test-all`` on pushes and pull
requests, and can also be started manually. It uses Python 3.12 on Ubuntu with
the example and LaTeX dependencies installed. Live service failures fail the job.

The old ``test-unit`` alias is now ``test``; ``test-biso``, ``test-live-biso``,
and the ``test-catalogs*`` / ``test-reports*`` targets are consolidated into
``test-live``. Use ``example`` instead of ``example-biso`` and ``docs`` instead
of ``doc``. Catalog tests now always check PDF compilation.

Build documentation with::

    pip install -r sphinx-doc/requirements.txt
    make docs

The package version is defined in ``tuttireporting/_version.py``.

Run ``make clean`` to remove build outputs and Python caches. The root Makefile
uses ``.venv/bin/python`` when available; override it with ``make PYTHON=python3 test``.

Testing the documented example
------------------------------------

The executable example lives in ``examples/biso/produce.py``. Sphinx includes
that file and ``report.toml`` with ``literalinclude``, so edits appear in the
walkthrough without copying code into documentation or a notebook.

Install ``examples/biso/requirements.txt`` and run ``make test-live`` to test
the live producer, compilation, ZIP export, and regeneration. These checks live
under ``tests/live`` and run separately from the offline suite. The same command
also generates full producer data once and compiles every catalog with its default
template, checking the BiSO bibliography. ``BISO_BIBLIOGRAPHY_LIMIT`` controls
the bibliography size (default 100). Run
``make example`` to keep the generated report under ``build/biso`` for
manual inspection. Both commands accept ``BISO_ENTITY`` and ``BISO_YEAR``.
