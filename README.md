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
The builder resolves these names, generates headings/tables/figures, and copies
the assets. Existing `main.tex` is preserved for your commentary; generated
content is updated on each build.

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
or `--template pubpart`. BiSO/PubPart use their original classes from the pinned
DiBISO v0.10.1 release (downloaded once, then cached). Users can provide a template
bundle with `--template-source ./template-directory`, a ZIP path, or an HTTPS URL.
See [template bundles](sphinx-doc/templates.rst) for the format and authoring guide.
Use a fresh output directory when switching templates to get its starter file.

## Understand and develop

Start with [how the project fits together](sphinx-doc/architecture.rst): input
roles, the generated directory, the execution path, and where to make changes.
Then read the [BiSO example](sphinx-doc/examples.rst), [TOML format](sphinx-doc/settings.rst),
and [Python API](sphinx-doc/reference/index.rst).

- `make test`: fast offline tests.
- `make test-biso`: live test of the documented producer, PDF compilation, and regeneration.
- `make docs`: build documentation, including the example's actual source files.
- `make clean`: remove build outputs and caches, including the generated example.

The previous report-class API has been removed. The BiSO example covers the
HAL-backed subset; full report parity still needs TeX-table and bibliography
support. Catalog `producer.toml` files preserve original plotting settings as
references; the builder does not execute them.
