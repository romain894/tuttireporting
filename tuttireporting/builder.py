"""Assemble machine-owned content around a preserved human-owned main.tex."""
import logging
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from .manifest import load_report
from .templating import get_latex_env, render_variables

log = logging.getLogger(__name__)
_TEMPLATES = Path(__file__).parent / 'templates'


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


def build_project(output_dir, manifest_path, template_name=None, *, report_path=None, template_dir=None, catalog_name=None) -> Path:
    """Build an editable project. All input paths are resolved before writing output.

    A custom template_dir contains main.tex and tutti/ (classes/styles/logos).
    The built-in article template supplies a generic starter.
    """
    if catalog_name is not None:
        if report_path is not None:
            raise ValueError('Choose either report_path or catalog_name, not both')
        from .catalog import report_path as catalog_report_path
        report_path = catalog_report_path(catalog_name)
    report = load_report(manifest_path, report_path)
    name = template_name or report.metadata['template']
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', name):
        raise ValueError(f'Invalid template name: {name!r}')
    if template_dir:
        source = Path(template_dir).resolve()
    elif name == 'article':
        source = _TEMPLATES / 'article'
    else:
        raise ValueError(f'Unknown template {name!r}; provide --template-dir')
    if not (source / 'main.tex').is_file() or not (source / 'tutti').is_dir():
        raise ValueError('Template directory must contain main.tex and tutti/')
    main = (source / 'main.tex').read_text(encoding='utf-8')
    variables = render_variables(report.variables)
    body = get_latex_env(str(_TEMPLATES)).get_template('body.tex.j2').render(sections=report.sections)
    output = Path(output_dir).absolute()
    if output.is_symlink():
        raise ValueError(f'Output directory is a symlink: {output}')
    output = output.resolve()
    if source == output or source.is_relative_to(output) or output.is_relative_to(source):
        raise ValueError('Template and output directories must not overlap')
    for path in [output / 'plots', output / 'tutti', output / 'main.tex',
                 output / 'generated_variables.tex', output / 'generated_body.tex']:
        if path.is_symlink():
            raise ValueError(f'Output contains a symlink: {path}')
    # Validate all template and asset destinations before changing any files.
    copies = list(report.assets)
    for path in (source / 'tutti').rglob('*'):
        if path.is_symlink():
            raise ValueError(f'Template contains a symlink: {path}')
        if path.is_file():
            copies.append((path, path.relative_to(source).as_posix()))
    for _, relative in copies:
        target = output / relative
        if target.is_symlink() or not target.resolve().is_relative_to(output):
            raise ValueError(f'Unsafe output path: {target}')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'plots').mkdir(exist_ok=True)
    (output / 'tutti').mkdir(exist_ok=True)
    for path, relative in copies:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.resolve() != target.resolve():
            shutil.copy2(path, target)
    _write(output / 'generated_variables.tex', variables)
    _write(output / 'generated_body.tex', body)
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
