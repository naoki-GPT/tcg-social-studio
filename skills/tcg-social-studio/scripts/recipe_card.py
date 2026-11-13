"""v2.0 (Grokbot 1.9を基に改修): 作り方カード（参考1件＝カード1枚）の検査。外部ライブラリなし。

使い方: python scripts/recipe_card.py path/to/recipe-card.json
カードが無い・不完全な参考は「再現」と呼ばない。この検査は記入漏れを見つける補助で、
見た目が参考と一致したことは保証しない（一致は compare_reference.py の比較画像で目視する）。
"""
import argparse
import json
import re
import math
from pathlib import Path

HEX = re.compile(r'^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$')
KINDS = ('slideshow', 'video', 'single-image')
RATIOS = {'4:5': (1080, 1350), '9:16': (1080, 1920)}
EFFECTS = ('cut', 'fade', 'slide-up', 'slide-down', 'slide-left', 'slide-right', 'pop', 'zoom-in',
           'zoom-out', 'typewriter', 'wipe', 'shake', 'glow', 'flash')
ROLES = ('hook', 'product', 'proof', 'compare', 'benefit', 'steps', 'cta')
TEXT_STYLES = ('headline', 'sub', 'cta', 'badge')
PLACEMENTS = ('last-slide', 'video-end', 'video-opening', 'caption')


def _empty(v):
    return v is None or (isinstance(v, str) and (not v.strip() or 'EDIT:' in v))


def _box(errors, where, b):
    if not isinstance(b, dict):
        errors.append(where + ': x,y,w,h（0〜1の比率）が必要'); return
    for k in ('x', 'y', 'w', 'h'):
        v = b.get(k)
        if not isinstance(v, (int, float)) or isinstance(v, bool) or not 0 <= v <= 1:
            errors.append(f'{where}.{k}: 0〜1の数値が必要')
    if all(isinstance(b.get(k), (int, float)) for k in 'xywh'):
        if b['w']<=0 or b['h']<=0: errors.append(where + ': width/height must be positive')
        if b['x'] + b['w'] > 1.001 or b['y'] + b['h'] > 1.001:
            errors.append(where + ': 画面からはみ出す')


def _layer(errors, where, layer, card):
    el = layer.get('element')
    if el not in ('text', 'product', 'shape'):
        errors.append(where + '.element: text / product / shape のどれか'); return
    if el == 'text':
        if layer.get('style') not in TEXT_STYLES: errors.append(where + '.style: ' + '/'.join(TEXT_STYLES))
        if _empty(layer.get('slot')): errors.append(where + '.slot: 本文のキー（content.textsの名前）が必要')
    if el == 'product' and (type(layer.get('product')) is not int or layer['product']<0):
        errors.append(where + '.product: 商品の番号（0始まり）が必要')
    if el == 'shape' and not HEX.match(str(layer.get('color', ''))):
        errors.append(where + '.color: #RRGGBB')
    if 'zone' in layer: _box(errors, where + '.zone', layer['zone'])
    elif el == 'text' and layer.get('style') not in card.get('text_zones', {}):
        errors.append(where + ': text_zonesに' + str(layer.get('style')) + 'が無いのでzoneが必要')
    if 'move' in layer:
        m = layer['move']
        if not isinstance(m, dict) or not isinstance(m.get('at'), (int, float)): errors.append(where + '.move.at: 動き始める秒数')
        else: _box(errors, where + '.move.to', m.get('to'))
    eff = layer.get('effect', 'cut')
    if eff not in EFFECTS: errors.append(where + '.effect: ' + '/'.join(EFFECTS))
    if layer.get('continuous') not in (None,'ken-burns','float'): errors.append(where+'.continuous: unsupported')
    keys=layer.get('keyframes') or []
    previous=-1
    for i,k in enumerate(keys):
        at=k.get('at')
        if type(at) not in (int,float) or not math.isfinite(at) or at<0 or at<=previous:
            errors.append(where+'.keyframes: local seconds must increase');continue
        previous=at
        if k.get('easing','linear') not in ('linear','ease-out','ease-in-out'):errors.append(where+'.keyframes: unsupported easing')
        for name in ('x_px','y_px','scale','rotation','opacity'):
            value=k.get(name)
            if type(value) not in (int,float) or not math.isfinite(value):errors.append(where+'.keyframes: explicit finite '+name+' required')
        if type(k.get('scale')) in (int,float) and k['scale']<=0:errors.append(where+'.keyframes: scale must be positive')
        if type(k.get('opacity')) in (int,float) and not 0<=k['opacity']<=1:errors.append(where+'.keyframes: opacity outside 0..1')
    if keys and keys[0].get('at')!=0:errors.append(where+'.keyframes: must start at local 0')


def validate_card(card):
    """記入漏れ・矛盾の一覧を返す。空なら形式上は使えるカード。"""
    e = []
    if not isinstance(card, dict): return ['カードがJSONオブジェクトではない']
    if card.get('schema') != 'tcg-recipe-card/1': e.append('schema: "tcg-recipe-card/1" が必要')
    ref = card.get('reference') or {}
    if not re.fullmatch(r'[A-Za-z0-9_-]+',str(ref.get('ref_id',''))):e.append('reference.ref_id: safe ID required')
    for k in ('ref_id', 'url', 'observed_scope', 'observed_at'):
        if _empty(ref.get(k)): e.append('reference.' + k + ': 未記入')
    kind = card.get('kind')
    if kind not in KINDS: e.append('kind: ' + '/'.join(KINDS)); kind = None
    ratio = (card.get('canvas') or {}).get('ratio')
    if ratio not in (*RATIOS,'custom'): e.append('canvas.ratio: 4:5 / 9:16 / custom')
    if ratio=='custom':
        for k in ('width','height'):
            v=card['canvas'].get(k)
            if type(v) is not int or not 100<=v<=4096:e.append('canvas.'+k+': integer 100..4096')
    pal = card.get('palette') or {}
    for k in ('background', 'primary_text', 'accent'):
        if not HEX.match(str(pal.get(k, ''))): e.append('palette.' + k + ': #RRGGBB で記入（不明なら参考画像からスポイトで取る）')
    for k, v in pal.items():
        if v and not HEX.match(str(v)): e.append('palette.' + k + ': #RRGGBB')
    bg = card.get('background') or {}
    if bg.get('type') not in ('solid', 'gradient', 'image', 'pattern'): e.append('background.type: solid/gradient/image/pattern')
    if bg.get('type') != 'solid' and _empty(bg.get('value')): e.append('background.value: CSS値または素材の相対パス')
    typo = card.get('typography') or {}
    for role in ('headline', 'body'):
        t = typo.get(role) or {}
        if _empty(t.get('family')): e.append(f'typography.{role}.family: 未記入')
        if t.get('match') not in ('exact', 'approx'): e.append(f'typography.{role}.match: exact（同一と確認）か approx（近似）')
        if t.get('match') == 'approx' and _empty(t.get('approx_note')): e.append(f'typography.{role}.approx_note: 近似の理由と元の特徴')
        if not isinstance(t.get('size_px'), (int, float)) or not 12 <= t.get('size_px', 0) <= 400: e.append(f'typography.{role}.size_px: 12〜400')
        if not isinstance(t.get('weight'), int): e.append(f'typography.{role}.weight: 100〜900の整数')
    ol = card.get('outline')
    if not isinstance(ol, dict) or not isinstance(ol.get('width_px'), (int, float)): e.append('outline.width_px: 縁取りの太さ（無しなら0）')
    elif ol['width_px'] > 0 and not HEX.match(str(ol.get('color', ''))): e.append('outline.color: #RRGGBB')
    prod = card.get('product') or {}
    if not isinstance(prod.get('area_pct'), (int, float)) or not 0 < prod.get('area_pct', 0) <= 100: e.append('product.area_pct: 画面に占める商品の面積％（0より大きく100以下）')
    _box(e, 'product.box', prod.get('box'))
    zones = card.get('text_zones') or {}
    for k, b in zones.items(): _box(e, 'text_zones.' + k, b)
    cta = card.get('cta_placement') or []
    if not cta or any(p not in PLACEMENTS for p in cta): e.append('cta_placement: ' + '/'.join(PLACEMENTS) + ' から1つ以上')
    if kind in ('slideshow', 'single-image'):
        slides = card.get('slides') or []
        need = 1 if kind == 'single-image' else 2
        if len(slides) < need: e.append(f'slides: {need}枚以上の各枚の役割が必要')
        if kind == 'slideshow' and card.get('slide_count') != len(slides): e.append('slide_count と slides の枚数が一致しない')
        for i, s in enumerate(slides):
            if s.get('role') not in ROLES: e.append(f'slides[{i}].role: ' + '/'.join(ROLES))
            if not s.get('layers'): e.append(f'slides[{i}].layers: 何をどこに置くかが空')
            for j, layer in enumerate(s.get('layers') or []): _layer(e, f'slides[{i}].layers[{j}]', layer, card)
        if kind == 'slideshow' and slides:
            last = slides[-1]
            has_cta = any(l.get('style') == 'cta' for l in last.get('layers') or [])
            if 'last-slide' in cta and not (last.get('role') == 'cta' and has_cta):
                e.append('最後の1枚に CTA（role=cta かつ style=cta の文字）が無い')
    if kind == 'video':
        dur = card.get('duration_s')
        if not isinstance(dur, (int, float)) or not 1 <= dur <= 180: e.append('duration_s: 1〜180秒'); dur = None
        tl = card.get('timeline') or []
        if not tl: e.append('timeline: 秒ごとの動きが空')
        if _empty((card.get('first_2s') or {}).get('observed')): e.append('first_2s.observed: 参考の冒頭2秒に何がどう出るか')
        for i, ev in enumerate(tl):
            w = f'timeline[{i}]'
            _layer(e, w, ev, card)
            a, b = ev.get('t_start'), ev.get('t_end')
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)) or a < 0 or b <= a:
                e.append(w + ': t_start < t_end の秒数'); continue
            if dur and b > dur + 1e-6: e.append(w + ': 尺を超える')
            if any(type(k.get('at')) in (int,float) and k['at']>b-a for k in ev.get('keyframes',[])):e.append(w+': keyframe outside layer duration')
            if ev.get('added') is not True and _empty(ev.get('observed')):
                e.append(w + '.observed: 参考で見えた内容（独自追加なら added:true）')
        good = [ev for ev in tl if isinstance(ev.get('t_start'), (int, float)) and isinstance(ev.get('t_end'), (int, float))]
        for i, a in enumerate(good):
            for b in good:
                if a is not b and a.get('element') == 'product' == b.get('element') and a.get('product') == b.get('product') and abs(a['t_end'] - b['t_start']) < 1e-6 and not (b.get('reference_cut') is True and not _empty(b.get('observed'))):
                    e.append(f"timeline: 商品{a.get('product')}が{b['t_start']}秒で出直す。同じ商品は1レイヤーにして move で動かす")
        # 参考に無い冒頭テロップを強制追加しない。観察と売るための変更は差分に記録。
        if dur and good:
            for s in range(int(dur)):
                if not any(ev['t_start'] <= s + .5 < ev['t_end'] for ev in good): e.append(f'{s}〜{s+1}秒に何も映らない区間がある')
            if 'video-end' in cta and not any(ev.get('style') == 'cta' and ev['t_end'] >= dur - 1e-6 and ev['t_start'] <= dur - 1 for ev in good):
                e.append('動画の最後1秒に CTA の文字が無い')
            if 'video-opening' in cta and not any(ev.get('style') == 'cta' and ev['t_start'] < 3 for ev in good):
                e.append('冒頭3秒以内に CTA の文字が無い')
    d = card.get('differences') or {}
    if not isinstance(d.get('intentional'), list) or not isinstance(d.get('unreproduced'), list):
        e.append('differences.intentional / unreproduced: 配列（無ければ[]）')
    return e


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('card'); a = ap.parse_args()
    card = load(a.card); errs = validate_card(card)
    print(json.dumps({'card': a.card, 'is_example': bool(card.get('is_example')), 'errors': errs}, ensure_ascii=False, indent=2))
    raise SystemExit(bool(errs))
