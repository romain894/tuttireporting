"""Shared test selection: external dependencies are always opt-in."""
from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption('--report-output-dir', type=Path,
                     help='Keep complete successfully compiled catalog projects in this directory')
    parser.addoption('--run-pdf', action='store_true', help='Include offline LaTeX tests')
    parser.addoption('--run-live', action='store_true', help='Include live integration tests')


def pytest_collection_modifyitems(config, items):
    for item in items:
        group = Path(item.path).relative_to(Path(__file__).parent).parts[0]
        if group in ('pdf', 'live'):
            item.add_marker(getattr(pytest.mark, group))
            if not config.getoption(f'--run-{group}'):
                item.add_marker(pytest.mark.skip(reason=f'Enable with --run-{group}'))
