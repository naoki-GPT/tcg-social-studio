"""v1.0: 収集の指標の区別と、メタデータ・向き・原本保全をオフラインで検証。"""
from pathlib import Path
import tempfile
import unittest

from PIL import Image, PngImagePlugin

from collect import Page, public_url, classify_page
from clean_metadata import clean, inspect
from summarize_sales import summarize
from analyze_posts import analyze
from contact_sheet import build


class ToolsTest(unittest.TestCase):
    def test_post_comparison_keeps_unknown_distinct_from_zero(self):
        base = dict(account='shop',post_id='a',published_at='2026-10-01T00:00:00+00:00',observed_at='2026-10-27T00:00:00+00:00',format='reel',metric_name='plays',metric_value=0,pinned=False,promotion=False,giveaway=False)
        rows = [base,dict(base,post_id='b',metric_value=100),dict(base,post_id='c',metric_value=None),dict(base,post_id='d',metric_value=-1),dict(base,post_id='e',pinned=None),dict(base,post_id='f',metric_name='views',metric_value=900)]
        r=analyze(dict(window=dict(start='2026-10-01',end='2026-10-26'),rows=rows))
        plays=next(x for x in r['groups'] if x['metric_name']=='plays')
        self.assertEqual((plays['n'],plays['median']),(2,50));self.assertEqual(len(r['excluded']),3)

    def test_post_latest_dedup_and_collaboration_counts(self):
        b=dict(account='shop',post_id='a',published_at='2026-10-01T00:00:00+00:00',observed_at='2026-10-20T00:00:00+00:00',format='reel',metric_name='plays',metric_value=10,pinned=False,promotion=False,giveaway=False)
        r=analyze(dict(window=dict(start='2026-10-01',end='2026-10-26'),rows=[b,dict(b,observed_at='2026-10-27T00:00:00+00:00',metric_value=40),dict(b,account='other')]))
        self.assertEqual(r['unique_posts'],1);self.assertEqual(r['unique_account_posts'],2)
        self.assertEqual(next(x for x in r['groups'] if x['account']=='shop')['median'],40)

    def test_portrait_contact_sheet_preserves_ratio_and_source(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);f=p/'frame-00.png';Image.new('RGB',(108,192),'blue').save(f);original=f.read_bytes()
            size=build(p,p/'sheet.jpg',p/'cover.jpg')
            self.assertEqual(size,(240,455))
            with Image.open(p/'cover.jpg') as cover:self.assertEqual(cover.size,(108,192))
            self.assertEqual(f.read_bytes(),original)
            with self.assertRaises(FileExistsError):build(p,p/'sheet.jpg')

    def test_mercari_http_shell_is_not_product_success(self):
        p = Page("https://jp.mercari.com/item/m123")
        p.feed("<title>商品名 - メルカリ</title><p>会社概要 利用規約</p>")
        self.assertEqual(classify_page(p.url, p.result()), "shell_only")
        p.feed("<h2>商品の説明</h2><p>イーブイ 078/066 売り切れました</p>")
        self.assertEqual(classify_page(p.url, p.result()), "fetched")

    def test_comparison_does_not_mix_conditions_or_count_duplicates(self):
        base = {"product": "card", "date": "2026-10-01", "title": "same listing", "group": "NM",
                "include": True, "reference_price_usd": 20, "excluded_reasons": []}
        rows = [dict(base, row=1), dict(base, row=2),
                dict(base, row=3, group="LP", title="different condition", reference_price_usd=10),
                dict(base, row=4, date="2026-01-01", title="old")]
        r = summarize({"window": {"start": "2026-09-21", "end": "2026-10-20"}, "rows": rows})
        self.assertEqual(r["excluded_count"], 2)
        self.assertEqual(len(r["groups"]), 2)
        self.assertTrue(all(x["market_total_sales"] is None for x in r["groups"]))

    def test_rank_is_not_sold_and_apparel_excluded(self):
        p = Page("https://snkrdunk.com/")
        p.feed('<h3>人気アパレル</h3><a href="/apparels/1">1 Shirt ¥999 40 / 出品5</a>'
               '<h3>人気トレカ</h3><a href="/apparels/2">1 BOX ¥999 500 / 出品99+</a>'
               '<script>5000 sold</script>')
        r = p.result()
        self.assertEqual(len(r["tcg_popularity_links"]), 1)
        self.assertTrue(r["tcg_popularity_links"][0]["url"].endswith("/2"))
        self.assertEqual(r["unverified_sold_matches"], [])

    def test_sold_count_is_unverified_not_market_volume(self):
        p = Page("https://www.ebay.com/itm/123")
        p.feed("<title>Card</title><p>10 available 103 sold</p>")
        r = p.result()
        self.assertIn("103 sold", r["unverified_sold_matches"][0])
        self.assertNotIn("monthly_sales", r)

    def test_reject_local_and_credential_urls(self):
        for url in ["file:///secret", "https://localhost/", "https://127.0.0.1/", "https://user:secret@example.com/"]:
            with self.assertRaises(ValueError):
                public_url(url)

    def test_exif_removed_orientation_preserved_source_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)
            src, out, report = b / "in.jpg", b / "out.jpg", b / "check.json"
            exif = Image.Exif()
            exif[274] = 6  # スマホの縦向き指定。出力時は画素へ反映する。
            exif[271] = "TestCamera"
            Image.new("RGB", (80, 40), "blue").save(src, exif=exif)
            original = src.read_bytes()
            r = clean(src, out, report)
            self.assertEqual(r["after"]["size"], [40, 80])
            self.assertTrue(inspect(out)["passed"])
            self.assertEqual(src.read_bytes(), original)
            with self.assertRaises(FileExistsError):
                clean(src, out, report)

    def test_png_text_and_xmp_removed(self):
        with tempfile.TemporaryDirectory() as td:
            b = Path(td)
            meta = PngImagePlugin.PngInfo()
            meta.add_text("Description", "private note")
            meta.add_itxt("XML:com.adobe.xmp", "private XMP")
            Image.new("RGB", (32, 40), "yellow").save(b / "in.png", pnginfo=meta)
            r = clean(b / "in.png", b / "out.jpg", b / "check.json")
            self.assertIn("XML:com.adobe.xmp", r["before"]["info_keys"])
            self.assertTrue(r["after"]["passed"])


if __name__ == "__main__":
    unittest.main()
