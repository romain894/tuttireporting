"""Command-line interface for declarative reports."""
import argparse
import logging
from pathlib import Path
import subprocess

from .catalog import export_report, list_reports
from .builder import build_project, compile_project, zip_project


def main(argv=None):
    parser = argparse.ArgumentParser(prog='tuttireporting')
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('build', help='Assemble an editable LaTeX project')
    build.add_argument('--manifest', required=True, type=Path)
    layout = build.add_mutually_exclusive_group()
    layout.add_argument('--catalog', help='Bundled report layout; see catalog list')
    layout.add_argument('--report', type=Path, help='Reusable report TOML (otherwise inline or automatic layout)')
    build.add_argument('--template', help='Override report.template; defaults to article')
    build.add_argument('--template-dir', type=Path, help='Local template with main.tex and tutti/')
    build.add_argument('--output', '-o', type=Path, help='Default: report/ beside manifest')
    build.add_argument('--compile', action='store_true')
    build.add_argument('--zip', action='store_true')
    catalog = commands.add_parser('catalog', help='List or export reusable report definitions')
    actions = catalog.add_subparsers(dest='action', required=True)
    actions.add_parser('list', help='List bundled reports')
    export = actions.add_parser('export', help='Copy editable report and producer TOML files')
    export.add_argument('name')
    export.add_argument('--output', '-o', type=Path, required=True)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    try:
        if args.command == 'catalog':
            if args.action == 'list':
                print('\n'.join(list_reports()))
            else:
                print(export_report(args.name, args.output))
            return
        output = build_project(args.output or args.manifest.resolve().parent / 'report', args.manifest,
                               args.template, report_path=args.report, template_dir=args.template_dir, catalog_name=args.catalog)
        if args.compile:
            compile_project(output)
        if args.zip:
            print(zip_project(output))
        print(output)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f'tuttireporting: {exc}\n')


if __name__ == '__main__':
    main()
