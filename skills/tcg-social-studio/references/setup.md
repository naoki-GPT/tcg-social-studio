# 利用環境と準備

ここからの操作はAIが担当する。パスは受け取った環境の実際の場所へ置き換える。作成者のPC、社内資料、別チャット、認証情報は不要。

## 初回の引き継ぎ（利用するAI環境で共通）

利用者向け入口は[START_HERE.md](../START_HERE.md)。AI側でフォルダの読み取り・新しい作業ファイルの保存・コマンド実行可否を確認する。利用者に使えない機能名や未確認の画面操作を案内しない。接続済み機能があれば再設定させず、APIキーをチャットや事業情報へ書かせない。必要な認証は利用環境の接続設定・秘密情報の管理機能を使う。

事業情報の雛形を利用者の制作場所へコピーして既知の条件を記録し、同じ場所に制作履歴の入口を残す。既存の履歴があればそちらを使う。初回で履歴がなければ制作後に企画ID・対象客・商品識別情報・訴求・型・参考区分・採用版・制作日・公開状態を記録する。別案件の顧客情報・予算・ログイン・公開承認を引き継がない。

初回準備の完了は、ファイル操作、必要な実行環境、素材・調査接続の利用可否と未確認事項を分けて報告する。接続の確認だけで外部取得・有料生成を実行しない。利用者が制作を依頼したらまず1本を完成させ、完成MP4の再生・英日本文・出力場所を確認して、その端末での制作確認とする。

## あるものを先に確認

Muse側で使える公開情報調査、ローカル素材、Python 3.10以上、Node.js 22以上、画像生成の利用可否を確認する。画像生成がない場合は取得画像とHTMLで作れる範囲を進め、不足を記録する。画像生成APIキーを標準で要求しない。外部収集サービスの契約は不要。ローカルブラウザは制作したHTMLの描画・検査に使う。

この配布物にはWeb取得補助、集計、画像の付加情報除去、HTML→MP4、動画検査がある。AI画像生成の契約・認証そのものは含まない。素材は[受け渡し手順](media-input.md)で取り込む。

## 同梱の動画道具を使う場合

スキルフォルダを作業場所にする。利用者の環境に必要部品がなければ次を実行する。インストール・ネット接続・ファイル書込みの権限は環境の通常手順に従う。

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
npm install
npx playwright-core install chromium
node scripts/check_env.mjs
```

macOS/LinuxではPythonを `python3`、仮想環境のPythonを `.venv/bin/python` に読み替える。LinuxでブラウザのOS部品が足りない場合はPlaywrightの公式診断に従い、管理者操作を無断で行わない。

Nodeの部品はpackage.jsonのバージョンを使用し、他の作業環境を勝手に更新しない。Playwright・ffmpegのコード／バイナリはZIPへ入れず、npm経由で各配布元から準備する。各ソフトウェアの利用条件は依存パッケージに従う。特定のサービスの利用料金を無料と保証しない。

既存ブラウザを使う場合は `CHROME_PATH` にその実行ファイルの絶対パスを設定可能。`FFMPEG_PATH` で既存ffmpegも指定可能。診断専用に `TCG_NODE_MODULES` で既存のNode部品フォルダを指定できるが、配布物に個人のパスを書かない。

## 制作フォルダを作る

`templates/reel/` を新しい制作先へコピー。`content.js` の素材・店名・文を編集する。画像は `assets/` へ実際に取得し、画像URLをHTMLから直接参照しない。`content.js` の空の素材リストは設定前を示す。何も設定せずに動画完成とは扱わない。

19型から始める場合は [story-template.md](story-template.md) の作成コマンドを使う。カルーセルの画像は `export_slides.mjs`、縦動画は既存の `render.mjs`。既存の一覧→選択演出も引き続き使える。

```powershell
node scripts/inspect.mjs "../制作物/index.html" --out "../制作物/checks/layout"
node scripts/render.mjs "../制作物/index.html" --out "../制作物/reel_v1.mp4" --width 1080 --height 1920 --fps 30 --workers 2
node scripts/verify_video.mjs "../制作物/reel_v1.mp4" --out "../制作物/checks/video" --duration 24
python scripts/contact_sheet.py "../制作物/checks/video" --out "../制作物/contact_sheet.jpg" --cover "../制作物/cover.jpg"
```

尺24秒は同梱例。今回の尺に合わせる。検査・動画・画像の出力先は新しい名前を使い、既存版を上書きしない。見直し後はv番号を上げる。`inspect.mjs` は構図の画像を生成するため、スキルのインストール確認だけでは実行しない。

ブラウザへの接続やファイル実行が制限されたら、エラーを残し通常の許可手順に従う。別の接続経路で制限を迂回しない。ネットや画像生成が利用不可でも、集計・原稿・手元で実行可能な制作は進める。

## オフラインの配布確認

```powershell
python scripts/test_tools.py
python scripts/test_formats.py
node --test scripts/runtime.test.mjs
node scripts/check_env.mjs
```

テストはローカルの架空データのみ。新規の競合取得、画像生成、本編動画の書き出しは行わない。ブラウザやffmpegの準備状態が不明なら、テスト成功と動画制作可能を混同しない。

ブラウザ準備後は `node --test scripts/template.test.mjs` で架空カード3枚・9枚の素材差し替え、場面の切替、時刻を戻した画面の一致も確認できる。一時フォルダの架空SVGだけを使用し、本編MP4や外部への通信は作らない。

`node --test scripts/story.test.mjs` は19型×画像・動画比率を架空素材で点検する。実商品・最新価格・AI生成・公開の確認ではない。
