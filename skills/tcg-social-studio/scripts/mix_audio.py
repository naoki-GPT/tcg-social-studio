#!/usr/bin/env python3
"""v4: 効果音（と任意のBGM）を時刻どおりに並べて1本の wav にする。標準ライブラリだけで動く。

使い方:
  python scripts/mix_audio.py <cues.json> --out <audio.wav> [--pack <se-packフォルダ>]

cues.json:
  {"duration": 13.0,
   "cues": [{"file": "whip_01.mp3", "t": 0.30, "gain_db": -10, "trim": 1.3}, ...],
   "bgm": {"file": "bgm.mp3", "gain_db": -18}}        <- bgm は任意
  - file    : se-pack/manifest.json に載っているファイル名
  - t       : 鳴らし始める時刻（秒）
  - gain_db : 省略すると manifest の default_gain_db
  - trim    : 頭から何秒だけ使うか（省略すると全部）
  - bgm.file: 任意の音声ファイル。相対パスは cues.json のあるフォルダから見る

処理: ffmpeg でモノラル 44.1kHz に読み込む -> 時刻に配置 -> 全体のピークを 0.85 にそろえる -> wav。
出力: <out> と <out>.credits.json（使った音の一覧と、必要なクレジット表記）。
"""
import argparse
import array
import json
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

SR = 44100
PEAK = 0.85
FADE = 0.03       # trim で切った末尾のプチ音を防ぐ短いフェード（秒）
BGM_FADE = 0.5    # BGM の末尾フェード（秒）
SKILL = Path(__file__).resolve().parent.parent
CREDIT_OTOLOGIC = '効果音: OtoLogic（https://otologic.jp）/ CC BY 4.0'


class Stop(Exception):
    pass


def find_ffmpeg():
    exe = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
    candidates = []
    if os.environ.get('FFMPEG_PATH'):
        candidates.append(Path(os.environ['FFMPEG_PATH']))
    candidates.append(SKILL / 'node_modules' / 'ffmpeg-static' / exe)
    if os.environ.get('TCG_NODE_MODULES'):
        candidates.append(Path(os.environ['TCG_NODE_MODULES']) / 'ffmpeg-static' / exe)
    for c in candidates:
        if c.is_file():
            return str(c)
    found = shutil.which('ffmpeg')
    if found:
        return found
    raise Stop('ffmpeg was not found. Run "npm install" in the skill folder, or set FFMPEG_PATH.')


def decode(ffmpeg, path, seconds=None):
    """音声ファイルをモノラル 44.1kHz の float 配列にする。"""
    cmd = [ffmpeg, '-v', 'error', '-i', str(path)]
    if seconds is not None:
        cmd += ['-t', f'{seconds:.6f}']
    cmd += ['-vn', '-ac', '1', '-ar', str(SR), '-f', 's16le', '-']
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise Stop(f'could not read audio: {path.name}: ' + r.stderr.decode('utf-8', 'replace').strip()[-400:])
    pcm = array.array('h')
    pcm.frombytes(r.stdout[: len(r.stdout) // 2 * 2])
    if sys.byteorder == 'big':
        pcm.byteswap()
    return pcm


def place(buf, pcm, start, gain, fade_samples):
    """buf の start 位置から pcm を足す。末尾 fade_samples はフェードアウト。"""
    n = min(len(pcm), len(buf) - start)
    if n <= 0:
        return 0
    scale = gain / 32768.0
    fade_from = n - fade_samples if fade_samples and fade_samples < n else n
    for i in range(fade_from):
        buf[start + i] += pcm[i] * scale
    for i in range(fade_from, n):
        buf[start + i] += pcm[i] * scale * (n - i) / fade_samples
    return n


def num(value, name, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Stop(f'{name} must be a number')
    if minimum is not None and value < minimum:
        raise Stop(f'{name} must be >= {minimum}')
    return float(value)


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    ap = argparse.ArgumentParser(description='Mix sound effects (and optional BGM) into one wav.')
    ap.add_argument('cues', help='cues.json')
    ap.add_argument('--out', required=True, help='output wav (must not exist)')
    ap.add_argument('--pack', default=str(SKILL / 'se-pack'), help='se-pack folder (default: the one inside the skill)')
    a = ap.parse_args()

    cues_path = Path(a.cues).resolve()
    if not cues_path.is_file():
        raise Stop(f'cues file not found: {cues_path}')
    out = Path(a.out).resolve()
    credits_path = Path(str(out) + '.credits.json')
    if out.suffix.lower() != '.wav':
        raise Stop('--out must end with .wav')
    for p in (out, credits_path):
        if p.exists():
            raise Stop(f'Output already exists: {p}')

    pack = Path(a.pack).resolve()
    manifest_path = pack / 'manifest.json'
    if not manifest_path.is_file():
        raise Stop(f'manifest.json not found in the pack folder: {pack}')
    manifest = {}
    for item in json.loads(manifest_path.read_text(encoding='utf-8')).get('items', []):
        manifest.setdefault(item['file'], item)   # 同じファイルが2回載っている場合は最初の行を使う

    try:
        spec = json.loads(cues_path.read_text(encoding='utf-8-sig'))
    except json.JSONDecodeError as e:
        raise Stop(f'cues.json is not valid JSON: {e}')
    if not isinstance(spec, dict):
        raise Stop('cues.json must be an object: {"duration": ..., "cues": [...]}')
    duration = num(spec.get('duration'), 'duration', 0.1)
    if duration > 600:
        raise Stop('duration must be 600 seconds or less')
    cues = spec.get('cues', [])
    bgm = spec.get('bgm')
    if not isinstance(cues, list):
        raise Stop('"cues" must be a list')
    if not cues and not bgm:
        raise Stop('nothing to mix: "cues" is empty and there is no "bgm"')

    # ---- 先に全部を確かめる（途中まで作って止まらないように） ----
    plan = []
    for i, c in enumerate(cues, 1):
        where = f'cues[{i}]'
        if not isinstance(c, dict) or not isinstance(c.get('file'), str):
            raise Stop(f'{where}: "file" is required')
        name = c['file']
        if name not in manifest:
            raise Stop(f'{where}: "{name}" is not listed in {manifest_path.name}. Use a file name from the manifest.')
        src = pack / name
        if not src.is_file():
            raise Stop(f'{where}: file not found: {src}')
        t = num(c.get('t'), f'{where}.t', 0)
        if t >= duration:
            raise Stop(f'{where}: t={t} is outside the duration {duration}')
        gain_db = num(c['gain_db'], f'{where}.gain_db') if c.get('gain_db') is not None else float(manifest[name].get('default_gain_db', -10))
        trim = num(c['trim'], f'{where}.trim', 0.05) if c.get('trim') is not None else None
        plan.append({'file': name, 'src': src, 't': t, 'gain_db': gain_db, 'trim': trim})
    bgm_plan = None
    if bgm is not None:
        if not isinstance(bgm, dict) or not isinstance(bgm.get('file'), str):
            raise Stop('bgm: "file" is required')
        src = Path(bgm['file'])
        if not src.is_absolute():
            src = cues_path.parent / src
        if not src.is_file():
            raise Stop(f'bgm: file not found: {src}')
        gain_db = num(bgm['gain_db'], 'bgm.gain_db') if bgm.get('gain_db') is not None else -18.0
        bgm_plan = {'file': src.name, 'src': src, 'gain_db': gain_db}

    ffmpeg = find_ffmpeg()
    total = int(round(duration * SR))
    buf = array.array('d', bytes(8 * total))
    cache = {}
    if bgm_plan:
        pcm = decode(ffmpeg, bgm_plan['src'], duration)
        place(buf, pcm, 0, 10 ** (bgm_plan['gain_db'] / 20), int(BGM_FADE * SR))
        bgm_plan['seconds'] = round(len(pcm) / SR, 3)
        if len(pcm) < total - SR // 10:
            print(f'[INFO] bgm is shorter than the video ({len(pcm) / SR:.2f}s < {duration:.2f}s). It is not looped.')
    for p in plan:
        if p['file'] not in cache:
            cache[p['file']] = decode(ffmpeg, p['src'])
        pcm = cache[p['file']]
        fade = 0
        if p['trim'] is not None and int(p['trim'] * SR) < len(pcm):
            pcm = pcm[: int(p['trim'] * SR)]
            fade = int(FADE * SR)
        start = int(round(p['t'] * SR))
        if start + len(pcm) > total:
            fade = fade or int(FADE * SR)    # 動画の終わりで切れる音もフェードさせる
        p['seconds'] = round(place(buf, pcm, start, 10 ** (p['gain_db'] / 20), fade) / SR, 3)

    peak = max(max(buf), -min(buf)) if total else 0.0
    if peak <= 1e-6:
        raise Stop('the mix is silent. Check the cues and gain_db.')
    k = PEAK / peak * 32767.0
    pcm_out = array.array('h', (int(round(v * k)) for v in buf))
    if sys.byteorder == 'big':
        pcm_out.byteswap()
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm_out.tobytes())

    # ---- 使った音の一覧とクレジット ----
    used = {}
    for p in plan:
        m = manifest[p['file']]
        u = used.setdefault(p['file'], {'file': p['file'], 'count': 0, 'site': m.get('site'), 'license': m.get('license'),
                                        'source_name': m.get('source_name'), 'source_url': m.get('source_url')})
        u['count'] += 1
    used = list(used.values())

    def is_otologic(u):
        return 'otologic' in (u.get('site') or '').lower() or 'otologic' in (u.get('source_url') or '').lower()

    def needs_credit(u):
        return is_otologic(u) or 'CC BY' in (u.get('license') or '').upper()

    credit_lines = []
    if any(is_otologic(u) for u in used):
        credit_lines.append(CREDIT_OTOLOGIC)
    for u in used:
        if needs_credit(u) and not is_otologic(u):
            credit_lines.append(f"効果音: {u.get('site')} / {u.get('license')}")
    credit_lines = list(dict.fromkeys(credit_lines))
    credits = {
        'audio': out.name, 'duration': duration, 'sample_rate': SR, 'channels': 1, 'peak': PEAK,
        'credit_required': bool(credit_lines), 'credit_text': credit_lines,
        'used': used,
        'cues': [{'file': p['file'], 't': p['t'], 'gain_db': p['gain_db'], 'trim': p['trim'], 'seconds': p['seconds']} for p in plan],
        'bgm': ({'file': bgm_plan['file'], 'gain_db': bgm_plan['gain_db'], 'seconds': bgm_plan['seconds'],
                 'note': 'BGM is not part of the se-pack. Check its license yourself.'} if bgm_plan else None),
    }
    credits_path.write_text(json.dumps(credits, ensure_ascii=False, indent=2), encoding='utf-8')

    for u in used:
        mark = ' (credit required)' if needs_credit(u) else ''
        print(f"[INFO] used: {u['file']} x{u['count']} / {u.get('site')} / {u.get('license')}{mark}")
    if bgm_plan:
        print(f"[INFO] used bgm: {bgm_plan['file']} ({bgm_plan['gain_db']} dB). Check its license yourself.")
    for line in credit_lines:
        print(f'[INFO] credit required: {line}')
    if not credit_lines:
        print('[INFO] credit required: none')
    print(f'[OK] {out} ({duration:.2f}s, {len(plan)} cue(s), peak {PEAK})')
    print(f'[OK] {credits_path}')


if __name__ == '__main__':
    try:
        main()
    except Stop as e:
        print(f'[ERROR] {e}', file=sys.stderr)
        sys.exit(1)
