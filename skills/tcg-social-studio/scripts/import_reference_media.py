"""v2.2: Muse等から受け取ったローカルの全参考素材を順番・ハッシュ付きで取り込む。

外部通信・契約・認証設定は不要。原本を変更せず新しい出力先へコピーする。
例: python scripts/import_reference_media.py media-input.json --out reference-v1
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

EXTENSIONS = {'image': {'.jpg', '.jpeg', '.png', '.webp', '.gif'},
              'video': {'.mp4', '.mov', '.webm', '.m4v'}}


def entries(record):
    kind = record.get('kind')
    files = record.get('files')
    expected = record.get('expected_count')
    if kind not in ('image', 'carousel', 'video'):
        raise ValueError('kind must be image/carousel/video')
    if type(expected) is not int or expected < 1 or not isinstance(files, list) or len(files) != expected:
        raise ValueError('All original files and expected_count are required')
    if (kind == 'carousel' and expected < 2) or (kind != 'carousel' and expected != 1):
        raise ValueError('Unexpected reference count')
    if [f.get('position') for f in files] != list(range(1, expected + 1)):
        raise ValueError('Positions must be unique and ordered from 1')
    for item in files:
        if not isinstance(item.get('path'), str) or not item['path'].strip():
            raise ValueError('Local file path required')
        if '://' in item['path']:
            raise ValueError('Supply a local file; remote URLs are not imported')
        media_kind = item.get('kind')
        if media_kind not in EXTENSIONS or (kind != 'carousel' and kind != media_kind):
            raise ValueError('Media kind mismatch')
        if Path(item['path']).suffix.lower() not in EXTENSIONS[media_kind]:
            raise ValueError('Unsupported media extension')
        yield dict(item, total=expected)


def import_media(input_path, out):
    input_path, out = Path(input_path).resolve(), Path(out).resolve()
    record = json.loads(input_path.read_text(encoding='utf-8-sig'))
    todo, resolved = list(entries(record)), []
    if out.exists():
        raise FileExistsError('Use a new output directory')
    seen = set()
    for item in todo:
        source = (input_path.parent / item['path']).resolve()
        if not source.is_file():
            raise FileNotFoundError('Reference source is missing: ' + item['path'])
        if source in seen:
            raise ValueError('One local file cannot stand in for multiple original pages')
        seen.add(source)
        if source.stat().st_size == 0:
            raise ValueError('Empty reference file')
        if item['kind'] == 'image':
            from PIL import Image
            with Image.open(source) as im:
                im.verify()
        resolved.append((item, source))
    out.mkdir(parents=True, exist_ok=False)
    media = []
    for item, source in resolved:
        name = f"{item['position']:02d}" + source.suffix.lower()
        target = out / name
        shutil.copyfile(source, target)
        sha = hashlib.sha256(target.read_bytes()).hexdigest()
        if sha != hashlib.sha256(source.read_bytes()).hexdigest():
            raise ValueError('Source changed during import; do not use this output')
        media.append({'position': item['position'], 'kind': item['kind'], 'file': name,
                      'sha256': sha, 'bytes': target.stat().st_size})
    result = {'version': '2.2', 'reference_url': record.get('reference_url'),
              'reference_id': record.get('reference_id'), 'expected_count': len(todo),
              'complete': True, 'media': media, 'visual_review': 'not_reviewed',
              'video_decode_review': 'not_reviewed'}
    (out / 'media-manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    result = import_media(args.input, args.out)
    print(json.dumps({'imported': len(result['media']), 'visual_review': result['visual_review']}))
