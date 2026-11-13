"""v2.0: Cutmatch方式で全フレームの差分・動きを計測し、境界候補を作る。

python scripts/analyze_reference_video.py reference.mp4 --out analysis
追加の原寸確認: --frames 0,29,30,31 --out detail
自動候補は字幕・被写体の動きも含む。カット確定・文字転記・音の確認は別工程。
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps


def write_sheets(video, indices, out, fps, timestamps):
    cap = cv2.VideoCapture(str(video))
    names = []
    for offset in range(0, len(indices), 18):
        subset = indices[offset:offset + 18]
        board = Image.new('RGB', (6 * 240, math.ceil(len(subset) / 6) * 454), '#171c23')
        draw = ImageDraw.Draw(board)
        for j, f in enumerate(subset):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f)
            ok, bgr = cap.read()
            if not ok: raise ValueError(f'Cannot decode frame {f}')
            pic = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            pic.save(out / f'frame-{f:06d}.jpg', quality=94)
            pic = ImageOps.contain(pic, (240, 426))
            x, y = j % 6 * 240, j // 6 * 454
            board.paste(pic, (x + (240-pic.width)//2, y+28))
            sec = timestamps[f] if timestamps else f/fps
            draw.text((x+5, y+7), f'f{f} / {sec:.4f}s', fill='white')
        name = f'sheet-{offset//18+1:03d}.jpg'
        board.save(out/name, quality=91)
        names.append(name)
    cap.release()
    return names


def analyze(video, out, sample_hz=4, frames=None):
    video, out = Path(video), Path(out)
    if not video.is_file(): raise FileNotFoundError(video)
    out.mkdir(parents=True, exist_ok=False)
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if not fps or not n: raise ValueError('動画を読み込めません')
    if frames is not None:
        cap.release()
        if any(type(f) is not int or f<0 or f>=n for f in frames): raise ValueError('Invalid frame')
        return {'sheets': write_sheets(video, sorted(set(frames)), out, fps, None), 'timestamp_basis': 'frame/fps; inspect source PTS for VFR'}
    previous = previous_hist = None
    rows, candidates, pts = [], [], []
    width = height = 0
    for f in range(n):
        ok, bgr = cap.read()
        if not ok: break
        height, width = bgr.shape[:2]
        # 元の縦横比を保持。動きは画面幅・高さに対する割合で出力する。
        scale = min(270/width, 480/height)
        frame = cv2.resize(bgr, (round(width*scale), round(height*scale)))
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0,1], None, [16,8], [0,180,0,256]); cv2.normalize(hist,hist)
        change = 0. if previous_hist is None else float(cv2.compareHist(previous_hist,hist,cv2.HISTCMP_BHATTACHARYYA))
        pts.append(float(cap.get(cv2.CAP_PROP_POS_MSEC))/1000)
        row = dict(frame=f, pts_s=pts[-1], diff=0., color_change=round(change,5), zoom=1., dx_pct=0.,dy_pct=0., rotation=0.,confidence=0.)
        if previous is not None:
            row['diff'] = round(float(np.mean(cv2.absdiff(gray,previous)))/255,5)
            estimates = []
            for mode in range(3):
                mask = np.zeros_like(gray)
                if mode==0: mask[:]=255
                elif mode==1: mask[:int(h*.38)]=255
                else: mask[:,:max(1,round(w*.2))]=255; mask[:,-max(1,round(w*.2)):]=255
                points = cv2.goodFeaturesToTrack(previous,160,.015,7,mask=mask)
                if points is None or len(points)<10: continue
                nxt,status,_ = cv2.calcOpticalFlowPyrLK(previous,gray,points,None,winSize=(25,25),maxLevel=3)
                if nxt is None or status is None: continue
                good = status.ravel()==1
                if good.sum()<8: continue
                mat, inliers = cv2.estimateAffinePartial2D(points[good],nxt[good],method=cv2.RANSAC,ransacReprojThreshold=1.6)
                if mat is None or inliers is None: continue
                z = math.hypot(mat[0,0],mat[1,0]); rot = math.degrees(math.atan2(mat[1,0],mat[0,0])); conf=float(inliers.mean())
                center=mat@np.array([w/2,h/2,1])
                if .85<z<1.18 and abs(rot)<8 and conf>.5:
                    estimates.append((conf+(.12 if mode else 0),z,(center[0]-w/2)/w*100,(center[1]-h/2)/h*100,rot,conf))
            if estimates:
                _,z,dx,dy,rot,conf=max(estimates)
                row.update(zoom=round(z,6),dx_pct=round(dx,4),dy_pct=round(dy,4),rotation=round(rot,4),confidence=round(conf,4))
            if (row['diff']>.07 and row['confidence']<.65) or row['diff']>.24 or change>.18: candidates.append(f)
        rows.append(row); previous=gray; previous_hist=hist
    cap.release()
    if len(rows)!=n: raise ValueError(f'Incomplete decode: expected {n}, decoded {len(rows)}')
    groups=[]
    for f in candidates:
        if groups and f-groups[-1][-1]<3: groups[-1].append(f)
        else: groups.append([f])
    cuts=[max(g,key=lambda f:rows[f]['diff']) for g in groups]
    monotonic=all(b>a for a,b in zip(pts,pts[1:]))
    cfr=monotonic and all(abs((b-a)-1/fps)<.002 for a,b in zip(pts,pts[1:]))
    indices=sorted(set(range(0,n,max(1,round(fps/sample_hz))))|{n-1}|{f+d for f in cuts for d in (-1,0,1) if 0<=f+d<n})
    sheets=write_sheets(video,indices,out,fps,pts if monotonic else None)
    result=dict(version='2.0',status='candidates_only',source_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),
                width=width,height=height,fps=fps,frames=n,duration_s=n/fps,pts_monotonic=monotonic,cfr_observed=cfr,
                timing_warning=None if cfr else 'VFR or unreadable timestamps: confirm decoder PTS before timing approval',
                cut_candidates=cuts,signals=rows,sheets=sheets,audio_review='pending',
                method='Every-frame difference, HSV histogram, LK optical flow + RANSAC in full/top/edge regions. Not a semantic cut detector. Camera and editing motion not distinguished.')
    (out/'signals.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return {k:result[k] for k in ('frames','fps','cut_candidates','sheets','cfr_observed')}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('video');ap.add_argument('--out',required=True);ap.add_argument('--sample-hz',type=float,default=4)
    ap.add_argument('--frames',help='原寸で追加確認する0始まりのフレーム番号、カンマ区切り')
    a=ap.parse_args()
    if not 0<a.sample_hz<=30: ap.error('sample-hz must be >0 and <=30')
    print(json.dumps(analyze(a.video,a.out,a.sample_hz,[int(x) for x in a.frames.split(',')] if a.frames else None),ensure_ascii=False))
