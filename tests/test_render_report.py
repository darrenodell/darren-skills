import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'plugins/crypto-research/skills/html-research-report/scripts/render_report.py'
spec=importlib.util.spec_from_file_location('render_report',path)
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)


def snapshot(product='XRP-USD',base=1.0):
    candles=[{'start_utc':f'2026-01-01T00:00:00Z','close':base+i*base/1000,'low':base,'high':base*2} for i in range(250)]
    metrics={'return_7d_pct':-13.7,'return_30d_pct':-23.8,'volatility_30d_annualized_pct':49.0,'max_drawdown_90d_pct':-33.9,'close_vs_sma_200_pct':-17.5}
    return {'snapshot_id':'SNAP1','generated_utc':'2026-11-13T02:56:34.345931Z','products':[{'product':product,'ticker':{'last_trade_price':base*1.02},'metrics':metrics,'candles':candles}]}


BRIEF='''# Crypto Buying Brief

Short-term · snapshot `SNAP1`

## Bottom line

1. **Nothing is a buy today.**

## XRP-USD

- **Verdict:** Avoid for now
- **Why:** Weakest chart of the set.
- **News:** Nov 10: [Example headline](https://example.com/news) moved the price.
- **Buy only if:** a daily close is above $1.2135 (20-day average)
- **Exit if:** a daily close is below $1.015 (30-day low)

## What is unverified

- Cause of the latest drop.

## Sources

- [Hidden source](https://example.com/source)
'''


class HtmlTests(unittest.TestCase):
    def test_source_html_and_unsafe_links_do_not_execute(self):
        result=renderer.markdown('<script>alert(1)</script>\n\n[bad](javascript:alert) [good](https://example.com)')
        self.assertNotIn('<script>',result)
        self.assertNotIn('href="javascript:',result)
        self.assertIn('href="https://example.com"',result)
        self.assertIn('&lt;script&gt;',result)

    def test_preserves_table_links_lists_and_code(self):
        result=renderer.markdown('# Title\n\n## Risks\n\n| Metric | Value |\n| --- | --- |\n| Close | $123 |\n\n- **Wait** for [evidence](https://example.com)\n\n```text\n<not-an-element>\n```')
        for expected in ['<th scope="col">Metric</th>','<td>$123</td>','<strong>Wait</strong>','https://example.com','&lt;not-an-element&gt;']:
            self.assertIn(expected,result)

    def test_rejects_mismatched_snapshot(self):
        with self.assertRaisesRegex(ValueError,'snapshot ID'):
            renderer.render('Wrong report',{'snapshot_id':'abc','products':[]})

    def test_unclosed_code_and_bad_tables_fail_instead_of_losing_content(self):
        with self.assertRaises(ValueError):renderer.markdown('```\nunfinished')
        with self.assertRaises(ValueError):renderer.markdown('| A | B |\n|---|---|\n| only one |')

    def test_card_groups_chart_verdict_metrics_and_levels(self):
        result=renderer.render(BRIEF,snapshot())
        card=result[result.index('<article class="card">'):result.index('</article>')]
        for expected in ['<h2>XRP</h2>','class="tag avoid"','Avoid for now','Weakest chart of the set.','Nov 10: Example headline moved the price.','<svg','$1.2135','$1.015','-13.7%','49%','<b>Buy only if</b>','<b>Exit if</b>']:
            self.assertIn(expected,card)
        self.assertLess(result.index('Nothing is a buy today'),result.index('<article class="card">'))
        self.assertGreater(result.index('Cause of the latest drop'),result.index('</article>'))

    def test_sources_are_left_out_and_page_is_self_contained(self):
        result=renderer.render(BRIEF,snapshot())
        self.assertNotIn('example.com',result)
        self.assertNotIn('Hidden source',result)
        self.assertNotIn('<script',result)
        self.assertIn("default-src 'none'",result)

    def test_missing_product_section_or_field_fails(self):
        with self.assertRaisesRegex(ValueError,'## XRP-USD'):
            renderer.render('snapshot `SNAP1`\n\n## Bottom line\n\n1. Wait.',snapshot())
        with self.assertRaisesRegex(ValueError,'Exit if'):
            renderer.render(BRIEF.replace('- **Exit if:** a daily close is below $1.015 (30-day low)\n',''),snapshot())
        with self.assertRaisesRegex(ValueError,'News'):
            renderer.render(BRIEF.replace('- **News:** Nov 10: [Example headline](https://example.com/news) moved the price.\n',''),snapshot())
        with self.assertRaisesRegex(ValueError,'dollar level'):
            renderer.render(BRIEF.replace('$1.2135','the 20-day average'),snapshot())

    def bounce_snapshot(self,state='bounce_setup',meets=True):
        data=snapshot()
        data['products'][0]['bounce']={'state':state,'rsi_14':24.0,'zscore_20':-2.4,'drop_from_30d_high_pct':-31.0,'consecutive_down_days':4,'volume_ratio_3d_max':2.6,
            'oversold':{'rsi_below_30':True,'below_lower_band':True,'deep_drop_from_30d_high':False,'three_down_days':True,'score':3,'peak_score_3d':3},
            'reversal':{'capitulation_volume':True,'reversal_candle':False,'rsi_divergence':False,'count':1},
            'plan':{'entry':1.05,'stop':1.0,'target':1.2,'risk_pct':-4.76,'reward_pct':14.29,'reward_to_risk':3.0 if meets else 0.8,'minimum_reward_to_risk':1.5,'meets_minimum':meets},
            'history':{'lookahead_days':5,'setups':4,'higher_after_5d':3,'average_5d_return_pct':3.2,'worst_5d_return_pct':-6.1,'best_5d_return_pct':9.0}}
        return data

    def bounce_brief(self,verdict):
        return f'# Crypto Bounce Finder\n\nsnapshot `SNAP1`\n\n## XRP-USD\n\n- **Verdict:** {verdict}\n- **Why:** Capitulation volume after a deep drop.\n- **News:** No dated news found in the last 7 days.\n'

    def test_bounce_card_shows_plan_signals_and_history_from_snapshot(self):
        result=renderer.render(self.bounce_brief('Buy setup'),self.bounce_snapshot(),'bounce')
        for expected in ['Bounce setup · oversold 3 of 4 · reversal 1 of 3','class="chip on">Volume spike','class="chip off">Reversal candle','<b>Entry</b> a daily close above $1.05','<b>Stop</b> $1.00','<b>Target</b> $1.20','3.0 to 1','4 earlier setups in this window, 3 higher after 5 days','Small sample, not a probability','class="target"']:
            self.assertIn(expected,result)

    def test_bounce_verdict_cannot_be_more_bullish_than_the_signal(self):
        with self.assertRaisesRegex(ValueError,'cannot start with Buy'):
            renderer.render(self.bounce_brief('Buy setup'),self.bounce_snapshot(state='oversold_falling'),'bounce')
        with self.assertRaisesRegex(ValueError,'cannot start with Buy'):
            renderer.render(self.bounce_brief('Buy setup'),self.bounce_snapshot(meets=False),'bounce')
        self.assertIn('below the 1.5 minimum: skip',renderer.render(self.bounce_brief('Skip'),self.bounce_snapshot(meets=False),'bounce'))

    def test_live_price_below_stop_voids_the_setup(self):
        data=self.bounce_snapshot()
        data['products'][0]['ticker']['last_trade_price']=0.98
        with self.assertRaisesRegex(ValueError,'cannot start with Buy'):
            renderer.render(self.bounce_brief('Buy setup'),data,'bounce')
        self.assertIn('already below the stop',renderer.render(self.bounce_brief('Skip'),data,'bounce'))
        self.assertNotIn('already below the stop',renderer.render(self.bounce_brief('Buy setup'),self.bounce_snapshot(),'bounce'))

    def test_bounce_mode_needs_bounce_data(self):
        with self.assertRaisesRegex(ValueError,'no bounce metrics'):
            renderer.render(self.bounce_brief('Wait'),snapshot(),'bounce')

    def test_money_keeps_precision_for_low_priced_assets(self):
        self.assertEqual(renderer.money(73079.85),'$73,080')
        self.assertEqual(renderer.money(88.9366),'$88.94')
        self.assertEqual(renderer.money(1.015),'$1.015')
        self.assertEqual(renderer.money(1.2),'$1.20')

if __name__=='__main__':unittest.main()
