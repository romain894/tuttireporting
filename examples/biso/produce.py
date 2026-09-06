"""Produce BiSO figures and a manifest from live HAL data.

Run from the repository root after installing examples/biso/requirements.txt.
This script is a data producer, independent of tuttireporting's build API.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path

from dibisoplot.biso import (AnrProjects, Chapters, CollaborationMap,
                             CollaborationNames, Conferences, EuropeanProjects,
                             Journals, JournalsHal, OpenAccessWorks,
                             PrivateSectorCollaborations, WorksBibtex, WorksType)
from dibisoplot.dibisoplot import DataStatus
from dibisoplot._version import __version__ as dibisoplot_version
import tomli_w


def produce(entity_id: str, year: int, output: Path, full: bool = False) -> Path:
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
            ('works_bibtex', lambda: make(WorksBibtex, max_plotted_entities=1000), 'Bibliographie'),
        ]
    results = {}
    stats = {}
    items = []
    for name, factory, caption in definitions:
        print(f'Fetching {name} for {entity_id}...', flush=True)
        target = plots / f'{name}.pdf'
        target.unlink(missing_ok=True)
        try:
            visualization = factory()
            if name == 'works_type':
                visualization.orientation = 'h'
            results[name] = visualization.fetch_data()
            if visualization.data_status != DataStatus.OK:
                raise RuntimeError(f'{visualization.data_status.name}')
            figure = visualization.get_figure()
            figure.update_layout(font_size=18)
            if name == 'works_type':
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
            figure.write_image(str(target))
        except Exception as exc:
            print(f'{name} failed: {exc}', flush=True)
            # Keep the declared path so tuttireporting can render a visible
            # incomplete-section notice and recover on a later run.
        items.append(dict(output_name=name, path=f'plots/{name}.pdf', caption=caption))

    manifest = {
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'config': {'entity_id': entity_id, 'year': year,
                   'entity_acronym': entity_id, 'entity_full_name': entity_id,
                   'dibisoplot_version': dibisoplot_version},
        'stats': stats,
        'items': items,
    }
    path = output / 'manifest.toml'
    path.write_text(tomli_w.dumps(manifest), encoding='utf-8')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entity-id', default='UNIV-PARIS-SACLAY', help='HAL collection identifier')
    parser.add_argument('--year', type=int, default=2024)
    parser.add_argument('--output', type=Path, default=Path('build/biso/data'))
    parser.add_argument('--full', action='store_true', help='Attempt every visualization in the BiSO catalog')
    args = parser.parse_args()
    print(produce(args.entity_id, args.year, args.output, full=args.full))


if __name__ == '__main__':
    main()
