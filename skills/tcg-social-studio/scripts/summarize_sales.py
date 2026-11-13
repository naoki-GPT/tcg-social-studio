"""v1.1: 条件付きの掲載サンプルを集計する。市場全体の販売数には換算しない。"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from statistics import median


def summarize(data):
    rows = data["rows"]
    start, end = data["window"]["start"], data["window"]["end"]
    groups, seen, excluded = defaultdict(list), set(), []
    for row in rows:
        reasons = list(row.get("excluded_reasons", []))
        if not start <= row["date"] <= end and "期間外" not in reasons:
            reasons.append("期間外")
        if not row.get("include", False) and not reasons:
            reasons.append("未採用")
        if row.get("reference_price_usd") is None:
            reasons.append("比較可能な単一価格なし")
        # タイトル・日付・価格が全く同じものは保守的に重複扱い。
        # 別の取引かもしれないため「実際の成約件数」とは説明しない。
        fingerprint = (row["product"], row["date"], row.get("title"), row.get("reference_price_usd"))
        if fingerprint in seen:
            reasons.append("日付・タイトル・表示価格が一致する重複候補")
        else:
            seen.add(fingerprint)
        if reasons:
            excluded.append({"product": row["product"], "row": row.get("row"), "reasons": reasons})
            continue
        groups[(row["product"], row["group"])].append(row)
    result = []
    for (product, group), selected in sorted(groups.items()):
        prices = [r["reference_price_usd"] for r in selected]
        result.append({"product": product, "group": group, "sample_rows_after_screening": len(selected),
                       "first_reported_date": min(r["date"] for r in selected),
                       "last_reported_date": max(r["date"] for r in selected),
                       "reference_displayed_price_usd": {"min": min(prices), "median": median(prices), "max": max(prices)},
                       "primary_sales_verified": sum(bool(r.get("primary_sale_verified")) for r in selected),
                       "market_total_sales": None,
                       "note": "掲載サンプル内の参考表示価格。送料・税・手数料未統一。実売中央値・月販数ではない。"})
    return {"window": data["window"], "input_rows": len(rows), "groups": result,
            "excluded_rows": excluded, "excluded_count": len(excluded),
            "warning": "取得上限や出品者未確認を含むため、掲載行数で市場全体の売上順位を作らない。"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    result = summarize(json.loads(a.input.read_text(encoding="utf-8")))
    with a.out.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[OK] input={result['input_rows']}, excluded={result['excluded_count']}, groups={len(result['groups'])}")
