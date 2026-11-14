/*
 * parts.js : 動きの部品集（依存なし）。window.Parts として使う。
 *
 * 約束:
 *  - どの部品も「時刻 t（秒）を受けて、要素の見た目を決める」だけ。同じ t なら必ず同じ結果になる。
 *    Math.random() も現在時刻も使わない。乱数が要る部品は種（seed）つきの擬似乱数を使う。
 *  - 部品は動きだけを担当する。色・書体・大きさ・配置は HTML/CSS 側で決める。
 *  - window.seek(t) の中で、毎回すべての部品を呼ぶ（t が前後に飛んでも正しい絵になる）。
 *  - 時刻の単位は秒。start = 始まる時刻、dur = かかる秒数。
 *  - wipeIn 以外の動く部品は style.transform を書く。1つの要素に transform を書く部品を2つ重ねると
 *    後の方が勝つので、重ねたいときは要素を入れ子にして、外側と内側に1つずつ当てる。
 *    （例: 外側に shake、内側に slam）
 */
(function (root) {
  'use strict';

  var TAU = Math.PI * 2;
  function f(v, n) { return Number(v).toFixed(n === undefined ? 3 : n); }
  function opt(o, key, fallback) { return o && o[key] !== undefined ? o[key] : fallback; }

  /* ---------- 基本 ---------- */

  // clamp01(v): 値を 0〜1 の範囲に収める。
  function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }

  // progress(t, start, dur): 時刻 t が start から dur 秒の区間のどこにいるかを 0〜1 で返す。
  //   始まる前は 0、終わった後は 1。dur が 0 以下なら、start を過ぎた瞬間に 1。
  function progress(t, start, dur) {
    if (!(dur > 0)) return t >= start ? 1 : 0;
    return clamp01((t - start) / dur);
  }

  // easeOutCubic(p): 速く出て、ゆっくり止まる。p は 0〜1。
  function easeOutCubic(p) { p = clamp01(p); return 1 - Math.pow(1 - p, 3); }

  // easeInOutCubic(p): ゆっくり始まり、ゆっくり止まる。p は 0〜1。
  function easeInOutCubic(p) { p = clamp01(p); return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; }

  // easeOutBack(p, overshoot): 行きすぎてから戻る（オーバーシュート）。途中で 1 を少し超える。
  //   overshoot = 行きすぎの強さ（省略時 1.70158。大きいほど強い）。
  function easeOutBack(p, overshoot) {
    p = clamp01(p);
    var c1 = overshoot === undefined ? 1.70158 : overshoot, c3 = c1 + 1;
    return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2);
  }

  // easeOutExpo(p): 一気に出て、長く余韻を残して止まる。p は 0〜1。
  function easeOutExpo(p) { p = clamp01(p); return p >= 1 ? 1 : 1 - Math.pow(2, -10 * p); }

  // rng(seed): 種つきの擬似乱数。同じ種なら毎回同じ並びの数（0 以上 1 未満）を返す関数を作る。
  function rng(seed) {
    var a = (Math.floor(Number(seed) || 0) >>> 0) || 1;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var x = Math.imul(a ^ (a >>> 15), 1 | a);
      x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
      return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
    };
  }

  // splitWords(el): 要素の文を空白で区切り、語ごとに <span>（inline-block）へ包み直して、その配列を返す。
  //   popWords に渡すための下ごしらえ。最初に1回だけ呼ぶ（seek の中では呼ばない）。
  function splitWords(el) {
    var words = el.textContent.split(/\s+/).filter(function (w) { return w.length; });
    el.textContent = '';
    return words.map(function (w, i) {
      if (i) el.appendChild(document.createTextNode(' '));
      var s = document.createElement('span');
      s.style.display = 'inline-block';
      s.textContent = w;
      el.appendChild(s);
      return s;
    });
  }

  /* ---------- 動きの部品 ---------- */

  // wipeIn(el, t, {start, dur, from, ease}): 帯・プレートが端から伸びて出る（clip-path で切り出す）。
  //   from = 'left' | 'right' | 'top' | 'bottom' | 'center'（どこから伸びるか。省略時 'left'）
  //   start 省略時 0、dur 省略時 0.5、ease 省略時 easeOutCubic。始まる前は見えない。
  function wipeIn(el, t, o) {
    var p = opt(o, 'ease', easeOutCubic)(progress(t, opt(o, 'start', 0), opt(o, 'dur', 0.5)));
    var rest = f((1 - p) * 100, 2) + '%', half = f((1 - p) * 50, 2) + '%';
    var from = opt(o, 'from', 'left'), v;
    if (from === 'right') v = 'inset(0 0 0 ' + rest + ')';
    else if (from === 'top') v = 'inset(0 0 ' + rest + ' 0)';
    else if (from === 'bottom') v = 'inset(' + rest + ' 0 0 0)';
    else if (from === 'center') v = 'inset(0 ' + half + ' 0 ' + half + ')';
    else v = 'inset(0 ' + rest + ' 0 0)';
    el.style.webkitClipPath = v;
    el.style.clipPath = v;
    return p;
  }

  // slam(el, t, {start, dur, fromScale, overshoot}): 数字の叩き込み。大きい状態から等倍へ落ち、少し行きすぎて戻る。
  //   fromScale = 始まりの倍率（省略時 2.6）、overshoot = 行きすぎの強さ（省略時 1.70158）
  //   start 省略時 0、dur 省略時 0.35。始まる前は見えない。
  function slam(el, t, o) {
    var start = opt(o, 'start', 0), p = progress(t, start, opt(o, 'dur', 0.35));
    var from = opt(o, 'fromScale', 2.6);
    var s = from + (1 - from) * easeOutBack(p, opt(o, 'overshoot', undefined));
    el.style.opacity = t < start ? '0' : f(clamp01(p * 5));
    el.style.transform = 'scale(' + f(s, 4) + ')';
    return p;
  }

  // popWords(els, t, {start, gap, dur, fromScale}): 語ごとに順番にポップイン（小さい状態から弾んで出る）。
  //   els = 語の要素の配列（inline-block にしておく。splitWords で作れる）
  //   gap = 語と語の時間差（省略時 0.08）、dur = 1語あたりの秒数（省略時 0.3）、fromScale = 始まりの倍率（省略時 0.5）
  function popWords(els, t, o) {
    var start = opt(o, 'start', 0), gap = opt(o, 'gap', 0.08), dur = opt(o, 'dur', 0.3), from = opt(o, 'fromScale', 0.5);
    for (var i = 0; i < els.length; i++) {
      var p = progress(t, start + i * gap, dur);
      els[i].style.opacity = f(clamp01(p * 3));
      els[i].style.transform = 'scale(' + f(from + (1 - from) * easeOutBack(p), 4) + ')';
    }
  }

  // tracking(el, t, {start, dur, from, to, ease}): 字間が広がる／詰まる。
  //   from, to = 字間（em 単位。省略時 from 0.6 → to 0.1）。from < to なら広がり、from > to なら詰まる。
  //   中央ぞろえの文がずれないよう、同じ量の負の margin-right も入れる。
  function tracking(el, t, o) {
    var p = opt(o, 'ease', easeOutCubic)(progress(t, opt(o, 'start', 0), opt(o, 'dur', 0.8)));
    var a = opt(o, 'from', 0.6), b = opt(o, 'to', 0.1), v = a + (b - a) * p;
    el.style.letterSpacing = f(v, 4) + 'em';
    el.style.marginRight = f(-v, 4) + 'em';
    return p;
  }

  // fadeSlide(el, t, {start, dur, dx, dy, ease}): フェードしながら移動して定位置に着く。
  //   dx, dy = 始まりのずれ（px。省略時 dx 0, dy 40 = 下から上がる）。始まる前は見えない。
  function fadeSlide(el, t, o) {
    var p = opt(o, 'ease', easeOutCubic)(progress(t, opt(o, 'start', 0), opt(o, 'dur', 0.5)));
    el.style.opacity = f(p);
    el.style.transform = 'translate(' + f((1 - p) * opt(o, 'dx', 0), 2) + 'px,' + f((1 - p) * opt(o, 'dy', 40), 2) + 'px)';
    return p;
  }

  // shake(el, t, {start, dur, amp, freq, seed}): 画面シェイク。揺れ幅がだんだん小さくなって止まる。
  //   amp = 最初の揺れ幅（px。省略時 24）、freq = 1秒あたりの揺れの回数（省略時 22）、seed = 揺れ方の種（省略時 1）
  //   区間の外では元の位置。画面全体を包む要素に当てる。
  function shake(el, t, o) {
    var start = opt(o, 'start', 0), dur = opt(o, 'dur', 0.5), amp = opt(o, 'amp', 24), freq = opt(o, 'freq', 22);
    var x = 0, y = 0;
    if (t >= start && t < start + dur) {
      var r = rng(opt(o, 'seed', 1)), ph1 = r() * TAU, ph2 = r() * TAU;
      var p = progress(t, start, dur), decay = Math.pow(1 - p, 2), u = t - start;
      x = amp * decay * Math.sin(TAU * freq * u + ph1);
      y = amp * decay * 0.7 * Math.sin(TAU * freq * 1.31 * u + ph2);
    }
    el.style.transform = 'translate(' + f(x, 2) + 'px,' + f(y, 2) + 'px)';
  }

  // flash(el, t, {start, dur, peak}): 白フラッシュ。start の瞬間に最も明るく、dur 秒かけて消える。
  //   el = 画面全体を覆う白い要素（色は CSS で決める）。peak = 最大の不透明度（省略時 1）。dur 省略時 0.25。
  function flash(el, t, o) {
    var start = opt(o, 'start', 0), a = 0;
    if (t >= start) a = opt(o, 'peak', 1) * (1 - easeOutCubic(progress(t, start, opt(o, 'dur', 0.25))));
    el.style.opacity = f(a);
    return a;
  }

  // sparkle(container, t, {seed, count, start, dur, size}): 星のきらめき。位置は種で固定、明滅だけ t で変わる。
  //   container = 星を置く箱（CSS で position:relative か absolute にしておく）。星は最初の呼び出しで自動で作る。
  //   seed = 位置の種（省略時 1）、count = 星の数（省略時 12）、size = 星の最大の大きさ（px。省略時 40）
  //   start〜start+dur の間だけ見える（省略時 start 0, dur 2）。星の色は container の文字色（CSS の color）。
  var sparkleStore = new WeakMap();
  function sparkle(container, t, o) {
    var seed = opt(o, 'seed', 1), count = opt(o, 'count', 12), size = opt(o, 'size', 40);
    var start = opt(o, 'start', 0), dur = opt(o, 'dur', 2);
    var key = seed + '|' + count + '|' + size, st = sparkleStore.get(container);
    if (!st || st.key !== key) {
      if (st) st.stars.forEach(function (s) { if (s.el.parentNode) s.el.parentNode.removeChild(s.el); });
      var r = rng(seed), stars = [];
      for (var i = 0; i < count; i++) {
        var d = document.createElement('div'), sz = size * (0.45 + 0.55 * r());
        var shape = 'polygon(50% 0%,60% 40%,100% 50%,60% 60%,50% 100%,40% 60%,0% 50%,40% 40%)';
        d.setAttribute('data-parts-sparkle', '');
        d.style.cssText = 'position:absolute;pointer-events:none;background:currentColor;opacity:0;' +
          'left:' + f(4 + 92 * r(), 2) + '%;top:' + f(4 + 92 * r(), 2) + '%;' +
          'width:' + f(sz, 1) + 'px;height:' + f(sz, 1) + 'px;margin:' + f(-sz / 2, 1) + 'px 0 0 ' + f(-sz / 2, 1) + 'px;' +
          '-webkit-clip-path:' + shape + ';clip-path:' + shape + ';';
        container.appendChild(d);
        stars.push({ el: d, phase: r() * TAU, speed: 1.2 + 1.6 * r() });
      }
      st = { key: key, stars: stars };
      sparkleStore.set(container, st);
    }
    var inside = t >= start && t <= start + dur, p = progress(t, start, dur);
    var env = inside ? clamp01(p / 0.15) * clamp01((1 - p) / 0.15) : 0;
    for (var k = 0; k < st.stars.length; k++) {
      var s = st.stars[k], tw = 0.5 + 0.5 * Math.sin(TAU * s.speed * (t - start) + s.phase);
      s.el.style.opacity = f(env * tw * tw);
      s.el.style.transform = 'scale(' + f(0.35 + 0.65 * tw, 4) + ') rotate(' + f(40 * tw, 2) + 'deg)';
    }
  }

  // lightSweep(el, t, {start, dur, angle, ease}): 光の帯が斜めに横切る。帯の位置と傾きだけを動かす。
  //   el = 光の帯。光らせたい箱（overflow:hidden）の中に position:absolute; left:0; top:0; height:100% で置き、
  //        幅・グラデーション・mix-blend-mode:screen は CSS で決める。
  //   angle = 傾き（度。省略時 20）。start 省略時 0、dur 省略時 0.8、ease 省略時 easeInOutCubic。区間の外では見えない。
  function lightSweep(el, t, o) {
    var start = opt(o, 'start', 0), dur = opt(o, 'dur', 0.8), angle = opt(o, 'angle', 20);
    var parent = el.parentElement, pw = parent ? parent.clientWidth : 0, w = el.offsetWidth, h = el.offsetHeight;
    var lean = Math.abs(Math.tan(angle * Math.PI / 180)) * h / 2 + 2;
    var p = opt(o, 'ease', easeInOutCubic)(progress(t, start, dur));
    var x = -(w + lean) + (pw + w + 2 * lean) * p;
    el.style.opacity = (t >= start && t <= start + dur) ? '1' : '0';
    el.style.transform = 'translateX(' + f(x, 2) + 'px) skewX(' + f(-angle, 2) + 'deg)';
    return p;
  }

  // kenBurns(el, t, {start, dur, fromScale, toScale, fromX, toX, fromY, toY, ease}): 写真にゆっくり寄る・流す。
  //   fromScale → toScale = 倍率（省略時 1 → 1.12）、fromX → toX / fromY → toY = 位置のずれ（px。省略時 0）
  //   start 省略時 0、dur 省略時 5。ease 省略時は等速。枠（overflow:hidden）の中の画像に当てる。
  function kenBurns(el, t, o) {
    var p = progress(t, opt(o, 'start', 0), opt(o, 'dur', 5)), e = opt(o, 'ease', null);
    if (e) p = e(p);
    function mix(a, b) { return a + (b - a) * p; }
    el.style.transform = 'translate(' + f(mix(opt(o, 'fromX', 0), opt(o, 'toX', 0)), 2) + 'px,' +
      f(mix(opt(o, 'fromY', 0), opt(o, 'toY', 0)), 2) + 'px) scale(' + f(mix(opt(o, 'fromScale', 1), opt(o, 'toScale', 1.12)), 4) + ')';
    return p;
  }

  // cut(scenes, t): 場面のハードカット。scenes = [{el, start, end}] のうち、start <= t < end の場面だけ表示する。
  //   それ以外の場面は display:none にする。end を省くと最後まで表示。今表示している場面の番号（無ければ -1）を返す。
  function cut(scenes, t) {
    var active = -1;
    for (var i = 0; i < scenes.length; i++) {
      var s = scenes[i], end = s.end === undefined ? Infinity : s.end;
      var on = t >= s.start && t < end;
      s.el.style.display = on ? '' : 'none';
      if (on && active < 0) active = i;
    }
    return active;
  }

  // countUp(el, t, {start, dur, from, to, format, ease}): 数字が上がる（下がる）。要素の文字を書き換える。
  //   from → to = 数（省略時 0 → 100）、format = 数を文字にする関数（省略時は四捨五入した整数）
  //   start 省略時 0、dur 省略時 1、ease 省略時 easeOutCubic。今の数を返す。
  function countUp(el, t, o) {
    var p = opt(o, 'ease', easeOutCubic)(progress(t, opt(o, 'start', 0), opt(o, 'dur', 1)));
    var a = opt(o, 'from', 0), b = opt(o, 'to', 100), v = a + (b - a) * p;
    var fmt = opt(o, 'format', null), text = fmt ? String(fmt(v)) : String(Math.round(v));
    if (el.textContent !== text) el.textContent = text;
    return v;
  }

  root.Parts = {
    clamp01: clamp01, progress: progress,
    easeOutCubic: easeOutCubic, easeInOutCubic: easeInOutCubic, easeOutBack: easeOutBack, easeOutExpo: easeOutExpo,
    rng: rng, splitWords: splitWords,
    wipeIn: wipeIn, slam: slam, popWords: popWords, tracking: tracking, fadeSlide: fadeSlide,
    shake: shake, flash: flash, sparkle: sparkle, lightSweep: lightSweep, kenBurns: kenBurns,
    cut: cut, countUp: countUp
  };
})(typeof window !== 'undefined' ? window : globalThis);
