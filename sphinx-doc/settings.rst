TOML format
===========

Run data
--------

The producer supplies ``manifest.toml`` and the referenced figure files::

    generated_at = "2026-09-06T12:00:00Z"

    [config]
    year = 2024

    [stats]
    publication_count = 120

    [[items]]
    output_name = "publications"
    path = "plots/publications.pdf"
    caption = "Publications by year"

``stats`` and ``config`` accept nested tables of scalar values. Select nested
keys with dotted names. Figure paths must stay inside the manifest directory;
supported formats are PDF, PNG, and JPEG. ``generated_at`` is supplied by the
producer, not updated by the builder.

Report definition
-----------------

A separate, reusable ``report.toml`` selects data without containing run values::

    [report]
    title = "Publication report"
    template = "article"

    [[sections]]
    title = "Publications"
    new_page = true
    stats = ["publication_count"]

    [[sections.sections]]
    title = "Annual distribution"
    plots = ["publications"]

``report`` accepts ``title``, ``author``, and ``template``. ``article`` is the
only bundled LaTeX template.

Sections are ordered arrays of tables, with up to three heading levels:
``sections``, ``sections.sections``, and ``sections.sections.sections``.
Each section accepts:

* ``title``: required heading.
* ``text``: optional plain-text introduction.
* ``stats``, ``config``, ``plots``: arrays of selectors, empty by default;
  ``["*"]`` selects all entries of that kind.
* ``new_page``: insert a page break before the heading, default ``false``.
* ``missing``: ``"omit"`` (default) skips absent keys; ``"error"`` rejects them.
* ``omit_if_empty``: default ``true``; sections with no selected data, text, or
  surviving children are omitted.
* ``sections``: child sections.

Statistics and configuration are rendered as two-column tables. Unknown fields
and invalid types are rejected. Text values are escaped for LaTeX.

Without ``--report`` or ``--catalog``, the builder uses inline ``report`` and
``sections`` from the manifest. If ``sections`` is absent, it generates sections
for all configuration, statistics, and figures. An explicit empty array disables
these sections. An external definition replaces the inline layout and metadata.

Generated project
-----------------

``main.tex`` is created once and never overwritten. Put commentary there.
``generated_variables.tex`` and ``generated_body.tex`` are regenerated.
Referenced figures are copied into ``plots/`` and template assets into ``tutti/``.
Unreferenced files from previous builds are retained.

Macros use the package prefix: ``\tuttiStatPublicationCount``,
``\tuttiCfgYear``, ``\tuttiPlotPublications``, ``\tuttiReportTitle``,
``\tuttiReportAuthor``, and ``\tuttiGeneratedAt``. Identifiers are converted to
ASCII letters, with digits spelled out; collisions are errors.

Custom templates
----------------

``--template-dir`` points to a directory containing ``main.tex`` and ``tutti/``.
The starter must load ``generated_variables.tex`` in its preamble and
``generated_body.tex`` where the report body belongs. Generated content requires
``graphicx``, ``booktabs``, and ``longtable``. Template source is trusted LaTeX.
Changing templates does not overwrite an existing ``main.tex``.
