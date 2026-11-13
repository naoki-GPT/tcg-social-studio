"""v1: 同一アカウント・形式・指標の公開反応を、重複と欠損を分けて集計。"""
import argparse
from collections import defaultdict
from datetime import datetime,date
import json,math
from pathlib import Path
from statistics import median

def timestamp(s):
    t=datetime.fromisoformat(s.replace('Z','+00:00'))
    if t.tzinfo is None: raise ValueError('日時にはタイムゾーンが必要です')
    return t

def analyze(data):
    start,end=(date.fromisoformat(data['window'][k]) for k in ('start','end'))
    if start>end: raise ValueError('期間の開始が終了より後です')
    age=data.get('min_age_days',7)
    if not isinstance(age,(int,float)) or age<0: raise ValueError('min_age_days must be nonnegative')
    latest={};excluded=[]; groups=defaultdict(list);all_groups=set()
    for i,row in enumerate(data['rows']):
        r=dict(row);r['_row']=i
        key=(r['account'],r['post_id'])
        observed=timestamp(r['observed_at'])
        if key in latest:
            old=latest[key]
            if observed>=timestamp(old['observed_at']):
                excluded.append({'row':old['_row'],'reason':'同投稿の古い取得または同時刻の重複'});latest[key]=r
            else: excluded.append({'row':i,'reason':'同投稿の古い取得'})
        else:latest[key]=r
    for r in latest.values():
        key=(r['account'],r.get('format'),r.get('metric_name'));all_groups.add(key)
        reason=[];pub=timestamp(r['published_at']);obs=timestamp(r['observed_at'])
        if not start<=pub.date()<=end:reason.append('期間外')
        if (obs-pub).total_seconds()<age*86400:reason.append('公開からの経過日数不足または未来日')
        if not r.get('format') or not r.get('metric_name'):reason.append('形式・指標不明')
        for flag in ('pinned','promotion','giveaway'):
            if r.get(flag) is not False:reason.append(flag+('あり' if r.get(flag) is True else '不明'))
        value=r.get('metric_value')
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:reason.append('指標不明・不正')
        if reason:excluded.append({'row':r['_row'],'post_id':r['post_id'],'reason':reason})
        else:groups[key].append(r)
    result=[]
    for key in sorted(all_groups,key=lambda k:tuple(str(x) for x in k)):
        rows=groups[key];values=[x['metric_value'] for x in rows]
        result.append(dict(account=key[0],format=key[1],metric_name=key[2],n=len(rows),median=median(values) if values else None,maximum=max(values) if values else None,publication_range=[min(x['published_at'] for x in rows),max(x['published_at'] for x in rows)] if rows else None,observed_range=[min(x['observed_at'] for x in rows),max(x['observed_at'] for x in rows)] if rows else None,post_ids=[x['post_id'] for x in rows]))
    return dict(window=data['window'],min_age_days=age,input_rows=len(data['rows']),unique_account_posts=len(latest),unique_posts=len({r['post_id'] for r in latest.values()}),groups=result,excluded=excluded,note='公開反応の条件付き比較。成長率・売上・因果関係ではない。日時範囲は原表記。')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input',type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    result=analyze(json.loads(a.input.read_text(encoding='utf-8')))
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print('[OK] groups:',len(result['groups']),'excluded:',len(result['excluded']))
