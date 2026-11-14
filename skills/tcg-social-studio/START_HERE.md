# 最初に読む

トレカ海外販売の毎日の投稿を、投稿の直前まで自動で作るスキルです（4.2.3）。
このページは**初回に1度だけ**行う準備です。2日目からは `SKILL.md` だけで進みます。

## 1. 渡す人がすること

### スプレッドシートを用意する

相手ごとに1つ、**ひな形をコピーして**作ります。ひな形には、5つのタブ（投稿／素材／参考帳／商品の候補／数値の記録）、見出し、選択式、チェックボックス、手本60件（参考帳）が入っています。

ひな形：https://docs.google.com/spreadsheets/d/19XXnnN8qqeR9QfVx0vm2pTFGMYACJrmC0l2njbYKO2M/edit

1. ひな形を開き、「ファイル」→「コピーを作成」を選ぶ。名前は `日付 相手の名前 TCG投稿づくり 運用表` にする。
2. コピーしてできた表の「共有」で、このスキルを動かすAIのGoogleアカウントを「編集者」で追加する。
3. コピーしてできた表のアドレスを、`client.json` の `sheet_url` に書く。

- **ひな形そのものは使わない。** `sheet_url` に書くのは、必ずコピーした表のアドレス。ひな形には何も書き込まない。
- ひな形が開けないときだけ、`sheets-template/` の5つのCSVを同じ名前のタブの1行目に貼って作る（`reference_library.csv` を「参考帳」タブに貼ると手本60件が入る。「投稿」タブのA列はチェックボックスにする）。
- 列の意味は [表の書き方](references/sheet.md)。

### 共有フォルダを用意する

Googleドライブにフォルダを1つ作り、「リンクを知っている全員が閲覧できる」設定にして、スキルを動かすAIのアカウントを「編集者」で追加します。完成物の置き場と、表の「見た目」に画像を出すために使います。アドレスを `client.json` の `share_folder_url` に書きます。

### client.json を書く

相手ごとに変えるのは [client.json](client.json) の1枚だけです。

| 欄 | 書くもの | 必須 |
|---|---|---|
| `client_name` | 相手の名前（フォルダの見出しに使う） | 必須 |
| `shop_name_en` | 投稿に出す英語の店名 | 必須 |
| `instagram_handle` | 投稿先のInstagramのアカウント名（@から） | 必須 |
| `facebook_page` | Facebookページの名前。使わなければ空 | |
| `sheet_url` | ひな形をコピーして作った、その相手専用のスプレッドシートのアドレス | 必須 |
| `output_folder` | 完成物を保存するPC上のフォルダ | 必須 |
| `share_folder_url` | 表に画像を出し、完成物を開くための共有フォルダのアドレス（Googleドライブなど） | 必須 |
| `target_market` / `post_language` | 売る国と投稿の言語。変えなければ US / en | |
| `platforms` | 本文を作る媒体 | |
| `daily_set` | 毎日作る3案の形式。変えなければ リール・カルーセル・画像 | |
| `create_time` | 毎日3案を作り始める時刻（日本時間）。変えなければ 6時 | |
| `post_times` | 表を見て投稿する時刻（日本時間）。1回につき1本出す。変えなければ 8時・12時・21時 | |
| `contact` | 問い合わせの受け口。DMなら `"type": "dm"`、商品ページへ送るなら `"type": "link"` と `link_url` | 必須 |
| `closing` | 毎回同じにする締め。`handle_text` は最後に出すアカウント名、`logo_file` はロゴ画像の場所（無ければ空） | `handle_text` 必須 |
| `reference_accounts` | 新しい手本を毎日探しに行くアカウント。はじめから9件入っている | |
| `do_not` | その相手で避けること（例：「自分の売値を書かない」） | |

商品の種類・合言葉・色は書きません。毎回スキルが決めて、表のその行に残します。

## 2. 受け取ったAIがすること：PCの準備（初回だけ）

スキルのフォルダで実行します。

```powershell
python -m pip install -r requirements.txt
python -m pip install -r requirements-analysis.txt
npm install
node scripts/check_env.mjs
```

`check_env.mjs` がすべて `[OK]` になれば準備完了です。`[ERROR]` が出た行だけ直します。

- ブラウザーは、PCに入っている Chrome か Edge をそのまま使います。どちらも無いときだけ `npx playwright-core install chromium` を実行します。
- 書体（`fonts/`）と効果音（`se-pack/`）は同梱済みです。

## 3. 効果音の扱い

`se-pack/` の音は動画の中で使うためのものです。音のファイルだけを第三者へ配ったり、公開の場所へ置いたりしません。
OtoLogic の音を使った投稿には、本文の最後に次のクレジットを入れます（`mix_audio.py` が必要なときに知らせます）。

```text
効果音: OtoLogic（https://otologic.jp）/ CC BY 4.0
```

## 4. 動くことを確かめる

同梱の実例で、コマ撮りから完成MP4、表に貼る画像までを1度通します。出力先は好きな新しいフォルダにしてください。

```powershell
node scripts/capture_frames.mjs templates/reel-example/index.html --out <新しいフォルダ>/frames --duration 13
python scripts/mix_audio.py templates/reel-example/cues.json --out <新しいフォルダ>/audio.wav
node scripts/finish_video.mjs --frames <新しいフォルダ>/frames --audio <新しいフォルダ>/audio.wav --out <新しいフォルダ>/reel_test.mp4 --checks <新しいフォルダ>/checks
python scripts/make_preview.py <新しいフォルダ>/reel_test.mp4 --out <新しいフォルダ>/preview.jpg
```

MP4が再生でき、音が入っていれば、そのPCで制作できます。この実例は道具の確認用で、投稿には使いません。

## 5. 毎日の動かし方

定期実行に、次の2つを登録します。登録した後は、頼まなくても毎日動きます。

| 登録するもの | いつ | 起きること |
|---|---|---|
| 「今日の投稿を作って」 | 毎日1回、`create_time` の時刻 | 商品を調べ、3案を作り、表の「投稿」タブに3行書く |
| 「表を見て、チェックした投稿を出して」 | `post_times` の各時刻 | 「投稿OK」にチェックが付いた行を1本投稿し、結果を表に書く |

人がするのは、表の「投稿」タブで、出したい案の「投稿OK」にチェックを入れることだけです。**チェックを入れると、次の投稿時刻に自動で投稿されます。** 出したくない案は、チェックを入れずにそのままにします。
