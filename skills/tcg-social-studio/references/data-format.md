# 保存データの形式

## アカウント・投稿

accounts.jsonにID、URL、立場、対象客、選定理由、プロフィール文、誘導先URL、販売商品、注文方法、取得日時、画面確認範囲、取得状態を保存。未確認はnullまたは説明付きの不明。

`scripts/analyze_posts.py` の入力は次の形。取得元固有の項目からAIが対応を判断して正規化する。数値がない項目を0にしない。

```json
{
  "window": {"start":"2026-07-29","end":"2026-10-26"},
  "min_age_days":7,
  "rows":[
    {
      "account":"example-shop",
      "post_id":"example-post",
      "url":"https://www.instagram.com/p/example/",
      "published_at":"2026-10-01T10:00:00+00:00",
      "observed_at":"2026-10-27T09:00:00+09:00",
      "format":"reel",
      "metric_name":"videoPlayCount",
      "metric_value":1200,
      "pinned":false,
      "promotion":false,
      "giveaway":false,
      "observation_scope":"全編視聴",
      "source_file":"sources/example.json"
    }
  ]
}
```

日付例は今回の調査期間へ変える。形式、指標定義、固定・広告・抽選の状態が不明ならnull。集計器は不明フラグを通常例の比較群へ入れず、別の未確認群として件数を残す。これは不明な投稿を分析から捨てる意味でない。人が実画面を見て補える。

出力は条件付きの中央値・最大値・比較対象数・実際の投稿日範囲・観測日範囲、除外理由。全ての投稿が除外されてもgroupの中央値はnullとする。URLがあれば数値の実測が確認済み、という意味ではない。

## 素材表

assets_manifest.jsonの各行：`id`, `type`（external/owner/ai/composite）, `product`, `number`, `language`, `set`, `quantity`, `page_url`, `image_url`, `observed_at`, `local_path`, `sha256`, `usage_status`（reference/prototype/public-ready）, `usage_basis`, `scene`, `identity_check`。

AIには `prompt_file`, `reference_ids`, `tool`, `confirmed_model_id`（不明ならnull）、合成には原素材IDも残す。集計された人気順位は素材の使用許諾を示さない。

## 取得履歴

sources/内に公開ページ・本文・スクリーンショットと取得日時。APIや有料取得の実行ID・入力・状態・確定費用は別記録。キーや認証付きURLを保存しない。取得失敗と外枠のみの取得も残す。

## 最終確認

checks/に機械検査JSONと目視コメントを保存。`status` は prototype / ready-for-review / ready-to-publish / published の意味を分ける。スキルを使って制作しただけではpublishedにならない。反応データが来るまで売上・DM数をnullのまま保持する。
