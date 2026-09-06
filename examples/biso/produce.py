"""Produce two BiSO figures and a manifest from live HAL data.

Run from the repository root after installing examples/biso/requirements.txt.
This script is a data producer, independent of tuttireporting's build API.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path

from dibisoplot.biso import OpenAccessWorks, WorksType
from dibisoplot.dibisoplot import DataStatus
import tomli_w


def produce(entity_id: str, year: int, output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    plots = output / 'plots'
    plots.mkdir(exist_ok=True)

    # Both plots use HAL; no scanR credentials or OpenAlex queries are needed.
    parameters = dict(entity_id=entity_id, year=year, language='fr',
                      main_color='#004e7d', width=900, height=450,
                      dynamic_height=False)
    works = WorksType(**parameters)
    works.orientation = 'h'  # Long French document-type labels need horizontal bars.
    access = OpenAccessWorks(**parameters)
    definitions = [
        ('works_type', works, f'Types de publications, {year}'),
        ('open_access_works', access, f'Accès ouvert, {year - 4} - {year}'),
    ]
    results = {}
    items = []
    for name, visualization, caption in definitions:
        print(f'Fetching {name} for {entity_id}...', flush=True)
        results[name] = visualization.fetch_data()
        # dibisoplot catches API errors internally. Do not publish an error plot
        # as though it contained valid data, or silently accept an empty query.
        if visualization.data_status != DataStatus.OK:
            raise RuntimeError(
                f'{name}: {visualization.data_status.name}. '
                'Check the HAL collection identifier, year, and API availability.'
            )
        figure = visualization.get_figure()
        figure.update_layout(font_size=18)
        if name == 'works_type':
            figure.update_layout(height=850)
            figure.update_yaxes(autorange='reversed')
        else:
            # dibisoplot 0.9 adds transparent bars for spacing and labels. With
            # Plotly 5 these join the stack; retain only the three data series.
            figure.data = tuple(trace for trace in figure.data if trace.showlegend is not False)
            figure.update_layout(bargap=0.25, legend=dict(orientation='h', y=1.1, x=0, xanchor='left', yanchor='bottom'))
            for trace in figure.data:
                trace.update(text=trace.y, textposition='inside', textfont_color='black')
        figure.write_image(str(plots / f'{name}.pdf'))
        items.append(dict(output_name=name, path=f'plots/{name}.pdf', caption=caption))

    manifest = {
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'config': {'entity_id': entity_id, 'year': year},
        'stats': {
            # WorksType groups the selected year's records by document type.
            'publications': int(sum(works.data.values())),
            # Map dibisoplot's returned name to the BiSO report selector.
            'oaworksperiod': results['open_access_works']['oa_works_period'],
        },
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
    args = parser.parse_args()
    print(produce(args.entity_id, args.year, args.output))


if __name__ == '__main__':
    main()
