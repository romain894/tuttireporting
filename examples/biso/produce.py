"""Produce BiSO figures and a manifest from live HAL data.

Run from the repository root after installing examples/biso/requirements.txt.
This script is a data producer, independent of tuttireporting's build API.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import unicodedata

from dibisoplot.biso import (AnrProjects, Chapters, CollaborationMap,
                             CollaborationNames, Conferences, EuropeanProjects,
                             Journals, JournalsHal, OpenAccessWorks,
                             PrivateSectorCollaborations, WorksBibtex, WorksType)
from dibisoplot.dibisoplot import DataStatus
from dibisoplot._version import __version__ as dibisoplot_version
from pylatexenc.latexencode import unicode_to_latex
import tomli_w


DEFAULT_BIBLIOGRAPHY_LIMIT = 100
_BIBTEX_TYPES = {
    'article', 'book', 'inbook', 'incollection', 'inproceedings', 'manual',
    'mastersthesis', 'misc', 'online', 'phdthesis', 'proceedings', 'report',
    'techreport', 'thesis', 'unpublished',
}
_BIBTEX_FIELDS = ('TITLE', 'AUTHOR', 'URL', 'JOURNAL', 'PUBLISHER', 'VOLUME',
                  'PAGES', 'YEAR', 'DOI')


def latex_safe(value) -> str:
    """Keep dibisoplot's LaTeX escapes and replace unsupported Unicode safely."""
    text = re.sub(r'[\x00-\x1f\x7f]', ' ', str(value))
    result = []
    for character in text:
        if ord(character) < 128:
            result.append(character)
            continue
        encoded = unicode_to_latex(character)
        # pylatexenc leaves unknown characters untouched; LuaLaTeX may then
        # lack a glyph or fail while Biber reads the file.
        result.append(encoded if encoded != character else '?')
    return ''.join(result)


def bibliography_text(entries: dict) -> str:
    """Serialize HAL records as a conservative, Biber-readable BibTeX file."""
    used_keys, output = set(), []
    for index, entry in enumerate(entries.values(), start=1):
        raw_key = unicodedata.normalize('NFKD', str(entry.get('HAL_ID', '')))
        key = re.sub(r'[^A-Za-z0-9:_.-]+', '-', raw_key).strip('-') or f'entry-{index}'
        base, suffix = key, 2
        while key in used_keys:
            key = f'{base}-{suffix}'
            suffix += 1
        used_keys.add(key)
        entry_type = str(entry.get('bibtex_entry_type', 'misc')).lower()
        if entry_type not in _BIBTEX_TYPES:
            entry_type = 'misc'
        fields = [f'  {field.lower()} = {{{latex_safe(entry.get(field, ""))}}}'
                  for field in _BIBTEX_FIELDS if entry.get(field)]
        output.append(f'@{entry_type}{{{key},\n' + ',\n'.join(fields) + '\n}')
    return '\n\n'.join(output) + ('\n' if output else '')


def produce(entity_id: str, year: int, output: Path, full: bool = False,
            bibliography_limit: int = DEFAULT_BIBLIOGRAPHY_LIMIT) -> Path:
    if bibliography_limit < 1:
        raise ValueError('bibliography_limit must be at least 1')
    output.mkdir(parents=True, exist_ok=True)
    plots = output / 'plots'
    plots.mkdir(exist_ok=True)

    # Both plots use HAL; no scanR credentials or OpenAlex queries are needed.
    parameters = dict(entity_id=entity_id, year=year, language='fr',
                      main_color='#004e7d', width=900, height=450,
                      dynamic_height=False)
    def make(cls, **extra):
        return cls(**parameters, **extra)
    definitions = [('works_type', lambda: make(WorksType), f'Types de publications, {year}'),
                   ('open_access_works', lambda: make(OpenAccessWorks), f'Accès ouvert, {year - 4} - {year}')]
    if full:
        definitions += [
            ('anr_projects', lambda: make(AnrProjects, max_plotted_entities=20), 'Projets ANR'),
            ('chapters', lambda: make(Chapters), 'Chapitres d’ouvrages'),
            ('collaboration_map_world', lambda: make(CollaborationMap, name='world'), 'Collaborations internationales'),
            ('collaboration_map_europe', lambda: make(CollaborationMap, name='europe', resolution=50, map_zoom=True), 'Collaborations en Europe'),
            ('collaboration_names', lambda: make(CollaborationNames, max_plotted_entities=40), 'Partenaires principaux'),
            ('conferences', lambda: make(Conferences, max_plotted_entities=40), 'Conférences'),
            ('european_projects', lambda: make(EuropeanProjects, max_plotted_entities=20), 'Projets européens'),
            ('journals', lambda: make(Journals), 'Revues de publication'),
            ('journals_hal', lambda: make(JournalsHal, max_plotted_entities=40), 'Revues dans HAL'),
            ('private_sector_collaborations', lambda: make(PrivateSectorCollaborations, max_plotted_entities=35), 'Collaborations avec le secteur privé'),
            ('works_bibtex', lambda: make(WorksBibtex, max_plotted_entities=bibliography_limit), 'Bibliographie'),
        ]
    results = {}
    stats = {}
    items, files = [], []
    for name, factory, caption in definitions:
        print(f'Fetching {name} for {entity_id}...', flush=True)
        extension = 'pdf'
        try:
            visualization = factory()
            extension = visualization.figure_file_extension
            target = plots / f'{name}.{extension}'
            target.unlink(missing_ok=True)
            if name == 'works_type':
                visualization.orientation = 'h'
            results[name] = visualization.fetch_data()
            if visualization.data_status != DataStatus.OK:
                raise RuntimeError(f'{visualization.data_status.name}')
            figure = visualization.get_figure()
            if extension == 'bib':
                target.write_text(bibliography_text(visualization.data), encoding='utf-8')
                files.append(dict(name='references', path=f'plots/{name}.bib',
                                  destination='references.bib'))
            elif name == 'works_type':
                figure.update_layout(font_size=18)
                figure.update_layout(height=850)
                figure.update_yaxes(autorange='reversed')
                stats['publications'] = int(sum(visualization.data.values()))
            elif name == 'open_access_works':
                # Remove spacing traces introduced by dibisoplot 0.9.
                figure.data = tuple(trace for trace in figure.data if trace.showlegend is not False)
                figure.update_layout(bargap=0.25, legend=dict(orientation='h', y=1.1, x=0, xanchor='left', yanchor='bottom'))
                for trace in figure.data:
                    trace.update(text=trace.y, textposition='inside', textfont_color='black')
                stats['oaworksperiod'] = results[name]['oa_works_period']
            else:
                figure.update_layout(font_size=18)
            if extension != 'bib':
                figure.write_image(str(target))
        except Exception as exc:
            print(f'{name} failed: {exc}', flush=True)
            # Keep the declared path so tuttireporting can render a visible
            # incomplete-section notice and recover on a later run.
        if extension != 'bib':
            items.append(dict(output_name=name, path=f'plots/{name}.pdf', caption=caption))

    manifest = {
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'config': {'entity_id': entity_id, 'year': year,
                   'entity_acronym': entity_id, 'entity_full_name': entity_id,
                   'dibisoplot_version': dibisoplot_version},
        'stats': stats,
        'items': items,
    }
    if files:
        manifest['files'] = files
    path = output / 'manifest.toml'
    path.write_text(tomli_w.dumps(manifest), encoding='utf-8')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entity-id', default='UNIV-PARIS-SACLAY', help='HAL collection identifier')
    parser.add_argument('--year', type=int, default=2024)
    parser.add_argument('--output', type=Path, default=Path('build/biso/data'))
    parser.add_argument('--full', action='store_true', help='Attempt every visualization in the BiSO catalog')
    parser.add_argument('--bibliography-limit', type=int, default=DEFAULT_BIBLIOGRAPHY_LIMIT,
                        help='Maximum number of BibTeX entries in a full report (default: 100)')
    args = parser.parse_args()
    print(produce(args.entity_id, args.year, args.output, full=args.full,
                  bibliography_limit=args.bibliography_limit))


if __name__ == '__main__':
    main()
