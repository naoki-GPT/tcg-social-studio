# TCG Social Studio

トレカ販売向けの画像・カルーセル・動画を作るスキルと制作プログラム。Museで今後の設計・改善を進めるための、2026-11-13時点の引き継ぎリポジトリです。

**Museは最初に [MUSE_START_HERE.md](MUSE_START_HERE.md) と [AGENTS.md](AGENTS.md) を読んでください。** 制作プログラムは取り込み済みですが、Museとの連携・管理表への反映・承認・投稿の自動化は未実装です。作成者だけが使う収集サービスの専用コードと手順は削除しました。素材はMuse側から受け取ります。

## 入っているもの

| 場所 | 内容・状態 |
|---|---|
| [skills/tcg-social-studio](skills/tcg-social-studio/SKILL.md) | 原本を基にした配布版2.2.0。制作・書き出し・比較検品、ローカル素材の取り込み |
| [skills/tcg-social-intake](skills/tcg-social-intake/SKILL.md) | 第1工程の前提確認1.0.0。記録形式と検査5ファイル |
| [experiments/stage2](experiments/stage2/README.md) | 停止時点の第2工程案5ファイル。未完成・通常実行対象外 |
| [docs/MUSE_WORKFLOW.md](docs/MUSE_WORKFLOW.md) | MuseとCodexの役割、受け渡す資料、承認と投稿の設計案 |
| [docs/COMMON_TRIAL_BRIEF.md](docs/COMMON_TRIAL_BRIEF.md) | 共通試作で既に決まった条件と、調査開始用の仮案 |
| [docs/REFERENCE_ASSETS.md](docs/REFERENCE_ASSETS.md) | 別配布の参考原本ZIP（画像27枚・動画5本・本文12件）の内容と検証結果 |
| [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) | 引き継ぐ問題と改善の完了条件 |
| [docs/PACKAGE_MANIFEST.json](docs/PACKAGE_MANIFEST.json) | 配布版の各ファイルのSHA256。受け渡し時の一致を確認する記録 |
| [docs/VALIDATION.md](docs/VALIDATION.md) | 今回実行した検査と、実行していない検査 |

`skills/` は元の制作プログラムを基に、外部収集サービスへの依存を削除した配布版です。参照素材はMuseからローカルファイルで受け取ります。元のPCにあるスキルは変更しておらず、このGitHubリポジトリと自動同期されません。

## 動作環境

- Python 3.10以上。通常の画像処理はPillow・requests、動画解析を使う場合はOpenCV・NumPy。
- Node.js 22以上。HTMLの画像／無音動画出力はPlaywrightとffmpegを使用。
- 商品画像・参考の全画像／全動画は案件ごとに用意。取得済みファイルや通常の公開情報取得を優先します。
- AI画像生成はMuse／Codex側で実際に使える機能を接続します。このリポジトリに画像生成サービスの認証・モデル利用権・API呼び出しの共通アダプターは含みません。既存の希望はgpt-image-2で、使えたモデルと代替の有無を記録します。

## 最初の確認

リポジトリのルートで実行します。以下はWindows PowerShellの例です。

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r skills/tcg-social-studio/requirements.txt
.venv/Scripts/python scripts/verify.py --check-snapshot
```

macOS/Linuxでは `.venv/Scripts/python` を `.venv/bin/python` に置き換えます。検査の実行はPython・JSON構文、配布時点のファイル一致、既存のPythonテスト、Node.jsのブラウザ不要テストです。市場調査・有料生成・投稿は実行しません。改修後は配布時点との差が生じるため `--check-snapshot` を外して検査します。

HTML出力を使う準備は、次のとおりです。これは外部サイトを操作するブラウザー自動化ではなく、ローカルHTMLの描画用です。

```powershell
cd skills/tcg-social-studio
npm ci
npx playwright-core install chromium
node scripts/check_env.mjs
```

既存のChromiumやffmpegを使う設定、Linuxの追加OS部品については [setup.md](skills/tcg-social-studio/references/setup.md) を確認してください。ネット接続・部品のインストール可否は利用環境で確認します。

動画のカット解析を使うときだけ、ルートから次を実行します。

```powershell
.venv/Scripts/python -m pip install -r skills/tcg-social-studio/requirements-analysis.txt
```

制作の実行例と入力ファイルの意味は [制作の使い方](docs/PRODUCTION_GUIDE.md) にあります。既存の例は架空の検証データで、需要の裏付けや公開できる広告ではありません。

## 保存と運用

案件ごとの素材・入力・完成物・根拠は `runs/<案件ID>/` など、Git管理外の制作場所へ保存します。ソース変更だけをコミットし、認証情報・顧客資料・管理スプシのコピー・取得した参考原本は同梱しません。大きな完成メディアは別の承認済み保存先を使い、保存場所と版・ハッシュを制作記録へ残します。

今後の変更はこのリポジトリで行い、Museが改善内容と検査結果を残します。投稿の承認とコード変更の承認は別です。GitHubへのプッシュはSNS投稿の許可にはなりません。
