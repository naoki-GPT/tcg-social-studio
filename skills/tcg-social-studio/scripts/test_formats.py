"""v1.1: 比較の誤り・カルーセルの欠落・全型の生成を架空データで検証する。"""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from compare_prices import compare
from create_story import ROOT, create
from import_reference_media import entries


class FormatsTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT/'templates/comparison.example.json').read_text(encoding='utf-8'))

    def test_price_gap_and_negative_gap(self):
        value = compare(self.data)
        self.assertEqual(value['reference_difference_usd'], 30)
        self.assertEqual(value['difference_pct_of_overseas'], 23.08)
        self.assertFalse(value['publication_ready'])
        self.data['overseas']['amount'] = 90
        self.assertEqual(compare(self.data)['reference_difference_usd'], -10)

    def test_mismatches_and_invalid_price_blocked(self):
        for key, value in [('language','English'), ('unit','case'), ('contents','10 packs'), ('grade','PSA10'), ('condition','damaged'), ('number','other')]:
            data = copy.deepcopy(self.data); data['overseas'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): compare(data)
        for number in [0, -1, True, float('nan'), float('inf'), '100']:
            data = copy.deepcopy(self.data); data['overseas']['amount'] = number
            with self.subTest(number=number), self.assertRaises(ValueError): compare(data)

    def test_stale_future_unknown_and_naive_blocked(self):
        for date in ['2026-10-29T08:00:00+09:00','2026-11-01T08:00:00+09:00','2026-10-31T08:00:00']:
            data = copy.deepcopy(self.data); data['fx']['observed_at'] = date
            with self.subTest(date=date), self.assertRaises(ValueError): compare(data)
        self.data['overseas']['packaging'] = 'unknown'
        with self.assertRaises(ValueError): compare(self.data)

    def test_mixed_basis_or_language_has_no_discount_pct(self):
        self.data['overseas']['basis'] = 'market_estimate'
        self.assertIsNone(compare(self.data)['difference_pct_of_overseas'])
        self.data['mode'] = 'language-edition'; self.data['overseas']['language'] = 'English'
        with self.assertRaises(ValueError): compare(self.data)
        self.data.update(pairing_reason='Same artwork', edition_differences='Different language and number')
        result = compare(self.data)
        self.assertFalse(result['conditions_aligned']); self.assertIsNone(result['difference_pct_of_overseas'])

    def test_full_carousel_and_missing_pages(self):
        record = {'kind':'carousel', 'expected_count':9,
                  'files':[{'position':i, 'kind':'image', 'path':f'{i}.jpg'} for i in range(1,10)]}
        rows = list(entries(record))
        self.assertEqual([x['position'] for x in rows], list(range(1,10)))
        record['files'].pop()
        with self.assertRaises(ValueError): list(entries(record))

    def test_all_formats_and_existing_output(self):
        formats = json.loads((ROOT/'templates/formats.json').read_text(encoding='utf-8'))['formats']
        self.assertEqual(len(formats), 19); self.assertEqual(len({f['id'] for f in formats}),19)
        with tempfile.TemporaryDirectory() as temp:
            for recipe in formats:
                for ratio in ['4:5','9:16']:
                    dest = Path(temp)/(recipe['id']+ratio.replace(':','-'))
                    story = create(recipe['id'], dest, ratio)
                    self.assertTrue(story['draft'])
                    self.assertEqual(len(story['scenes']),len(recipe['scenes']))
                    self.assertTrue((dest/'index.html').exists())
                    design = json.loads((dest/'reference-design.json').read_text(encoding='utf-8'))
                    self.assertEqual(design['status'], 'draft')
                    self.assertFalse(design['review']['rendered_video_visual_match'])
                    self.assertFalse(design['review']['reference_opened'])
                    with self.assertRaises(FileExistsError): create(recipe['id'], dest, ratio)


if __name__ == '__main__': unittest.main()
