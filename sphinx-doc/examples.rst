A runnable BiSO example
=============================

This example uses dibisoplot 0.9 to query HAL and create two French-language
figures: publication types for one year, and open-access status over five years.
It then passes those files and statistics to tuttireporting. It covers a subset
of BiSO; it does not query OpenAlex or scanR.

The example is a normal Python file, included below directly from the repository.
The live integration test executes the same file. There is no separate notebook
implementation to keep synchronized, and building the documentation does not
execute queries.

Install and run
---------------------

From the repository root, with a virtual environment activated::

    pip install -e .
    pip install -r examples/biso/requirements.txt
    make example

This uses the HAL collection ``UNIV-PARIS-SACLAY`` and publication year 2024.
Override them with ``make example BISO_ENTITY=YOUR_COLLECTION BISO_YEAR=2023``.
Use a HAL collection identifier, not an OpenAlex identifier or a laboratory name.

The example requires network access to HAL and LuaLaTeX/latexmk for compilation.
Its plotting dependencies are separate from the core package:

.. literalinclude:: ../examples/biso/requirements.txt
   :language: text

The Plotly/Kaleido pins matter: dibisoplot 0.9 accesses
``plotly.io.kaleido.scope``, which is absent in Plotly 7. The example uses the
bundled French translations. It makes publication-type bars horizontal so their
labels fit, and removes transparent helper traces from the open-access chart
because Plotly 5 includes them in the stack. These are presentation adjustments
to dibisoplot figures; the fetched counts are unchanged. It needs no OpenAlex or scanR credentials.

The two stages
--------------------

``make example`` runs these commands::

    python examples/biso/produce.py --entity-id UNIV-PARIS-SACLAY --year 2024
    tuttireporting build --manifest build/biso/data/manifest.toml --report examples/biso/report.toml --output build/biso/report --compile --zip

The first command fetches data and produces::

    build/biso/data/
    ├── manifest.toml
    └── plots/
        ├── works_type.pdf
        └── open_access_works.pdf

The second command reads those saved inputs and creates the LaTeX project under
``build/biso/report/``. Its PDF is ``main.pdf`` and the archive is
``build/biso/report.zip``. Omit ``--compile`` to assemble the project without a
local LaTeX installation; select LuaLaTeX when compiling it in Overleaf.

HAL is a live source: counts can change between fetches, even for a fixed year.
To reproduce a particular report, retain its entire data directory, including
the manifest and PDFs, and rerun only the second command. Building from those
files does not need network access once the template bundle has been cached
(or when a local template source is provided). Copy results you want to keep elsewhere
before ``make clean``, which removes ``build/``.

The producer: plots and run values
----------------------------------------

The script instantiates ``WorksType`` and ``OpenAccessWorks``, calls
``fetch_data()``, checks that data was actually returned, and exports
``get_figure()`` as PDF. It does not import the report builder.

.. literalinclude:: ../examples/biso/produce.py
   :language: python
   :linenos:

Three names connect the producer to the layout:

.. list-table::
   :header-rows: 1
   :widths: 28 35 37

   * - Producer value
     - Manifest entry
     - Report selector
   * - Sum of ``WorksType.data`` counts
     - ``stats.publications``
     - ``paragraphs = ["... {{stats.publications}} ..."]``
   * - Returned ``oa_works_period``
     - ``stats.oaworksperiod``
     - ``paragraphs = ["... {{stats.oaworksperiod}} ..."]``
   * - Exported open-access figure
     - item ``output_name = "open_access_works"``
     - ``plots = ["open_access_works"]``

The publication count covers the document types returned for the selected year.
The open-access figure covers articles and communications over ``year - 4``
through ``year``; its population differs from the publication-type figure.
The period value comes from dibisoplot's returned statistics.

The layout: sections and selectors
----------------------------------------

The example's reusable layout contains no fetched values:

.. literalinclude:: ../examples/biso/report.toml
   :language: toml
   :linenos:

The parent section groups two subsections. ``new_page`` controls page breaks.
``missing = "error"`` marks missing data in this example, so a failed
producer leaves its section visible with an incomplete-section notice.

You can also build these inputs using ``--catalog biso`` instead of ``--report``.
The bundled layout omits unpopulated sections, such as collaborations and research
projects. The example layout adds a numeric publication count and explicit page
breaks. Export the catalog to customize it::

    tuttireporting catalog export biso --output my-biso

This copies ``report.toml`` and the reference plotting settings in
``producer.toml``. The example calls two dibisoplot classes explicitly; it does not
execute that larger plotting recipe. The example and the BiSO catalog select the original ``dibiso/biso`` class
from v0.10.1. Its first use downloads and caches the template archive. A local
ZIP can be supplied with ``--template-source``; see :doc:`templates`. To switch
from an earlier generated article project, use a fresh output directory, since
its existing ``main.tex`` is preserved. A catalog can declare a named manifest
file as its BibLaTeX bibliography; the full BiSO producer exports
``works_bibtex.bib`` as that file. It limits that bibliography to 100 entries
by default, because larger lists can make LaTeX compilation slow.

Editing and testing the report
------------------------------------

Open ``build/biso/report/main.tex`` and add commentary before
``\end{document}``. Rerun the build command: generated content updates, while
``main.tex`` is preserved. Avoid editing ``generated_body.tex`` or
``generated_variables.tex`` because they are overwritten.

Run the live integration test with::

    make test-live

It executes the same producer in a temporary directory, checks the two PDF plots
and manifest, builds and compiles the example, adds a review comment, changes a
statistic in its temporary test copy, and rebuilds. It checks preservation of
``main.tex``, updated variables, ZIP contents, and omission of absent catalog
sections. Each subprocess has a timeout. It needs the example dependencies,
network access, and LaTeX; service failures are reported as test failures.

``make test`` remains the fast offline suite. ``make docs`` includes the example
source as text; it does not install dibisoplot, query HAL, or compile a report.
See :doc:`architecture` for the rendering pipeline and where to change the code.
