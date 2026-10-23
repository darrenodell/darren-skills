import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / 'plugins/market-release-watch/skills/market-release-watch/scripts'
if not SCRIPT_ROOT.exists():
    SCRIPT_ROOT = Path(__file__).resolve().parent / 'market-release-watch-v1.1.0/skills/market-release-watch/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_ROOT / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


renderer = load('render_report')
poller = load('poll_plan')


def report():
    return {'schema_version': 1, 'report_id': 'synthetic-test', 'title': 'Synthetic release test',
            'session_date_et': '2026-10-23', 'as_of_utc': '2026-10-23T14:02:00Z',
            'local_timezone': 'Asia/Manila',
            'assessment': {'score': 4, 'label': 'BUY', 'confidence': 'Low', 'phase': 'provisional',
                           'scope': 'SPY / broad U.S. equities', 'horizon': 'Next 30–120 minutes',
                           'evaluated_at_utc': '2026-10-23T14:02:00Z', 'reassess_at_utc': '2026-10-23T14:30:00Z',
                           'evidence_event_ids': ['michigan'], 'summary': 'Synthetic bullish research judgment.',
                           'action': 'Treat as a provisional bullish lean.', 'reasons': ['Growth improved.', 'Prices eased.'],
                           'contrary_risk': 'Prices could reverse.', 'invalidation': 'Fresh equities reverse lower.',
                           'evaluator': 'synthetic fixture, not a live analyst'},
            'events': [{'id': 'michigan', 'title': 'Michigan sentiment', 'period': 'October 2026', 'vintage': 'final',
                        'scheduled_at_utc': '2026-10-23T14:00:00Z', 'status': 'primary_verified',
                        'metrics': [{'name': 'Sentiment', 'actual': 50.0, 'consensus': 46.3, 'prior': 46.3,
                                     'unit': 'index points', 'comparison': 'Same-month preliminary'}],
                        'source_ids': ['publisher'], 'notes': 'Synthetic test data only.'}],
            'sources': [{'id': 'publisher', 'title': 'Synthetic publisher', 'url': 'https://example.com/release',
                         'retrieved_at_utc': '2026-10-23T14:01:00Z', 'note': 'Fixture, not evidence.'}],
            'market_reaction': {'status': 'Prices unavailable.', 'observations': [], 'equity_confirmation': 'unavailable'},
            'limitations': ['Unvalidated research rubric.'], 'next_checks': ['Recheck fresh quotes.']}


class SignalReportTests(unittest.TestCase):
    def test_provisional_call_renders_without_quotes_and_preserves_evidence(self):
        data = report()
        html = renderer.render(data)
        self.assertIn('BUY <small>4 / 5</small>', html)
        self.assertIn('Low confidence', html)
        self.assertIn('10:00 PM', html)
        self.assertIn('Same-month preliminary', html)
        self.assertIn('Synthetic test data only.', html)
        self.assertIn('Content-Security-Policy', html)
        self.assertNotIn('<script', html)

    def test_pending_report_cannot_become_directional(self):
        data = report()
        data['events'][0].update(status='scheduled', scheduled_at_utc='2026-10-23T14:10:00Z')
        data['events'][0]['metrics'][0]['actual'] = None
        with self.assertRaisesRegex(ValueError, 'released evidence'):
            renderer.render(data)
        data['assessment'].update(score=3, label='WAIT', phase='pre_release', evidence_event_ids=[])
        self.assertIn('WAIT <small>3 / 5</small>', renderer.render(data))

    def test_unverified_actual_and_wrong_vintage_boundary_fail(self):
        data = report()
        data['events'][0]['status'] = 'due_not_verified'
        with self.assertRaisesRegex(ValueError, 'cannot contain actuals'):
            renderer.render(data)

    def test_source_qualification_caps_signal(self):
        data = report()
        data['events'][0]['status'] = 'secondary_reported'
        renderer.validate(data)
        data['assessment'].update(score=5, label='STRONG BUY', confidence='High', phase='confirmed')
        with self.assertRaises(ValueError):
            renderer.render(data)

    def test_primary_confirmed_call_needs_fresh_aligned_quotes(self):
        data = report()
        data['assessment'].update(score=5, label='STRONG BUY', confidence='High', phase='confirmed')
        data['market_reaction'].update(equity_confirmation='bullish', observations=[{
            'instrument': 'SPY', 'change': 0.3, 'unit': '%', 'baseline_at_utc': '2026-10-23T13:59:00Z',
            'observed_at_utc': '2026-10-23T14:01:00Z', 'feed': 'synthetic same-feed trades', 'note': 'Fixture.'}])
        renderer.validate(data)
        data['market_reaction']['equity_confirmation'] = 'bearish'
        with self.assertRaisesRegex(ValueError, 'contradicts'):
            renderer.validate(data)
        data['market_reaction']['equity_confirmation'] = 'bullish'
        data.update(as_of_utc='2026-10-23T14:12:00Z')
        data['assessment']['evaluated_at_utc'] = '2026-10-23T14:12:00Z'
        with self.assertRaisesRegex(ValueError, 'fresh comparable'):
            renderer.validate(data)

    def test_expired_call_is_not_a_current_buy(self):
        data = report()
        data.update(as_of_utc='2026-10-23T17:00:00Z')
        data['assessment'].update(evaluated_at_utc='2026-10-23T17:00:00Z', reassess_at_utc='2026-10-23T17:03:00Z')
        with self.assertRaisesRegex(ValueError, 'two-hour horizon'):
            renderer.validate(data)

    def test_no_consensus_cannot_claim_confirmed_call(self):
        data = report()
        data['events'][0]['metrics'][0]['consensus'] = None
        renderer.validate(data)
        data['assessment'].update(phase='confirmed', confidence='Medium')
        with self.assertRaises(ValueError):
            renderer.validate(data)

    def test_escapes_source_text_and_rejects_unsafe_urls(self):
        data = report()
        data['assessment']['summary'] = '</p><script>alert(1)</script>'
        data['sources'][0]['title'] = '<img src=x onerror=alert(1)>'
        html = renderer.render(data)
        self.assertNotIn('<script', html)
        self.assertNotIn('<img', html)
        self.assertIn('&lt;script&gt;', html)
        for url in ('javascript:alert(1)', 'https://user:secret@example.com', 'file:///tmp/private'):
            with self.subTest(url=url):
                data['sources'][0]['url'] = url
                with self.assertRaisesRegex(ValueError, 'public HTTP'):
                    renderer.render(data)

    def test_score_label_nonfinite_and_future_quotes_rejected(self):
        for mutate in ('label', 'nonfinite', 'future'):
            data = report()
            if mutate == 'label':
                data['assessment']['label'] = 'SELL'
            elif mutate == 'nonfinite':
                data['events'][0]['metrics'][0]['actual'] = float('nan')
            else:
                data['market_reaction']['observations'] = [{'instrument': 'SPY', 'change': 0.1, 'unit': '%',
                    'baseline_at_utc': '2026-10-23T13:59:00Z', 'observed_at_utc': '2026-10-23T14:05:00Z',
                    'feed': 'fixture', 'note': 'Future observation.'}]
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                renderer.validate(data)


class RetryPlanTests(unittest.TestCase):
    def state(self):
        return {'watch_end_at_utc': '2026-10-23T14:20:00Z', 'events': [{
            'id': 'michigan', 'status': 'due_not_verified', 'scheduled_at_utc': '2026-10-23T14:00:00Z',
            'last_attempt_at_utc': '2026-10-23T14:00:00Z'}]}

    def test_retry_at_exactly_three_minutes_not_one_minute(self):
        state = self.state()
        for now in ('2026-10-23T14:01:00Z', '2026-10-23T14:02:59Z'):
            self.assertEqual(poller.plan(state, now)['ready_event_ids'], [])
        self.assertEqual(poller.plan(state, '2026-10-23T14:03:00Z')['ready_event_ids'], ['michigan'])
        state['events'][0]['last_attempt_at_utc'] = '2026-10-23T14:03:00Z'
        self.assertEqual(poller.plan(state, '2026-10-23T14:05:59Z')['ready_event_ids'], [])
        self.assertEqual(poller.plan(state, '2026-10-23T14:06:00Z')['ready_event_ids'], ['michigan'])

    def test_pre_release_read_does_not_delay_initial_check(self):
        state = self.state()
        state['events'][0].update(status='scheduled', last_attempt_at_utc='2026-10-23T13:59:00Z')
        self.assertEqual(poller.plan(state, '2026-10-23T13:59:59Z')['ready_event_ids'], [])
        self.assertEqual(poller.plan(state, '2026-10-23T14:00:00Z')['ready_event_ids'], ['michigan'])

    def test_published_and_expired_reports_stop_retrying(self):
        state = self.state()
        state['events'][0]['status'] = 'primary_verified'
        self.assertEqual(poller.plan(state, '2026-10-23T14:03:00Z')['ready_event_ids'], [])
        state['events'][0]['status'] = 'due_not_verified'
        self.assertTrue(poller.plan(state, '2026-10-23T14:20:00Z')['expired'])

    def test_other_release_is_checked_while_first_report_waits(self):
        state = self.state()
        state['events'].append({'id': 'other', 'status': 'scheduled', 'scheduled_at_utc': '2026-10-23T14:01:00Z'})
        self.assertEqual(poller.plan(state, '2026-10-23T14:01:00Z')['ready_event_ids'], ['other'])


if __name__ == '__main__':
    unittest.main()
