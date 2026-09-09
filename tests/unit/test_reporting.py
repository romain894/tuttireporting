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
        main = (self.output / 'main.tex').read_text()
        self.assertIn(r'\section{Results}', main)
        self.assertIn(r'\subsection{Measurements}', main)
        self.assertIn(r'\includegraphics', main)
        self.assertNotIn(r'\input{generated_body.tex}', main)
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

    def test_missing_bibliography_is_optional(self):
        self.layout.write_text('[report]\nbibliography = "references"\n')
        self.build()
        self.assertNotIn('tuttiBibliographyFile', load_report(self.manifest, self.layout).variables)
        self.assertIn('% \\makebiblio', (self.output / 'generated_bibliography.tex').read_text())

    def test_bibliography_switch_updates_without_overwriting_main(self):
        self.layout.write_text('[report]\nbibliography = "references"\n')
        (self.source / 'references.bib').write_text('@book{x,title={Example}}')
        for supplied in (True, False):
            for flag in ('true', 'false', None):
                with self.subTest(supplied=supplied, flag=flag):
                    manifest = '[config]\n'
                    if flag is not None:
                        manifest += f'include_bibliography = {flag}\n'
                    if supplied:
                        manifest += ('[[files]]\nname="references"\n'
                                     'path="references.bib"\ndestination="references.bib"\n')
                    self.manifest.write_text(manifest)
                    before = (self.output / 'main.tex').read_bytes() if self.output.exists() else None
                    self.build()
                    command = (self.output / 'generated_bibliography.tex').read_text().splitlines()[-1]
                    self.assertEqual(command, ('' if supplied and flag == 'true' else '% ') + r'\makebiblio')
                    if before is not None:
                        self.assertEqual(before, (self.output / 'main.tex').read_bytes())
        self.manifest.write_text('[config]\ninclude_bibliography = "true"\n')
        with self.assertRaisesRegex(ValueError, 'must be a boolean'):
            self.build()

    def test_reviewer_comments_are_preserved_and_follow_section_content(self):
        self.layout.write_text('''[report]
[[sections]]
title = "Review"
text = "Before the reviewer text."
reviewer_comment = {id = "review", style = "block", prompt = "Écrire ici.\\nSecond line."}
[[sections]]
title = "Recommendations"
omit_if_empty = false
reviewer_comment = {id = "recommendations", style = "comment"}
''')
        self.build()
        comment = self.output / 'main.tex'
        starter = comment.read_text()
        self.assertIn('% BEGIN REVIEWER COMMENT', starter)
        self.assertIn('% Écrire ici.\n% Second line.', starter)
        self.assertIn('% END REVIEWER COMMENT', starter)
        self.assertEqual(starter.count('BEGIN REVIEWER'), 1)
        self.assertFalse((self.output / 'comments').exists())
        self.assertNotIn(r'\input{generated_body.tex}', starter)
        self.assertNotIn(r'\input{comments/', starter)
        self.assertIn('Second line.\n\n\n\n\n\n% END REVIEWER COMMENT', starter)
        body = (self.output / 'generated_body.tex').read_text()
        self.assertLess(body.index('Before the reviewer text.'), body.index('% BEGIN REVIEWER COMMENT'))
        comment.write_text(starter.replace('\n\n\n\n', '\nReviewer interpretation.\n'))
        before = comment.read_bytes(), comment.stat().st_mtime_ns
        self.layout.write_text(self.layout.read_text().replace('title = "Review"', 'title = "Renamed"'))
        self.build()
        self.assertEqual(before, (comment.read_bytes(), comment.stat().st_mtime_ns))
        from tuttireporting.builder import zip_project
        with zipfile.ZipFile(zip_project(self.output)) as archive:
            self.assertEqual(archive.read('main.tex'), before[0])

    def test_legacy_split_project_preserves_comments(self):
        self.layout.write_text('[[sections]]\ntitle="Review"\nomit_if_empty=false\n'
                               'reviewer_comment={id="review"}\n')
        self.output.mkdir()
        main = self.output / 'main.tex'
        main.write_text(r'\input{generated_body.tex}')
        comments = self.output / 'comments'
        comments.mkdir()
        review = comments / 'review.tex'
        review.write_text('Existing reviewer text.\n')
        self.build()
        self.assertEqual(main.read_text(), r'\input{generated_body.tex}')
        self.assertEqual(review.read_text(), 'Existing reviewer text.\n')
        self.assertIn(r'\input{comments/review.tex}',
                      (self.output / 'generated_body.tex').read_text())

    def test_reviewer_comment_validation_and_paths(self):
        for comment in ('{id="../escape"}', '{id="review", style="unknown"}',
                        '{id="review", prompt=1}', '{}', '"text"'):
            with self.subTest(comment=comment):
                self.layout.write_text('[report]\n[[sections]]\ntitle="Review"\n'
                                       f'reviewer_comment={comment}\n')
                with self.assertRaises(ValueError):
                    self.build()
        section = '[[sections]]\ntitle="Review"\nomit_if_empty=false\nreviewer_comment={id="review"}\n'
        self.layout.write_text('[report]\n' + section * 2)
        with self.assertRaisesRegex(ValueError, 'Duplicate reviewer_comment'):
            self.build()
        self.layout.write_text('[report]\n' + section)
        self.output.mkdir()
        (self.output / 'comments').symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
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
