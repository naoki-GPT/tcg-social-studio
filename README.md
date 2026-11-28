# TCG Social Studio

トレカ海外販売の毎日のInstagram・Facebook投稿を作って出すためのスキルです（5.3.0）。

> **移行済み・旧版（2026-11-28）**：このスキルは新しいスキル一式（企画 tcg-neta-planning／制作 tcg-post-production／分析 tcg-analysis）へ移行しました。今後はこのスキルでは制作しません。価格・文章、運用表、検品、投稿、素材の取得先、型カード、効果音、フォント、スクリプト、client.json の部品は制作スキル側へ移し済みで、毎朝の制作ジョブと自動投稿ジョブも新しいスキル一式へ組み替え済みです。このリポジトリは、過去の投稿・記録との照合用として残します。新しいスキル一式は naoki-bot-ops の projects/tcg/instagram/ にあります。

2026-11-14に、このリポジトリの中身を新しい版へ全面的に置き換えました。以前の引き継ぎ資料・試作の記録・前提確認のスキルは外してあります（Gitの履歴には残っています）。

## 読む順番

1. [skills/tcg-social-studio/START_HERE.md](skills/tcg-social-studio/START_HERE.md) — 初回に1度だけ行う準備
2. [skills/tcg-social-studio/SKILL.md](skills/tcg-social-studio/SKILL.md) — 毎日の流れ（本体）
3. [skills/tcg-social-studio/CHANGES.md](skills/tcg-social-studio/CHANGES.md) — 変えたことの一覧

## 何をするスキルか

| いつ | すること |
|---|---|
| 毎日1回（`client.json` の `create_time`） | その日の動きを調べてネタを出し、選ばれた案（リール・カルーセル・画像）を作り、スプレッドシートの「投稿」タブに書く。`client.json` の `plan_approval` が `off` なら、聞かずに3案を作る |
| `client.json` の `post_times` の各時刻 | 表を見て、「投稿OK」にチェックが付いた行を1本投稿し、結果を表に書く |

人がするのは、表で出したい案の「投稿OK」にチェックを入れることだけです。チェックは投稿の許可として扱います。

## 相手ごとに変える場所

[skills/tcg-social-studio/client.json](skills/tcg-social-studio/client.json) の1枚だけです。店名、アカウント、スプレッドシートのアドレス、保存先、作る時刻と投稿の時刻を書きます。

## 参考投稿の原本

[reference-originals/](reference-originals/) に、手本にする参考投稿の原本37件（全ページ・全編）があります。参考IDごとのフォルダに分かれています。作るときは、まずここの原本を測ります。配布用のZipには入れていません。
