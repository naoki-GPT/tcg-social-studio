#!/usr/bin/env python3
"""v4: 参考投稿の原本（画像・動画）を制作フォルダへ取り込み、証拠（media-manifest.json）を残す。

使い方:
  python scripts/import_reference.py --post-url <URL> --expected <枚数> --out <制作フォルダ/reference> <ファイル1> <ファイル2> ...

- ファイルは指定した順番＝元の投稿の順番。01.jpg, 02.mp4 ... の連番でコピーする（元のファイルは動かさない）。
- sha256・バイト数・画像の実寸を media-manifest.json に記録する。
- 渡した数が --expected と違う／同じ中身のファイルが重複／0バイト／開けない画像 は失敗で止まる。
- 既にある出力フォルダには書かない。
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
IMAGE = {'.jpg': '.jpg', '.jpeg': '.jpg', '.png': '.png', '.webp': '.webp'}
VIDEO = {'.mp4': '.mp4', '.mov': '.mov', '.webm': '.webm', '.m4v': '.m4v'}


class Stop(Exception):
    pass


def find_ffmpeg():
    exe = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
    candidates = []
    if os.environ.get('FFMPEG_PATH'):
        candidates.append(Path(os.environ['FFMPEG_PATH']))
    candidates.append(SKILL / 'node_modules' / 'ffmpeg-static' / exe)
    for c in candidates:
        if c.is_file():
            return str(c)
    return shutil.which('ffmpeg')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def video_info(ffmpeg, path):
    """ffmpeg があれば動画の実寸と尺を読む。読めなければ None のまま。"""
    info = {'width': None, 'height': None, 'duration': None}
    if not ffmpeg:
        return info
    r = subprocess.run([ffmpeg, '-hide_banner', '-i', str(path)], capture_output=True)
    text = r.stderr.decode('utf-8', 'replace')
    line = next((s for s in text.splitlines() if 'Video:' in s), '')
    size = re.search(r'\b(\d{2,5})x(\d{2,5})\b', line)
    d = re.search(r'Duration: (\d+):(\d+):([\d.]+)', text)
    if not size:
        raise Stop(f'not a readable video: {path.name}')
    info['width'], info['height'] = int(size.group(1)), int(size.group(2))
    if d:
        info['duration'] = round(int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)), 3)
    return info


def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass
    ap = argparse.ArgumentParser(description='Import the original media of a reference post.')
    ap.add_argument('--post-url', required=True)
    ap.add_argument('--expected', required=True, type=int, help='number of media in the original post')
    ap.add_argument('--out', required=True, help='new folder, e.g. <work>/reference')
    ap.add_argument('files', nargs='*')
    a = ap.parse_args()

    if not re.match(r'^https?://[^\s/]+\.[^\s/]+', a.post_url):
        raise Stop('--post-url must be the http(s) URL of the reference post')
    if a.expected < 1:
        raise Stop('--expected must be 1 or more')
    if len(a.files) != a.expected:
        raise Stop(f'the post has {a.expected} media but {len(a.files)} file(s) were given. Get every original in order before importing.')
    out = Path(a.out).resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise Stop(f'Output already exists: {out}')

    try:
        from PIL import Image
    except ImportError:
        raise Stop('Pillow is not installed. Run: python -m pip install -r requirements.txt')

    ffmpeg = find_ffmpeg()
    digits = max(2, len(str(a.expected)))
    items, seen = [], {}
    for i, raw in enumerate(a.files, 1):
        src = Path(raw).resolve()
        if not src.is_file():
            raise Stop(f'file {i} not found: {raw}')
        ext = src.suffix.lower()
        if ext not in IMAGE and ext not in VIDEO:
            raise Stop(f'file {i}: unsupported type "{ext}" ({src.name}). Use jpg / png / webp / mp4 / mov / webm.')
        size = src.stat().st_size
        if size == 0:
            raise Stop(f'file {i} is empty (0 bytes): {src.name}')
        digest = sha256(src)
        if digest in seen:
            raise Stop(f'file {i} ({src.name}) has the same content as file {seen[digest]}. Each media of the post must be a different file.')
        seen[digest] = i
        item = {'index': i, 'file': f'{i:0{digits}d}{(IMAGE.get(ext) or VIDEO.get(ext))}', 'original_name': src.name,
                'kind': 'image' if ext in IMAGE else 'video', 'bytes': size, 'sha256': digest,
                'width': None, 'height': None}
        if ext in IMAGE:
            try:
                with Image.open(src) as im:
                    im.verify()
                with Image.open(src) as im:
                    item['width'], item['height'] = im.size
            except Exception as e:
                raise Stop(f'file {i} is not a readable image: {src.name}: {e}')
        else:
            item.update(video_info(ffmpeg, src))
        items.append((src, item))

    out.mkdir(parents=True, exist_ok=True)
    for src, item in items:
        dest = out / item['file']
        shutil.copyfile(src, dest)
        if sha256(dest) != item['sha256']:
            raise Stop(f'copy check failed: {dest}')
    manifest = {
        'post_url': a.post_url,
        'imported_at': datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds'),
        'expected': a.expected,
        'count': len(items),
        'items': [item for _, item in items],
    }
    (out / 'media-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    for _, item in items:
        dims = f"{item['width']}x{item['height']}" if item['width'] else 'size unknown'
        print(f"[OK] {item['file']} <- {item['original_name']} ({item['kind']}, {dims}, {item['bytes']} bytes)")
    print(f"[OK] {len(items)}/{a.expected} media -> {out}")
    print(f"[OK] {out / 'media-manifest.json'}")


if __name__ == '__main__':
    try:
        main()
    except Stop as e:
        print(f'[ERROR] {e}', file=sys.stderr)
        sys.exit(1)
