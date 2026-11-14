#!/usr/bin/env python3
"""v4.1: 表に貼る「見た目」画像（横並びの小さな1枚）を作る。Pillow と標準ライブラリだけで動く。

使い方:
  python scripts/make_preview.py <入力> --out <新規.jpg> [--count 3 --height 320]

入力:
  - 動画（mp4 / mov / webm）: 全体を --count 個の区間に等分し、各区間の中央のコマを抜いて横に並べる
  - フォルダ               : 中の画像（jpg / png / webp）を名前順に先頭 --count 枚、横に並べる（カルーセル用）
  - 画像1枚                : その1枚を高さ --height に縮める

出力: 各コマの高さを --height にそろえ、6px の白い間隔で横に並べた JPEG（品質86）。
      既にあるファイルには上書きしない。
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

GAP = 6
QUALITY = 86
VIDEO_EXT = {'.mp4', '.mov', '.webm'}
IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.webp'}
SKILL = Path(__file__).resolve().parent.parent


class Stop(Exception):
    pass


def find_ffmpeg():
    """mix_audio.py と同じ順で探す: FFMPEG_PATH -> スキル内 node_modules/ffmpeg-static -> PATH。"""
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


def natural_key(path):
    """slide_2 が slide_10 より先に来る名前順。"""
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', path.name)]


def open_image(source, label):
    from PIL import Image, ImageOps
    try:
        im = Image.open(source)
        im.load()
    except Exception as e:
        raise Stop(f'could not read image: {label}: {e}')
    im = ImageOps.exif_transpose(im)
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA')
        base = Image.new('RGB', im.size, (255, 255, 255))
        base.paste(im, mask=im.split()[-1])
        return base
    return im.convert('RGB')


def video_duration(ffmpeg, path):
    r = subprocess.run([ffmpeg, '-hide_banner', '-i', str(path)], capture_output=True)
    text = r.stderr.decode('utf-8', 'replace')
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', text)
    if not m or 'Video:' not in text:
        raise Stop(f'could not read the video: {path.name}: ' + text.strip()[-400:])
    seconds = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    if seconds <= 0:
        raise Stop(f'the video has no length: {path.name}')
    return seconds


def video_frames(ffmpeg, path, count):
    duration = video_duration(ffmpeg, path)
    frames = []
    for i in range(count):
        t = (i + 0.5) * duration / count
        cmd = [ffmpeg, '-v', 'error', '-ss', f'{t:.3f}', '-i', str(path), '-frames:v', '1',
               '-an', '-f', 'image2pipe', '-vcodec', 'png', '-']
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0 or not r.stdout:
            raise Stop(f'ffmpeg could not take a frame at {t:.2f}s: ' + r.stderr.decode('utf-8', 'replace').strip()[-400:])
        frames.append(open_image(io.BytesIO(r.stdout), f'{path.name} @ {t:.2f}s'))
    return frames, duration


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    ap = argparse.ArgumentParser(description='Make one small side-by-side preview image from a video, a folder of images, or one image.')
    ap.add_argument('input', help='video (mp4/mov/webm), folder of images (jpg/png/webp), or one image')
    ap.add_argument('--out', required=True, help='output jpg (must not exist)')
    ap.add_argument('--count', type=int, default=3, help='how many frames / images to line up (default 3)')
    ap.add_argument('--height', type=int, default=320, help='height of the preview in pixels (default 320)')
    a = ap.parse_args()

    if not 1 <= a.count <= 12:
        raise Stop('--count must be between 1 and 12')
    if not 40 <= a.height <= 2000:
        raise Stop('--height must be between 40 and 2000')
    out = Path(a.out).resolve()
    if out.suffix.lower() not in ('.jpg', '.jpeg'):
        raise Stop('--out must end with .jpg')
    if out.exists():
        raise Stop(f'Output already exists: {out}')
    src = Path(a.input).resolve()
    if not src.exists():
        raise Stop(f'input not found: {src}')
    try:
        from PIL import Image
    except ImportError:
        raise Stop('Pillow is not installed. Run "pip install -r requirements.txt" in the skill folder.')

    if src.is_dir():
        files = sorted((p for p in src.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXT), key=natural_key)
        if not files:
            raise Stop(f'no images (jpg/png/webp) in the folder: {src}')
        picked = files[: a.count]
        tiles = [open_image(p, p.name) for p in picked]
        kind = f'folder, {len(picked)} of {len(files)} image(s)'
    elif src.suffix.lower() in VIDEO_EXT:
        tiles, duration = video_frames(find_ffmpeg(), src, a.count)
        kind = f'video {duration:.2f}s, {len(tiles)} frame(s)'
    elif src.suffix.lower() in IMAGE_EXT:
        tiles = [open_image(src, src.name)]
        kind = 'single image'
    else:
        raise Stop(f'unsupported input: {src.name} (use mp4/mov/webm, a folder, or jpg/png/webp)')

    resized = []
    for im in tiles:
        w = max(1, round(im.width * a.height / im.height))
        resized.append(im.resize((w, a.height), Image.LANCZOS))
    total = sum(im.width for im in resized) + GAP * (len(resized) - 1)
    sheet = Image.new('RGB', (total, a.height), (255, 255, 255))
    x = 0
    for im in resized:
        sheet.paste(im, (x, 0))
        x += im.width + GAP

    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(out, 'xb') as f:       # 'x' = 既にあれば失敗（上書きしない）
            sheet.save(f, 'JPEG', quality=QUALITY)
    except FileExistsError:
        raise Stop(f'Output already exists: {out}')
    print(f'[INFO] input: {kind}')
    print(f'[OK] {out} ({total}x{a.height})')


if __name__ == '__main__':
    try:
        main()
    except Stop as e:
        print(f'[ERROR] {e}', file=sys.stderr)
        sys.exit(1)
