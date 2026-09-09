"""Reviewer source prompts stay hidden while preserved commentary is printed."""
import os
import shutil
import subprocess
from unittest.mock import patch

import pytest

from tuttireporting import build_project
from tuttireporting.builder import compile_project


def test_reviewer_text_compiles_and_survives_rebuild(tmp_path):
    for command in ('latexmk', 'lualatex', 'pdftotext'):
        if shutil.which(command) is None:
            pytest.skip(f'{command} is unavailable')
    manifest = tmp_path / 'manifest.toml'
    manifest.write_text('''[report]
title = "Reviewer fixture"
[[sections]]
title = "Interpretation"
omit_if_empty = false
reviewer_comment = {id="interpretation", style="block", prompt="Hidden reviewer instruction"}
[[sections]]
title = "Recommendations"
omit_if_empty = false
reviewer_comment = {id="recommendations", style="comment", prompt="Another hidden instruction"}
''')
    output = build_project(tmp_path / 'output', manifest)
    comment = output / 'main.tex'
    comment.write_text(comment.read_text().replace('% END REVIEWER COMMENT',
                                                 'Preserved reviewer analysis.\n% END REVIEWER COMMENT'))
    build_project(output, manifest)
    with patch.dict(os.environ, {'TEXMFVAR': str(tmp_path / 'texmf-var')}):
        compile_project(output)
    text = subprocess.run(['pdftotext', str(output / 'main.pdf'), '-'],
                          check=True, capture_output=True, text=True).stdout
    assert 'Preserved reviewer analysis.' in text
    assert 'Hidden reviewer instruction' not in text
    assert 'Another hidden instruction' not in text
    assert 'BEGIN REVIEWER' not in text
