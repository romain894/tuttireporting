"""Live integration check for the documented BiSO example; run with make test-live."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from tuttireporting.manifest import read_toml

ROOT = Path(__file__).resolve().parents[2]


class BisoExampleTest(unittest.TestCase):
    def test_live_producer_build_and_edit_preservation(self):
        def run(*args):
            result = subprocess.run([sys.executable, *map(str, args)], cwd=ROOT,
                                    capture_output=True, text=True, timeout=240)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        with tempfile.TemporaryDirectory(prefix='tutti-biso-test-') as temporary:
            root = Path(temporary)
            data, output = root / 'data', root / 'report'
            run(ROOT / 'examples/biso/produce.py', '--entity-id',
                os.environ.get('BISO_ENTITY', 'UNIV-PARIS-SACLAY'), '--year',
                os.environ.get('BISO_YEAR', '2024'), '--output', data)
            manifest_path = data / 'manifest.toml'
            manifest = read_toml(manifest_path)
            self.assertGreater(manifest['stats']['publications'], 0)
            self.assertEqual({item['output_name'] for item in manifest['items']},
                             {'works_type', 'open_access_works'})
            for item in manifest['items']:
                self.assertTrue((data / item['path']).read_bytes().startswith(b'%PDF-'))

            command = ('-m', 'tuttireporting', 'build', '--manifest', manifest_path,
                       '--report', ROOT / 'examples/biso/report.toml', '--output', output,
                       '--compile', '--zip')
            run(*command)
            self.assertTrue((output / 'main.pdf').read_bytes().startswith(b'%PDF-'))
            self.assertIn('{dibiso/biso}', (output / 'main.tex').read_text())
            self.assertTrue((output / 'dibiso/biso.cls').is_file())
            self.assertTrue((output / 'LICENSE.txt').is_file())
            body = (output / 'generated_body.tex').read_text()
            self.assertIn('Types de publications', body)
            self.assertIn('Accès ouvert', body)
            self.assertIn(r'\textbf{\tuttiStatPublications{}}', body)
            self.assertIn('Ce bilan présente les publications', body)
            self.assertNotIn('longtable', body)

            main = output / 'main.tex'
            main.write_text(main.read_text().replace(
                r'\end{document}', '% REVIEW EDIT: retained by regeneration\n' + r'\end{document}'))
            before = main.read_bytes(), main.stat().st_mtime_ns
            # Change only a temporary test copy; do not mislabel altered counts
            # as a real fetched dataset. This exercises regenerated statistics.
            import tomli_w
            manifest['stats']['publications'] += 1
            manifest_path.write_text(tomli_w.dumps(manifest), encoding='utf-8')
            run(*command)
            self.assertEqual(before, (main.read_bytes(), main.stat().st_mtime_ns))
            self.assertIn(str(manifest['stats']['publications']),
                          (output / 'generated_variables.tex').read_text())
            with zipfile.ZipFile(output.with_suffix('.zip')) as archive:
                self.assertEqual(archive.read('main.tex'), before[0])
                self.assertIn('plots/OpenAccessWorks.pdf', archive.namelist())

            # The full catalog requires bibliography data that the small
            # example does not produce. Full builds are covered in test_catalogs.
            result = subprocess.run(
                [sys.executable, '-m', 'tuttireporting', 'build', '--manifest',
                 str(manifest_path), '--catalog', 'biso', '--output', str(root / 'catalog')],
                cwd=ROOT, capture_output=True, text=True, timeout=240,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Report bibliography must name a manifest file: 'references'", result.stderr)


if __name__ == '__main__':
    unittest.main()
