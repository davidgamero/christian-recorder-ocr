import sys
import os
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build import source_links, transcription, url


class SiteTests(unittest.TestCase):
    def test_diagrams_are_small_self_contained_vectors(self):
        root = Path(__file__).resolve().parents[1]
        diagrams = list((root / 'src/assets/diagrams').glob('*.svg'))
        self.assertEqual(len(diagrams), 5)
        for path in diagrams:
            svg = ET.parse(path).getroot()
            self.assertEqual(svg.get('viewBox'), '0 0 240 160')
            self.assertIsNotNone(svg.find('{http://www.w3.org/2000/svg}title'))
            self.assertFalse(svg.findall('.//{http://www.w3.org/2000/svg}image'))
            self.assertLess(path.stat().st_size, 4000)

    def test_ocr_html_is_escaped(self):
        result = transcription('<script>alert("x")</script>\nA & B')
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)
        self.assertIn('A &amp; B', result)

    def test_archive_leaf_not_scan_ordinal(self):
        viewer, member = source_links({"id":"volume", "archive_url":"https://archive.org/details/volume"},
                                      {"number":3,"source_page":"volume_jp2/volume_0017.jp2"})
        self.assertIn('/page/n17/', viewer)
        self.assertTrue(member.endswith('volume_jp2/volume_0017.jp2'))

    def test_project_subpath(self):
        expected = '/' + os.environ.get('BASE_PATH', '/christian-recorder-ocr/').strip('/') + '/'
        self.assertEqual(url('scans/page/'), expected.replace('//', '/') + 'scans/page/')


if __name__ == '__main__':
    unittest.main()
