"""v1.1: 商品条件・確認日時を点検し、USDの参考差額を計算する。取得・利益計算はしない。"""
import argparse
import json
import math
from datetime import datetime
from pathlib import Path


def positive(value, key):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError('Positive numeric value required: ' + key)
    return value


def stamp(value):
    date = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if date.tzinfo is None:
        raise ValueError('Timezone required')
    return date


def compare(data):
    mode = data['mode']
    if mode not in ('same-item', 'language-edition'):
        raise ValueError('Use same-item or language-edition; time-change requires a separate historical comparison')
    now = stamp(data['as_of'])
    age = positive(data.get('max_age_hours', 24), 'max_age_hours')
    fx = data['fx']
    rate = positive(fx['jpy_per_usd'], 'fx.jpy_per_usd')
    left, right = data['japan'], data['overseas']
    for label, row in [('fx', fx), ('japan', left), ('overseas', right)]:
        if not str(row.get('source_url', '')).startswith('https://'):
            raise ValueError('HTTPS source required: ' + label)
        elapsed = (now - stamp(row['observed_at'])).total_seconds() / 3600
        if elapsed < 0 or elapsed > age:
            raise ValueError('Future or stale observation: ' + label)
    identity = ('product_id', 'name', 'language', 'edition', 'number', 'unit', 'contents', 'condition', 'grade', 'packaging')
    details = ('basis', 'shipping', 'tax')
    unknowns = ('unknown', 'unconfirmed', '—', '-', '')
    for label, row in [('japan', left), ('overseas', right)]:
        for key in identity + details:
            if not isinstance(row.get(key), str) or row[key].strip().lower() in unknowns:
                raise ValueError('Explicit field required: ' + label + '.' + key)
        positive(row['amount'], label + '.amount')
        if row['currency'] not in ('JPY', 'USD'):
            raise ValueError('Convert other currencies with sourced FX before use')
        if row['basis'] not in ('asking', 'sold_median', 'market_estimate'):
            raise ValueError('Unknown price basis')
    if left['currency'] != 'JPY':
        raise ValueError('Japan reference must be JPY')
    if mode == 'same-item':
        if left['language'] != 'Japanese':
            raise ValueError('same-item is for Japanese products in Japan and overseas')
        # 英語の商品名は同一でなくてよい。条件と共通の照合IDは一致が必要。
        for key in identity:
            if key != 'name' and left[key] != right[key]:
                raise ValueError('Product mismatch: ' + key)
    else:
        if left['language'] != 'Japanese' or right['language'] != 'English':
            raise ValueError('language-edition requires Japanese / English')
        for key in ('pairing_reason', 'edition_differences'):
            if not isinstance(data.get(key), str) or not data[key].strip():
                raise ValueError('Edition comparison requires ' + key)
    japan_usd = left['amount'] / rate
    overseas_usd = right['amount'] / rate if right['currency'] == 'JPY' else right['amount']
    delta = overseas_usd - japan_usd
    aligned = mode == 'same-item' and all(left[k] == right[k] for k in details)
    return {
        'mode': mode, 'sample': bool(data.get('sample', False)), 'as_of': data['as_of'],
        'japan_usd': round(japan_usd, 2), 'overseas_usd': round(overseas_usd, 2),
        'reference_difference_usd': round(delta, 2),
        'difference_pct_of_overseas': round(delta / overseas_usd * 100, 2) if aligned else None,
        'conditions_aligned': aligned,
        'labels': {'japan': left['basis'], 'overseas': right['basis']},
        'note': 'Reference price difference only. Not profit or a shipping-inclusive quote.',
        'publication_ready': False,
        'review_required': ['Source contents', 'Product images and usage rights', 'Caption and labels', 'Actual selling terms']
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input'); parser.add_argument('--out', required=True)
    args = parser.parse_args()
    result = compare(json.loads(Path(args.input).read_text(encoding='utf-8-sig')))
    with Path(args.out).open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print('[OK] Comparison calculated; source and visual review remain required')
