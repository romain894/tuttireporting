How the project fits together
===================================

tuttireporting assembles a report from data that already exists. A plotting tool
such as dibisoplot produces figures and statistics; this package decides how to
place them in a LaTeX document.

The three inputs
----------------------

There are three distinct choices when building a report:

.. list-table::
   :header-rows: 1
   :widths: 20 45 35

   * - Input
     - Responsibility
     - When it changes
   * - ``manifest.toml``
     - Names the statistics, configuration values, and figure files available.
     - For each dataset or analysis run.
   * - ``report.toml``
     - Selects those names and organizes sections and subsections.
     - When the report's structure changes.
   * - LaTeX template
     - Supplies the document class, styling, and starter ``main.tex``.
     - When the document's presentation changes.

A catalog entry is a bundled ``report.toml``. ``--catalog biso`` selects the
BiSO layout, which declares ``template = "biso"``. It does not run an analysis.
The selected template uses the original DiBISO BiSO class; it can be overridden
independently of the layout with ``--template``.

``producer.toml`` is a separate reference containing the plotting settings from
the original BiSO/PubPart implementations. The report builder does not read it.
A producer may use those settings when preparing its data.

Following one figure through a build
------------------------------------------

Suppose the producer writes this item into its manifest::

    [[items]]
    output_name = "open_access_works"
    path = "plots/open_access_works.pdf"
    caption = "Publications en accès ouvert"

The BiSO layout selects it in a subsection::

    [[sections.sections]]
    title = "Accès ouvert"
    paragraphs = ["L’évolution de l’accès ouvert est présentée sur la période {{stats.oaworksperiod}}."]
    plots = ["open_access_works"]

``output_name`` is the link between these files. The figure's location can change
without changing the layout, as long as that name stays the same. Statistic
references work similarly: ``{{stats.oaworksperiod}}`` inserts a macro for the
key under ``[stats]`` into a sentence, with its value emphasized in bold.

The builder resolves the path relative to the manifest, checks that the file
exists, and copies it into the project as ``plots/OpenAccessWorks.pdf``. It writes
an ``includegraphics`` command into ``generated_body.tex`` and makes the path
available as ``\tuttiPlotOpenAccessWorks`` in ``generated_variables.tex``.

A selected key that is absent is skipped by default. An empty section disappears;
a parent remains if it has a populated child. This lets the same layout work
with different subsets of data. Use ``missing = "error"`` in a section if absent
data should be marked as incomplete. Missing plot files are always reported in
the affected section. Structural errors, malformed TOML, and unsafe paths still
fail the build before files are written.

Output and ownership
--------------------------

For the article template, the generated project looks like this::

    report/
    ├── main.tex
    ├── generated_variables.tex
    ├── generated_body.tex
    ├── tutti/
    │   └── report.cls
    └── plots/
        └── OpenAccessWorks.pdf

``main.tex`` belongs to the researcher. It loads the generated variables in its
preamble and the generated body inside the document. Add discussion and review
comments there: the builder creates this file only if it does not exist.

The generated body, variables, and referenced assets are updated on subsequent
builds. Edit ``report.toml`` to change generated sections, or change the producer's
data to update statistics and figures. Editing generated LaTeX directly is
temporary: the next build replaces it. Old unreferenced assets are retained.

The Python code, in execution order
-----------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 27 73

   * - Module
     - What to look for
   * - ``cli.py``
     - Parses command-line arguments and calls the builder; optionally compiles
       or archives the finished project.
   * - ``catalog/__init__.py``
     - Lists, locates, and exports the bundled TOML definitions.
   * - ``builder.py``
     - ``build_project`` orchestrates input loading, template rendering, asset
       copying, and preservation of ``main.tex``.
   * - ``template_bundle.py``
     - Resolves built-in names or custom directory/ZIP/HTTPS sources, checks the
       archive, and reads template entry points and assets.
   * - ``manifest.py``
     - ``load_report`` validates both TOML files and resolves selectors into a
       ``Report`` object ready for rendering.
   * - ``templating.py``
     - Configures Jinja's LaTeX delimiters, escapes text, and renders macros.
   * - ``templates/body.tex.j2``
     - Turns resolved sections into headings, prose, optional tables, and figures.
   * - ``templates/templates.toml``
     - Registry mapping template names to external sources, starters, adapters,
       and copied assets. It contains data only; the resolver has no knowledge of
       individual document types.

Inside ``manifest.py``, ``flatten`` converts nested data into dotted keys.
``select`` matches each section's selectors to available data. ``resolve`` walks
the nested sections, omits empty entries, and produces a flat ordered list with
explicit heading commands. ``Report`` holds that list, metadata, escaped macro
values, and source/destination asset pairs. It has no filesystem-writing logic.
Each resolved section's ``paragraphs`` is a list of paragraphs, each containing
parts with either ``text`` (plain text to escape) or ``macro`` (a validated macro
name). Custom body renderers can use these parts to style inline values.

Where to make a change
----------------------------

* To add or rearrange report content, edit a catalog layout or an exported
  ``report.toml``.
* To add a data source, write a producer that emits a manifest and supported
  figure files. It need not import tuttireporting.
* To change the rendering of every statistics table or figure, edit
  ``templates/body.tex.j2``.
* To change typography, supply a custom LaTeX template directory.
* To add a new TOML feature, update validation/resolution in ``manifest.py``, its
  rendering where needed, the schema documentation, and tests.

See :doc:`examples` for the BiSO walkthrough, :doc:`settings` for the complete
TOML fields, and :doc:`reference/index` for Python entry points.
