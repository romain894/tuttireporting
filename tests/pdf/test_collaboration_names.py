"""Dense collaboration charts retain every label in the exported report."""
import os
from pathlib import Path
import runpy
import shutil
import subprocess
from unittest.mock import Mock, patch

import pytest

from tuttireporting import build_project
from tuttireporting.builder import compile_project
from tuttireporting.catalog import report_path
from tuttireporting.manifest import read_toml


def test_forty_international_institutions_are_labeled(tmp_path, monkeypatch):
    for command in ('latexmk', 'lualatex', 'pdftotext'):
        if shutil.which(command) is None:
            pytest.skip(f'{command} is unavailable')
    root = Path(__file__).resolve().parents[2]
    producer = runpy.run_path(str(root / 'examples/biso/produce.py'))
    produce = producer['produce']
    # Mock HAL responses, but exercise the real filtering, limiting, chart
    # construction, PDF export, report assembly, and LaTeX compilation.
    records = [dict(docid=str(i), label_s=f'Institution {i:02d}', country_s='de')
               for i in range(45)]
    records.append(dict(docid='99', label_s='French institution', country_s='fr'))
    facets = [value for record in records for value in (record['docid'], 100 + int(record['docid']))]
    responses = [Mock(json=Mock(return_value={'facet_counts': {'facet_fields': {'structId_i': facets}}})),
                 Mock(json=Mock(return_value={'response': {'docs': records}}))]
    recipe = read_toml(report_path('biso').with_name('producer.toml'))
    for name in recipe['visualizations']:
        if name != 'CollaborationNames':
            monkeypatch.setitem(produce.__globals__, name, Mock(side_effect=RuntimeError('Not selected')))
    with patch('dibisoplot.biso.biso.requests.get', side_effect=responses) as get:
        manifest = produce('TEST', 2024, tmp_path / 'data', full=True)
    assert '-country_s:fr' in get.call_args.args[0]
    figure = manifest.parent / 'plots/collaboration_names.pdf'
    assert figure.is_file()
    text = subprocess.run(['pdftotext', '-layout', str(figure), '-'],
                          check=True, capture_output=True, text=True).stdout
    for i in range(5, 45):
        assert f'Institution {i:02d}' in text
    assert 'Institution 04' not in text
    assert 'French institution' not in text

    output = build_project(tmp_path / 'report', manifest, catalog_name='biso', template_name='article')
    main = (output / 'main.tex').read_text()
    assert r'\includegraphics[width=1.0\linewidth]{plots/CollaborationNames.pdf}' in main
    with patch.dict(os.environ, {'TEXMFVAR': str(tmp_path / 'texmf-var')}):
        compile_project(output)
    pages = subprocess.run(['pdftotext', '-layout', str(output / 'main.pdf'), '-'],
                           check=True, capture_output=True, text=True).stdout.split('\f')
    # All forty labels must fit together on the same report page.
    chart_page = next(page for page in pages if 'Institution 44' in page)
    assert all(f'Institution {i:02d}' in chart_page for i in range(5, 45))
    assert 'Collaborations internationales par établissements' in ' '.join(chart_page.split())
    assert 'Float too large' not in (output / 'main.log').read_text()
