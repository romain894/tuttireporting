"""Resolve templates declared by a registry, without template-specific code."""
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
PACKAGED = Path(__file__).parent / 'templates'
DEFAULT_REGISTRY = PACKAGED / 'templates.toml'
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


def _assets(root: Path, entries) -> list[tuple[Path, str]]:
    if not isinstance(entries, list) or any(not isinstance(entry, str) for entry in entries):
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


def _registry(path: Path) -> dict:
    definition = read_toml(path)
    if set(definition) - {'schema_version', 'templates'} or definition.get('schema_version') != 1:
        raise ValueError('templates.toml requires schema_version = 1')
    entries = definition.get('templates')
    if not isinstance(entries, dict):
        raise ValueError('templates.toml requires a [templates] table')
    return entries


def list_templates(registry=None) -> tuple[str, ...]:
    path = Path(registry or DEFAULT_REGISTRY).resolve()
    return tuple(sorted(_registry(path)))


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
    root = destination
    while len(list(root.iterdir())) == 1 and next(root.iterdir()).is_dir():
        root = next(root.iterdir())
    return root


def _download(url: str, cache_dir: Path) -> Path:
    if urlparse(url).scheme != 'https':
        raise ValueError('Remote template sources must use HTTPS')
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / (hashlib.sha256(url.encode()).hexdigest() + '.zip')
    if path.is_symlink():
        raise ValueError(f'Template cache entry is a symlink: {path}')
    if path.is_file():
        return path
    log.info('Downloading template: %s', url)
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
        with tempfile.TemporaryDirectory() as extracted:
            _extract(temporary, Path(extracted))
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


@contextmanager
def load_template(name: str, source=None, *, registry=None, cache_dir=None):
    """Yield a template selected from a registry and optional source override.

    A registry entry describes an existing directory or ZIP: ``main`` and
    ``assets`` are source-relative. ``adapter`` is registry-relative and lets
    an untouched upstream release use a local starter.
    """
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', name):
        raise ValueError(f'Invalid template name: {name!r}')
    registry_path = Path(registry or DEFAULT_REGISTRY).resolve()
    entries = _registry(registry_path)
    if name not in entries:
        raise ValueError(f'Unknown template {name!r} in {registry_path}')
    entry = entries[name]
    allowed = {'source', 'main', 'adapter', 'assets', 'body', 'version'}
    if not isinstance(entry, dict) or set(entry) - allowed:
        raise ValueError(f'Invalid definition for template {name!r}')
    if ('main' in entry) == ('adapter' in entry):
        raise ValueError(f'Template {name!r} requires exactly one of main or adapter')
    if not isinstance(entry.get('source'), str):
        raise ValueError(f'Template {name!r} requires a source')
    if 'version' in entry and not isinstance(entry['version'], str):
        raise ValueError('Template version must be a string')
    override = source is not None
    origin = str(source if override else entry['source'])
    if urlparse(origin).scheme in {'http', 'https'}:
        cache = Path(cache_dir) if cache_dir else Path(os.environ.get(
            'TUTTIREPORTING_TEMPLATE_CACHE', str(Path.home() / '.cache' / 'tuttireporting' / 'templates')))
        archive = _download(origin, cache)
        archive_source = True
    else:
        archive = Path(origin)
        if not archive.is_absolute():
            archive = archive if override else registry_path.parent / archive
        archive = archive.resolve()
        archive_source = archive.is_file()
    provenance = {'name': name, 'source': origin, 'registry': str(registry_path),
                  'version': entry.get('version')}
    if archive.is_dir():
        root = archive
        main = _file(root, entry['main']) if 'main' in entry else _file(registry_path.parent, entry['adapter'])
        body = _file(root, entry['body']) if 'body' in entry else PACKAGED / 'body.tex.j2'
        yield Template(root, main, body, _assets(root, entry.get('assets', [])), provenance)
    else:
        if not archive_source or archive.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ValueError(f'Template ZIP missing or larger than 64 MiB: {archive}')
        with tempfile.TemporaryDirectory(prefix='tutti-template-') as temporary:
            root = _extract(archive, Path(temporary))
            main = _file(root, entry['main']) if 'main' in entry else _file(registry_path.parent, entry['adapter'])
            body = _file(root, entry['body']) if 'body' in entry else PACKAGED / 'body.tex.j2'
            yield Template(root, main, body, _assets(root, entry.get('assets', [])), provenance)
