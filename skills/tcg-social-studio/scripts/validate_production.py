"""v2.0: 完成宣言の前に、需要・行動・全参考・出力・比較記録を検査する。

python scripts/validate_production.py production-contract.json --out checks/acceptance.json
書類の整合と不足を検査する。真の需要・見た目の一致・売上を自動保証しない。
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path


def stamp(value):
    d=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if d.tzinfo is None: raise ValueError('timezone required')
    return d


def filled(value):
    return isinstance(value,str) and bool(value.strip()) and not any(x in value for x in ('EDIT:','TODO:','YOUR SHOP'))


def validate(contract, base, now=None):
    base=Path(base).resolve(); now=now or datetime.now(timezone.utc); errors=[]
    def err(msg): errors.append(msg)
    def field(obj,key,scope):
        if not filled(obj.get(key)): err(scope+'.'+key+': missing')
    def file(value,label,sha=None):
        if not filled(value): err(label+': file missing');return None
        p=Path(value)
        if p.is_absolute() or not (base/p).resolve().is_relative_to(base): err(label+': use a relative path within production folder');return None
        p=(base/p).resolve()
        if not p.is_file() or p.stat().st_size==0: err(label+': file not found or empty');return None
        if sha is not None and (not filled(sha) or hashlib.sha256(p.read_bytes()).hexdigest()!=sha): err(label+': SHA256 mismatch/missing')
        return p
    def read_record(value,label):
        p=file(value,label)
        if not p:return None
        try:
            d=json.loads(p.read_text(encoding='utf-8-sig'))
            if not isinstance(d,dict):raise ValueError('object required')
            return d
        except ValueError:err(label+': invalid JSON object');return None
    def fresh(value,hours,label):
        try:
            age=(now-stamp(value)).total_seconds()/3600
            if not 0<=age<=hours:raise ValueError('stale/future')
        except (ValueError,TypeError):err(label+': invalid, future or stale timestamp')
    def window(value,cap,label):
        if type(value) not in (int,float) or not math.isfinite(value) or not 0<value<=cap:
            err(label+': invalid window');return cap
        return value
    if contract.get('version')!='2.0':err('version: expected 2.0')
    if contract.get('mode')!='sales':err('mode: only sales completion is supported; prototypes do not pass this gate')
    objective=contract.get('objective') or {}
    for key in ('audience','product','benefit','why_now','action','destination','cta_text'):field(objective,key,'objective')
    caption=file(objective.get('caption_file'),'objective.caption_file')
    if caption:
        body=caption.read_text(encoding='utf-8-sig')
        if objective.get('cta_text') not in body:err('caption: exact CTA sentence is absent from body')
        if any(x in body for x in ('EDIT:','TODO:','YOUR SHOP')):err('caption: unresolved placeholder')
    selection=contract.get('selection') or {}
    if selection.get('decision')!='adopt':err('selection: product not adopted')
    for k in ('reason','goal'):field(selection,k,'selection')
    file(selection.get('alternatives_file'),'selection.alternatives_file')
    review=read_record(selection.get('review_file'),'selection.review_file')
    if review:
        if review.get('result')!='supported':err('selection.review: demand not supported')
        for k in ('repeated_demand','target_market_fit','alternative_comparison','limitations'):field(review,k,'selection.review')
    maxdays=window(selection.get('max_age_days',7),30,'selection.max_age_days')
    evidence=selection.get('evidence') or []
    if not evidence:err('selection.evidence: missing')
    ids=set();qualified=[]
    for i,row in enumerate(evidence):
        tag=f'evidence[{i}]'
        for k in ('id','market','source_url','definition','period_start','period_end'):field(row,k,tag)
        if row.get('id') in ids:err(tag+': duplicate evidence id')
        ids.add(row.get('id'))
        file(row.get('record_file'),tag+'.record_file')
        fresh(row.get('observed_at'),maxdays*24,tag+'.observed_at')
        try:
            start=stamp(row.get('period_start'));end=stamp(row.get('period_end'))
            if start>end or end>now or (now-end).total_seconds()>maxdays*86400:raise ValueError('period')
        except (ValueError,TypeError):err(tag+': invalid/stale observation period')
        if not str(row.get('source_url','')).startswith('https://') and row.get('kind')!='own_product_inquiry':err(tag+': HTTPS source required')
        if row.get('product_match') is not True:err(tag+': exact product/language/condition not matched')
        if row.get('kind') in ('completed_sale','official_sales_aggregate','own_product_inquiry') and row.get('product_match') is True:
            qualified.append(row.get('id'))
    if not qualified:err('demand: ranks/likes/asking prices alone do not support buying demand')
    if review and not set(review.get('evidence_ids') or []).intersection(qualified):err('selection.review: no qualifying evidence used')
    price=contract.get('price_claim') or {}
    if price.get('required') is True:
        fresh(price.get('observed_at'),window(price.get('max_age_hours',24),168,'price.max_age_hours'),'price.observed_at')
        comp=read_record(price.get('comparison_file'),'price.comparison_file')
        if price.get('material_advantage') is not True:err('price: meaningful buyer advantage not established')
        field(price,'reason','price')
        if comp:
            if comp.get('sample') is True:err('price: example figures cannot be published')
            axis=comp.get('axis')
            if axis not in ('same_item_markets','language_editions','same_item_time'):err('price: comparison axis missing')
            for k in ('identity_and_condition','currency_and_unit','price_basis','costs_and_limitations','buyer_advantage_reason'):field(comp,k,'price.comparison')
            for side in ('left','right'):
                x=comp.get(side) or {}; v=x.get('amount')
                if type(v) not in (int,float) or not math.isfinite(v) or v<=0:err('price.'+side+': positive amount required')
                file(x.get('record_file'),'price.'+side+'.record_file')
            left=(comp.get('left') or {}).get('amount');right=(comp.get('right') or {}).get('amount')
            # left=比較基準、right=提案条件。安値/値下がり訴求は同通貨・単位で正の差が必要。
            if comp.get('claim') in ('cheaper','price_drop') and type(left) in (int,float) and type(right) in (int,float) and right>=left:
                err('price: cheaper/drop claim has no positive difference')
    reference=contract.get('reference') or {}; kind=reference.get('kind')
    media=reference.get('media') or [];expected=reference.get('expected_count')
    if type(expected) is not int or expected<1:
        err('reference.expected_count: positive integer required');expected=0
    if len(media)!=expected:err('reference: incomplete source count')
    indices=[m.get('position') for m in media]
    if type(expected) is int and sorted(i for i in indices if type(i) is int)!=list(range(1,expected+1)):err('reference: missing/duplicate source positions')
    for i,m in enumerate(media):file(m.get('file'),f'reference.media[{i}]',m.get('sha256',''))
    file(reference.get('full_review_file'),'reference.full_review_file')
    breakdown=read_record(reference.get('breakdown_file'),'reference.breakdown_file')
    units=[]
    if breakdown:
        units=breakdown.get('units') or []
        if breakdown.get('full_reference_reviewed') is not True or breakdown.get('status')!='reviewed':err('breakdown: full reference review pending')
        if breakdown.get('kind')!=kind:err('breakdown: kind mismatch')
        if breakdown.get('unresolved_differences'):err('breakdown: unresolved differences')
        if not units:err('breakdown: no units')
        if kind in ('carousel','image'):
            if len(units)!=expected or [u.get('source_index') for u in units]!=list(range(1,(expected or 0)+1)):err('breakdown: incomplete slide mapping')
        elif kind=='video':
            fps=breakdown.get('fps');frames=breakdown.get('duration_frames')
            if type(fps) not in (int,float) or fps<=0 or type(frames) is not int or frames<1:err('breakdown: invalid frame timing')
            end=0
            for u in units:
                a,b=u.get('start_frame'),u.get('end_frame')
                if type(a) is not int or type(b) is not int or a!=end or b<=a:err('breakdown: shot gap, overlap or invalid frame range')
                end=b
            if end!=frames:err('breakdown: does not cover complete video')
            if breakdown.get('audio_review') not in ('reviewed','verified_no_audio'):err('breakdown: audio review pending')
            for track in ('captions','motion','effects','audio'):
                if track not in (breakdown.get('tracks') or {}):err('breakdown: missing '+track+' track')
        else:err('reference.kind: unknown')
        for i,u in enumerate(units):
            for k in ('id','role','onscreen_text','replacement'):field(u,k,f'unit[{i}]')
            if not all(filled((u.get('design') or {}).get(k)) for k in ('background','typography','geometry','decorations')):err(f'unit[{i}]: design measurements missing')
    outputs=contract.get('outputs') or []
    if len(outputs)!=(1 if kind=='video' else expected):err('outputs: count differs from reference')
    ids_out=[o.get('reference_position') for o in outputs]
    if kind in ('carousel','image') and ids_out!=list(range(1,(expected or 0)+1)):err('outputs: order/mapping differs from reference')
    for i,o in enumerate(outputs):
        p=file(o.get('file'),f'outputs[{i}]',o.get('sha256',''))
        if p:
            try:
                if kind in ('carousel','image'):
                    from PIL import Image
                    with Image.open(p) as im:im.verify()
                elif kind=='video':
                    with p.open('rb') as f:header=f.read(32)
                    if p.suffix.lower()!='.mp4' or b'ftyp' not in header:raise ValueError('not MP4')
            except Exception:err(f'outputs[{i}]: unreadable or wrong media type')
    qa=contract.get('qa') or {}
    if qa.get('unresolved_differences'):err('qa: unresolved differences')
    for key in ('visual_result','technical_result'):
        if qa.get(key)!='pass':err('qa.'+key+': pending/fail')
    for key in ('paired_review_file','full_visual_review_file','technical_report_file'):file(qa.get(key),'qa.'+key)
    return {'version':'2.0','checked_at':now.isoformat(),'structural_pass':not errors,'errors':errors,
            'limits':'Files and declarations checked. Does not prove market truth, visual fidelity, copyright clearance, or business results.'}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('contract');ap.add_argument('--out',required=True);a=ap.parse_args()
    p=Path(a.contract);result=validate(json.loads(p.read_text(encoding='utf-8-sig')),p.parent)
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(not result['structural_pass'])
