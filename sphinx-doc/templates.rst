Choosing external templates
===========================

A report layout selects content; a template controls presentation. The report
names a template, while a template registry declares where that template comes
from and which existing files it needs. This keeps document definitions free of
URLs and keeps template-specific knowledge out of the Python resolver.

Registry
--------

``templates.toml`` is a collection of templates. The bundled registry includes
``article``, ``biso``, and ``pubpart``. List its names or choose another one::

    tuttireporting templates list
    tuttireporting templates list --templates my-templates.toml
    tuttireporting build --manifest run/manifest.toml --report report.toml \
      --templates my-templates.toml

The report chooses only the logical name::

    [report]
    title = "My report"
    template = "company"

The registry supplies the location and paths in the external release::

    schema_version = 1

    [templates.company]
    source = "https://example.org/company-template-1.0.zip"
    main = "main.tex"
    assets = ["company", "LICENSE.txt"]
    version = "1.0"

``source`` may be a directory, a ZIP, or an HTTPS ZIP. Relative paths resolve
beside the registry; an explicit ``--template-source`` path resolves from the
working directory. ``main`` and ``assets`` are paths inside that source.
Declared assets are copied recursively into the generated project. Only declared
assets are copied. ``main.tex``, generated files, and ``plots/`` cannot be
declared as assets.

The source needs no ``tuttireporting`` descriptor or other added file. Its main
file must already load ``generated_variables.tex`` and ``generated_body.tex`` if
it is to use the generated content::

    \input{generated_variables.tex}
    ...
    \input{generated_body.tex}

On first creation, the builder expands the literal ``\input{generated_body.tex}``
into editable sections directly in ``main.tex``. Keep that placeholder in the
template source. Generated variables remain imported so data macros can refresh
without overwriting reviewer edits.

Adapters for untouched releases
-------------------------------

When an upstream starter does not load generated content, keep upstream untouched
and declare a registry-local adapter instead of ``main``::

    [templates.biso]
    source = "https://example.org/dibiso-v0.10.1.zip"
    adapter = "adapters/biso.tex"
    assets = ["dibiso", "LICENSE.txt"]

``adapter`` resolves beside ``templates.toml``. It is copied to the output as
the initial ``main.tex`` and can load an existing class from the external source.
Exactly one of ``main`` or ``adapter`` is required. The bundled BiSO and PubPart
entries use this mechanism because their published release has no suitable
machine-readable starter.

The default body renderer
-------------------------

``generated_body.tex`` is rendered from the package's ``body.tex.j2``. The
``.j2`` suffix marks a Jinja2 source template that produces TeX. It uses
``\BLOCK{...}`` and ``\VAR{...}`` delimiters so that Jinja does not conflict with
LaTeX braces. A registry entry may set ``body = "body.tex.j2"`` to select a
source-relative renderer; it receives the resolved ``sections`` value.

Development and caching
-----------------------

Use a directory while editing an external template, then publish a ZIP. An
explicit source override is useful while testing without editing the registry::

    tuttireporting build --manifest run/manifest.toml --report report.toml \
      --templates templates.toml --template-source ../company-template

HTTPS sources are cached by URL in ``~/.cache/tuttireporting/templates``. Set
``--template-cache`` or ``TUTTIREPORTING_TEMPLATE_CACHE`` to choose another
cache. Use versioned URLs when publishing releases. The generated project's
``.tutti-template.json`` records the selected name, source, registry, and
optional registry version. Existing ``main.tex`` is always preserved; use a
fresh output directory to receive a different starter.
