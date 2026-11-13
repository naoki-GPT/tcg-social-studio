"""v2.0 (Grokbot 1.9を基に改修): 作り方カード＋今回の文・素材から、制作用HTMLフォルダを作る（既存は上書きしない）。

python scripts/build_from_recipe.py --card refs/recipe-card.json --content content.json --out output/production

- ひな形は templates/recipes/<ref_id>/index.html があればそれ、無ければ templates/recipe/index.html。
- 作ったフォルダは render.mjs（MP4）と export_slides.mjs（PNG連番）にそのまま渡せる。
- カードの記入漏れ、本文の空き、商品画像の欠けがあれば止まる。例のカードは試作だけに使える。
"""
import argparse
import json
import shutil
import re
from pathlib import Path
from recipe_card import validate_card, load

ROOT = Path(__file__).resolve().parents[1]


def template_for(card):
    ref_id = (card.get('reference') or {}).get('ref_id', '')
    if not re.fullmatch(r'[A-Za-z0-9_-]+',ref_id): raise ValueError('Unsafe reference ID')
    own = ROOT / 'templates' / 'recipes' / ref_id / 'index.html'
    return own if ref_id and own.is_file() else ROOT / 'templates' / 'recipe' / 'index.html'


def used_layers(card):
    if card.get('kind') == 'video':
        return card.get('timeline') or []
    return [l for s in card.get('slides') or [] for l in s.get('layers') or []]


def check_content(card, content):
    e = []
    texts = content.get('texts') or {}
    products = content.get('products') or []
    for l in used_layers(card):
        if l.get('element') == 'text':
            v = texts.get(l.get('slot'))
            if not isinstance(v, str) or not v.strip(): e.append('texts.' + str(l.get('slot')) + ': 空')
        if l.get('element') == 'product':
            i = l.get('product')
            if type(i) is not int or i<0 or i >= len(products) or not (products[i] or {}).get('image'):
                e.append(f'products[{i}].image: 商品画像が無い')
    if any(p!='caption' for p in card.get('cta_placement',[])) and not any(l.get('style') == 'cta' for l in used_layers(card)):
        e.append('カードにCTAの文字レイヤーが無い')
    return sorted(set(e))


def build(card_path, content_path, out, base=None):
    card = load(card_path); content = load(content_path)
    errs = validate_card(card)
    if errs: raise ValueError('作り方カードの不足: ' + '; '.join(errs))
    errs = check_content(card, content)
    if errs: raise ValueError('今回の文・素材の不足: ' + '; '.join(errs))
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    base = Path(base) if base else Path(content_path).resolve().parent
    assets = out / 'assets'; assets.mkdir()

    def bring(src, name):
        p = Path(src)
        if not p.is_absolute(): p = base / p
        if not p.is_file(): raise FileNotFoundError(str(src))
        allowed=('.woff','.woff2','.ttf','.otf') if name.startswith('font_') else ('.jpg','.jpeg','.png','.webp','.svg','.gif')
        if p.suffix.lower() not in allowed:raise ValueError('Unsupported asset type: '+p.suffix)
        dest = assets / (name + p.suffix.lower()); shutil.copyfile(p, dest)
        return 'assets/' + dest.name

    content = {k: v for k, v in json.loads(json.dumps(content)).items() if not k.startswith('_')}  # 説明用の_noteは画面へ渡さない
    for i, prod in enumerate(content.get('products') or []):
        if prod.get('image'): prod['image'] = bring(prod['image'], f'product_{i+1:02d}')
    card = json.loads(json.dumps(card))
    bg = card.get('background') or {}
    if bg.get('type') == 'image': bg['value'] = bring(bg['value'], 'background')
    for k, f in enumerate((card.get('typography') or {}).get('font_files') or []):
        f['src'] = bring(f['src'], f'font_{k+1:02d}')
    tpl = template_for(card)
    shutil.copyfile(tpl, out / 'index.html')
    (out / 'recipe.js').write_text('window.RECIPE = ' + json.dumps(card, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
    (out / 'content.js').write_text('window.CONTENT = ' + json.dumps(content, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
    (out / 'content.json').write_text(json.dumps(content, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (out / 'recipe-card.json').write_text(json.dumps(card, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    info = {'template': str(tpl.relative_to(ROOT)), 'kind': card['kind'], 'ratio': card['canvas']['ratio'],
            'ref_id': card['reference']['ref_id'], 'is_example': bool(card.get('is_example')),
            'slides': len(card.get('slides') or []) if card['kind'] != 'video' else None,
            'duration_s': card.get('duration_s')}
    (out / 'build.json').write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    shutil.copyfile(ROOT/'templates/production-contract.example.json',out/'production-contract.json')
    return info


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--card', required=True); ap.add_argument('--content', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args(); info = build(a.card, a.content, a.out)
    if info['is_example']: print('[WARN] 例のカードで組みました。試作専用で、参考の再現とは呼べません。')
    print('[OK]', json.dumps(info, ensure_ascii=False))
