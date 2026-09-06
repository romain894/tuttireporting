# Changelog

## 0.9.0

- Rename the package to `tuttireporting`.
- Replace the report-class API with declarative TOML inputs and `build_project`.
- Remove BiSO/PubPart Python classes and their collection dependencies.
- Preserve BiSO/PubPart report selections and plotting settings as TOML files.
- Generate LaTeX projects while preserving existing `main.tex`.
- Add optional LuaLaTeX compilation and ZIP export.

- Select native template bundles from directories, ZIPs, or HTTPS sources.
- Use the pinned original DiBISO v0.10.1 classes for BiSO/PubPart by default.
