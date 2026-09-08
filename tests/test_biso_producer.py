import runpy
from pathlib import Path
import unittest


PRODUCER = runpy.run_path(str(Path(__file__).parents[1] / 'examples' / 'biso' / 'produce.py'))


class BisoProducerTests(unittest.TestCase):
    def test_bibliography_serialization_limits_syntax_to_safe_bibtex(self):
        text = PRODUCER['bibliography_text']({
            'first': {
                'HAL_ID': 'hal:émoji😀',
                'bibtex_entry_type': 'article',
                # WorksBibtex has already escaped HAL punctuation before this
                # final sanitizer receives the record.
                'TITLE': r'A \& B 😀',
                'AUTHOR': 'Doe, Jane',
                'YEAR': '2024',
            },
            'second': {
                'HAL_ID': 'same key',
                'bibtex_entry_type': 'untrusted-type',
                'TITLE': 'A\x00title',
            },
        })
        self.assertIn('@article{hal:e-moji', text)
        self.assertIn('@misc{same-key', text)
        self.assertIn(r'title = {A \& B ?}', text)
        self.assertNotIn('😀', text)
        self.assertNotIn('\x00', text)
        self.assertEqual(PRODUCER['DEFAULT_BIBLIOGRAPHY_LIMIT'], 100)


if __name__ == '__main__':
    unittest.main()
