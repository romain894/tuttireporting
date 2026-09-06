"""Command-line interface for declarative reports."""
import argparse
import logging
from pathlib import Path
import subprocess

from .catalog import export_report, list_reports
from .template_bundle import BUILTINS
from .builder import build_project, compile_project, zip_project


def main(argv=None):
    parser = argparse.ArgumentParser(prog='tuttireporting')
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('build', help='Assemble an editable LaTeX project')
    build.add_argument('--manifest', required=True, type=Path)
    layout = build.add_mutually_exclusive_group()
    layout.add_argument('--catalog', help='Bundled report layout; see catalog list')
    layout.add_argument('--report', type=Path, help='Reusable report TOML (otherwise inline or automatic layout)')
    build.add_argument('--template', help='Template name: article, biso, pubpart, or a name in a custom bundle')
    build.add_argument('--template-source', '--template-dir', help='Template directory, ZIP file, or HTTPS URL')
    build.add_argument('--template-sha256', help='Expected SHA-256 of the template ZIP')
    build.add_argument('--template-cache', type=Path, help='Override the template download cache directory')
    build.add_argument('--output', '-o', type=Path, help='Default: report/ beside manifest')
    build.add_argument('--compile', action='store_true')
    build.add_argument('--zip', action='store_true')
    catalog = commands.add_parser('catalog', help='List or export reusable report definitions')
    actions = catalog.add_subparsers(dest='action', required=True)
    actions.add_parser('list', help='List bundled reports')
    export = actions.add_parser('export', help='Copy editable report and producer TOML files')
    export.add_argument('name')
    export.add_argument('--output', '-o', type=Path, required=True)
    templates = commands.add_parser('templates', help='Discover built-in LaTeX templates')
    templates.add_argument('action', choices=['list'])
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    try:
        if args.command == 'templates':
            print('\n'.join(BUILTINS))
            return
        if args.command == 'catalog':
            if args.action == 'list':
                print('\n'.join(list_reports()))
            else:
                print(export_report(args.name, args.output))
            return
        output = build_project(args.output or args.manifest.resolve().parent / 'report', args.manifest,
                               args.template, report_path=args.report, template_source=args.template_source,
                               template_sha256=args.template_sha256, template_cache=args.template_cache,
                               catalog_name=args.catalog)
        if args.compile:
            compile_project(output)
        if args.zip:
            print(zip_project(output))
        print(output)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'tuttireporting: {exc}\n')


if __name__ == '__main__':
    main()
