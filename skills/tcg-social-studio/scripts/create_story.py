"""v1.3: 編集用雛形と再現範囲の未確認記録を作る。見た目と動きを参考と照合する。"""
import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def create(format_id, out, ratio='4:5'):
    formats = json.loads((ROOT/'templates/formats.json').read_text(encoding='utf-8'))['formats']
    recipe = next((f for f in formats if f['id'] == format_id), None)
    if recipe is None:
        raise ValueError('Unknown format: ' + format_id)
    if ratio not in ('4:5', '9:16'):
        raise ValueError('Ratio must be 4:5 or 9:16')
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    scenes = []
    for layout, heading, purpose in recipe['scenes']:
        count = {'hero':1, 'grid':3, 'compare':2, 'table':3, 'steps':3, 'cta':0}[layout]
        scenes.append({'layout':layout, 'seconds':4, 'heading':heading, 'subheading':'EDIT: '+purpose,
                       'note':'', 'source':'',
                       'items':[{'label':'EDIT: 商品または項目', 'value':'EDIT: 確認済みの情報', 'image':''} for _ in range(count)]})
    story = {'draft':True, 'format':format_id, 'ratio':ratio, 'brand':'YOUR SHOP',
             'showAnnotations':False,
             'evidence':{'sources':[], 'checked_at':'', 'price_basis':'', 'shipping_basis':''},
             'scenes':scenes}
    shutil.copyfile(ROOT/'templates/story/index.html', out/'index.html')
    shutil.copyfile(ROOT/'templates/reference-design.example.json', out/'reference-design.json')
    shutil.copyfile(ROOT/'templates/production-contract.example.json', out/'production-contract.json')
    (out/'content.js').write_text('window.STORY = '+json.dumps(story, ensure_ascii=False, indent=2)+';\n', encoding='utf-8')
    (out/'BRIEF.md').write_text('# '+recipe['name']+'\n\nこれは編集用雛形です。完成投稿ではありません。\n\n'
        +'必要な情報：'+recipe['inputs']+'\n\n注意：'+recipe['caution']+'\n\n'
        +'参考ID：'+', '.join(recipe['reference'])+'\n\n'
        +'reference-design.jsonに実見した参考・構図・変更理由を記録する。共通HTMLは完成デザインではない。参考に合わせて配置・文字量・場面尺・動きを編集し、参考と代表画面を並べて確認する。\n\n'
        +'忠実な再現指定では、fidelityに配色・背景・書体・縁取り・商品比率・演出の観察時刻も残す。抜粋画像しかない動きを確認済みにせず、完成MP4の中盤と切替も検査する。\n\n'
        +'この汎用ひな形は試作専用。忠実再現は全参考からrecipe-cardを作りbuild_from_recipe.pyを使う。参考に実在するカットは観察時刻を記録して再現し、参考にない商品リセットは入れない。\n\n'
        +'content.jsに素材・画面文・価格・日時を入れる。EDIT:を全て解消し、原本と参考デザインを照合してからdraftをfalseにする。'
        +'不足する価格や在庫を架空の値で埋めない。英語・日本語の投稿本文と出典記録も完成させる。\n', encoding='utf-8')
    return story


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('format'); parser.add_argument('--out', required=True)
    parser.add_argument('--ratio', choices=['4:5','9:16'], default='4:5')
    args = parser.parse_args(); create(args.format, args.out, args.ratio)
    print('[OK] Editable draft created; populate verified content before delivery')
