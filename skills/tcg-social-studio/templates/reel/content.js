// v1: 今回の素材・文章・店名だけを設定する。下の例文は事業情報に合わせて編集する。
window.C = {
  brand: 'YOUR SHOP',
  segments: [0,3,5,7,10,14,18,24],
  // 例: {id:'card01',src:'assets/card01.webp',name:'商品英語名',number:'番号',language:'Japanese',crop:[0,0,1,1]}
  // cropは原画像全体を1とした [左,上,幅,高さ]。余白だけを外し、商品本体を切らない。
  cards: [],
  selected: 0,
  binder: {
    background: null,
    // 背景に合わせた各ポケットの [左,上,幅]。1080×1920画面に対する0〜1の比率。
    // 空配列ならHTMLのポケットを自動配置。AI背景を使用するときは実画像へ合わせる。
    slots: []
  },
  texts: {
    hook:['YOU MIGHT ONLY BE','LOOKING FOR','ONE.'],
    favourite:'One favourite Pokémon.',
    artwork:'One artwork.',
    binder:['One missing space','in your binder.'],
    enquiry:['You can start a sourcing enquiry','with just that card.'],
    send:['Send me its name or a photo,',"and I'll check the options in Japan."],
    cta:['DM A CARD NAME','OR A PHOTO.'],
    note:['Availability, condition and the total cost','need confirming before an order.']
  }
};
