"""v1.0: Muse引き継ぎのローカル検査。ネット接続・ブラウザー・投稿なし。

--check-snapshot は配布時点のファイル一致を追加確認する。
改修後はこのオプションを外し、変更内容をGitで確認する。
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-snapshot', action='store_true')
    args = parser.parse_args()
    if args.check_snapshot:
        manifest = json.loads((ROOT / 'docs/PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
        count = 0
        for package in manifest['packages']:
            for relative, expected in package['files'].items():
                path = ROOT / package['path'] / relative
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    raise SystemExit('Package snapshot mismatch: ' + package['path'] + '/' + relative)
                count += 1
        print('Package snapshot hashes match:', count, flush=True)
    studio = ROOT / 'skills/tcg-social-studio'
    python = [sys.executable, '-X', 'utf8', '-B']
    commands = []
    for package in ('skills/tcg-social-studio', 'skills/tcg-social-intake', 'experiments/stage2/tcg-social-select'):
        commands.append(python + [str(studio / 'scripts/validate_package.py'), str(ROOT / package)])
    for test in ('test_tools.py', 'test_formats.py', 'test_v20.py', 'test_import_reference_media.py'):
        commands.append(python + [str(studio / 'scripts' / test)])
    commands.append(python + [str(ROOT / 'skills/tcg-social-intake/scripts/test_validate_intake.py')])
    node = shutil.which('node')
    if not node:
        raise SystemExit('Node.jsが見つかりません。Python検査だけで全検査成功にしません。')
    commands.append([node, '--test', str(studio / 'scripts/runtime.test.mjs')])
    for command in commands:
        print('Running:', Path(command[-1]).name, flush=True)
        result = subprocess.run(command, cwd=ROOT, timeout=90)
        if result.returncode:
            raise SystemExit(result.returncode)
    print('Offline checks passed. Rendering, image generation and Muse integrations are not tested.', flush=True)


if __name__ == '__main__':
    main()
