# 全参考を実装する作り方カード

版2.0。Grokbot版1.9の「参考ごとのJSON → 専用HTML選択」を取り込んだ。例カードは実在参考の分析ではない。`is_example:true` を完成判定へ使わない。

## 作成と出力

1. [分解表](../templates/reference-breakdown.example.json)に全ページ・全編の文字、寸法、フレーム、置換内容を確定する。
2. 静止画は[カード例](../templates/recipe-card.example.slideshow.json)、動画は[カード例](../templates/recipe-card.example.video.json)を参考ごとに書き換える。画面の文と商品画像は[content例](../templates/recipe-content.example.json)へ。
3. `python scripts/recipe_card.py recipe-card.json` で記入漏れを確認。
4. `python scripts/build_from_recipe.py --card recipe-card.json --content content.json --out production` で編集用フォルダを生成。未記入の `production-contract.json` も作る。完成判定は自動で付けない。
5. `node scripts/export_slides.mjs production/index.html --out production/slides --ratio 4:5`。原寸を保持する場合は `--ratio custom --width 1088 --height 1344` 等を指定。動画は `render.mjs` に元の寸法・fpsを指定する。

## 値の意味

- `canvas.ratio`: 4:5 / 9:16 / custom。customはwidth/heightも必要。元参考の縦横比を勝手に変えない。
- `reference`: 台帳ID・元URL・確認日・確認範囲。`ref_id` は英数字・下線・ハイフンのみ。
- `palette/background/typography/outline/product/text_zones`: 色、背景、書体、縁取り、商品面積、座標。座標は0〜1、文字はpx。書体のexactは同一と確認したときだけ。approxは未解決差分を記録。
- `slides`: 元の全枚数と順序。各枚の役割とレイヤー。原参考に締めのCTA画像が無い場合、勝手に1枚増やさない。
- `timeline`: `t_start,t_end`は秒。分解表のフレーム/fpsから計算し、終端は含めない。字幕と商品を独立したレイヤーにする。
- `keyframes`: 各レイヤーの開始を0秒とする `at,x_px,y_px,scale,rotation,opacity,easing` の列。全値を明記。linear/ease-out/ease-in-outに対応。未対応の補間・曲線・特殊効果は専用実装へ。
- `reference_cut:true` と `observed` がある場合のみ、同一商品への実在カットを許す。単なる字幕変更のリセットは不合格。
- `cta_placement`: 元の画面を保持したまま本文へ導線を置く場合はcaption。last-slide/video-end/video-openingを指定したときは、その位置にCTAが必要。
- `differences.intentional/unreproduced`: 自社素材への置換と、未解決の再現不足を分ける。近いプリセットは未解決差分を消す根拠ではない。

## 実装範囲

共通HTMLが扱うのは、画像・文字・図形・基本効果・明示キーフレーム。文字溢れは停止し、書体サイズを勝手に縮めない。複雑な背景・音・実映像・粒子・3D等の完全な代替ではない。

表現できない見た目は[参考専用HTML](../templates/recipes/README.md)または動画編集環境へ。REF-005専用HTMLは実測配置の出発点として同梱し、書体・背景アイコンは近似と明記している。9枚すべての対応と比較が完了するまで忠実再現の完成にしない。

`compare_reference.py slides --ref reference --ours production/slides --out production/compare` は枚数不一致で停止する。動画は `video --ref reference.mp4 --ours production.mp4 --fps 30 --boundaries reference-breakdown.json --out compare`。fpsは実ファイルのCFRを確認して指定。VFRはPTSを扱う編集環境で同期比較する。比較画像を生成しただけでは合格ではない。
