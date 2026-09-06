# BiSO example with dibisoplot

This runnable subset produces publication types and open-access figures from
HAL using `dibisoplot` 0.9. It does not query OpenAlex or scanR.

From the repository root, with your virtual environment activated:

```bash
pip install -e .
pip install -r examples/biso/requirements.txt
python examples/biso/produce.py --entity-id UNIV-PARIS-SACLAY --year 2024
tuttireporting build --manifest build/biso/data/manifest.toml \
  --report examples/biso/report.toml --output build/biso/report --compile --zip
```

Omit `--compile` if LuaLaTeX/latexmk are not installed. The data producer needs
internet access; building from its saved manifest and PDF figures does not.
Live HAL data may change, so retain the generated data directory to reproduce a
particular report. `make clean` removes everything under `build/`.

- `produce.py` calls dibisoplot, exports two PDFs, and writes `manifest.toml`.
- `report.toml` selects those figures and statistics and organizes them into sections.
- `requirements.txt` pins the plotting dependencies for this example only.

The resulting PDF is `build/biso/report/main.pdf`; the editable archive is
`build/biso/report.zip`. Add commentary inside `main.tex`, before
`\end{document}`, and rerun only the build command to preserve it.

The full catalog also accepts the same data: replace
`--report examples/biso/report.toml` with `--catalog biso`. Sections without
matching data disappear. The example layout additionally displays a numeric
publication count and uses explicit page breaks and required selectors.

Use `make example-biso` as a shortcut for the producer and build commands above,
or `make test-biso` to execute the same producer and test compilation and
regeneration in a temporary directory. The regular `make test` does not query HAL.

The Sphinx walkthrough includes `produce.py` and `report.toml` directly, so the
documented code is also the executable, tested example.
