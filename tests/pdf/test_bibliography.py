"""End-to-end BibLaTeX test using the bundled article report template."""
import os
from pathlib import Path
import shutil
from unittest.mock import patch

import pytest

from tuttireporting import build_project
from tuttireporting.builder import compile_project


def test_biso_catalog_bibliography_is_copied_and_compiled(tmp_path):
    for command in ('latexmk', 'lualatex', 'biber'):
        if shutil.which(command) is None:
            pytest.skip(f'{command} is unavailable')
    manifest = tmp_path / 'manifest.toml'
    bibliography = tmp_path / 'references.bib'
    bibliography.write_text('''@article{example,
  author = {Doe, Jane},
  title = {A small bibliography fixture},
  year = {2024},
}
''', encoding='utf-8')
    manifest.write_text('''generated_at = "2026-09-08T12:00:00Z"
[[files]]
name = "references"
path = "references.bib"
destination = "references.bib"
''', encoding='utf-8')
    output = build_project(tmp_path / 'output', manifest, catalog_name='biso',
                           template_name='article')
    assert (output / 'references.bib').read_bytes() == bibliography.read_bytes()
    assert r'\addbibresource{\tuttiBibliographyFile}' in (output / 'main.tex').read_text(encoding='utf-8')
    texmfvar = tmp_path / 'texmf-var'
    texmfvar.mkdir()
    with patch.dict(os.environ, {'TEXMFVAR': str(texmfvar)}):
        compile_project(output)
    assert (output / 'main.pdf').read_bytes().startswith(b'%PDF-')
    assert r'\entry{example}' in (output / 'main.bbl').read_text(encoding='utf-8')
