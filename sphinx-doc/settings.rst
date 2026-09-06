TOML format
=================

Run data
--------------

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
-----------------------

A separate, reusable ``report.toml`` selects data without containing run values::

    [report]
    title = "Publication report"
    template = "article"

    [[sections]]
    title = "Publications"
    new_page = true
    paragraphs = ["The corpus contains {{stats.publication_count}} publications."]

    [[sections.sections]]
    title = "Annual distribution"
    plots = ["publications"]

``report`` accepts ``title``, ``author``, and ``template``. A template registry
maps the selected template name to its external source; see :doc:`templates`.

Sections are ordered arrays of tables, with up to three heading levels:
``sections``, ``sections.sections``, and ``sections.sections.sections``.
Each section accepts:

* ``title``: required heading.
* ``text``: optional plain-text introduction.
* ``paragraphs``: array of prose paragraphs with inline ``{{stats.key}}`` or
  ``{{config.key}}`` references; see below.
* ``stats``, ``config``, ``plots``: arrays of selectors, empty by default;
  ``["*"]`` selects all entries of that kind.
* ``new_page``: insert a page break before the heading, default ``false``.
* ``missing``: ``"omit"`` (default) skips absent keys; ``"error"`` rejects them.
* ``omit_if_empty``: default ``true``; sections with no selected data, text, or
  surviving children are omitted.
* ``sections``: child sections.

Explicit ``stats`` and ``config`` selectors produce two-column tables. Prefer
``paragraphs`` for readable narrative reports; referencing a value in prose does
not also select it for a table. Unknown fields and invalid types are rejected.
Text values are escaped for LaTeX.

Writing sentences with live values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Keep reusable wording in the report definition and actual values in the manifest::

    [[sections]]
    title = "Périmètre du rapport"
    paragraphs = [
      "Ce bilan présente les publications de la collection HAL {{config.entity_id}} pour l’année {{config.year}}.",
      "Le corpus comprend {{stats.publications}} publications.",
    ]
    missing = "error"

Each array entry becomes a paragraph. Values are emphasized in bold by the
default body renderer. References support nested keys such as
``{{config.grid.res}}``; whitespace around the reference is optional. These are
data references, not arbitrary Jinja expressions or raw LaTeX. Literal prose and
data are escaped, including percent signs, underscores, and ampersands.

The generated sentence calls the existing macro (for example,
``\textbf{\tuttiStatPublications{}}``). Rebuilding after changing the manifest
updates that macro's value. No numbers need to be copied into ``report.toml``.

With ``missing = "omit"`` (the default), a paragraph with any missing reference
is omitted in its entirety. Other paragraphs and figures remain. If nothing
survives, the section is omitted as usual. Use ``missing = "error"`` when every
referenced value is required. Invalid syntax always raises an error.

Reusable explanatory sentences belong here; researcher interpretation and review
comments still belong in the preserved ``main.tex``. The BiSO example and both
catalog layouts use prose; the automatic layout remains a generic table view.

Without ``--report`` or ``--catalog``, the builder uses inline ``report`` and
``sections`` from the manifest. If ``sections`` is absent, it generates sections
for all configuration, statistics, and figures. An explicit empty array disables
these sections. An external definition replaces the inline layout and metadata.

Generated project
-----------------------

``main.tex`` is created once and never overwritten. Put commentary there.
``generated_variables.tex`` and ``generated_body.tex`` are regenerated.
Referenced figures are copied into ``plots/``. Template assets retain the paths
declared by their registry (for example, ``tutti/``, ``dibiso/``, or ``company/``).
Unreferenced files from previous builds are retained.

Macros use the package prefix: ``\tuttiStatPublicationCount``,
``\tuttiCfgYear``, ``\tuttiPlotPublications``, ``\tuttiReportTitle``,
``\tuttiReportAuthor``, and ``\tuttiGeneratedAt``. Identifiers are converted to
ASCII letters, with digits spelled out; collisions are errors.

Custom templates
----------------------

Use ``--template`` to select a name from ``--templates templates.toml``. Use
``--template-source`` only to override that selected entry while developing a
local directory, ZIP, or HTTPS release. See :doc:`templates` for the registry
contract, adapters, custom body renderers, and caching. Changing templates does
not overwrite an existing ``main.tex``.
