"""v1.9: 動画から抽出した縦コマの一覧と表紙（build）、参考と完成物を同じ時刻・同じ枚目で並べる比較画像（build_pairs）。"""
import argparse,math
from pathlib import Path
from PIL import Image,ImageDraw

def build(folder,out,cover=None):
    files=sorted(Path(folder).glob('frame-*.png'))
    if not files:raise ValueError('verify_video.mjsでコマを抽出してください')
    out=Path(out)
    if out.exists() or (cover and Path(cover).exists()):raise FileExistsError('既存成果物は上書きしません')
    with Image.open(files[0]) as first:
        w=240;h=round(first.height*w/first.width)
    columns=min(4,len(files));rows=math.ceil(len(files)/columns)
    sheet=Image.new('RGB',(columns*w,rows*(h+28)),'#eeeadd');draw=ImageDraw.Draw(sheet)
    for i,p in enumerate(files):
        with Image.open(p) as im:
            if im.width*h!=im.height*w and abs(im.width/im.height-w/h)>.002:raise ValueError('コマの比率が不一致')
            sheet.paste(im.convert('RGB').resize((w,h),Image.Resampling.LANCZOS),((i%columns)*w,(i//columns)*(h+28)+28))
        draw.text(((i%columns)*w+10,(i//columns)*(h+28)+8),str(i+1),fill='#132a21')
    out.parent.mkdir(parents=True,exist_ok=True);sheet.save(out,quality=94)
    if cover:
        with Image.open(files[0]) as im:im.convert('RGB').save(cover,quality=96)
    return sheet.size

def build_pairs(pairs,out,width=300,title=None):
    """pairs=[(ラベル, 参考の画像, 完成物の画像)]。左に参考、右に完成物を同じ縮尺で並べる。既存は上書きしない。"""
    if not pairs:raise ValueError('比べる組が無い')
    out=Path(out)
    if out.exists():raise FileExistsError('既存成果物は上書きしません')
    def fit(p):
        with Image.open(p) as im:
            im=im.convert('RGB');return im.resize((width,round(im.height*width/im.width)),Image.Resampling.LANCZOS)
    rows=[(label,fit(a),fit(b)) for label,a,b in pairs]
    gap,head=16,40;top=44 if title else 0
    rh=[max(a.height,b.height)+head for _,a,b in rows]
    sheet=Image.new('RGB',(width*2+gap*3,top+sum(rh)+gap*len(rows)),'#f2efe6');d=ImageDraw.Draw(sheet)
    if title:d.text((gap,14),title,fill='#132a21')
    d.text((gap,top+4),'REFERENCE',fill='#8a1c1c');d.text((width+gap*2,top+4),'OURS',fill='#1c3f8a')
    y=top+18
    for (label,a,b),h in zip(rows,rh):
        d.text((gap,y+6),str(label),fill='#132a21')
        sheet.paste(a,(gap,y+head-12));sheet.paste(b,(width+gap*2,y+head-12));y+=h+gap
    out.parent.mkdir(parents=True,exist_ok=True);sheet.save(out,quality=92)
    return sheet.size

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('folder');ap.add_argument('--out',required=True);ap.add_argument('--cover');a=ap.parse_args();print('[OK]',build(a.folder,a.out,a.cover))
