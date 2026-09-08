import contextlib
import io
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tuttireporting import build_project
from tuttireporting.builder import compile_project
from tuttireporting.cli import main
from tuttireporting.manifest import load_report
from tuttireporting.templating import tex_escape, to_camel_case

FIXTURE = Path(__file__).parents[1] / 'fixtures' / 'report'


class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'run'
        shutil.copytree(FIXTURE, self.source)
        import runpy
        runpy.run_path(str(self.source / 'make_plot.py'))
        self.manifest = self.source / 'manifest.toml'
        self.layout = self.source / 'report.toml'
        self.output = self.root / 'project'

    def build(self, **kwargs):
        return build_project(self.output, self.manifest, report_path=self.layout, **kwargs)

    def test_roundtrip_preserves_main_bytes_and_mtime(self):
        self.build()
        main_file = self.output / 'main.tex'
        main_file.write_bytes(main_file.read_bytes() + b'\n% REVIEW EDIT: Test commentary added by researcher\n')
        before = main_file.read_bytes(), main_file.stat().st_mtime_ns
        self.manifest.write_text(self.manifest.read_text().replace('124.5', '250.75').replace('12:00:00Z', '13:00:00Z'))
        self.build()
        self.assertEqual(before, (main_file.read_bytes(), main_file.stat().st_mtime_ns))
        variables = (self.output / 'generated_variables.tex').read_text()
        self.assertIn('250.75', variables)
        self.assertIn('13:00:00Z', variables)
        self.assertIn(r'\tuttiCfgSamplingInterval', variables)
        self.assertIn(r'\tuttiPlotScoreTwo', variables)
        self.assertEqual((self.output / 'plots/ScoreTwo.pdf').read_bytes(),
                         (self.source / 'plots/score2.pdf').read_bytes())

    def test_sections_and_auto_layout(self):
        self.build()
        body = (self.output / 'generated_body.tex').read_text()
        self.assertIn('\\clearpage\n\n\\section{Results}', body)
        self.assertIn(r'\subsection{Measurements}', body)
        self.assertNotIn('Optional diagnostics', body)
        self.assertIn(r'Complete: 100\%', body)
        self.assertLess(body.index('Run configuration'), body.index('Measurements'))
        report = load_report(self.manifest)
        self.assertEqual([s['title'] for s in report.sections], ['Configuration', 'Statistics', 'Figures'])

    def test_missing_policy_and_keep_empty(self):
        self.layout.write_text('[[sections]]\ntitle="Absent"\nstats=["missing"]\nomit_if_empty=false\n')
        self.assertEqual(load_report(self.manifest, self.layout).sections[0]['title'], 'Absent')
        self.layout.write_text(self.layout.read_text() + 'missing="error"\n')
        self.build()
        body = (self.output / 'generated_body.tex').read_text()
        self.assertIn('Report section incomplete', body)
        self.assertIn('Missing stats key', body)

    def test_missing_plot_is_reported_and_later_recovers(self):
        self.manifest.write_text(self.manifest.read_text().replace('plots/score2.pdf', 'plots/missing.pdf'))
        self.build()
        body = (self.output / 'generated_body.tex').read_text()
        self.assertIn('Report section incomplete', body)
        self.assertIn('Plot file does not exist', body)
        (self.source / 'plots/missing.pdf').write_bytes(b'%PDF-1.4 recovered')
        self.build()
        self.assertNotIn('Report section incomplete', (self.output / 'generated_body.tex').read_text())

    def test_paragraphs_use_macros_and_escape_prose(self):
        self.layout.write_text('''[[sections]]
title="Narrative"
paragraphs=["Score: {{stats.score2}} & status: {{ stats.status }}.",
            "Sampling interval: {{config.sampling.interval}}."]
missing="error"
''')
        self.build()
        body = (self.output / 'generated_body.tex').read_text()
        self.assertIn(r'Score: \textbf{\tuttiStatScoreTwo{}} \& status: \textbf{\tuttiStatStatus{}}.', body)
        self.assertIn(r'\textbf{\tuttiCfgSamplingInterval{}}', body)
        self.assertNotIn('longtable', body)
        self.assertNotIn('{{', body)
        self.assertIn(r'Complete: 100\%', (self.output / 'generated_variables.tex').read_text())
        self.manifest.write_text(self.manifest.read_text().replace('124.5', '250.75'))
        self.build()
        self.assertEqual(body, (self.output / 'generated_body.tex').read_text())
        self.assertIn('250.75', (self.output / 'generated_variables.tex').read_text())

    def test_missing_paragraphs_are_omitted_whole(self):
        self.layout.write_text('''[[sections]]
title="Available"
paragraphs=["Keep {{stats.score2}}.", "Drop {{stats.score2}} and {{stats.absent}}."]
[[sections]]
title="Absent"
paragraphs=["Drop {{config.absent}}."]
''')
        self.build()
        body = (self.output / 'generated_body.tex').read_text()
        self.assertIn('Keep', body)
        self.assertNotIn('Drop', body)
        self.assertNotIn('Absent', body)
        self.layout.write_text(self.layout.read_text() + 'missing="error"\n')
        self.build()
        self.assertIn('missing paragraph data', (self.output / 'generated_body.tex').read_text())

    def test_invalid_paragraphs(self):
        for value in ['"not an array"', '[1]', '["{{stats.score2"]',
                      '["{{unknown.key}}"]', '["{{stats.}}"]',
                      '["{{stats.absent}} {{bad}}"]']:
            with self.subTest(value=value):
                self.layout.write_text('[[sections]]\ntitle="Invalid"\nparagraphs=' + value)
            with self.assertRaises(ValueError):
                self.build()

    def test_sanitization_and_collisions(self):
        self.assertEqual(to_camel_case('sample_count'), 'SampleCount')
        self.assertEqual(to_camel_case('score2'), 'ScoreTwo')
        self.assertEqual(to_camel_case('résolution'), 'Resolution')
        self.assertEqual(tex_escape('a_b%&#${}\\^~'),
                         r'a\_b\%\&\#\$\{\}\textbackslash{}\textasciicircum{}\textasciitilde{}')
        self.manifest.write_text('[stats]\na_b=1\na-b=2\n')
        with self.assertRaisesRegex(ValueError, 'collision'):
            self.build()

    def test_invalid_data(self):
        for text in ['[stats]\nx=[1,2]', '[stats]\nx=nan', 'items="bad"',
                     '[[sections]]\ntitle="x"\nnew_page="yes"',
                     '[[sections]]\ntitle="x"\nstat=["typo"]']:
            with self.subTest(text=text):
                self.manifest.write_text(text)
                with self.assertRaises(ValueError):
                    load_report(self.manifest)

    def test_plot_paths_and_duplicate_names(self):
        original = self.manifest.read_text()
        for path in ['../outside.pdf', '/tmp/external.pdf']:
            self.manifest.write_text(original.replace('plots/score2.pdf', path))
            with self.assertRaises(ValueError):
                self.build()
        self.manifest.write_text(original.replace('plots/score2.pdf', 'missing.pdf'))
        self.build()
        self.assertIn('Plot file does not exist', (self.output / 'generated_body.tex').read_text())
        self.manifest.write_text(original + '\n[[items]]\noutput_name="score2"\npath="plots/score2.pdf"\n')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.build()

    def test_manifest_files_are_copied_and_exposed_as_macros(self):
        (self.source / 'references.bib').write_text('@book{example, title={Example}}\n')
        self.manifest.write_text(self.manifest.read_text() + '''
[[files]]
name = "references"
path = "references.bib"
destination = "references.bib"
''')
        self.layout.write_text(self.layout.read_text().replace(
            'template = "article"', 'template = "article"\nbibliography = "references"'))
        self.build()
        self.assertEqual((self.output / 'references.bib').read_text(),
                         '@book{example, title={Example}}\n')
        self.assertIn(r'\newcommand{\tuttiFileReferences}{references.bib}',
                      (self.output / 'generated_variables.tex').read_text())
        self.assertIn(r'\newcommand{\tuttiBibliographyFile}{references.bib}',
                      (self.output / 'generated_variables.tex').read_text())
        self.manifest.write_text(self.manifest.read_text().replace('destination = "references.bib"',
                                                                     'destination = "../references.bib"'))
        with self.assertRaisesRegex(ValueError, 'destination'):
            self.build()
        self.manifest.write_text(self.manifest.read_text().replace('destination = "../references.bib"',
                                                                     'destination = "main.tex"'))
        with self.assertRaisesRegex(ValueError, 'destination'):
            self.build()

    def test_bibliography_requires_a_named_manifest_file(self):
        self.layout.write_text('[report]\nbibliography = "references"\n')
        with self.assertRaisesRegex(ValueError, 'bibliography'):
            self.build()

    def test_symlink_output_rejected(self):
        self.output.mkdir()
        (self.output / 'plots').symlink_to(self.source / 'plots', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.build()

    def test_custom_template(self):
        template = self.root / 'template'
        (template / 'tutti').mkdir(parents=True)
        (template / 'main.tex').write_text('% Custom starter')
        (template / 'tutti' / 'custom.cls').write_text('% Custom class')
        registry = self.root / 'templates.toml'
        registry.write_text('schema_version=1\n[templates.custom]\nsource="template"\nmain="main.tex"\nassets=["tutti"]\n')
        self.build(template_name='custom', template_registry=registry)
        self.assertEqual((self.output / 'main.tex').read_text(), '% Custom starter')
        self.assertTrue((self.output / 'tutti' / 'custom.cls').exists())

    def test_cli_zip_and_compile_command(self):
        with contextlib.redirect_stdout(io.StringIO()):
            main(['build', '--manifest', str(self.manifest), '--output', str(self.output), '--zip'])
        with zipfile.ZipFile(self.output.with_suffix('.zip')) as archive:
            self.assertIn('main.tex', archive.namelist())
            self.assertIn('plots/ScoreTwo.pdf', archive.namelist())
            self.assertFalse(any(n.endswith('.zip') for n in archive.namelist()))
        with patch('tuttireporting.builder.subprocess.run') as run:
            compile_project(self.output)
            run.assert_called_once_with(['latexmk', '-lualatex', '-interaction=nonstopmode', '-halt-on-error', 'main.tex'],
                                        cwd=self.output, check=True)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main(['build', '--manifest', str(self.root / 'absent')])
        self.assertEqual(error.exception.code, 1)



if __name__ == '__main__':
    unittest.main()
