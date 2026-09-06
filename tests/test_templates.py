import hashlib
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tuttireporting import build_project
from tuttireporting.catalog import report_path
from tuttireporting.manifest import read_toml
from tuttireporting.template_bundle import DIBISO_SHA256, DIBISO_URL, load_template


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / 'manifest.toml'
        self.manifest.write_text('[stats]\nvalue=12\n')
        self.bundle = self.root / 'bundle'
        (self.bundle / 'company').mkdir(parents=True)
        (self.bundle / 'company' / 'report.cls').write_text('% custom class')
        (self.bundle / 'LICENSE.txt').write_text('Example license')
        (self.bundle / 'starter.tex').write_text('% Custom main\n')
        (self.bundle / 'body.tex.j2').write_text('\\VAR{sections[0].title|tex_escape}')
        (self.bundle / 'template.toml').write_text('''schema_version=1
version="2.0"
[templates.company]
main="starter.tex"
assets=["company", "LICENSE.txt"]
body="body.tex.j2"
''')

    def archive(self):
        path = self.root / 'bundle.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            for source in self.bundle.rglob('*'):
                if source.is_file():
                    archive.write(source, Path('release') / source.relative_to(self.bundle))
        return path

    def test_directory_and_zip_share_contract(self):
        for source in (self.bundle, self.archive()):
            output = self.root / ('from-directory' if source.is_dir() else 'from-zip')
            build_project(output, self.manifest, 'company', template_source=source)
            self.assertEqual((output / 'main.tex').read_text(), '% Custom main\n')
            self.assertEqual((output / 'generated_body.tex').read_text(), 'Statistics')
            self.assertEqual((output / 'LICENSE.txt').read_text(), 'Example license')
            self.assertTrue((output / 'company/report.cls').is_file())
            self.assertFalse((output / 'template.toml').exists())
            info = json.loads((output / '.tutti-template.json').read_text())
            self.assertEqual(info['version'], '2.0')
            if source.is_file():
                self.assertEqual(info['sha256'], hashlib.sha256(source.read_bytes()).hexdigest())
            main = output / 'main.tex'
            main.write_text('% review edit')
            before = main.read_bytes(), main.stat().st_mtime_ns
            build_project(output, self.manifest, 'company', template_source=source)
            self.assertEqual(before, (main.read_bytes(), main.stat().st_mtime_ns))

    def test_relative_source_in_report_and_cli_override(self):
        definition = self.root / 'report.toml'
        definition.write_text('[report]\ntemplate="company"\ntemplate_source="bundle"\n')
        output = self.root / 'report'
        build_project(output, self.manifest, report_path=definition)
        self.assertTrue((output / 'company/report.cls').is_file())
        other = self.root / 'other.toml'
        other.write_text('[report]\ntemplate="company"\ntemplate_source="missing.zip"\n')
        build_project(output, self.manifest, report_path=other, template_source=self.bundle)

    def test_download_checked_once_and_cached_for_offline_builds(self):
        raw = self.archive().read_bytes()
        checksum = hashlib.sha256(raw).hexdigest()
        url = 'https://example.org/template-v2.zip'
        response = io.BytesIO(raw)
        response.geturl = lambda: url
        cache = self.root / 'cache'
        with patch('tuttireporting.template_bundle.urlopen', return_value=response) as download:
            with load_template('company', url, sha256=checksum, cache_dir=cache) as template:
                self.assertEqual(template.main.read_text(), '% Custom main\n')
            download.assert_called_once_with(url, timeout=30)
        with patch('tuttireporting.template_bundle.urlopen', side_effect=AssertionError('offline')):
            with load_template('company', url, sha256=checksum, cache_dir=cache):
                pass
        next(cache.glob('*.zip')).write_bytes(b'corrupted')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            with load_template('company', url, sha256=checksum, cache_dir=cache):
                pass

    def test_bad_checksum_and_unsafe_zip_leave_output_untouched(self):
        output = self.root / 'report'
        archive = self.archive()
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            build_project(output, self.manifest, 'company', template_source=archive,
                          template_sha256='0' * 64)
        self.assertFalse(output.exists())
        for filename in ('../escape', '/absolute', 'folder/../../escape', 'folder\\escape'):
            with zipfile.ZipFile(archive, 'w') as bundle:
                bundle.writestr(filename, 'bad')
            with self.subTest(filename=filename), self.assertRaisesRegex(ValueError, 'path'):
                build_project(output, self.manifest, 'company', template_source=archive)
            self.assertFalse(output.exists())
        with zipfile.ZipFile(archive, 'w') as bundle:
            link = zipfile.ZipInfo('link')
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            bundle.writestr(link, '/tmp')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            build_project(output, self.manifest, 'company', template_source=archive)

    def test_invalid_descriptor_and_reserved_assets(self):
        descriptor = self.bundle / 'template.toml'
        for definition in (
            'schema_version=2\n[templates.company]\nmain="starter.tex"',
            'schema_version=1\n[templates.company]\nmain="../manifest.toml"',
            'schema_version=1\n[templates.company]\nmain="starter.tex"\nassets=["plots"]',
            'schema_version=1\n[templates.company]\nmain="starter.tex"\nasset=["company"]',
        ):
            descriptor.write_text(definition)
            with self.subTest(definition=definition), self.assertRaises(ValueError):
                with load_template('company', self.bundle):
                    pass

    def test_dibiso_release_bridge_and_default_selection(self):
        release = self.root / 'release'
        (release / 'dibiso').mkdir(parents=True)
        for name in ('biso', 'pubpart'):
            (release / 'dibiso' / f'{name}.cls').write_text(f'% original {name}')
        (release / 'LICENSE.txt').write_text('Upstream license')
        for name in ('biso', 'pubpart'):
            self.assertEqual(read_toml(report_path(name))['report']['template'], name)
            with load_template(name, release) as template:
                self.assertIn('{dibiso/' + name + '}', template.main.read_text())
                self.assertIn('generated_variables.tex', template.main.read_text())
                self.assertIn('generated_body.tex', template.main.read_text())
                self.assertIn('LICENSE.txt', [relative for _, relative in template.assets])
                self.assertEqual((release / 'dibiso' / f'{name}.cls').read_text(), f'% original {name}')
        with zipfile.ZipFile(self.root / 'release.zip', 'w') as archive:
            for path in release.rglob('*'):
                if path.is_file():
                    archive.write(path, path.relative_to(release))
        with patch('tuttireporting.template_bundle._download', return_value=self.root / 'release.zip') as download:
            # The real pinned digest is checked separately from the download;
            # this fixture verifies the default URL and checksum selection.
            with patch('tuttireporting.template_bundle._hash', return_value=DIBISO_SHA256):
                with load_template('biso', cache_dir=self.root / 'cache'):
                    pass
            download.assert_called_once_with(DIBISO_URL, self.root / 'cache', DIBISO_SHA256)


if __name__ == '__main__':
    unittest.main()
