# 止まったときの早見表

人に聞く前に、ここの対処を上から試す。直ったら、そのまま制作を続ける。

| 起きたこと | 表示の例 | 対処 |
|---|---|---|
| ブラウザーが無い | `[ERROR] browser: No browser could be started` | スキルのフォルダで `npm run browser` を実行する。試験用のChromeが `.browsers/` に入り、次からは自動で使われる。別の場所のChromeを使うときは、環境変数 `CHROME_PATH` にその実行ファイルの場所を入れる。 |
| ブラウザーのダウンロードに失敗する | `Error: Download failure, code=1` | もう1度 `npm run browser` を実行する。それでも失敗するなら、PCに入っているChromeかEdgeの実行ファイルの場所を `CHROME_PATH` に入れる。 |
| Pythonの部品を入れられない | `error: externally-managed-environment` | PC全体には入れず、スキルのフォルダに専用の環境を作る。手順は [START_HERE.md](../START_HERE.md) の「2. PCの準備」。以後、`python` の代わりに専用の環境の中のPythonを使う。 |
| 分析の道具が動かない | `ModuleNotFoundError: No module named 'cv2'` | 専用の環境のPythonで `-m pip install -r requirements-analysis.txt` を実行し、同じPythonで道具を動かす。 |
| 設定が足りない | `[ERROR] sheet_url: empty` など | `node scripts/check_client.mjs` が出した欄を `client.json` に書く。書き方は `client.example.json`。 |
| 表がひな形のまま | `[ERROR] sheet_url: this is the template sheet itself` | ひな形を開き、「ファイル」→「コピーを作成」で作った表のアドレスを `sheet_url` に書く。ひな形には書き込まない。 |
| 参考投稿を保存できない | 文章は読めるが、画像や動画のファイルが手に入らない | [素材を取ってくる](assets.md) の「開けない・保存できないとき」のとおりに進む。保存を試さずに先へ進まない。 |
| 表の「見た目」に画像が出ない | 欄が空、またはエラー表示 | 画像を置いたフォルダが「リンクを知っている全員が閲覧できる」になっているかを確かめる。直らなければ、欄にどんな画像かを10字ほどで書く（[表の書き方](sheet.md)）。 |
