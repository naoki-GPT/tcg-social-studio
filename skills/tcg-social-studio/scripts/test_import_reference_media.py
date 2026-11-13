"""v2.2: ローカル全素材の取り込み・原本保持・欠落停止を通信なしで検証。"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from import_reference_media import import_media


class ImportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for i in (1, 2): Image.new('RGB', (20, 25), (i * 60, 0, 0)).save(self.root / f'{i}.png')
        self.record = {'kind': 'carousel', 'expected_count': 2,
                       'files': [{'position': i, 'kind': 'image', 'path': f'{i}.png'} for i in (1, 2)]}

    def run_import(self):
        path = self.root / 'input.json'
        path.write_text(json.dumps(self.record), encoding='utf-8')
        return import_media(path, self.root / 'out')

    def test_import_keeps_bytes_and_requires_visual_review(self):
        before = (self.root / '1.png').read_bytes()
        result = self.run_import()
        self.assertTrue(result['complete'])
        self.assertEqual(result['visual_review'], 'not_reviewed')
        self.assertEqual((self.root / 'out/01.png').read_bytes(), before)
        self.assertEqual((self.root / '1.png').read_bytes(), before)
        self.assertEqual(result['media'][0]['sha256'], hashlib.sha256(before).hexdigest())

    def test_existing_output_is_protected(self):
        self.run_import()
        with self.assertRaises(FileExistsError): self.run_import()

    def test_missing_source_does_not_create_output(self):
        self.record['files'][1]['path'] = 'missing.png'
        with self.assertRaises(FileNotFoundError): self.run_import()
        self.assertFalse((self.root / 'out').exists())

    def test_repeated_file_cannot_fill_missing_page(self):
        self.record['files'][1]['path'] = '1.png'
        with self.assertRaises(ValueError): self.run_import()
        self.assertFalse((self.root / 'out').exists())


if __name__ == '__main__': unittest.main()
