"""Prerequisites shared by all live integration checks."""
import importlib.util
import shutil

import pytest


@pytest.fixture(scope='session', autouse=True)
def live_dependencies():
    for module in ('dibisoplot', 'tomli_w'):
        if importlib.util.find_spec(module) is None:
            pytest.fail('Install examples/biso/requirements.txt before running make test-live')
    for command in ('latexmk', 'lualatex', 'biber'):
        if shutil.which(command) is None:
            pytest.fail(f'{command} is required for make test-live')
