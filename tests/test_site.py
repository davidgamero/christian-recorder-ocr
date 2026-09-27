import sys
import os
from pathlib import Path
import unittest
import hashlib
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build import source_links, transcription, url, volume_label, volume_sort


class SiteTests(unittest.TestCase):
    def test_volume_labels_and_chronological_sort(self):
        self.assertEqual(volume_label('christianrecorder_1868_v8_no16_to_28'), 'Issues 16–28')
        self.assertEqual(volume_label('christianrecordephil_4a2'), 'Bound volume 4a2')
        sources = [{'id':'z_no13_to_25','year':'1861'}, {'id':'a','year':'Undated volume'}, {'id':'z_no1_to_12','year':'1861'}]
        self.assertEqual([s['id'] for s in sorted(sources,key=volume_sort)], ['z_no1_to_12','z_no13_to_25','a'])
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

    def test_paragraph_positions_are_derived_from_crop_metadata(self):
        text = 'First paragraph.\n\nSecond paragraph.'
        position = {'text_sha256': hashlib.sha256(text.encode()).hexdigest(), 'spans': [
            {'start':0, 'end':len(text), 'leaf':'leaf-1', 'leaf_count':2, 'column':3, 'kind':'column'}]}
        result = transcription(text, position)
        self.assertEqual(result.count('class="ocr-paragraph"'), 2)
        self.assertIn('0% through text · Leaf 2 · Column 4', result)
        self.assertIn('id="p2"', result)
        with self.assertRaises(ValueError):
            transcription(text+'changed', position)

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
