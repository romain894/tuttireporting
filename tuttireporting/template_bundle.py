"""Resolve LaTeX templates from bundled starters, directories, ZIPs, or HTTPS.

Native bundles declare entry points and copied assets in template.toml. The
published DiBISO v0.10.1 archive is supported separately, without editing its
classes or requiring the previous reporting Python API.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import logging
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from urllib.parse import urlparse
from urllib.request import urlopen
import zipfile

from .manifest import read_toml

log = logging.getLogger(__name__)
BUILTINS = ('article', 'biso', 'pubpart')
PACKAGED = Path(__file__).parent / 'templates'
DIBISO_URL = ('https://github.com/dibiso-upsaclay/dibiso-latex-templates/releases/'
              'download/v0.10.1/dibiso-latex-template-v0.10.1.zip')
DIBISO_SHA256 = '82706067f7aadb4175d43128322a4faf0794ca05166bdfd18e4249006eec849e'
RESERVED = {'main.tex', 'generated_variables.tex', 'generated_body.tex', 'plots', '.tutti-template.json'}
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024


@dataclass
class Template:
    root: Path
    main: Path
    body: Path
    assets: list[tuple[Path, str]]
    provenance: dict


def _relative(value: str) -> Path:
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError(f'Expected a relative template path: {value!r}')
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {'.', '..'} for part in value.split('/')) or ':' in value:
        raise ValueError(f'Unsafe template path: {value!r}')
    return Path(*path.parts)


def _file(root: Path, value: str) -> Path:
    path = root / _relative(value)
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
        raise ValueError(f'Template file missing or unsafe: {value}')
    return path


def _assets(root: Path, entries: list[str]) -> list[tuple[Path, str]]:
    if not isinstance(entries, list):
        raise ValueError('template assets must be an array of relative paths')
    result = {}
    for entry in entries:
        relative = _relative(entry)
        if relative.parts[0] in RESERVED:
            raise ValueError(f'Template asset uses a reserved output path: {entry}')
        source = root / relative
        if not source.exists():
            raise ValueError(f'Template asset does not exist: {entry}')
        for path in [source, *source.rglob('*')] if source.is_dir() else [source]:
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise ValueError(f'Template contains a symlink or escaping path: {path}')
            if path.is_file():
                result[path.relative_to(root).as_posix()] = path
    return [(path, relative) for relative, path in sorted(result.items())]


def _native(root: Path, name: str, provenance: dict) -> Template:
    definition = read_toml(root / 'template.toml')
    if set(definition) - {'schema_version', 'version', 'templates'}:
        raise ValueError('Unknown fields in template.toml')
    if type(definition.get('schema_version')) is not int or definition['schema_version'] != 1:
        raise ValueError('template.toml requires schema_version = 1')
    entries = definition.get('templates')
    if not isinstance(entries, dict) or name not in entries:
        raise ValueError(f'Template {name!r} is not declared in template.toml')
    entry = entries[name]
    if not isinstance(entry, dict) or set(entry) - {'main', 'assets', 'body'}:
        raise ValueError(f'Invalid definition for template {name!r}')
    main = _file(root, entry.get('main'))
    body = _file(root, entry['body']) if 'body' in entry else PACKAGED / 'body.tex.j2'
    version = definition.get('version')
    if version is not None and not isinstance(version, str):
        raise ValueError('Template version must be a string')
    provenance.update(format='native', version=version)
    return Template(root, main, body, _assets(root, entry.get('assets', [])), provenance)


def _dibiso(root: Path, name: str, provenance: dict) -> Template:
    if name not in {'biso', 'pubpart'} or not (root / 'dibiso' / f'{name}.cls').is_file():
        raise ValueError('Template source needs template.toml (or the DiBISO release for biso/pubpart)')
    # Preserve upstream paths, classes, and license notices. Only the starter is
    # supplied by this package to connect the class to declarative content.
    entries = ['dibiso'] + [p.name for p in root.iterdir()
                           if p.is_file() and (p.name.startswith('LICENSE') or p.name == 'README.md')]
    provenance.update(format='dibiso')
    return Template(root, PACKAGED / name / 'main.tex', PACKAGED / 'body.tex.j2',
                    _assets(root, entries), provenance)


def _extract(archive: Path, destination: Path) -> Path:
    try:
        with zipfile.ZipFile(archive) as bundle:
            infos = bundle.infolist()
            if len(infos) > 4096 or sum(i.file_size for i in infos) > 256 * 1024 * 1024:
                raise ValueError('Template ZIP exceeds extraction limits')
            seen = set()
            for info in infos:
                path = _relative(info.filename.rstrip('/'))
                if path.as_posix().casefold() in seen:
                    raise ValueError(f'Duplicate ZIP path: {path}')
                seen.add(path.as_posix().casefold())
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError(f'Template ZIP contains a symlink: {path}')
            bundle.extractall(destination)
    except zipfile.BadZipFile as exc:
        raise ValueError(f'Invalid template ZIP: {archive}') from exc
    # Release ZIPs may contain a single enclosing directory.
    root = destination
    while not (root / 'template.toml').is_file() and not (root / 'dibiso').is_dir():
        children = list(root.iterdir())
        if len(children) != 1 or not children[0].is_dir():
            break
        root = children[0]
    return root


def _hash(path: Path) -> str:
    with path.open('rb') as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _download(url: str, cache_dir: Path, expected: str | None) -> Path:
    if urlparse(url).scheme != 'https':
        raise ValueError('Remote template sources must use HTTPS')
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / (hashlib.sha256(url.encode()).hexdigest() + '.zip')
    if path.is_symlink():
        raise ValueError(f'Template cache entry is a symlink: {path}')
    if path.is_file():
        if expected and _hash(path) != expected:
            raise ValueError(f'Cached template checksum mismatch; remove {path} and retry')
        return path
    log.info('Downloading template bundle: %s', url)
    temporary = None
    try:
        with urlopen(url, timeout=30) as response, tempfile.NamedTemporaryFile(dir=cache_dir, delete=False) as stream:
            temporary = Path(stream.name)
            if urlparse(response.geturl()).scheme != 'https':
                raise ValueError('Template download redirected away from HTTPS')
            total = 0
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > MAX_ARCHIVE_BYTES:
                    raise ValueError('Template download exceeds 64 MiB')
                stream.write(block)
        if expected and _hash(temporary) != expected:
            raise ValueError('Downloaded template SHA-256 does not match the expected checksum')
        # Validate the archive before retaining it in the cache.
        with tempfile.TemporaryDirectory() as extracted:
            _extract(temporary, Path(extracted))
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


@contextmanager
def load_template(name: str, source=None, *, sha256=None, cache_dir=None):
    """Yield a validated template while extracted files remain available.

    With no source, article is bundled locally; biso/pubpart resolve to the
    pinned DiBISO release. Custom sources can be directories, ZIPs, or HTTPS URLs.
    """
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', name):
        raise ValueError(f'Invalid template name: {name!r}')
    if sha256 is not None and (not isinstance(sha256, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', sha256)):
        raise ValueError('template_sha256 must contain 64 hexadecimal characters')
    sha256 = sha256.lower() if sha256 else None
    if source is None:
        if name == 'article':
            source = PACKAGED / 'article'
        elif name in {'biso', 'pubpart'}:
            source, sha256 = DIBISO_URL, sha256 or DIBISO_SHA256
        else:
            raise ValueError(f'Unknown template {name!r}; provide --template-source')
    origin = str(source)
    provenance = {'name': name, 'source': origin}
    if urlparse(origin).scheme in {'http', 'https'}:
        cache = Path(cache_dir) if cache_dir else Path(os.environ.get(
            'TUTTIREPORTING_TEMPLATE_CACHE', str(Path.home() / '.cache' / 'tuttireporting' / 'templates')))
        path = _download(origin, cache, sha256)
    else:
        path = Path(source).resolve()
    if path.is_dir():
        if sha256:
            raise ValueError('A template checksum applies to ZIP files, not directories')
        provenance['source'] = str(path)
        root = path
        yield _native(root, name, provenance) if (root / 'template.toml').is_file() else _dibiso(root, name, provenance)
    else:
        if not path.is_file() or path.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ValueError(f'Template ZIP missing or larger than 64 MiB: {path}')
        actual = _hash(path)
        if sha256 and actual != sha256:
            raise ValueError('Template ZIP SHA-256 does not match the expected checksum')
        provenance['sha256'] = actual
        with tempfile.TemporaryDirectory(prefix='tutti-template-') as temporary:
            root = _extract(path, Path(temporary))
            yield _native(root, name, provenance) if (root / 'template.toml').is_file() else _dibiso(root, name, provenance)
