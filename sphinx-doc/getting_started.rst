Getting started
===============

Install this checkout with ``pip install -e .``. Prepare run data as described in
:doc:`settings`, then build a project::

    tuttireporting build --manifest run/manifest.toml --report report.toml --output report

Add ``--compile`` to run LuaLaTeX through latexmk. Add ``--zip`` to create an
archive beside the output directory. In Overleaf, select the LuaLaTeX compiler.
Without ``--output``, the destination is ``report/`` beside the manifest.

The previous report classes have been removed. The API now consumes report
structure and run data rather than collecting data itself.
