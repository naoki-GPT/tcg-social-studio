# 既存の制作プログラムを使う

ルートのREADME.mdで依存部品を準備してから使います。以下のPythonは必要部品を入れた環境のものを指定します。命令は `skills/tcg-social-studio/` を作業場所とする例です。

## 入力を作る

1. `templates/reference-breakdown.example.json` を使い、参考の全枚／全編の観察を記録。
2. 静止画なら `templates/recipe-card.example.slideshow.json`、動画なら `templates/recipe-card.example.video.json` を案件の参考に合わせて編集。
3. `templates/recipe-content.example.json` に、確定した文字とローカルの商品画像を指定。

これらは架空の検証例です。そのまま広告へ使わず、商品や文、書体、配置、時刻を実際の確認結果で置き換えます。`recipe-card.json`、`content.json` と素材をルート直下の `runs/trial-001/` に置いた例を示します。

```powershell
python scripts/recipe_card.py ../../runs/trial-001/recipe-card.json
python scripts/build_from_recipe.py --card ../../runs/trial-001/recipe-card.json --content ../../runs/trial-001/content.json --out ../../runs/trial-001/production
```

## 出力する

静止画／カルーセル：

```powershell
node scripts/export_slides.mjs ../../runs/trial-001/production/index.html --out ../../runs/trial-001/slides-v1 --ratio 4:5
```

静止画像＋HTMLによる無音動画：

```powershell
node scripts/render.mjs ../../runs/trial-001/production/index.html --out ../../runs/trial-001/reel-v1.mp4 --width 1080 --height 1920 --fps 30 --workers 2
```

寸法・尺・fpsは今回の参考仕様に合わせます。既存出力の上書きを避け、修正時はv2等へ変えます。原画像や動画・音を生成したという意味のコマンドではありません。音や実映像を含む企画には別の編集経路が必要です。

## 検品する

`scripts/verify_video.mjs` でMP4の技術条件を確認し、`scripts/compare_reference.py` で全枚・同時刻の比較資料を作ります。使い方は `--help` と [recipe-cards.md](../skills/tcg-social-studio/references/recipe-cards.md) を確認してください。

`production-contract.json` は生成直後には未完成です。実際の需要・導線・原素材・比較結果を記入して、次の検査を通します。

```powershell
python scripts/validate_production.py ../../runs/trial-001/production/production-contract.json --out ../../runs/trial-001/checks/acceptance.json
```

検査が通っても、完成画像・動画・本文を実際に開き、元参考との一致と買う理由を確認します。承認待ちへ渡す版と実際に検品した版を同じにします。

## 同梱されない接続

画像生成サービス、素材取得サービス、MuseからのCodex呼び出し、管理表への書き込み、SNS投稿は、今後の連携実装の範囲です。ここに書いた制作コマンドはそれらを自動実行しません。
