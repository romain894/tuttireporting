Choosing and providing templates
======================================

A report layout selects content; a LaTeX template controls presentation. Keep ZIP
files as the release format, and use an unpacked directory while editing a
template. Both forms use the same bundle structure.

Selecting a template
--------------------------

List the built-in names and override a report's selection::

    tuttireporting templates list
    tuttireporting build --manifest run/manifest.toml --catalog biso --template article

Or set the default in the report definition::

    [report]
    title = "My report"
    template = "biso"

``article`` is the minimal starter shipped with this Python package.
``biso`` and ``pubpart`` use their respective document classes from the
`DiBISO LaTeX templates v0.10.1 release <https://github.com/dibiso-upsaclay/dibiso-latex-templates/releases/tag/v0.10.1>`_.
The BiSO and PubPart catalog layouts select those classes by default.

The default DiBISO archive is fetched from a fixed release URL and checked
against its SHA-256. Its ``dibiso/`` assets and license files are copied into the
project unchanged. The reporting package supplies small starters that load
``generated_variables.tex`` and ``generated_body.tex`` and use the class's cover
page, fonts, colors, and section styling. They do not invoke the old hand-written
report body or its last-page macros, which depend on the previous report's labels
and variables. No old Python report classes are involved.

These classes require LuaLaTeX and more packages than the minimal starter,
including Open Sans, emoji, TikZ/PGFPlots, and the French Babel language files.
They retain their upstream institutional branding. Local TeX installations may
report upstream font-shape or package warnings even when compilation succeeds.

Directory, ZIP, or URL
----------------------------

Use ``--template-source`` to supply a bundle. The template name selects an entry
inside it::

    tuttireporting build --manifest run/manifest.toml --template company --template-source ./company-template
    tuttireporting build --manifest run/manifest.toml --template company --template-source ./company-template-v1.zip
    tuttireporting build --manifest run/manifest.toml --template company --template-source https://example.org/company-template-v1.zip

You can also use the existing DiBISO release ZIP directly::

    tuttireporting build --manifest run/manifest.toml --template biso --template-source ./dibiso-latex-template-v0.10.1.zip

For a reusable selection, put the source in the report TOML::

    [report]
    title = "My report"
    template = "company"
    template_source = "./company-template-v1.zip"

``template_source`` paths in TOML resolve relative to that TOML file.
CLI paths resolve relative to the working directory. ``--template`` overrides
only the name; ``--template-source`` overrides only the source. If replacing a
custom bundle with a built-in template, remove its source from the report or
supply the appropriate source explicitly. ``--template-dir`` is an alias of
``--template-source``.

A template bundle for a new release
-----------------------------------------

This is a complete minimal contract for a user template::

    company-template/
    ├── template.toml
    ├── main.tex
    ├── company/
    │   ├── report.cls
    │   └── logo.pdf
    └── LICENSE.txt

``template.toml`` declares the entry point and the assets to copy::

    schema_version = 1
    version = "1.0.0"

    [templates.company]
    main = "main.tex"
    assets = ["company", "LICENSE.txt"]

The name ``company`` is arbitrary. ``main`` is required. ``assets`` defaults to
an empty array; directories are copied recursively, preserving their relative
paths. Only declared assets are copied. Nothing requires a ``tutti/`` directory.
Bundle files must stay inside the source; symlinks and escaping ZIP paths are
rejected. Assets cannot replace ``main.tex``, generated files, ``plots/``, or the
builder's provenance file.

The main file must load the two generated files in the appropriate places::

    \documentclass{company/report}
    \input{generated_variables.tex}
    \title{\tuttiReportTitle}
    \author{\tuttiReportAuthor}
    \begin{document}
    \maketitle
    \input{generated_body.tex}
    % Researcher commentary belongs here.
    \end{document}

The class or main file must provide ``graphicx``, ``booktabs``, and ``longtable``
for the default body renderer. Templates are trusted LaTeX/Jinja source.

A bundle can contain several named starters sharing the same assets. For the
next release of the separate LaTeX-template repository, a suitable structure is::

    template.toml
    starters/biso.tex
    starters/pubpart.tex
    dibiso/...
    LICENSE.txt
    LICENSE-GPL-3.0-only.txt
    LICENSE-lppl-1-3c.txt

With this descriptor::

    schema_version = 1
    version = "NEXT_RELEASE_VERSION"

    [templates.biso]
    main = "starters/biso.tex"
    assets = ["dibiso", "LICENSE.txt", "LICENSE-GPL-3.0-only.txt", "LICENSE-lppl-1-3c.txt"]

    [templates.pubpart]
    main = "starters/pubpart.tex"
    assets = ["dibiso", "LICENSE.txt", "LICENSE-GPL-3.0-only.txt", "LICENSE-lppl-1-3c.txt"]

This is a proposed format for a future template release, not a published release.
The existing v0.10.1 ZIP is supported without this descriptor. If the template
repository later renames its class directory, its starters and asset declarations
can be updated together; no hard-coded directory name is needed in the builder.

Custom body rendering
---------------------------

To change how sections, tables, and figures are rendered, add
``body = "body.tex.j2"`` to the selected entry. This optional file uses the same
LaTeX-safe Jinja environment as the built-in renderer. Its context is
``sections``, the ordered resolved section list described in :doc:`architecture`.
Copy :download:`the default renderer <../tuttireporting/templates/body.tex.j2>`
as a starting point. Omitting ``body`` uses the built-in renderer.

Caching, verification, and regeneration
---------------------------------------------

HTTPS bundles are downloaded once into ``~/.cache/tuttireporting/templates``.
Override this with ``--template-cache`` or ``TUTTIREPORTING_TEMPLATE_CACHE``.
Versioned URLs are recommended: cached URLs are not automatically refreshed.
The DiBISO defaults include a pinned checksum. For custom ZIPs, optionally set
``template_sha256`` in TOML or pass ``--template-sha256`` with the archive's
64-character SHA-256 digest. A mismatch fails the build.

After the bundle has been cached, building from local report data works offline.
A local ZIP or directory also avoids downloading. Generated Overleaf projects
contain their template assets and do not need the cache to compile.
``.tutti-template.json`` records the selected template source, archive digest,
and native bundle version where supplied. Keep the source bundle as well as the
run data for reproducibility.

Existing ``main.tex`` is always preserved. Template selection controls which
starter is used only when creating a new main file. To try another template,
use a fresh output directory or edit your existing ``main.tex`` to load its
class. Old assets are retained when rebuilding an existing project.
