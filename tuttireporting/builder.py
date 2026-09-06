"""Assemble machine-owned content around a preserved human-owned main.tex."""
import logging
from pathlib import Path
import json
import shutil
import subprocess
import tempfile

from .manifest import load_report
from .templating import get_latex_env, render_variables
from .template_bundle import load_template

log = logging.getLogger(__name__)


def _write(path: Path, content: str):
    if path.is_symlink():
        raise ValueError(f'Refusing to overwrite a symlink: {path}')
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def build_project(output_dir, manifest_path, template_name=None, *, report_path=None,
                  template_source=None, template_sha256=None, template_cache=None,
                  template_dir=None, catalog_name=None) -> Path:
    """Build a report using a named template and optional directory/ZIP/HTTPS source.

    Relative sources in report TOML resolve beside that TOML; explicit Python/CLI
    sources resolve from the current directory. Existing main.tex is preserved.
    """
    if catalog_name is not None:
        if report_path is not None:
            raise ValueError('Choose either report_path or catalog_name, not both')
        from .catalog import report_path as catalog_report_path
        report_path = catalog_report_path(catalog_name)
    report = load_report(manifest_path, report_path)
    if template_dir is not None:
        if template_source is not None:
            raise ValueError('Choose either template_source or template_dir, not both')
        template_source = template_dir
    if template_source is None and report.metadata.get('template_source'):
        template_source = report.metadata['template_source']
        if not template_source.startswith(('https://', 'http://')):
            template_source = Path(report_path or manifest_path).resolve().parent / template_source
    name = template_name or report.metadata['template']
    checksum = template_sha256 if template_sha256 is not None else report.metadata.get('template_sha256')
    with load_template(name, template_source, sha256=checksum, cache_dir=template_cache) as template:
        return _assemble(output_dir, report, template)


def _assemble(output_dir, report, template):
    main = template.main.read_text(encoding='utf-8')
    variables = render_variables(report.variables)
    body = get_latex_env(str(template.body.parent)).get_template(template.body.name).render(sections=report.sections)
    source = template.root
    output = Path(output_dir).absolute()
    if output.is_symlink():
        raise ValueError(f'Output directory is a symlink: {output}')
    output = output.resolve()
    if source == output or source.is_relative_to(output) or output.is_relative_to(source):
        raise ValueError('Template and output directories must not overlap')
    for path in [output / 'plots', output / 'tutti', output / 'main.tex',
                 output / 'generated_variables.tex', output / 'generated_body.tex', output / '.tutti-template.json']:
        if path.is_symlink():
            raise ValueError(f'Output contains a symlink: {path}')
    # Validate all template and asset destinations before changing any files.
    copies = [*report.assets, *template.assets]
    for _, relative in copies:
        target = output / relative
        if target.is_symlink() or not target.resolve().is_relative_to(output):
            raise ValueError(f'Unsafe output path: {target}')
    provenance_path = output / '.tutti-template.json'
    if (output / 'main.tex').exists() and provenance_path.is_file():
        previous = json.loads(provenance_path.read_text(encoding='utf-8'))
        if previous != template.provenance:
            log.warning('Template selection changed; existing main.tex is preserved. '
                        'Update it yourself or use a fresh output directory to use the new starter.')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'plots').mkdir(exist_ok=True)
    for path, relative in copies:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.resolve() != target.resolve():
            shutil.copy2(path, target)
    _write(output / 'generated_variables.tex', variables)
    _write(output / 'generated_body.tex', body)
    _write(output / '.tutti-template.json', json.dumps(template.provenance, indent=2) + '\n')
    try:
        with (output / 'main.tex').open('x', encoding='utf-8') as stream:
            stream.write(main)
    except FileExistsError:
        log.info('Preserving existing main.tex and researcher edits: %s', output / 'main.tex')
    return output


def compile_project(output_dir) -> Path:
    """Compile with LuaLaTeX; propagate missing tools and compilation errors."""
    output = Path(output_dir).resolve()
    subprocess.run(['latexmk', '-lualatex', '-interaction=nonstopmode', '-halt-on-error', 'main.tex'],
                   cwd=output, check=True)
    return output / 'main.pdf'


def zip_project(output_dir) -> Path:
    """Place an Overleaf archive beside the project, never inside itself."""
    import zipfile
    output = Path(output_dir).resolve()
    archive = output.with_name(output.name + '.zip')
    if archive.is_symlink():
        raise ValueError(f'Archive is a symlink: {archive}')
    ignored = {'.aux', '.log', '.fls', '.fdb_latexmk', '.out', '.toc', '.synctex.gz'}
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as stream:
        for path in sorted(output.rglob('*')):
            if path.is_symlink() or not path.resolve().is_relative_to(output):
                raise ValueError(f'Cannot archive symlink: {path}')
            if path.is_file() and path.suffix not in ignored and not path.name.endswith('.synctex.gz'):
                stream.write(path, path.relative_to(output))
    return archive
