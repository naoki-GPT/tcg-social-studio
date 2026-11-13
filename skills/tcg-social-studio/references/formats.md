# 調査から使える19の型

版2.0追記：需要・導線・全参考の再現はSKILL.mdと[全参考仕様](reference-reproduction.md)を優先する。以下の旧テンプレートの秒数や先頭画像の観察範囲は、今回の完成仕様ではない。2026-11-12の再確認は[実物の索引](verified-reference-map.md)を参照。
v1.1.0 / 2026-10-31。型の定義・画面順・必要入力は [formats.json](../templates/formats.json) を管理元とする。制作では該当する行を読む。19型は今回の調査から制作に使える構造をまとめたもの。「世の中の全型」「19種類すべてが実測でバズった」という意味ではない。

## 先に選ぶもの

連続制作や「おまかせ」は[履歴を使う選定ルール](selection-and-questions.md)で絞ってから下表へ進む。19型の番号順やランダムでは選ばず、対象客・根拠と、直近の主役商品・訴求・デザインの偏りを合わせて判断する。

| 目的 | 型ID |
|---|---|
| 人気カード・BOXの国内外価格差 | price-gap、comparison-slideshow |
| 鈴木さんの英語版対日本語版の参考 | language-compare、comparison-slideshow |
| 欲しいカードを見つけてもらう | card-detail、art-compare、pick-one、theme-set、trend-picks |
| 相場・条件を分かりやすく見せる | price-timeline、market-range、condition-compare、box-check |
| 海外店・配信者から相談をもらう | bulk-offer、assortment、restock、preorder |
| 買い方・相談方法を伝える | order-steps、screen-guide、sourcing-request |

商品の原画像を使い、AIで背景・構成・文章・切替を制作する。ホロの光り方、傷、実際の梱包作業、出荷実績の再現には実素材が必要。素材がないときも、絵柄の拡大・説明図・商品一覧へ変換して作れる型を選ぶ。顔や声は必須にしない。

## 参考の根拠（2026-10-25取得の既存調査）

次の表の数値・確認範囲は当時の記録。2026-11-01の動画4本の全編確認を踏まえた見せ方は[参考7区分](design-library.md)へ整理。受け取り先で実物を見たことにはせず、現在の反応数とも区別する。

| 参照ID | 実際の参考 | 確認した工夫・数字の範囲 |
|---|---|---|
| japan2uk | [@japan2uk](https://www.instagram.com/p/DdjbR4qjaUb/) | 過去の保存記録ではカルーセル9枚・161いいね。通常写真13本の中央値63という当時の集計。英語版シングルの発売時と4日後の価格比較。日海外価格差の実例ではない。旧目視は先頭画像のみで全9枚の内容確認ではない |
| okjluv | [カード接写](https://www.instagram.com/p/Dcirc56pfsP/) | 99,089再生、比較動画15本の中央値28,534。5場面を観察。カード名・番号、細部・切替を採用。音声・全区間未確認 |
| pokenin | [好きな1枚](https://www.instagram.com/p/DeubX7ADf8V/) | 商品一覧と選択、商品ページへの接続。取得時5いいね、公開7日未満。成功の数値根拠にはしない |
| tcgex | [配信者向け](https://www.instagram.com/p/DcuXW_vTRrd/) | 1,274いいね、通常写真3本の中央値252。少数比較。対象客を名指し、商品・DMをつなぐ |
| bokudora | [まとめ商品](https://www.instagram.com/p/Dc4A0PEs2-Q/) | 975再生、比較9本の中央値929。量・用途・相談の流れ。突出した高反応の例ではない |
| pokecollect | [3手順動画](https://www.instagram.com/p/DeXsyV-DVyx/) | 約30.1秒のうち5場面観察。26,991再生、比較2本のみ。商品画像・大見出し・番号付き手順を採用 |
| pokecollect-screen | [画面で案内](https://www.instagram.com/p/DeVl6XKCe7s/) | 約22.6秒・4,044再生。実ページの操作案内を参考にする |
| samurai | [注文説明](https://www.instagram.com/p/Ded9BFBT2fC/) | 人物主役の再現ではなく個人注文と卸相談の案内を採用 |
| sumdex | [注文先](https://sumdex.jp/) | 商品・数量・国→送料込み見積もり→注文という案内 |
| nox | [調達相談](https://nox-jdm.com/) | 希望品→条件と費用確認→調達。相手の最低金額・手数料率は転用しない |
| kanade | [鈴木さん指定の投稿](https://www.instagram.com/p/DeCOaEbDEg9/) | 2026-10-31、先頭画像と本文を確認。左右に英語版／日本語版ルギア、各価格と円換算、日付、選択を促す。相対的に伸びたという本人情報。インサイト・全スライド・売上は未確認 |
| user-20261031 | 今回の本人指定 | 国内外価格差・複数商品の価格比較スライドを追加。別の「バズった人」は保存済みデータで未特定。特定アカウントの実証済み成功例とは書かない |

161いいねは現在値として再利用しない。写真・Sidecar・動画を取り違えず、元の集計区分（写真にSidecarを含めた等）を記録する。反応数は売上・保存数・需要の証明ではない。

## 旧提案を漏らさず引き継ぐ対応表

| 既存調査のテーマ | 対応する型 |
|---|---|
| 元の投稿案01 同じカードで比較 | condition-compare、price-gap |
| 02 売切れでも探す | sourcing-request |
| 03 欲しい1枚 | pick-one |
| 04 ホロ・細部 | card-detail |
| 05 写真からDM | sourcing-request、order-steps |
| 06 コレクター／店舗向け | theme-set、bulk-offer |
| 07 BOX条件 | box-check |
| 08 高い成約1件だけに頼らない | market-range |
| 追加案① 旧ホロ・日本語絵柄・同じポケモン・人気イラスト・テーマセット・選び方 | card-detail、art-compare、trend-picks、theme-set、pick-one |
| 追加案② 2時点・発売後の値動き・日本の候補 | price-timeline、market-range、price-gap、trend-picks |
| 追加案③ 配信者・まとめ商品・入荷予約 | bulk-offer、assortment、restock、preorder |
| 商品から購入へ、実画面で手順 | order-steps、screen-guide |

元の8案の「本人実写だけ」「秋葉原へ行った」等は個別の過去制作条件。最新方針では商品画像取得とAI補完を使い、本人がしていない行動は語らない。

## 価格比較のスライド設計

最初の1枚に比較テーマと商品を出し、2枚目以降は1商品1枚。左右の意味、通貨、価格の基準、文字の位置を統一する。画像には商品名・番号・言語・通貨・単位など比較に必要な項目を簡潔に示す。出典URL・確認日・送料条件は制作記録に残し、定型注釈を画像・本文へ自動追加しない。[注釈を載せない](copy-delivery.md#注釈を載せない)に従う。最後は「どれを選ぶ？」または商品を指定した見積もりのどちらか1つ。

動画では各比較画面を3〜5秒程度保持する案から始め、実際に読めるか確認する。商品が多ければ秒数を減らさず本数を分ける。目立つ差額だけを選んで条件が違う商品を混ぜない。価格差が逆転・小差・不明の候補も調査記録に残す。

各型の画像生成指示は [価格比較](price-comparison.md) と [制作手順](production.md)。実装雛形は [story-template.md](story-template.md)。抽選・顔出し実績・会員課金・ランダム開封販売は、この19型の導入に付随して新設しない。
