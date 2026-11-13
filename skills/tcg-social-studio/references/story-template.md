# 19型の画像・スライド・動画を作る

版2.0追記：需要・導線・全参考の再現はSKILL.mdと[全参考仕様](reference-reproduction.md)を優先する。以下の旧テンプレートの秒数や先頭画像の観察範囲は、今回の完成仕様ではない。2026-11-12の再確認は[実物の索引](verified-reference-map.md)を参照。
v1.2.0。これはAIが使う編集手順。利用者へコード入力を要求するマニュアルではない。利用環境は [setup.md](setup.md)。共通HTMLは動作確認用の出発点で、完成デザインではない。先に [参考との対応](reference-design.md) を設計し、必要ならHTMLの配置自体を変える。

```powershell
python scripts/create_story.py comparison-slideshow --out "../制作物/比較01" --ratio 4:5
```

型IDは [formats.json](../templates/formats.json)。新規フォルダへ `index.html`、`content.js`、`BRIEF.md` ができる。既存のフォルダは上書きしない。

1. BRIEFに今回の目的、参考ID・URL、確認範囲、商品・出典・次の行動を記入。
2. `content.js` の `EDIT:` を今回の英語へ置換し、商品原画像のローカル相対パスを `items[].image` に設定する。ファイルは制作フォルダ内 `assets/` 等へ。商品がない場所に架空カードを生成しない。
3. 各場面の `layout` は hero（商品主役）、grid（一覧）、compare（左右比較）、table（条件表）、steps（番号付き手順）、cta（次の行動）。`heading`・`subheading`・`items` を編集する。AI背景を使うときは取得済み背景をHTMLの背景へ設定し、可読性を実画面で確認する。
4. 比較は左右に商品名と言語、価格＋通貨＋価格種別。出典・確認日時・送料の扱いは`evidence`と比較記録へ保持する。`note`・`source`は通常空欄、`showAnnotations:false`が既定。個別の表示依頼がある場合だけtrueにし、本文へも注釈を自動転記しない。`compare_prices.py` の結果を照合して表示する。表紙と各比較画像に食い違いがないか点検する。
5. `comparison-slideshow` は商品数に合わせてcompare場面を複製／削減。1画面1商品で同じ左右配置を保つ。1枚だけの画像依頼なら完成した比較場面だけを書き出す。無関係なCTA枚数を増やさない。
6. 商品・金額・日時・原稿と、参考との目視照合後に `draft:false`。文字や色を差し替えただけで完成にしない。下の検査はデザイン一致や出典を検証する機能ではなく、空欄・画像欠損・文字あふれを見つける補助。

全画像の書き出し：

```powershell
node scripts/export_slides.mjs "../制作物/比較01/index.html" --out "../制作物/比較01/slides_v1" --ratio 4:5
```

1080×1350のPNG連番。画像を開いてチェック後、必要に応じ同梱の `clean_metadata.py` でJPEGへ。1つの型でも商品数・文字量で調整が必要。小さく詰め込まず、場面分割や短文化で読みやすくする。

動画は同じ原稿・素材から別の制作フォルダを作り、`ratio:9:16` にする。各 `seconds` は1〜30秒、初期4秒。読み切れる秒数へ調整。1080×1920で全場面を検査してから既存レンダラーを使う。

```powershell
node scripts/export_slides.mjs "../制作物/比較動画/index.html" --out "../制作物/比較動画/checks_v1" --ratio 9:16
node scripts/render.mjs "../制作物/比較動画/index.html" --out "../制作物/比較動画/reel_v1.mp4" --width 1080 --height 1920
```

その後 `verify_video.mjs` で実MP4を検査する。静止画を出せたことをMP4完成としない。商品写真と確定数字の切替動画であり、実物が動く映像の生成ではない。実物動画や音声を入れるときは適した動画編集環境を使用する。

英語本文・日本語訳・参考・素材と価格の出典・検品記録・review.htmlも一緒に渡す。スキル整備時の架空素材テストと、実投稿の完成・公開を分ける。
