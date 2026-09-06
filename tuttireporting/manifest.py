"""Read run data and resolve a reusable, ordered report definition."""
from dataclasses import dataclass
from datetime import date, datetime, time
import math
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from .templating import render_variables, tex_escape, to_camel_case


@dataclass
class Report:
    metadata: dict
    variables: dict[str, str]
    sections: list[dict]
    assets: list[tuple[Path, str]]


def read_toml(path: str | Path) -> dict:
    with Path(path).open('rb') as stream:
        return tomllib.load(stream)


def flatten(table: dict, prefix: str = '') -> dict:
    """Flatten nested scalar tables to dotted selector keys."""
    if not isinstance(table, dict):
        raise ValueError(f'{prefix or "data"} must be a TOML table')
    result = {}
    for key, value in table.items():
        name = f'{prefix}.{key}' if prefix else key
        if isinstance(value, dict):
            entries = flatten(value, name)
        else:
            if not isinstance(value, (str, int, float, bool, date, datetime, time)):
                raise ValueError(f'{name}: expected a scalar value')
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(f'{name}: non-finite numbers are unsupported')
            entries = {name: value}
        if result.keys() & entries.keys():
            raise ValueError(f'Ambiguous dotted data key: {name}')
        result.update(entries)
    return result


def _keys(value: dict, allowed: set, context: str):
    if not isinstance(value, dict):
        raise ValueError(f'{context} must be a table')
    unknown = value.keys() - allowed
    if unknown:
        raise ValueError(f'{context}: unknown fields: {", ".join(sorted(unknown))}')


def load_report(manifest_path: str | Path, report_path: str | Path | None = None) -> Report:
    manifest_path = Path(manifest_path).resolve()
    data = read_toml(manifest_path)
    _keys(data, {'generated_at', 'stats', 'config', 'items', 'report', 'sections'}, 'manifest')
    definition = read_toml(report_path) if report_path else data
    if report_path:
        _keys(definition, {'report', 'sections'}, 'report definition')
    _keys(definition.get('report', {}), {'title', 'author', 'template', 'template_source', 'template_sha256'}, 'report')
    metadata = dict(definition.get('report', {}))
    if not isinstance(data.get('generated_at', ''), (str, datetime)):
        raise ValueError('generated_at must be a string or TOML datetime')
    for key, value in metadata.items():
        if not isinstance(value, str):
            raise ValueError(f'report.{key} must be a string')
    metadata.setdefault('title', 'Scientific report')
    metadata.setdefault('author', '')
    metadata.setdefault('template', 'article')
    variables = {'tuttiReportTitle': tex_escape(metadata['title']),
                 'tuttiReportAuthor': tex_escape(metadata['author']),
                 'tuttiGeneratedAt': tex_escape(data.get('generated_at', ''))}
    stats, config = flatten(data.get('stats', {})), flatten(data.get('config', {}))

    def macro(prefix, key, value):
        name = prefix + to_camel_case(key)
        if name in variables:
            raise ValueError(f'Macro name collision for {key!r}: {name}')
        variables[name] = value
        return name

    for prefix, table in [('tuttiStat', stats), ('tuttiCfg', config)]:
        for key, value in table.items():
            macro(prefix, key, tex_escape(value))
    plots, assets = {}, []
    items = data.get('items', [])
    if not isinstance(items, list):
        raise ValueError('items must be an array of tables')
    for item in items:
        _keys(item, {'output_name', 'path', 'caption'}, 'item')
        if any(not isinstance(item.get(k), str) or not item[k] for k in ('output_name', 'path')):
            raise ValueError('Each item requires non-empty output_name and path strings')
        key = item['output_name']
        if key in plots:
            raise ValueError(f'Duplicate output_name: {key}')
        source = Path(item['path'])
        if source.is_absolute():
            raise ValueError(f'Plot path must be relative to the manifest: {source}')
        source = (manifest_path.parent / source).resolve()
        if not source.is_relative_to(manifest_path.parent):
            raise ValueError(f'Plot path escapes the manifest directory: {item["path"]}')
        if not source.is_file():
            raise ValueError(f'Plot file does not exist: {source}')
        if source.suffix.lower() not in {'.pdf', '.png', '.jpg', '.jpeg'}:
            raise ValueError(f'Unsupported plot format: {source.suffix}')
        if not isinstance(item.get('caption', ''), str):
            raise ValueError(f'Caption must be a string: {key}')
        relative = 'plots/' + to_camel_case(key) + source.suffix.lower()
        macro('tuttiPlot', key, relative)
        plots[key] = {'path': relative, 'caption': item.get('caption', key)}
        assets.append((source, relative))

    def select(section, field, available):
        selectors = section.get(field, [])
        if not isinstance(selectors, list) or any(not isinstance(s, str) for s in selectors):
            raise ValueError(f'section.{field} must be an array of strings')
        selected = []
        for key in selectors:
            if key == '*':
                selected.extend(k for k in available if k not in selected)
            elif key in available:
                if key not in selected:
                    selected.append(key)
            elif section.get('missing', 'omit') == 'error':
                raise ValueError(f'Section {section["title"]!r}: missing {field} key {key!r}')
        return selected

    def resolve(sections, depth=0):
        if not isinstance(sections, list):
            raise ValueError('sections must be an array of tables')
        if sections and depth > 2:
            raise ValueError('At most three heading levels are supported')
        resolved = []
        for section in sections:
            _keys(section, {'title', 'text', 'new_page', 'omit_if_empty', 'missing',
                            'stats', 'config', 'plots', 'sections'}, 'section')
            if not isinstance(section.get('title'), str) or not section['title'].strip():
                raise ValueError('Each section needs a non-empty title')
            if not isinstance(section.get('text', ''), str):
                raise ValueError('section.text must be a string')
            for flag in ('new_page', 'omit_if_empty'):
                if flag in section and not isinstance(section[flag], bool):
                    raise ValueError(f'section.{flag} must be a boolean')
            if section.get('missing', 'omit') not in {'omit', 'error'}:
                raise ValueError('section.missing must be "omit" or "error"')
            rows = []
            for field, available in [('stats', stats), ('config', config)]:
                rows.extend({'label': k, 'value': available[k]} for k in select(section, field, available))
            figures = [plots[k] for k in select(section, 'plots', plots)]
            children = resolve(section.get('sections', []), depth + 1)
            if section.get('omit_if_empty', True) and not (rows or figures or children or section.get('text')):
                continue
            resolved.append(dict(title=section['title'], text=section.get('text', ''),
                                 new_page=section.get('new_page', False), rows=rows, plots=figures,
                                 command=('section', 'subsection', 'subsubsection')[depth]))
            resolved.extend(children)
        return resolved

    sections = definition.get('sections', [
        {'title': 'Configuration', 'config': ['*']},
        {'title': 'Statistics', 'stats': ['*']},
        {'title': 'Figures', 'plots': ['*'], 'new_page': True},
    ])
    return Report(metadata, variables, resolve(sections), assets)


def generate_variables(manifest_path: str | Path) -> str:
    """Render all run variables independently of section selection."""
    return render_variables(load_report(manifest_path).variables)
