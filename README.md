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
make example
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

If a selected plot or value is unavailable, the report is still assembled and
the affected section contains a visible incomplete-section notice. Fix the data
and run the same command again; `main.tex` remains preserved. Malformed TOML,
invalid references, and unsafe paths still stop the build.

## Understand and develop

Start with [how the project fits together](sphinx-doc/architecture.rst): input
roles, the generated directory, the execution path, and where to make changes.
Then read the [BiSO example](sphinx-doc/examples.rst), [TOML format](sphinx-doc/settings.rst),
and [Python API](sphinx-doc/reference/index.rst).

- `make test`: fast offline tests; install with `pip install -e '.[dev]'`.
- `make test-pdf`: offline tests plus LaTeX/BibLaTeX compilation.
- `make test-live`: live BiSO example and full catalog compilation, including bibliography.
- `make test-all`: the complete suite, including offline, PDF, and live tests.
- `make example`: generate the BiSO example under `build/biso`.
- `make docs`: build documentation, including the example's actual source files.
- `make clean`: remove build outputs and caches, including the generated example.

The previous report-class API has been removed. The BiSO example covers the
HAL-backed subset; full report parity still needs TeX-table support. Catalog
`producer.toml` files preserve original plotting settings as references; the
builder does not execute them.

The full producer writes at most 100 BibTeX entries by default, because larger
bibliographies can make LaTeX compilation impractical. Override the limit for a
catalog test with `make test-live BISO_BIBLIOGRAPHY_LIMIT=200`.

All checks use pytest, organized under `tests/unit`, `tests/pdf`, and `tests/live`,
with shared data in `tests/fixtures`. Plain `python -m pytest` runs the offline
unit suite; opt in with `--run-pdf` or `--run-live`. Pass filters through Make,
for example `make test PYTEST_ARGS='-k catalog'`. See the
[development guide](sphinx-doc/development.rst) for prerequisites and selection.

Bibliography inclusion is opt-in. Keep `bibliography = "references"` in
`[report]` and provide the named `[[files]]` asset as before, then set
`include_bibliography = true` under `[config]` in the manifest to print it.
If false, omitted, or the named asset is absent, the PDF omits the bibliography
and `generated_bibliography.tex` contains `% \makebiblio` for later activation.
Supplied assets are still copied. Rebuilding regenerates this command while
preserving `main.tex`; existing projects need the updated starter's bibliography
setup and `\input{generated_bibliography.tex}` (or a fresh output directory).
