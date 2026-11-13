"""v1.0: 前提不備・未決・工程ごとの停止を検証する。外部サービス不要。"""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from validate_intake import REQUIRED, validate


def valid_record():
    data = json.loads((Path(__file__).resolve().parents[1] / 'assets/intake.template.json').read_text(encoding='utf-8'))
    data['recorded_on'] = '2026-11-13'
    data['sources'] = [dict(id='USER', kind='conversation', locator='今回の依頼', excerpt='共通試作を1企画作る', checked_on='2026-11-13')]
    for key in REQUIRED:
        data['brief'][key] = dict(status='confirmed', value=1 if key == 'concept_count' else '検査用の条件', source_ids=['USER'], note='検査用の架空記録。')
    data['handoff']['ready_for_selection'] = True
    return data


class IntakeTests(unittest.TestCase):
    def test_stepwise_does_not_continue_even_when_ready(self):
        result = validate(valid_record())
        self.assertTrue(result['ready_for_selection'])
        self.assertFalse(result['continue_now'])

    def test_full_request_can_continue(self):
        data = valid_record()
        data['execution_mode'] = 'full_production'
        data['handoff']['stop_after_this_stage'] = False
        self.assertTrue(validate(data)['continue_now'])

    def test_unknown_audience_is_a_blocker_not_bad_record(self):
        data = valid_record()
        data['brief']['audience'].update(status='unknown', value=None, source_ids=[])
        data['handoff']['ready_for_selection'] = False
        result = validate(data)
        self.assertTrue(result['record_valid'])
        self.assertFalse(result['ready_for_selection'])
        self.assertIn('audience', result['blockers'])

    def test_invented_project_is_not_accepted_as_assumption(self):
        data = valid_record()
        data['brief']['project']['status'] = 'proposed'
        data['handoff']['ready_for_selection'] = False
        self.assertIn('project', validate(data)['blockers'])

    def test_reasoned_audience_assumption_is_visible(self):
        data = valid_record()
        data['brief']['audience'].update(status='proposed', source_ids=[])
        result = validate(data)
        self.assertTrue(result['ready_for_selection'])
        self.assertIn('audience', result['assumptions'])

    def test_unresolved_sales_terms_do_not_block_research(self):
        data = valid_record()
        self.assertEqual(data['brief']['sales_terms']['status'], 'deferred')
        self.assertTrue(validate(data)['ready_for_selection'])

    def test_confirmed_value_requires_evidence(self):
        data = valid_record()
        for refs in ([], ['UNREAD']):
            case = deepcopy(data)
            case['brief']['objective']['source_ids'] = refs
            self.assertFalse(validate(case)['record_valid'])

    def test_count_does_not_accept_boolean_or_fraction(self):
        data = valid_record()
        for count in (True, 0, -1, 1.5, '1'):
            case = deepcopy(data)
            case['brief']['concept_count']['value'] = count
            self.assertFalse(validate(case)['record_valid'])

    def test_missing_field_cannot_advance(self):
        data = valid_record()
        del data['brief']['product_scope']
        self.assertFalse(validate(data)['ready_for_selection'])

    def test_stepwise_stop_cannot_be_disabled(self):
        data = valid_record()
        data['handoff']['stop_after_this_stage'] = False
        result = validate(data)
        self.assertFalse(result['record_valid'])
        self.assertFalse(result['continue_now'])

    def test_blocking_question_cannot_be_hidden_by_ready_flag(self):
        data = valid_record()
        data['open_questions'] = [dict(question='対象案件が矛盾している', blocks_selection=True, source_ids=[])]
        result = validate(data)
        self.assertFalse(result['ready_for_selection'])
        self.assertTrue(result['blockers'])

    def test_bad_field_type_reports_error(self):
        data = valid_record()
        data['brief']['audience']['status'] = ['confirmed']
        self.assertFalse(validate(data)['record_valid'])


if __name__ == '__main__':
    unittest.main()
