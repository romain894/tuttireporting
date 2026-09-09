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

Supporting files
~~~~~~~~~~~~~~~~

Use ``files`` for a producer output that is not a figure, such as a BibLaTeX
bibliography. The source stays inside the manifest directory and the builder
copies it to the requested relative destination::

    [[files]]
    name = "references"
    path = "references.bib"
    destination = "references.bib"

Each file name creates a macro from ``\tuttiFile`` plus its CamelCase name:
the example creates ``\tuttiFileReferences``. To render it as a bibliography,
the report definition declares the file by name::

    [report]
    bibliography = "references"

When the named asset is supplied, this produces ``\tuttiBibliographyFile``.
To include the bibliography in the PDF, also set this boolean in the manifest::

    [config]
    include_bibliography = true

The default is false. The article and BiSO starters print every entry only when
both the named asset is supplied and this flag is true. Otherwise,
``generated_bibliography.tex`` contains a commented ``% \makebiblio`` command.
The asset is still copied, so you can uncomment the command before compiling
manually. A subsequent build regenerates this file from the configuration.
Existing ``main.tex`` files are preserved: use a fresh output directory to adopt
the updated starter, or copy its bibliography setup and generated-file input
into your existing main file.
Destinations cannot escape the generated project or replace its machine-managed
files. An absent named bibliography asset simply omits the bibliography.
An explicitly listed ``[[files]]`` source must still exist.

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
* ``missing``: ``"omit"`` (default) skips absent keys; ``"error"`` keeps the
  section and renders an incomplete-section notice.
* ``omit_if_empty``: default ``true``; sections with no selected data, text, or
  surviving children are omitted.
* ``sections``: child sections.

Explicit ``stats`` and ``config`` selectors produce two-column tables. Prefer
``paragraphs`` for readable narrative reports; referencing a value in prose does
not also select it for a table. Unknown fields and invalid types are rejected.
Text values are escaped for LaTeX.

Figure dimensions
~~~~~~~~~~~~~~~~~

An optional section-level ``plot_layout`` table controls its figures::

    [[sections]]
    title = "Collaborations internationales par établissements"
    plots = ["collaboration_names"]
    plot_layout = {width = 1.0}

``width`` is a fraction of the line width. Optional ``height`` caps the figure
at a fraction of the text height while preserving its aspect ratio.
``x_offset`` shifts the figure horizontally by a fraction of the line width.
Dimensions must be finite numbers; width and height must be positive.
``placement`` accepts LaTeX float positions (``htbp`` by default); BiSO uses
``!htbp`` so dense charts can stay with their section heading.
Without ``plot_layout``, figures retain the generic 0.95 line-width / 0.72
text-height limits. An explicit table defaults to full width with no height cap.

The BiSO catalog restores the original full-width figures, the world map at
1.2 line widths with a -0.1 offset, and project charts at 0.85 line widths.
These LaTeX dimensions scale the exported PDF; they cannot recover labels
omitted during plotting. The example producer uses dynamic height for horizontal
bar charts (25 pixels per bar, up to 40 institutions), at 800 pixels wide,
and explicitly displays every category label. France is excluded from the
international institution chart. The two overview plots keep their custom sizing.
Regenerate plots to update their labels. Build into a fresh output directory
or edit preserved ``main.tex`` to adopt changed LaTeX dimensions.

Reviewer comment areas
~~~~~~~~~~~~~~~~~~~~~~

Add an optional ``reviewer_comment`` table to a section in ``report.toml``::

    [[sections]]
    title = "Types de publications"
    plots = ["works_type"]
    reviewer_comment = {id = "works-type", style = "block", prompt = "Écrire votre commentaire ci-dessous :"}

``style = "comment"`` creates a simple LaTeX comment prompt.
``style = "block"`` (the default) adds a separator and BEGIN/END markers with
blank lines between them. These instructions are source comments and do not
appear in the PDF. Text the reviewer writes between them is ordinary LaTeX
and appears in the report.

The builder places the writing area directly in ``main.tex`` at the end of the
section, after its figures, explanatory notes, and closing paragraphs, before
child sections. Five blank source lines separate the prompt from its end marker
(or the following content for a simple prompt). Edit the report and add text in
this single file, including in Overleaf. Its contents are preserved byte-for-byte
on rebuild and included in ZIP exports. Prompts do not create empty PDF boxes.
Do not write review text into ``generated_body.tex``.
LaTeX figures remain floats, so their final page placement follows LaTeX rules.

``id`` is required and must be unique across all sections, using lowercase
letters, digits, hyphens, or underscores. Keep it stable when renaming or
reordering sections so the same commentary stays attached. ``prompt`` defaults
to ``Comment on:`` followed by the section title. Prompt/style changes apply to
new projects only; edit existing ``main.tex`` directly to update instructions.
The ``comments/`` directory is reserved and cannot be an asset destination.

Omit ``reviewer_comment`` to disable an area in new projects. Existing
``main.tex`` files remain unchanged. Normal empty-section omission still applies; use
``omit_if_empty = false`` for a section intended only for reviewer text, such as
recommendations. The BiSO catalog includes block prompts at the locations used
in the earlier report.

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
referenced value is required; the section is generated with a visible failure
notice instead of aborting the entire report. Invalid syntax and unsafe paths
still raise an error.

Reusable explanatory sentences belong here; researcher interpretation and review
comments belong in the preserved ``main.tex``. The BiSO example and both
catalog layouts use prose; the automatic layout remains a generic table view.

Without ``--report`` or ``--catalog``, the builder uses inline ``report`` and
``sections`` from the manifest. If ``sections`` is absent, it generates sections
for all configuration, statistics, and figures. An explicit empty array disables
these sections. An external definition replaces the inline layout and metadata.

Generated project
-----------------------

``main.tex`` is created once with the complete report body and never overwritten.
Edit section headings, prose, figures, and reviewer commentary directly there.
``generated_variables.tex`` and assets are refreshed on rebuild, so referenced
macro values and existing figures update. Structural changes (new/removed
sections, prompts, or incomplete-section notices) require a fresh output directory
or manual edits to ``main.tex``. Keep the old project to transfer reviewer edits.
``generated_body.tex`` is regenerated as a reference copy; new main files do not
import it. Bibliography activation remains in ``generated_bibliography.tex``.
Older projects that import ``generated_body.tex`` continue using their split
layout and preserved ``comments/*.tex`` files. Build into a fresh output directory
to adopt the single-file editing layout without overwriting existing work.
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

Report figure narrative
-----------------------

Sections may provide ``plot_captions``, a table mapping plot selectors to
caption text with the same ``{{config.key}}`` and ``{{stats.key}}`` references
as paragraphs. If caption data is absent, the manifest caption is retained.
``figure_notes`` adds optional small-print paragraphs after figures;
missing note data omits that note. ``after_plots`` adds explanatory paragraphs,
``bullets`` adds an itemized list, and ``closing_paragraphs`` follows the list.
These fields accept the same safe references as ``paragraphs``. HTTP(S) URLs
in prose are rendered as clickable, breakable links; raw LaTeX remains escaped.

The ``pubpart`` catalog implements the six-section Publications & Partenariats
report. Supply ``config.year`` (a year or period), ``config.entities_full_name``
and ``config.entities_acronym``. Its five figure selectors are declared in the
catalog's ``producer.toml``; optional figure notes use the corresponding stem
without underscores plus ``info`` under ``stats`` (for example,
``stats.topicscollaborationsinfo``). Missing figures produce visible incomplete
section notices. ``config.data_fetch_date`` and ``config.dibisoplot_version``
populate the final-page metadata when available.

Existing ``main.tex`` files remain human-owned. Use a fresh output directory
or update the existing starter to adopt the corrected pubpart cover, contents
and final page.
