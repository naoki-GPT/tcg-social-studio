"""v2.0: 過去の失敗を再発させないための回帰検査（架空データ・通信なし）。"""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from PIL import Image

from build_from_recipe import build,check_content
from recipe_card import load,validate_card
from compare_reference import run_slides,default_times,natural
from import_reference_media import entries
from validate_production import validate

ROOT=Path(__file__).resolve().parents[1]
NOW=datetime(2026,11,12,0,0,tzinfo=timezone.utc)


def fixture(base):
    c=load(ROOT/'templates/production-contract.example.json')
    (base/'record.txt').write_text('Offline test record; not market evidence',encoding='utf-8')
    (base/'caption.md').write_text('DM TEST for details.',encoding='utf-8')
    h=hashlib.sha256((base/'record.txt').read_bytes()).hexdigest()
    c['objective']={k:'TEST' for k in ('audience','product','benefit','why_now','action','destination')}
    c['objective'].update(cta_text='DM TEST for details.',caption_file='caption.md')
    evidence=dict(id='test1',kind='completed_sale',market='TEST',product_match=True,observed_at='2026-11-11T00:00:00Z',period_start='2026-10-13T00:00:00Z',period_end='2026-11-11T00:00:00Z',source_url='https://example.com/test',record_file='record.txt',definition='test fixture')
    c['selection'].update(decision='adopt',reason='TEST',goal='TEST',alternatives_file='record.txt',review_file='review.json',evidence=[evidence])
    review={k:'TEST' for k in ('repeated_demand','target_market_fit','alternative_comparison','limitations')};review.update(result='supported',evidence_ids=['test1'])
    (base/'review.json').write_text(json.dumps(review),encoding='utf-8')
    c['reference'].update(kind='image',expected_count=1,media=[dict(position=1,file='record.txt',sha256=h)],full_review_file='record.txt',breakdown_file='breakdown.json')
    b=dict(kind='image',status='reviewed',full_reference_reviewed=True,units=[dict(id='s1',source_index=1,onscreen_text='none in this fixture',role='TEST',replacement='TEST',design={k:'TEST' for k in ('background','typography','geometry','decorations')})])
    (base/'breakdown.json').write_text(json.dumps(b),encoding='utf-8')
    Image.new('RGB',(20,25),'blue').save(base/'output.png')
    c['outputs']=[dict(reference_position=1,file='output.png',sha256=hashlib.sha256((base/'output.png').read_bytes()).hexdigest())]
    c['qa'].update(visual_result='pass',technical_result='pass',paired_review_file='record.txt',full_visual_review_file='record.txt',technical_report_file='record.txt')
    return c


class V20Test(unittest.TestCase):
    def test_missing_carousel_children_is_failure(self):
        with self.assertRaises(ValueError):list(entries({'kind':'carousel','expected_count':9,'files':[]}))
        with self.assertRaises(ValueError):list(entries({'kind':'image','expected_count':1,
            'files':[{'position':1,'kind':'image','path':'https://example.com/x.jpg'}]}))

    def test_incomplete_slides_not_repeat_last_or_silently_drop(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'ref').mkdir();(p/'ours').mkdir()
            for n in (1,2):Image.new('RGB',(20,25)).save(p/'ref'/f'{n}.png')
            Image.new('RGB',(20,25)).save(p/'ours'/'1.png')
            with self.assertRaises(ValueError):run_slides(SimpleNamespace(ref=p/'ref',ours=p/'ours',out=p/'compare'))
            self.assertFalse((p/'compare').exists())
            self.assertEqual([x.name for x in sorted([Path('10.png'),Path('2.png')],key=natural)],['2.png','10.png'])

    def test_short_video_times_stay_inside_duration(self):
        self.assertTrue(all(0<=x<.4 for x in default_times(.4)))

    def test_recipe_blocks_negative_product_and_path_traversal(self):
        card=load(ROOT/'templates/recipe-card.example.slideshow.json')
        product=next(l for s in card['slides'] for l in s['layers'] if l['element']=='product');product['product']=-1
        card['reference']['ref_id']='../outside'
        self.assertTrue(validate_card(card))
        self.assertTrue(check_content(card,{'texts':{},'products':[{'image':'x'}]}))

    def test_observed_hard_cut_allowed_but_silent_restart_fails(self):
        card=load(ROOT/'templates/recipe-card.example.video.json')
        a=next(l for l in card['timeline'] if l['element']=='product');b=copy.deepcopy(a)
        a['t_end']=4;b['t_start']=4;b['t_end']=8;b.pop('move',None);card['timeline'].append(b)
        self.assertTrue(any('出直す' in e for e in validate_card(card)))
        b.update(reference_cut=True,observed='Source frames 119/120 show an actual hard cut')
        self.assertFalse(any('出直す' in e for e in validate_card(card)))

    def test_caption_only_does_not_force_extra_cta_page(self):
        card=load(ROOT/'templates/recipe-card.example.slideshow.json');card['cta_placement']=['caption']
        for s in card['slides']:s['layers']=[l for l in s['layers'] if l.get('style')!='cta']
        content={'texts':{l['slot']:'TEST' for s in card['slides'] for l in s['layers'] if l['element']=='text'},'products':[{'image':'x'},{'image':'y'}]}
        self.assertNotIn('カードにCTAの文字レイヤーが無い',check_content(card,content))

    def test_gate_valid_then_rank_stale_cta_partial_and_hash_failures(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);c=fixture(p)
            self.assertTrue(validate(c,p,NOW)['structural_pass'])
            for mutate,word in [
                (lambda d:d['selection']['evidence'][0].update(kind='social_likes'),'demand:'),
                (lambda d:d['selection']['evidence'][0].update(observed_at='2025-01-01T00:00:00Z'),'stale'),
                (lambda d:d['objective'].update(cta_text='Not in caption'),'CTA'),
                (lambda d:d['reference'].update(expected_count=9),'count'),
                (lambda d:d['qa']['unresolved_differences'].append('wrong font'),'unresolved'),
                (lambda d:d['outputs'][0].update(sha256='bad'),'SHA256')]:
                bad=copy.deepcopy(c);mutate(bad);result=validate(bad,p,NOW)
                self.assertFalse(result['structural_pass']);self.assertIn(word,' '.join(result['errors']))

    def test_price_declared_cheap_without_positive_gap_fails(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);c=fixture(p)
            comp={k:'TEST' for k in ('identity_and_condition','currency_and_unit','price_basis','costs_and_limitations','buyer_advantage_reason')}
            comp.update(axis='language_editions',claim='cheaper',left={'amount':100,'record_file':'record.txt'},right={'amount':101,'record_file':'record.txt'})
            (p/'price.json').write_text(json.dumps(comp),encoding='utf-8')
            c['price_claim'].update(required=True,comparison_file='price.json',observed_at='2026-11-11T23:00:00Z',material_advantage=True,reason='TEST')
            self.assertIn('no positive difference',' '.join(validate(c,p,NOW)['errors']))


if __name__=='__main__':unittest.main()
