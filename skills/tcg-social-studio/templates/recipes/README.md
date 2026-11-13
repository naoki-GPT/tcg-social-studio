# 参考専用HTMLの約束

版2.0。Grokbot版1.9の参考別テンプレート選択を引き継ぐ。

`templates/recipes/<ref_id>/index.html` があれば `build_from_recipe.py` が選ぶ。IDは英数字・ハイフン・下線のみ。参考の実物、分解表、全ページ・全編の比較が根拠。HTMLがあるだけで再現済みとはしない。

- `recipe.js` の `window.RECIPE` と `content.js` の `window.CONTENT` を読む。
- `window.STORY` に `ratio,width,height,draft`、`window.__dur` に秒数を出す。
- `window.__sceneStarts` に全スライドの開始秒、`window.__seek(t)` に決定的な時刻指定描画を実装。
- `window.__check()` は空欄・仮文・画像欠損・文字溢れ等のエラー配列を返す。
- 実映像・音声はこのHTMLコマ撮り機構で同期しない。動画編集・FFmpeg等で別々のトラックを組み、全編検査する。
- 特殊な効果は近いプリセットで完成扱いにせず、専用実装または動画編集へ移る。近似書体、未再現効果、素材置換は差分へ残す。

元の静止画が1088×1344なら `canvas.ratio:"custom",width:1088,height:1344` として保持できる。出力にも同じ `--ratio custom --width 1088 --height 1344` を指定する。配信面に合わせて寸法を変える場合は理由と比較を記録する。

## REF-005専用データ

[実測カード](REF-005/recipe-card.measured.json)を入口にする。content.jsonにはproductsとtextsに加えて、元の9枚に対応するcomparisonsを9行指定する。各行は `product, description, number, before, after, before_label, after_label, before_date, after_date, basis, method, price_basis, axis`。brand/siteは自社の確認済み表記。before/afterは同一通貨・同一商品条件の数値、labelは通貨付き表示。`price_basis:"completed_sale", axis:"same_item_time"` が必要。出品価格や日英比較へ固定ラベルのまま流用しない。

架空値での試作を実相場として出さない。原書体・背景模様が近似という差分は、比較で解消するまで残す。
