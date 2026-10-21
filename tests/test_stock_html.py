import importlib.util,json
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'plugins/stock-research/skills/html-stock-report/scripts/render_report.py'
spec=importlib.util.spec_from_file_location('stock_html',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class StockHtmlTests(unittest.TestCase):
    def test_standalone_uses_stock_feed_and_session_semantics(self):
        bars=[{'close':100+i/10,'start_utc':'2026-01-01T05:00:00Z','session_date':'2026-01-01'} for i in range(250)]
        snapshot={'snapshot_id':'test123','generated_utc':'2026-10-21T00:00:00Z','feed':'iex','stocks':[{'symbol':'SPY','bars':bars}]}
        text=m.render('# Stock report\n\n## Research judgment\n\nWait. SPY test123.\n\n[Source](https://example.com)\n\n<script>bad()</script>',snapshot)
        for expected in ['Alpaca iex','250 prior trading-session','current New York day excluded','adjustment=all','&lt;script&gt;','<svg']:
            self.assertIn(expected,text)
        for forbidden in ['<script>','Coinbase','UTC daily closes','<link','<img','<iframe']:self.assertNotIn(forbidden,text)
        self.assertIn(json.dumps(snapshot,indent=2).replace('"','&quot;'),text)

    def test_mismatched_or_incomplete_snapshot_rejected(self):
        with self.assertRaises(ValueError):m.render('Wrong',{'snapshot_id':'not-in-report','stocks':[]})
        with self.assertRaises(ValueError):m.render('SPY abc',{'snapshot_id':'abc','stocks':[{'symbol':'SPY','bars':[]}]})

if __name__=='__main__':unittest.main()
