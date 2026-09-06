# tuttireporting

Build an editable LaTeX report from existing statistics and figures. A separate
producer (for example, dibisoplot) collects data and creates plots; tuttireporting
assembles them into a report.

Three inputs have different roles:

| Input | What it describes |
| --- | --- |
| `manifest.toml` | Each run's statistics, configuration, and figure paths |
| `report.toml` | Reusable sections, subsections, page breaks, and data selectors |
| LaTeX template | Document class, styling, and a starter `main.tex` |

A figure's `output_name` in the manifest matches a selector in `report.toml`.
The builder resolves these names, generates headings, prose, tables and figures, and copies
the assets. Existing `main.tex` is preserved for your commentary; generated
content is updated on each build.

Write sentences with live values in `report.toml`, for example
`paragraphs = ["Le corpus comprend {{stats.publications}} publications."]`.
The builder inserts the generated macro and emphasizes its value in bold.
See [the TOML guide](sphinx-doc/settings.rst) for optional and required data.

## Try the BiSO example

With Python 3.10+, a virtual environment, and LuaLaTeX/latexmk installed:

```bash
pip install -e .
pip install -r examples/biso/requirements.txt
make example-biso
```

This uses dibisoplot to query HAL for two BiSO figures: publication types and
open access. It uses `UNIV-PARIS-SACLAY`, year 2024; both are configurable.
The PDF is `build/biso/report/main.pdf` and the editable archive is
`build/biso/report.zip`. See the [walkthrough](sphinx-doc/examples.rst) for the
separate commands, running without local LaTeX, and preserving fetched data.

For your own data:

```bash
tuttireporting build --manifest run/manifest.toml --report report.toml --output report
```

Add `--compile` or `--zip` as needed. Bundled BiSO and PubPart layouts can be
selected with `--catalog biso` / `--catalog pubpart`, or copied with
`tuttireporting catalog export biso --output my-biso`.

Choose presentation independently with `--template article`, `--template biso`,
or `--template pubpart`. A template registry maps those names to a local directory,
local ZIP, or HTTPS ZIP; BiSO/PubPart use the untouched DiBISO v0.10.1 release with
local adapters declared in the bundled registry. Pass another registry with
`--templates templates.toml`, and temporarily override one source with
`--template-source ./template-directory`. See [template bundles](sphinx-doc/templates.rst)
for the registry format and authoring guide.
Use a fresh output directory when switching templates to get its starter file.

## Understand and develop

Start with [how the project fits together](sphinx-doc/architecture.rst): input
roles, the generated directory, the execution path, and where to make changes.
Then read the [BiSO example](sphinx-doc/examples.rst), [TOML format](sphinx-doc/settings.rst),
and [Python API](sphinx-doc/reference/index.rst).

- `make test`: fast offline tests.
- `make test-biso`: live test of the documented producer, PDF compilation, and regeneration.
- `make test-reports`: generate BiSO and PubPart reports from the live BiSO sample data.
- `make test-reports-pdf`: generate and compile both reports.
- `make docs`: build documentation, including the example's actual source files.
- `make clean`: remove build outputs and caches, including the generated example.

The previous report-class API has been removed. The BiSO example covers the
HAL-backed subset; full report parity still needs TeX-table and bibliography
support. Catalog `producer.toml` files preserve original plotting settings as
references; the builder does not execute them.
