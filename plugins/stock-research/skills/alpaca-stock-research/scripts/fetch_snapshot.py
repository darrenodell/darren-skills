#!/usr/bin/env python3
"""Read Alpaca stock bars, latest snapshots and US calendar. No account or order access."""
import argparse
from datetime import datetime, time as dtime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import statistics
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, HTTPRedirectHandler, build_opener
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UTC=timezone.utc
DATA_BASE='https://data.alpaca.markets'
CALENDAR_BASES={'https://paper-api.alpaca.markets','https://api.alpaca.markets'}
SYMBOL=re.compile(r'[A-Z][A-Z0-9]{0,9}(?:[.\-][A-Z0-9]{1,3})?')


def iso(value): return value.astimezone(UTC).isoformat().replace('+00:00','Z')


def timestamp(value):
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None: raise ValueError('Timestamp must include timezone')
    return parsed.astimezone(UTC)


def positive(value):
    n=float(value)
    if not math.isfinite(n) or n<=0: raise ValueError('Expected finite positive value')
    return n


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('Redirect rejected; credentials are restricted to Alpaca hosts')


class Client:
    def __init__(self, environ=None, transport=None):
        env=os.environ if environ is None else environ
        self._key=env.get('ALPACA_KEY','').strip() or env.get('APCA_API_KEY_ID','').strip()
        self._secret=env.get('ALPACA_SECRET','').strip() or env.get('APCA_API_SECRET_KEY','').strip()
        if not self._key or not self._secret: raise ValueError('Set ALPACA_KEY and ALPACA_SECRET in your environment; do not paste them into chat')
        # Deliberately disallow custom credential destinations, even if Wheel accepts them.
        if env.get('ALPACA_DATA_URL',DATA_BASE).rstrip('/')!=DATA_BASE:
            raise ValueError('ALPACA_DATA_URL must be https://data.alpaca.markets')
        self.calendar_base=env.get('ALPACA_BASE_URL','https://paper-api.alpaca.markets').rstrip('/')
        if self.calendar_base not in CALENDAR_BASES: raise ValueError('ALPACA_BASE_URL must be an official Alpaca paper or live API host')
        self.transport=transport or build_opener(NoRedirect()).open

    def get(self,base,path,params=None):
        allowed=(base==DATA_BASE and re.fullmatch(r'/v2/stocks/[A-Z0-9.\-]+/(?:bars|snapshot)',path)) or (base==self.calendar_base and path=='/v2/calendar')
        if not allowed: raise ValueError('Read-only endpoint allowlist rejected request')
        url=base+path+('?' + urlencode(params) if params else '')
        for attempt in range(3):
            req=Request(url,headers={'APCA-API-KEY-ID':self._key,'APCA-API-SECRET-KEY':self._secret,'Accept':'application/json','User-Agent':'darren-stock-research/1.0'},method='GET')
            try:
                with self.transport(req,timeout=25) as response: return json.load(response),url
            except HTTPError as e:
                if e.code not in (429,500,502,503,504) or attempt==2:
                    raise RuntimeError(f'Alpaca HTTP {e.code} at {path}; verify keys, host and feed entitlement. No response body logged.') from None
            except (URLError,TimeoutError):
                if attempt==2: raise RuntimeError(f'Alpaca network failure at {path}') from None
            time.sleep(2**attempt)
        raise RuntimeError('Retry limit reached')


def calendar_dates(raw, today):
    if not isinstance(raw,list): raise ValueError('Calendar response must be a list')
    rows={}
    for row in raw:
        day=datetime.fromisoformat(row['date']).date()
        if day in rows and rows[day]!=row: raise ValueError('Conflicting calendar dates')
        rows[day]=row
    sessions=sorted(day for day in rows if day<today)
    if len(sessions)<250: raise ValueError('Calendar has fewer than 250 prior trading sessions')
    return sessions[-250:],rows


def regular_session_open(now,rows,ny):
    local=now.astimezone(ny);row=rows.get(local.date())
    if row is None:return False
    def at(value):return datetime.combine(local.date(),dtime.fromisoformat(value),ny)
    return at(row['open'])<=local<at(row['close'])


def clean_bars(raw,expected,ny):
    if not isinstance(raw,list):raise ValueError('Bars must be an array')
    expected_set=set(expected);found={}
    for row in raw:
        dt=timestamp(row['t']);day=dt.astimezone(ny).date()
        if day not in expected_set:continue
        o,h,l,c=(positive(row[k]) for k in ('o','h','l','c'))
        v=float(row['v'])
        if not math.isfinite(v) or v<0 or l>min(o,c) or h<max(o,c) or l>h:raise ValueError('Invalid bar OHLC or volume')
        bar={'start_utc':iso(dt),'session_date':day.isoformat(),'open':o,'high':h,'low':l,'close':c,'volume':v}
        if day in found and found[day]!=bar:raise ValueError('Conflicting duplicate daily bar')
        found[day]=bar
    missing=sorted(expected_set-found.keys())
    if missing:raise ValueError(f'Missing {len(missing)} required trading-session bars; first {missing[0]} (halt/new listing/feed coverage possible)')
    return [found[d] for d in expected]


def metrics(bars):
    closes=[b['close'] for b in bars]
    if len(closes)<200:raise ValueError('Need at least 200 daily closes')
    log_returns=[math.log(b/a) for a,b in zip(closes[-31:-1],closes[-30:])]
    peak=closes[-90];drawdown=0
    for close in closes[-90:]:peak=max(peak,close);drawdown=min(drawdown,close/peak-1)
    result={'last_complete_close':closes[-1],'return_7_sessions_pct':(closes[-1]/closes[-8]-1)*100,'return_30_sessions_pct':(closes[-1]/closes[-31]-1)*100,'volatility_30_sessions_annualized_pct':statistics.stdev(log_returns)*math.sqrt(252)*100,'max_drawdown_90_sessions_pct':drawdown*100,'average_volume_20_sessions':statistics.mean(b['volume'] for b in bars[-20:])}
    for window in (20,50,200):
        average=statistics.mean(closes[-window:]);result[f'sma_{window}']=average;result[f'close_vs_sma_{window}_pct']=(closes[-1]/average-1)*100
    return {k:round(v,8) for k,v in result.items()}


def latest_observations(raw,now,market_open):
    ticker={};warnings=[];trade=raw.get('latestTrade') or {};quote=raw.get('latestQuote') or {}
    for label,item in [('trade',trade),('quote',quote)]:
        if not item or not item.get('t'):
            warnings.append(f'Latest {label} unavailable');ticker[f'{label}_fresh_within_5_minutes']=False;continue
        age=(now-timestamp(item['t'])).total_seconds()
        if age< -60:raise ValueError('Latest observation is in the future; check clock')
        ticker[f'{label}_utc']=iso(timestamp(item['t']));ticker[f'{label}_age_seconds']=round(age,3)
        ticker[f'{label}_fresh_within_5_minutes']=age<=300
    if trade:
        try:ticker['last_trade_price']=positive(trade['p'])
        except (ValueError,KeyError,TypeError):warnings.append('Trade price invalid or missing')
    if quote:
        try:
            bid,ask=positive(quote['bp']),positive(quote['ap'])
            if ask<bid:raise ValueError('Crossed quote')
            ticker.update(bid=bid,ask=ask,spread_bps=round((ask-bid)/((bid+ask)/2)*10000,6))
        except (ValueError,KeyError,TypeError):warnings.append('Quote missing, zero-sided, nonfinite or crossed; spread unavailable')
    fresh=all(ticker.get(k,False) for k in ('trade_fresh_within_5_minutes','quote_fresh_within_5_minutes')) and all(k in ticker for k in ('last_trade_price','bid','ask'))
    if not fresh:warnings.append('Current entry-price assessment unavailable; latest trade/quote missing or older than 5 minutes')
    if not market_open:warnings.append('Outside the regular US session; observations are historical/extended-hours context, not current regular-session execution prices')
    return ticker,warnings,market_open and fresh


def collect(client,symbols,feed,now,ny):
    today=now.astimezone(ny).date();start=today-timedelta(days=600)
    calendar,url=client.get(client.calendar_base,'/v2/calendar',{'start':start.isoformat(),'end':today.isoformat()})
    expected,rows=calendar_dates(calendar,today);is_open=regular_session_open(now,rows,ny)
    lower=datetime.combine(expected[0],dtime.min,ny);upper=datetime.combine(today,dtime.min,ny)-timedelta(microseconds=1)
    stocks=[]
    for symbol in symbols:
        params={'timeframe':'1Day','start':iso(lower),'end':iso(upper),'adjustment':'all','limit':10000,'feed':feed,'sort':'asc'}
        bars=[];sources=[url];seen=set()
        for page in range(100):
            response,bar_url=client.get(DATA_BASE,f'/v2/stocks/{symbol}/bars',params)
            if response.get('symbol') not in (None,symbol):raise ValueError('Bar response symbol mismatch')
            batch=response.get('bars')
            if not isinstance(batch,list):raise ValueError('Bars missing from response')
            bars.extend(batch);sources.append(bar_url);token=response.get('next_page_token')
            if not token:break
            if token in seen:raise ValueError('Repeated pagination token')
            seen.add(token);params=dict(params,page_token=token)
        else:raise ValueError('Bar pagination limit reached')
        cleaned=clean_bars(bars,expected,ny)
        raw,snapshot_url=client.get(DATA_BASE,f'/v2/stocks/{symbol}/snapshot',{'feed':feed})
        retrieved=datetime.now(UTC);ticker,warnings,current=latest_observations(raw,retrieved,regular_session_open(retrieved,rows,ny))
        stocks.append({'symbol':symbol,'retrieved_utc':iso(retrieved),'feed':feed,'adjustment':'all','source_urls':sources+[snapshot_url],'ticker':ticker,'quality':{'complete_sessions':len(cleaned),'missing_sessions':0,'current_new_york_day_excluded':True,'entry_price_eligible':current,'warnings':warnings},'metrics':metrics(cleaned),'bars':cleaned})
    generated=datetime.now(UTC)
    return {'schema_version':1,'snapshot_id':generated.strftime('%Y%m%dT%H%M%S%fZ'),'generated_utc':iso(generated),'source':'Alpaca stock market data','feed':feed,'adjustment':'all','market_state':{'checked_utc':iso(generated),'regular_session_open':regular_session_open(generated,rows,ny),'new_york_date':today.isoformat()},'history_policy':'Prior 250 exchange sessions before current America/New_York date; current NY day always excluded, including after close. Calendar verifies holidays/early closes.','session_dates':[d.isoformat() for d in expected],'stocks':stocks}


def packet(snapshot):
    lines=['# Alpaca stock research data packet','',f"Snapshot ID: {snapshot['snapshot_id']}",f"Captured UTC: {snapshot['generated_utc']}",f"Feed: {snapshot['feed']}; adjustment=all.",'IEX covers one exchange; SIP is consolidated and requires appropriate access. No silent feed fallback.','Daily bars are adjusted feed aggregates, not guaranteed regular-session auction closes.','7/30-session adjusted-price returns; volatility uses sample daily log-return standard deviation × sqrt(252).','No account/holdings or order access. This packet does not contain credentials.','',snapshot['history_policy'],'',f"Regular US session open at collection start: {snapshot['market_state']['regular_session_open']}"]
    for item in snapshot['stocks']:
        lines+=['',f"## {item['symbol']}",'','```json',json.dumps({k:v for k,v in item.items() if k not in ('bars','source_urls')},indent=2),'```','','Sources:']+[f'- {u}' for u in item['source_urls']]
        lines+=['','```csv','session_date,adjusted_close,volume']+[f"{b['session_date']},{b['close']},{b['volume']}" for b in item['bars']]+['```']
    lines+=['','Use the alpaca-stock-research report-prompt.md. Refresh a snapshot older than five minutes at analysis start; label closed-session or stale quotes and do not use them for a current entry-price judgment.']
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbols',nargs='+',required=True)
    parser.add_argument('--feed',choices=['iex','sip'],default='iex')
    parser.add_argument('--out',type=Path,default=Path('data'))
    args=parser.parse_args();symbols=list(dict.fromkeys(s.upper() for s in args.symbols))
    if not 1<=len(symbols)<=10 or any(not SYMBOL.fullmatch(s) for s in symbols):parser.error('Choose 1–10 US stock/ETF symbols, e.g. AAPL MSFT SPY')
    try:
        ny=ZoneInfo('America/New_York')
        snapshot=collect(Client(),symbols,args.feed,datetime.now(UTC),ny)
        folder=args.out.expanduser().resolve()/snapshot['snapshot_id'];folder.mkdir(parents=True,exist_ok=False)
        (folder/'snapshot.json').write_text(json.dumps(snapshot,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        (folder/'chatgpt-packet.md').write_text(packet(snapshot),encoding='utf-8')
    except ZoneInfoNotFoundError:parser.exit(1,'STOP: Timezone data missing. Install it with python -m pip install tzdata, then retry.\n')
    except (RuntimeError,ValueError,KeyError,TypeError,OverflowError,OSError) as error:
        parser.exit(1,f'STOP: {error}\nNo successful research snapshot is available from this run.\n')
    print(f"Snapshot: {folder/'snapshot.json'}")
    print(f"Packet: {folder/'chatgpt-packet.md'}")
    for item in snapshot['stocks']:print(f"{item['symbol']}: 250 validated sessions; feed={args.feed}; entry_price_eligible={item['quality']['entry_price_eligible']}")

if __name__=='__main__':main()
