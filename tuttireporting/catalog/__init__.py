"""Bundled report layouts and plotting configuration references."""
from pathlib import Path

_ROOT = Path(__file__).parent


def list_reports() -> list[str]:
    """Return available catalog names without importing plotting dependencies."""
    return sorted(path.parent.name for path in _ROOT.glob('*/report.toml'))


def report_path(name: str) -> Path:
    """Resolve an exact catalog name (never an arbitrary filesystem path)."""
    if name not in list_reports():
        raise ValueError(f'Unknown catalog report {name!r}; available: {", ".join(list_reports())}')
    return _ROOT / name / 'report.toml'


def export_report(name: str, output_dir: str | Path) -> Path:
    """Copy editable catalog files into a directory; refuse existing targets."""
    source = report_path(name)
    files = [source]
    producer = source.with_name('producer.toml')
    if producer.is_file():
        files.append(producer)
    output = Path(output_dir)
    for path in files:
        target = output / path.name
        if target.exists() or target.is_symlink():
            raise FileExistsError(f'Refusing to overwrite catalog file: {target}')
    output.mkdir(parents=True, exist_ok=True)
    for path in files:
        with (output / path.name).open('x', encoding='utf-8') as stream:
            stream.write(path.read_text(encoding='utf-8'))
    return output
