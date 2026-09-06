import contextlib
import io
from pathlib import Path
import re
import tempfile
import unittest

from tuttireporting import build_project
from tuttireporting.catalog import export_report, list_reports, report_path
from tuttireporting.cli import main
from tuttireporting.manifest import read_toml


class CatalogTests(unittest.TestCase):
    def test_recipes_preserve_variants_filters_and_stat_names(self):
        biso = read_toml(report_path('biso').with_name('producer.toml'))['visualizations']
        self.assertEqual(len(biso), 12)
        self.assertEqual([p['name'] for p in biso['CollaborationMap']], ['world', 'europe'])
        self.assertEqual(biso['CollaborationMap'][0]['countries_to_ignore'], ['France'])
        self.assertEqual(biso['Journals'][0]['stats_to_save']['nb_works'], 'bsojournalsnbworks')
        pubpart = read_toml(report_path('pubpart').with_name('producer.toml'))['visualizations']
        self.assertEqual([p['metric'] for p in pubpart['WorksCollaborations']],
                         ['citation_normalized_percentile', 'cited_by_count'])
        biso['CollaborationMap'][0]['name'] = 'changed'
        self.assertEqual(read_toml(report_path('biso').with_name('producer.toml'))['visualizations']['CollaborationMap'][0]['name'], 'world')

    def test_layouts_cover_producer_figures(self):
        def selectors(sections):
            result = set()
            for section in sections:
                result.update(section.get('plots', []))
                result.update(selectors(section.get('sections', [])))
            return result
        for name in ('biso', 'pubpart'):
            expected = set()
            for plot, configs in read_toml(report_path(name).with_name('producer.toml'))['visualizations'].items():
                if plot == 'WorksBibtex':
                    continue  # Bibliography processing is not implemented yet.
                for config in configs:
                    stem = re.sub(r'(?<!^)(?=[A-Z])', '_', plot).lower()
                    expected.add(stem + ('_' + config['name'] if config.get('name') else ''))
            self.assertEqual(selectors(read_toml(report_path(name))['sections']), expected)

    def test_export_build_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                main(['catalog', 'list'])
            self.assertEqual(output.getvalue().splitlines(), ['biso', 'pubpart'])
            with contextlib.redirect_stdout(io.StringIO()):
                main(['catalog', 'export', 'biso', '--output', str(root / 'definition')])
            exported = root / 'definition/report.toml'
            exported.write_text(exported.read_text() + '\n# User customization\n')
            before = exported.read_bytes()
            with self.assertRaises(FileExistsError):
                export_report('biso', root / 'definition')
            self.assertEqual(exported.read_bytes(), before)
            self.assertTrue((root / 'definition/producer.toml').is_file())
            manifest = root / 'manifest.toml'
            manifest.write_text('[stats]\noaworksperiod="2020–2024"\n')
            for name in list_reports():
                build_project(root / name, manifest, catalog_name=name, template_name='article')
            body = (root / 'biso/generated_body.tex').read_text()
            self.assertIn('Accès ouvert', body)
            self.assertNotIn('Collaborations internationales', body)
            with self.assertRaisesRegex(ValueError, 'either'):
                build_project(root / 'bad', manifest, catalog_name='biso', report_path=exported)
            with self.assertRaisesRegex(ValueError, 'Unknown catalog'):
                report_path('../biso')



if __name__ == '__main__':
    unittest.main()
