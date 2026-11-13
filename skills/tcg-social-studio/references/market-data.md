# 市場の掲載サンプルの集計

`summarize_sales.py` は下記のJSONを読み、同一商品・条件別の表示価格を集計する。架空の入力例なので、実測で置き換える。

```json
{
  "window":{"start":"2026-09-27","end":"2026-10-26","basis":"掲載日付基準"},
  "rows":[
    {"row":1,"product":"example-card","date":"2026-10-01","title":"Example Japanese card NM single","group":"Japanese_NM_single","reference_price_usd":20,"include":true,"excluded_reasons":[],"primary_sale_verified":false,"source_url":"https://www.ebay.com/itm/example"}
  ]
}
```

`include=false` は除外。`group` は言語・状態・数量・鑑定等の条件を分ける。日付・タイトル・表示価格の一致は重複候補として除外される。別取引の可能性もあるため、実際の販売件数を確定する機能ではない。

```powershell
python scripts/summarize_sales.py "../制作物/sales.json" --out "../制作物/sales_summary.json"
```

集計の中央値はサンプル内の表示価格。送料・税・手数料の統一、成約価格の確定、海外需要や利益の判断は別途必要。市場全体の月販数・売上順位を出力しない。
