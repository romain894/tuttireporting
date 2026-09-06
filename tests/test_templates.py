import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tuttireporting import build_project
from tuttireporting.template_bundle import list_templates, load_template


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
        self.registry = self.root / 'templates.toml'
        self.registry.write_text('''schema_version=1
[templates.company]
source="bundle"
main="starter.tex"
assets=["company", "LICENSE.txt"]
body="body.tex.j2"
version="2.0"
''')

    def archive(self):
        path = self.root / 'bundle.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            for source in self.bundle.rglob('*'):
                if source.is_file():
                    archive.write(source, Path('release') / source.relative_to(self.bundle))
        return path

    def test_registry_declares_external_template_and_directory_or_zip_source(self):
        self.assertEqual(list_templates(self.registry), ('company',))
        for source in (self.bundle, self.archive()):
            output = self.root / ('from-directory' if source.is_dir() else 'from-zip')
            build_project(output, self.manifest, 'company', template_registry=self.registry,
                          template_source=source)
            self.assertEqual((output / 'main.tex').read_text(), '% Custom main\n')
            self.assertEqual((output / 'generated_body.tex').read_text(), 'Statistics')
            self.assertTrue((output / 'company/report.cls').is_file())
            self.assertFalse((output / 'template.toml').exists())
            info = json.loads((output / '.tutti-template.json').read_text())
            self.assertEqual(info['version'], '2.0')
            self.assertEqual(info['source'], str(source))

    def test_download_is_cached_without_a_checksum(self):
        raw = self.archive().read_bytes()
        url = 'https://example.org/template-v2.zip'
        response = io.BytesIO(raw)
        response.geturl = lambda: url
        cache = self.root / 'cache'
        with patch('tuttireporting.template_bundle.urlopen', return_value=response) as download:
            with load_template('company', url, registry=self.registry, cache_dir=cache) as template:
                self.assertEqual(template.main.read_text(), '% Custom main\n')
            download.assert_called_once_with(url, timeout=30)
        with patch('tuttireporting.template_bundle.urlopen', side_effect=AssertionError('offline')):
            with load_template('company', url, registry=self.registry, cache_dir=cache):
                pass

    def test_adapter_stays_outside_an_untouched_external_release(self):
        release = self.root / 'release'
        (release / 'dibiso').mkdir(parents=True)
        (release / 'dibiso' / 'biso.cls').write_text('% original class')
        (release / 'LICENSE.txt').write_text('Upstream license')
        (self.root / 'adapters').mkdir()
        (self.root / 'adapters' / 'biso.tex').write_text(
            '\\documentclass{dibiso/biso}\n\\input{generated_body.tex}\n')
        self.registry.write_text('''schema_version=1
[templates.biso]
source="release"
adapter="adapters/biso.tex"
assets=["dibiso", "LICENSE.txt"]
''')
        output = self.root / 'report'
        build_project(output, self.manifest, 'biso', template_registry=self.registry)
        self.assertIn('{dibiso/biso}', (output / 'main.tex').read_text())
        self.assertTrue((output / 'dibiso/biso.cls').is_file())
        self.assertEqual((release / 'dibiso/biso.cls').read_text(), '% original class')

    def test_invalid_registry_and_unsafe_archives_fail(self):
        self.registry.write_text('schema_version=1\n[templates.company]\nsource="bundle"\nmain="starter.tex"\nadapter="x.tex"\n')
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            with load_template('company', registry=self.registry):
                pass
        self.registry.write_text('''schema_version=1
[templates.company]
source="bundle"
main="starter.tex"
assets=[]
''')
        archive = self.archive()
        with zipfile.ZipFile(archive, 'w') as bundle:
            bundle.writestr('../escape', 'bad')
        with self.assertRaisesRegex(ValueError, 'path'):
            with load_template('company', archive, registry=self.registry):
                pass
        with zipfile.ZipFile(archive, 'w') as bundle:
            link = zipfile.ZipInfo('link')
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            bundle.writestr(link, '/tmp')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            with load_template('company', archive, registry=self.registry):
                pass
