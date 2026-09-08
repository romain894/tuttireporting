Development
=================

Install and test from the repository root::

    python -m venv .venv
    . .venv/bin/activate
    pip install -e .
    make test

Tests use generic fixtures under ``tests/fixtures`` and do not fetch report data.

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
under ``tests/integration`` and run separately from the offline suite. Run
``make example`` to keep the generated report under ``build/biso`` for
manual inspection. Both commands accept ``BISO_ENTITY`` and ``BISO_YEAR``.
