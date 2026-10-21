import importlib.util
from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

p=Path(__file__).resolve().parents[1]/'plugins/stock-research/skills/alpaca-stock-research/scripts/fetch_snapshot.py'
spec=importlib.util.spec_from_file_location('stock_snapshot',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
NY=ZoneInfo('America/New_York');UTC=timezone.utc


def fake_calendar(today):
    days=[today-timedelta(days=i) for i in range(500,-1,-1)]
    return [{'date':d.isoformat(),'open':'09:30','close':'16:00'} for d in days if d.weekday()<5]


def bars(dates):
    return [{'t':datetime.combine(d,datetime.min.time(),NY).isoformat(),'o':100,'h':110,'l':90,'c':100+i/10,'v':1000} for i,d in enumerate(dates)]


class StockTests(unittest.TestCase):
    def test_auth_in_headers_only_and_endpoint_allowlist(self):
        requests=[]
        def open_fake(req,timeout):requests.append(req);return BytesIO(b'{}')
        c=m.Client({'ALPACA_KEY':'secret-key','ALPACA_SECRET':'secret-value'},transport=open_fake)
        _,url=c.get(m.DATA_BASE,'/v2/stocks/AAPL/snapshot',{'feed':'iex'})
        self.assertNotIn('secret',url);self.assertEqual(requests[0].get_method(),'GET')
        self.assertEqual(requests[0].get_header('Apca-api-key-id'),'secret-key')
        for base,path in [(m.DATA_BASE,'/v2/orders'),('https://evil.example','/v2/calendar'),(c.calendar_base,'/v2/account')]:
            with self.assertRaises(ValueError):c.get(base,path)

    def test_credentials_missing_and_untrusted_hosts_rejected(self):
        with self.assertRaisesRegex(ValueError,'Set ALPACA_KEY'):m.Client({})
        for key in ('ALPACA_DATA_URL','ALPACA_BASE_URL'):
            with self.assertRaises(ValueError):m.Client({'ALPACA_KEY':'x','ALPACA_SECRET':'y',key:'https://evil.example'})

    def test_weekends_holidays_and_current_day_are_not_missing_bars(self):
        today=datetime(2026,10,21).date();cal=fake_calendar(today)
        holiday=datetime(2026,7,3).date();cal=[r for r in cal if r['date']!=holiday.isoformat()]
        expected,_=m.calendar_dates(cal,today)
        self.assertNotIn(today,expected);self.assertNotIn(holiday,expected)
        raw=bars(expected)
        for r in raw:r['h']=200
        # Out-of-window current day and exact duplicate are excluded/deduped.
        raw += [raw[0],{'t':datetime.combine(today,datetime.min.time(),NY).isoformat()}]
        result=m.clean_bars(list(reversed(raw)),expected,NY)
        self.assertEqual(len(result),250);self.assertEqual(result[-1]['session_date'],expected[-1].isoformat())

    def test_missing_conflicting_and_nonfinite_history_fail(self):
        expected=[datetime(2026,10,19).date(),datetime(2026,10,20).date()];raw=bars(expected)
        with self.assertRaisesRegex(ValueError,'Missing'):m.clean_bars(raw[:1],expected,NY)
        with self.assertRaisesRegex(ValueError,'Conflicting'):m.clean_bars(raw+[dict(raw[0],c=101)],expected,NY)
        with self.assertRaises(ValueError):m.clean_bars([dict(raw[0],c=float('inf')),raw[1]],expected,NY)

    def test_early_close_and_dst_are_calendar_aware(self):
        day=datetime(2026,11,27).date();rows={day:{'open':'09:30','close':'13:00'}}
        self.assertTrue(m.regular_session_open(datetime(2026,11,27,17,59,tzinfo=UTC),rows,NY))
        self.assertFalse(m.regular_session_open(datetime(2026,11,27,18,tzinfo=UTC),rows,NY))
        self.assertEqual(datetime(2026,7,1,9,30,tzinfo=NY).astimezone(UTC).hour,13)

    def test_stale_and_zero_sided_quotes_never_eligible(self):
        now=datetime.now(UTC)
        raw={'latestTrade':{'t':m.iso(now),'p':100},'latestQuote':{'t':m.iso(now),'bp':0,'ap':101}}
        _,warnings,eligible=m.latest_observations(raw,now,True)
        self.assertFalse(eligible);self.assertTrue(warnings)
        raw['latestQuote']={'t':m.iso(now-timedelta(minutes=6)),'bp':99,'ap':101}
        self.assertFalse(m.latest_observations(raw,now,True)[2])
        raw['latestQuote']['t']=m.iso(now)
        self.assertTrue(m.latest_observations(raw,now,True)[2])
        self.assertFalse(m.latest_observations(raw,now,False)[2])

    def test_stock_metrics_use_sessions_and_252(self):
        raw=[{'close':100+i,'volume':1000} for i in range(250)]
        metrics=m.metrics(raw)
        self.assertAlmostEqual(metrics['return_7_sessions_pct'],(349/342-1)*100)
        log=[m.math.log((100+i)/(99+i)) for i in range(220,250)]
        self.assertAlmostEqual(metrics['volatility_30_sessions_annualized_pct'],m.statistics.stdev(log)*m.math.sqrt(252)*100)
        self.assertEqual(metrics['average_volume_20_sessions'],1000)
        self.assertEqual(metrics['max_drawdown_90_sessions_pct'],0)

    def test_pagination_collected_and_repeated_tokens_fail(self):
        now=datetime.now(UTC);today=now.astimezone(NY).date();cal=fake_calendar(today);dates,_=m.calendar_dates(cal,today)
        raw=bars(dates)
        for row in raw:row['h']=200
        calls=[]
        class Fake:
            calendar_base='https://paper-api.alpaca.markets'
            repeat=False
            def get(self,base,path,params):
                calls.append((path,dict(params)))
                if path=='/v2/calendar':return cal,'https://paper-api.alpaca.markets/v2/calendar'
                if path.endswith('/bars'):
                    if 'page_token' not in params:return {'bars':raw[:125],'next_page_token':'next'},'https://data.alpaca.markets/bars'
                    return {'bars':raw[125:],'next_page_token':'next' if self.repeat else None},'https://data.alpaca.markets/bars?page_token=next'
                return {'latestTrade':{'p':100,'t':m.iso(now)},'latestQuote':{'bp':99,'ap':101,'t':m.iso(now)}},'https://data.alpaca.markets/snapshot'
        result=m.collect(Fake(),['AAPL'],'iex',now,NY)
        self.assertEqual(len(result['stocks'][0]['bars']),250)
        self.assertTrue(any('page_token' in params for _,params in calls))
        self.assertTrue(all(params.get('feed','iex')=='iex' for _,params in calls))
        fake=Fake();fake.repeat=True
        with self.assertRaisesRegex(ValueError,'Repeated pagination'):m.collect(fake,['AAPL'],'iex',now,NY)

    def test_redirects_cannot_forward_credentials(self):
        with self.assertRaisesRegex(ValueError,'Redirect rejected'):m.NoRedirect().redirect_request(None,None,None,None,None,None)

if __name__=='__main__':unittest.main()
