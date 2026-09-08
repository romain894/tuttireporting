"""Regression coverage for the full Publications & Partenariats report."""
from pathlib import Path

from tuttireporting import build_project
from tuttireporting.catalog import report_path
from tuttireporting.manifest import read_toml


def pubpart_manifest(root):
    definition = read_toml(report_path('pubpart'))
    stems = [s['plots'][0] for s in definition['sections'][1:]]
    (root / 'plot.pdf').write_bytes(b'%PDF-1.4\n')
    manifest = root / 'manifest.toml'
    manifest.write_text('''generated_at = "2026-09-08"
[config]
year = "2021–2026"
entities_full_name = "Université A & Université B"
entities_acronym = "A & B"
[stats]
''' + ''.join(f'{stem.replace("_", "")}info = "Note {i}: 50% & détails"\n'
              for i, stem in enumerate(stems)) + ''.join(
        f'\n[[items]]\noutput_name = "{stem}"\npath = "plot.pdf"\ncaption = "Fallback"\n'
        for stem in stems), encoding='utf-8')
    return manifest


def test_pubpart_complete_report(tmp_path):
    manifest = pubpart_manifest(tmp_path)
    output = build_project(tmp_path / 'output', manifest, catalog_name='pubpart', template_name='article')
    body = (output / 'generated_body.tex').read_text()
    headings = [s['title'] for s in read_toml(report_path('pubpart'))['sections']]
    assert body.count('\\section{') == 6
    assert [body.index('\\section{' + h + '}') for h in headings] == sorted(
        body.index('\\section{' + h + '}') for h in headings)
    assert body.count('\\includegraphics') == 5
    assert body.count('\\label{fig_') == 5
    assert body.count('\\footnotesize') == 5
    assert body.index('\\includegraphics', body.index(headings[2])) < body.index('Le potentiel') < body.index('\\begin{itemize}')
    assert '\\tuttiCfgYear{}' in body and '2020-2025' not in body
    assert r'\url{https://docs.openalex.org/api-entities/works/work-object\#citation\_normalized\_percentile}' in body
    assert 'Fallback' not in body
    assert 'incomplete' not in body
    assert r'50\% \& détails' in (output / 'generated_variables.tex').read_text()


def test_pubpart_missing_figures_are_visible_and_notes_optional(tmp_path):
    manifest = tmp_path / 'manifest.toml'
    manifest.write_text('[config]\nyear="2026"\n')
    output = build_project(tmp_path / 'output', manifest, catalog_name='pubpart', template_name='article')
    body = (output / 'generated_body.tex').read_text()
    assert body.count('Missing plots key') == 5
    assert 'Un score de potentiel' in body
    assert 'Cette métrique' in body
    assert 'missing paragraph data' not in body


def test_pubpart_adapter_is_a_report():
    adapter = Path(__file__).resolve().parents[2] / 'tuttireporting/templates/adapters/pubpart.tex'
    main = adapter.read_text()
    assert r'\tableofcontents' in main
    assert r'\makelastpagereport' in main
    assert r'\reporteremail{}' in main
    assert 'biblatex' not in main and 'Liste des travaux' not in main
