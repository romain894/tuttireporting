"""Exercise the catalog fixture across real worker processes without network calls."""
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize('producer_fails', [False, True])
def test_catalog_workers_share_one_producer_run(tmp_path, producer_fails):
    fixture_source = Path(__file__).resolve().parents[1] / 'live/test_catalogs.py'
    config = tmp_path / 'pytest.ini'
    config.write_text('[pytest]\n', encoding='utf-8')
    attempts = tmp_path / 'attempts.txt'
    test = tmp_path / 'test_workers.py'
    test.write_text(f'''
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('catalog_fixture', {str(fixture_source)!r})
catalog_fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog_fixture)
full_manifest = catalog_fixture.full_manifest

def produce(data):
    with Path({str(attempts)!r}).open('a') as stream:
        stream.write('producer call\\n')
    if {producer_fails!r}:
        raise RuntimeError('Producer fixture failed')
    data.mkdir()
    (data / 'manifest.toml').write_text('complete')

catalog_fixture._produce_full_manifest = produce

@pytest.mark.parametrize('catalog', ['biso', 'pubpart'])
def test_catalog(full_manifest, worker_id, catalog):
    assert full_manifest.read_text() == 'complete'
    Path({str(tmp_path)!r}, catalog + '.worker').write_text(worker_id)
''', encoding='utf-8')
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', '-c', str(config), str(test),
         '-n', '2', '--dist=load', '--maxschedchunk=1', '-q'],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == (1 if producer_fails else 0), result.stdout + result.stderr
    assert attempts.read_text().splitlines() == ['producer call']
    if producer_fails:
        assert 'Producer fixture failed' in result.stdout
    else:
        workers = {(tmp_path / f'{catalog}.worker').read_text()
                   for catalog in ('biso', 'pubpart')}
        assert workers == {'gw0', 'gw1'}
