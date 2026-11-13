"""v2.0 (Grokbot 1.9を基に改修): 参考と完成物を同じ時刻（動画）・同じ枚目（スライド）で並べ、差分メモの下書きを作る。

動画:   python scripts/compare_reference.py video --ref refs/ref.mp4 --ours output/video.mp4 --out output/compare
        （参考MP4が無く静止コマだけなら --ref-frames refs/frames。ファイル名は t0.000000.png, t0.500000.png … の秒数）
        既定の時刻は 0,0.5,1,1.5,2 と、以降1秒ごと（冒頭2秒は0.5秒刻み）。--times で変更できる。
スライド: python scripts/compare_reference.py slides --ref refs/slides --ours output/slides --out output/compare

出力: compare_001.jpg 等（左=参考、右=完成物）、compare_notes.md（差分メモ。EDIT: を全部埋め、判定を書く）、frames/。
比較画像を作っただけでは合格ではない。目で見て差分を書き、直してから判定を「合格」にする。
"""
import argparse
import os
import re
import shutil
import subprocess
import json
import math
import html
from pathlib import Path
from contact_sheet import build_pairs

IMG = ('.png', '.jpg', '.jpeg', '.webp')


def ffmpeg_bin():
    p = os.environ.get('FFMPEG_PATH') or shutil.which('ffmpeg')
    if not p: raise RuntimeError('ffmpeg が見つからない。FFMPEG_PATH を設定するか ffmpeg を入れる')
    return p


def duration(ff, video):
    r = subprocess.run([ff, '-hide_banner', '-i', str(video)], capture_output=True, text=True)
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r.stderr)
    if not m: raise ValueError('尺を読めない: ' + str(video))
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def grab(ff, video, t, dest):
    r = subprocess.run([ff, '-v', 'error', '-n', '-ss', f'{t:.3f}', '-i', str(video), '-frames:v', '1', str(dest)], capture_output=True, text=True)
    if r.returncode or not dest.exists(): raise RuntimeError(r.stderr or 'frame failed')


def default_times(d):
    ts = [0, .5, 1, 1.5, 2] + [float(s) for s in range(3, int(d) + 1)]
    return [t for t in ts if t < d - .05] + [round(max(0, d - .1), 2)]


def natural(path):
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)',path.name)]


def write_pairs(pairs,out,kind):
    names=[]
    for offset in range(0,len(pairs),8):
        name=f'compare_{offset//8+1:03d}.jpg'
        build_pairs(pairs[offset:offset+8],out/name,title=kind+': reference vs ours');names.append(name)
    (out/'compare.json').write_text(json.dumps({'pairs':len(pairs),'sheets':names,'visual_review':'pending'},indent=2),encoding='utf-8')
    (out/'compare_notes.md').write_text(notes([p[0] for p in pairs],kind).replace('compare_sheet.jpg','compare_*.jpg'),encoding='utf-8')


def notes(rows, kind):
    head = ['# 参考との見比べメモ', '', f'種類: {kind}', '',
            '比較画像 compare_*.jpg を開き、各行の「差分」を書く。差が無ければ「差なし」。直したら「対応」に何をしたか、意図的な差なら理由を書く。',
            '冒頭2秒（動画）は入り方・エフェクト・文字の出る順番・速さを必ず書く。', '',
            '| 場面 | 見るところ | 差分 | 対応 |', '|---|---|---|---|']
    look = '文字の入り方・エフェクト・色・書体・縁取り・商品の大きさと位置' if kind == 'video' else '色・書体・縁取り・背景・商品の面積と位置・文字の位置・枚の役割'
    body = [f'| {r} | {look} | EDIT: | EDIT: |' for r in rows]
    return '\n'.join(head + body + ['', '判定: EDIT: 合格／要修正（全行の差分を埋めてから「合格」と書く）', ''])


def run_video(a):
    if not math.isfinite(a.fps) or a.fps<=0:raise ValueError('fps must be positive and finite')
    ff = ffmpeg_bin(); out = Path(a.out); out.mkdir(parents=True, exist_ok=False); fr = out / 'frames'; fr.mkdir()
    d = duration(ff, a.ours)
    times = [float(x) for x in a.times.split(',')] if a.times else default_times(d)
    if a.ref:
        rd=duration(ff,a.ref)
        if abs(rd-d)>1/a.fps+.015: raise ValueError(f'Duration differs: reference={rd}, ours={d}')
    if a.boundaries:
        b=json.loads(Path(a.boundaries).read_text(encoding='utf-8-sig'))
        for unit in b.get('units',[]):
            for key in ('start_frame','end_frame'):
                if type(unit.get(key)) is int:times.extend((unit[key]+delta)/a.fps for delta in (-1,0,1))
        for events in b.get('tracks',{}).values():
            for ev in events:
                for key in ('start_frame','end_frame'):
                    if type(ev.get(key)) is int:times.extend((ev[key]+delta)/a.fps for delta in (-1,0,1))
    times=sorted(set(round(t,6) for t in times if 0<=t<d-1/a.fps/2))
    if not times:raise ValueError('No valid comparison times')
    pairs = []
    for index,t in enumerate(times):
        mine = fr / f'ours_{index:05d}_t{t:.6f}.png'; grab(ff, a.ours, t, mine)
        if a.ref:
            ref = fr / f'ref_{index:05d}_t{t:.6f}.png'; grab(ff, a.ref, t, ref)
        else:
            ref = next((Path(a.ref_frames) / f't{t:.6f}{ext}' for ext in IMG if (Path(a.ref_frames) / f't{t:.6f}{ext}').exists()), None)
            if ref is None: raise FileNotFoundError(f'参考コマが無い: {a.ref_frames}/t{t:.1f}.png')
        pairs.append((f'{t:.6f}s', ref, mine))
    write_pairs(pairs,out,'video')
    if a.ref:
        # 全編は二つのプレーヤーを同じ時刻へシークして照合。音声は左右を別々に確認。
        refs=html.escape(os.path.relpath(Path(a.ref).resolve(),out.resolve()).replace(os.sep,'/'),quote=True)
        ours=html.escape(os.path.relpath(Path(a.ours).resolve(),out.resolve()).replace(os.sep,'/'),quote=True)
        (out/'full_comparison.html').write_text('''<!doctype html><meta charset="utf-8"><title>Full reference comparison</title><style>body{background:#111;color:white;font:16px sans-serif}main{display:flex;gap:12px}section{width:48%}video{width:100%;max-height:80vh}input{width:65%}</style><p>Left: reference / Right: output. Play together; pause and seek by frame. Listen to each audio track separately.</p><button onclick="for(const v of vids)v.play()">Play both</button><button onclick="for(const v of vids)v.pause()">Pause both</button><button onclick="step(-1)">−1 frame</button><button onclick="step(1)">+1 frame</button><input type="range" min="0" step="0.001" id="seek"><span id="time"></span><main><section>REFERENCE<video controls src="'''+refs+'''"></video></section><section>OUTPUT<video controls muted src="'''+ours+'''"></video></section></main><script>const vids=[...document.querySelectorAll('video')],slider=document.querySelector('#seek');slider.max='''+str(d)+''';function set(t){for(const v of vids){v.pause();v.currentTime=t}slider.value=t;document.querySelector('#time').textContent=t.toFixed(6)+' s'}slider.oninput=()=>set(+slider.value);function step(n){set(Math.max(0,Math.min(+slider.max,vids[0].currentTime+n/'''+str(a.fps)+''')))}setInterval(()=>{if(!vids[0].paused&&Math.abs(vids[0].currentTime-vids[1].currentTime)>0.08)vids[1].currentTime=vids[0].currentTime},100);</script>''',encoding='utf-8')
    return len(pairs)


def run_slides(a):
    refs = sorted((p for p in Path(a.ref).iterdir() if p.suffix.lower() in IMG),key=natural)
    ours = sorted((p for p in Path(a.ours).iterdir() if p.suffix.lower() in IMG),key=natural)
    if not refs or not ours: raise ValueError('参考または完成物のスライドが無い')
    if len(refs) != len(ours): raise ValueError(f'枚数が違う：参考{len(refs)}枚／完成物{len(ours)}枚。全枚を揃える')
    out = Path(a.out); out.mkdir(parents=True, exist_ok=False)
    pairs = [(f'slide {i+1}', refs[i], o) for i, o in enumerate(ours)]
    write_pairs(pairs,out,'slides')
    return len(pairs)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='mode', required=True)
    v = sub.add_parser('video'); g = v.add_mutually_exclusive_group(required=True)
    g.add_argument('--ref'); g.add_argument('--ref-frames'); v.add_argument('--ours', required=True); v.add_argument('--out', required=True); v.add_argument('--times')
    v.add_argument('--fps',type=float,default=30);v.add_argument('--boundaries',help='reference-breakdown.json; source/output must share this CFR fps')
    s = sub.add_parser('slides'); s.add_argument('--ref', required=True); s.add_argument('--ours', required=True); s.add_argument('--out', required=True)
    a = ap.parse_args()
    n = run_video(a) if a.mode == 'video' else run_slides(a)
    print(f'[OK] {n}組を並べた。compare_*.jpg を開いて compare_notes.md を埋める')
