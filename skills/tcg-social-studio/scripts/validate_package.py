"""v1: 配布範囲、ローカルリンク、個人パス、成果物混入をオフラインで確認。"""
from pathlib import Path
import argparse,ast,json,re

def validate(root):
    root=Path(root).resolve();errors=[];count=0
    for path in root.rglob('*'):
        if not path.is_file():continue
        rel=path.relative_to(root)
        if any(p in ('node_modules','.venv','__pycache__') for p in rel.parts):continue
        if path.suffix in ('.pyc',):continue
        count+=1
        if path.suffix.lower() in ('.mp4','.webp','.png','.jpg','.jpeg','.zip') or path.name.startswith('.env'):errors.append(str(rel)+': private/media file not expected')
        if path.suffix not in ('.md','.json','.js','.mjs','.html','.py','.yaml','.txt') and path.name!='.gitignore':continue
        text=path.read_text(encoding='utf-8-sig')
        # パターンそのものの実装を、実際のパスと混同しない。
        if re.search(r'[A-Z]:[/\\]Users[/\\][^/\\\s]+',text,re.I):errors.append(str(rel)+': machine-specific user path')
        if path.suffix=='.py':
            try:ast.parse(text)
            except SyntaxError as e:errors.append(str(rel)+': '+str(e))
        if path.suffix=='.json':
            try:json.loads(text)
            except ValueError as e:errors.append(str(rel)+': '+str(e))
        if path.suffix=='.md':
            for ref in re.findall(r'\]\(([^)]+)\)',text):
                if re.match(r'^(https?://|#)',ref):continue
                target=(path.parent/ref.split('#')[0]).resolve()
                if not target.is_relative_to(root):errors.append(str(rel)+': link outside package: '+ref)
                elif not target.exists():errors.append(str(rel)+': missing link: '+ref)
    return dict(files_checked=count,errors=errors)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',nargs='?',default=Path(__file__).resolve().parents[1]);a=ap.parse_args();r=validate(a.root);print(json.dumps(r,ensure_ascii=False,indent=2));raise SystemExit(bool(r['errors']))
