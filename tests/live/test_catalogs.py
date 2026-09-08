"""Build every catalog from one full live producer run."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tuttireporting import build_project
from tuttireporting.builder import compile_project
from tuttireporting.catalog import list_reports

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope='module')
def full_manifest(tmp_path_factory):
    data = tmp_path_factory.mktemp('catalog-data')
    result = subprocess.run(
        [sys.executable, str(ROOT / 'examples/biso/produce.py'), '--full',
         '--entity-id', os.environ.get('BISO_ENTITY', 'UNIV-PARIS-SACLAY'),
         '--year', os.environ.get('BISO_YEAR', '2024'),
         '--bibliography-limit', os.environ.get('BISO_BIBLIOGRAPHY_LIMIT', '100'),
         '--output', str(data)],
        cwd=ROOT, capture_output=True, text=True, timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    bibliography = data / 'plots/works_bibtex.bib'
    assert bibliography.is_file() and bibliography.stat().st_size > 0, result.stdout + result.stderr
    return data / 'manifest.toml'


@pytest.mark.parametrize('catalog', list_reports())
def test_full_catalog_compiles(full_manifest, tmp_path, catalog):
    output = build_project(tmp_path / catalog, full_manifest, catalog_name=catalog)
    if catalog == 'biso':
        assert (output / 'references.bib').stat().st_size > 0
    compile_project(output)
    assert (output / 'main.pdf').read_bytes().startswith(b'%PDF-')
    if catalog == 'biso':
        assert r'\entry{' in (output / 'main.bbl').read_text(encoding='utf-8')
