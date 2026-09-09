"""Build every catalog from one full live producer run."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from filelock import FileLock

from tuttireporting import build_project
from tuttireporting.builder import compile_project
from tuttireporting.catalog import list_reports

ROOT = Path(__file__).resolve().parents[2]


def _produce_full_manifest(data):
    data.mkdir(parents=True, exist_ok=True)
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
    import tomli_w
    from tuttireporting.manifest import read_toml
    manifest = data / 'manifest.toml'
    content = read_toml(manifest)
    content.setdefault('config', {})['include_bibliography'] = True
    manifest.write_text(tomli_w.dumps(content), encoding='utf-8')
    return manifest


@pytest.fixture(scope='module')
def full_manifest(tmp_path_factory, worker_id):
    # xdist gives each worker its own base directory beneath the shared run.
    # Only producer setup is locked; report builds and compilation run in parallel.
    base = tmp_path_factory.getbasetemp()
    shared = base if worker_id == 'master' else base.parent
    data = shared / 'catalog-data'
    ready = shared / 'catalog-data.ready'
    failed = shared / 'catalog-data.failed'
    with FileLock(str(shared / 'catalog-data.lock'), timeout=660):
        if failed.exists():
            pytest.fail(failed.read_text(encoding='utf-8'))
        if not ready.exists():
            try:
                _produce_full_manifest(data)
            except Exception as error:
                failed.write_text(str(error), encoding='utf-8')
                raise
            ready.write_text('ready\n', encoding='utf-8')
    return data / 'manifest.toml'


@pytest.mark.parametrize('catalog', list_reports())
def test_full_catalog_compiles(full_manifest, tmp_path, catalog, pytestconfig):
    output = build_project(tmp_path / catalog, full_manifest, catalog_name=catalog)
    if catalog == 'biso':
        assert (output / 'references.bib').stat().st_size > 0
    compile_project(output)
    assert (output / 'main.pdf').read_bytes().startswith(b'%PDF-')
    if catalog == 'biso':
        assert r'\entry{' in (output / 'main.bbl').read_text(encoding='utf-8')

    # Compile in a fresh temporary project so preserved main.tex files cannot
    # mask template changes. Keep the complete project for manual inspection.
    report_output = pytestconfig.getoption('--report-output-dir')
    if report_output is not None:
        destination = report_output / catalog
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(output, destination, dirs_exist_ok=True)
        assert (destination / 'main.tex').is_file()
        assert (destination / 'generated_body.tex').is_file()
        assert any(destination.glob('plots/*'))
        reporter = pytestconfig.pluginmanager.get_plugin('terminalreporter')
        if reporter is not None:
            reporter.write_line(f'{catalog} report: {destination.resolve()}')
