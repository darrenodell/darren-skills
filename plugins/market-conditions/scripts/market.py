#!/usr/bin/env python3
"""Read-only historical market context. Python 3.10+, standard library only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import statistics
import calendar as calendar_module
import sys
import time
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener
from zoneinfo import ZoneInfo

UTC = timezone.utc
NY = ZoneInfo('America/New_York')
VERSION = '1.0.0'
BENCHMARKS = ['SPY', 'QQQ', 'IWM', 'RSP', 'XLK', 'SMH']
# Freshness is calendar-day tolerance for delayed public observations, not a claim of release timing.
SERIES = {
    'DGS10': ('10-year Treasury yield', 'percent', 'daily', 7, True),
    'CPIAUCSL': ('Consumer price index, seasonally adjusted', 'index 1982-84=100', 'monthly', 75, True),
    'UNRATE': ('Unemployment rate', 'percent', 'monthly', 75, True),
    'FEDFUNDS': ('Effective federal funds rate', 'percent', 'monthly', 75, True),
    'PAYEMS': ('Nonfarm payrolls', 'thousands of persons', 'monthly', 75, False),
    'GDPC1': ('Real GDP', 'billions of chained 2017 dollars, SAAR', 'quarterly', 150, False),
    'VIXCLS': ('Cboe VIX daily close', 'index points', 'daily', 7, False),
    'BAMLH0A0HYM2': ('ICE BofA US high-yield option-adjusted spread', 'percentage points', 'daily', 7, False),
    'NFCI': ('Chicago Fed financial conditions index', 'index', 'weekly', 18, False),
}


def stamp(value=None):
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat().replace('+00:00', 'Z')


def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone required')
    return result.astimezone(UTC)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def read_json(path):
    def bad(value):
        raise ValueError('Non-finite JSON number')
    return json.loads(Path(path).read_text(encoding='utf-8'), parse_constant=bad)


def safe_url(value):
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Only credential-free HTTPS source links are accepted')
    return value


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Redirect rejected')


class Reader:
    """Only official historical bars/calendar/FRED GET routes; never account/orders."""
    def __init__(self, env=None, transport=None):
        self.env = os.environ if env is None else env
        self.transport = transport or build_opener(NoRedirect()).open

    def get(self, base, path, params, auth=False):
        market = base == 'https://data.alpaca.markets' and re.fullmatch(r'/v2/stocks/[A-Z0-9.\-]+/bars', path)
        calendar = base in ('https://paper-api.alpaca.markets', 'https://api.alpaca.markets') and path == '/v2/calendar'
        fred = base == 'https://fred.stlouisfed.org' and path == '/graph/fredgraph.csv'
        if not (market or calendar or fred) or auth != bool(market or calendar):
            raise ValueError('Read-only source allowlist rejected request')
        # FRED's CSV route responds reliably to urllib's default headers;
        # an explicit text/csv Accept header can stall this endpoint.
        headers = {'User-Agent': 'darren-market-conditions/' + VERSION, 'Accept': 'application/json'} if auth else {}
        if auth:
            key = self.env.get('ALPACA_KEY') or self.env.get('APCA_API_KEY_ID')
            secret = self.env.get('ALPACA_SECRET') or self.env.get('APCA_API_SECRET_KEY')
            if not key or not secret:
                raise ValueError('Alpaca runtime credentials unavailable; do not paste them into chat')
            headers.update({'APCA-API-KEY-ID': key, 'APCA-API-SECRET-KEY': secret})
        url = base + path + '?' + urlencode(params)
        for attempt in range(3):
            try:
                with self.transport(Request(url, headers=headers, method='GET'), timeout=30 if auth else 10) as response:
                    body = response.read(20_000_001)
                    if len(body) > 20_000_000:
                        raise ValueError('Source response too large')
                    return body.decode('utf-8-sig'), url
            except HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise RuntimeError(f'HTTP {exc.code} at {path}; response/credentials omitted') from None
            except (URLError, TimeoutError, OSError):
                if attempt == 2:
                    raise RuntimeError(f'Network failure at {path}; details omitted') from None
            time.sleep(2 ** attempt)
        raise RuntimeError('Read retry limit reached')


def symbols(values):
    result = []
    for value in values:
        value = value.strip().upper()
        if not re.fullmatch(r'[A-Z0-9][A-Z0-9.\-]{0,14}', value):
            raise ValueError('Invalid benchmark symbol')
        if value not in result:
            result.append(value)
    if not 1 <= len(result) <= 10:
        raise ValueError('Use 1–10 benchmarks per run')
    return result


def session_calendar(reader, now, count=250):
    today = now.astimezone(NY).date()
    base = reader.env.get('ALPACA_BASE_URL', 'https://paper-api.alpaca.markets').rstrip('/')
    raw, url = reader.get(base, '/v2/calendar', {'start': str(today - timedelta(days=count * 2 + 40)), 'end': str(today)}, True)
    rows = json.loads(raw)
    dates = [date.fromisoformat(row['date']) for row in rows]
    if len(dates) != len(set(dates)) or dates != sorted(dates):
        raise ValueError('Duplicate or unsorted calendar')
    dates = [d for d in dates if d < today]
    if len(dates) < count:
        raise ValueError('Insufficient exchange calendar')
    return dates[-count:], {'url': url, 'retrieved_utc': stamp(), 'calendar': rows}


def validate_bars(raw, expected):
    found = {}
    for row in raw:
        when = instant(row['t'])
        day = when.astimezone(NY).date()
        if day not in expected:
            continue
        if day in found:
            raise ValueError('Duplicate daily bar')
        o, h, l, c, v = [float(row[k]) for k in ('o', 'h', 'l', 'c', 'v')]
        if not all(math.isfinite(x) for x in (o, h, l, c, v)) or min(o, h, l, c) <= 0 or v < 0 or l > min(o, c) or h < max(o, c) or l > h:
            raise ValueError('Invalid OHLCV')
        found[day] = {'session': str(day), 'timestamp': row['t'], 'open': o, 'high': h, 'low': l, 'close': c, 'volume': v}
    missing = [str(d) for d in expected if d not in found]
    if missing:
        raise ValueError(f'Missing {len(missing)} exchange sessions; first {missing[0]}')
    return [found[d] for d in expected]


def collect_prices(reader, requested, expected, feed):
    result = []
    lower = datetime.combine(expected[0], datetime.min.time(), NY)
    upper = datetime.combine(expected[-1] + timedelta(days=1), datetime.min.time(), NY) - timedelta(microseconds=1)
    for symbol in requested:
        params = {'feed': feed, 'timeframe': '1Day', 'start': stamp(lower), 'end': stamp(upper), 'adjustment': 'all', 'limit': 10000, 'sort': 'asc'}
        raw, urls, tokens = [], [], set()
        for page in range(100):
            body, url = reader.get('https://data.alpaca.markets', f'/v2/stocks/{symbol}/bars', params, True)
            value = json.loads(body)
            if value.get('symbol', symbol) != symbol or not isinstance(value.get('bars'), list):
                raise ValueError(f'{symbol}: invalid bars response')
            raw.extend(value['bars']); urls.append(url)
            token = value.get('next_page_token')
            if not token:
                break
            if token in tokens:
                raise ValueError('Repeated pagination token')
            tokens.add(token); params['page_token'] = token
        else:
            raise ValueError('Pagination limit reached')
        result.append({'symbol': symbol, 'feed': feed, 'adjustment': 'all', 'retrieved_utc': stamp(), 'source_urls': urls, 'raw_bars': raw, 'bars': validate_bars(raw, expected)})
    return result


def fred_series(reader, series_id, now):
    name, units, frequency, max_age, required = SERIES[series_id]
    today = now.astimezone(NY).date()
    body, url = reader.get('https://fred.stlouisfed.org', '/graph/fredgraph.csv', {'id': series_id, 'cosd': str(today - timedelta(days=800)), 'coed': str(today)})
    observations = []
    for row in csv.DictReader(io.StringIO(body)):
        if series_id not in row or not row.get('observation_date', row.get('DATE')):
            raise ValueError('Unexpected FRED CSV columns')
        day = date.fromisoformat(row.get('observation_date', row.get('DATE')))
        if day > today:
            raise ValueError('Future macro observation')
        if row[series_id] in ('', '.'):
            continue
        value = float(row[series_id])
        if not math.isfinite(value):
            raise ValueError('Invalid macro observation')
        observations.append({'date': str(day), 'value': value})
    if not observations or len({x['date'] for x in observations}) != len(observations):
        raise ValueError('Empty or duplicate FRED observations')
    observations.sort(key=lambda x: x['date'])
    period_end = observation_end(date.fromisoformat(observations[-1]['date']), frequency)
    age = (today - period_end).days
    return {'id': series_id, 'name': name, 'units': units, 'frequency': frequency, 'required': required, 'max_age_days': max_age, 'age_days': age, 'age_basis': 'observation date for daily/weekly; period end for monthly/quarterly', 'period_end': str(period_end), 'fresh': 0 <= age <= max_age, 'source_url': url, 'series_url': 'https://fred.stlouisfed.org/series/' + series_id, 'retrieved_utc': stamp(), 'publication_date': None, 'vintage': 'latest downloaded; historical revisions possible; no point-in-time vintage claim', 'observations': observations, 'raw_csv': body}


def metrics(bars):
    values = [b['close'] for b in bars]
    result = {'last_close': values[-1], 'sessions': len(values), 'first_session': bars[0]['session'], 'last_session': bars[-1]['session']}
    for n in (20, 50, 200):
        avg = statistics.mean(values[-n:]) if len(values) >= n else None
        result[f'sma{n}'] = avg
        result[f'distance_sma{n}_pct'] = 100 * (values[-1] / avg - 1) if avg else None
    result['returns_pct'] = {str(n): 100 * (values[-1] / values[-n-1] - 1) if len(values) > n else None for n in (1, 5, 20, 63, 126, 252)}
    returns = [math.log(b / a) for a, b in zip(values[-21:-1], values[-20:])]
    result['rv20_pct'] = statistics.stdev(returns) * math.sqrt(252) * 100 if len(returns) == 20 else None
    peak, worst = values[0], 0
    for value in values:
        peak = max(peak, value); worst = min(worst, value / peak - 1)
    result['max_drawdown_window_pct'] = worst * 100
    return result


def validate_snapshot(snapshot, now=None):
    now = now or datetime.now(UTC)
    if snapshot.get('schema_version') != 'market-snapshot.v1' or instant(snapshot['generated_utc']) > now + timedelta(minutes=1):
        raise ValueError('Invalid snapshot schema/time')
    requested = symbols(snapshot['requested_symbols'])
    if snapshot['feed'] not in ('sip', 'iex') or snapshot['adjustment'] != 'all':
        raise ValueError('Unsupported feed/adjustment')
    expected = [date.fromisoformat(x) for x in snapshot['session_dates']]
    if len(expected) < 250 or expected != sorted(set(expected)) or expected[-1] >= instant(snapshot['generated_utc']).astimezone(NY).date():
        raise ValueError('Invalid session window')
    if (now.astimezone(NY).date() - expected[-1]).days > 5:
        raise ValueError('Price history stale for a new backdrop assessment')
    if [x['symbol'] for x in snapshot['stocks']] != requested:
        raise ValueError('Requested-symbol accounting mismatch')
    for stock in snapshot['stocks']:
        if stock['feed'] != snapshot['feed'] or stock['adjustment'] != 'all':
            raise ValueError('Mixed feeds/adjustments')
        rebuilt = validate_bars(stock['raw_bars'], expected)
        if rebuilt != stock['bars']:
            raise ValueError('Clean/raw bar mismatch')
        for url in stock['source_urls']:
            safe_url(url)
    return True


def observation_end(day, frequency):
    if frequency == 'monthly':
        return day.replace(day=calendar_module.monthrange(day.year, day.month)[1])
    if frequency == 'quarterly':
        month = ((day.month - 1) // 3 + 1) * 3
        return date(day.year, month, calendar_module.monthrange(day.year, month)[1])
    return day


def macro_state(item, key, now):
    try:
        dates = [date.fromisoformat(x['date']) for x in item['observations']]
        period_end = observation_end(dates[-1], SERIES[key][2])
        age = (now.astimezone(NY).date() - period_end).days
        valid = (dates == sorted(set(dates)) and 0 <= age <= SERIES[key][3]
                 and all(d <= now.astimezone(NY).date() for d in dates)
                 and all(math.isfinite(float(x['value'])) for x in item['observations'])
                 and item['units'] == SERIES[key][1] and item['frequency'] == SERIES[key][2]
                 and instant(item['retrieved_utc']) <= now + timedelta(minutes=1))
        return {'fresh': valid, 'age_days': age, 'max_age_days': SERIES[key][3], 'period_end': str(period_end)}
    except (ValueError, TypeError, KeyError, IndexError):
        return {'fresh': False, 'age_days': None, 'max_age_days': SERIES[key][3]}


def assess(snapshot, now=None):
    now = now or datetime.now(UTC)
    errors = []
    try:
        validate_snapshot(snapshot, now)
    except (ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    values = {s['symbol']: metrics(s['bars']) for s in snapshot.get('stocks', []) if s.get('bars')}
    required = [key for key, spec in SERIES.items() if spec[-1]]
    macro = {x['id']: x for x in snapshot.get('macro', [])}
    states = {key: macro_state(macro[key], key, now) for key in SERIES if key in macro}
    for key in required:
        valid = states.get(key, {}).get('fresh', False)
        if not valid:
            errors.append(f'Required macro series missing/stale: {key}')
    for key in BENCHMARKS:
        if key not in values:
            errors.append(f'Core benchmark unavailable: {key}')
    relative = {}
    for numerator, denominator in [('RSP', 'SPY'), ('IWM', 'SPY'), ('QQQ', 'SPY'), ('XLK', 'SPY'), ('SMH', 'SPY')]:
        if numerator in values and denominator in values and all(values[k]['returns_pct'][str(n)] is not None for k in (numerator, denominator) for n in (20, 63)):
            relative[f'{numerator}/{denominator}'] = {str(n): 100 * ((1 + values[numerator]['returns_pct'][str(n)] / 100) / (1 + values[denominator]['returns_pct'][str(n)] / 100) - 1) for n in (20, 63)}
    components = {}
    def trend(key):
        v = values[key]
        return 1 if v['last_close'] > v['sma50'] > v['sma200'] else -1 if v['last_close'] < v['sma50'] < v['sma200'] else 0
    if not errors:
        broad = (trend('SPY') + trend('QQQ')) / 2
        tech = statistics.mean(relative[x]['63'] for x in ('XLK/SPY', 'SMH/SPY'))
        participation = statistics.mean(relative[x]['63'] for x in ('RSP/SPY', 'IWM/SPY'))
        components = {'broad_trend': 'SUPPORTIVE' if broad > 0 else 'ADVERSE' if broad < 0 else 'MIXED', 'technology_relative_strength': 'SUPPORTIVE' if tech > 0 else 'ADVERSE' if tech < 0 else 'MIXED', 'participation_proxy': 'SUPPORTIVE' if participation > 0 else 'ADVERSE' if participation < 0 else 'MIXED'}
        stress_flags = []
        for key, threshold in [('VIXCLS', 30), ('BAMLH0A0HYM2', 5), ('NFCI', 0.5)]:
            if key in macro and states[key]['fresh'] and macro[key]['observations'][-1]['value'] >= threshold:
                stress_flags.append(key)
        label = 'ADVERSE' if broad < 0 and (tech <= 0 or stress_flags) else 'SUPPORTIVE' if broad > 0 and tech > 0 and participation >= 0 and not stress_flags else 'MIXED'
    else:
        stress_flags, label = [], 'INSUFFICIENT EVIDENCE'
    optional_gaps = [key for key in SERIES if not states.get(key, {}).get('fresh')]
    return {'schema_version': 'market-assessment.v1', 'snapshot_id': snapshot['snapshot_id'], 'generated_utc': stamp(now), 'assessment': label, 'confidence': 'LOW' if errors else 'MODERATE', 'required_input_errors': errors, 'optional_gaps': optional_gaps, 'macro_status': states, 'components': components, 'stress_flags': stress_flags, 'metrics': values, 'relative_strength_pct': relative, 'rubric': 'Unvalidated heuristic v1. Broad trend: close/SMA50/SMA200 ordering in SPY and QQQ; tech: mean XLK/SPY and SMH/SPY 63-session relative change; participation: mean RSP/SPY and IWM/SPY. SUPPORTIVE requires positive broad/tech, nonnegative participation and no stress flags. ADVERSE requires negative broad and nonpositive tech or a stress flag. Otherwise MIXED. Missing required prices or macro freshness forces INSUFFICIENT EVIDENCE. Macro observations are contextual, not forecast scores. Stress thresholds: VIX >=30, HY OAS >=5 percentage points, NFCI >=0.5. Correlated ratios are not independent votes.', 'horizons': {'3–6 months': 'Historical trend, leadership, volatility and upcoming catalysts inform timing; this report supplies no live entry price.', 'one year or more': 'Backdrops inform confidence and drawdown risk; company cash generation, debt, dilution and valuation determine the investment thesis. No automatic sale follows a weak backdrop.'}, 'countercase': 'Trend and ETF leadership can reverse; proxies omit constituent breadth, expectations, flows and company valuation. Falling rates can signal weakening growth rather than easier financing alone.', 'change_conditions': ['Reassess after a newly completed exchange session or a material macro/earnings release.', 'Broad trend changes when SPY/QQQ move across the stated moving averages; leadership changes when the 63-session relative ratios change sign.', 'Any required stale/missing source withholds the overall assessment until repaired.'], 'current_entry_price_eligible': False, 'scope': 'Historical market backdrop; no trading, allocations or execution prices.'}


def external_evidence(path, now=None):
    now = now or datetime.now(UTC)
    value = read_json(path)
    if value.get('schema_version') != 'external-evidence.v1':
        raise ValueError('Unsupported external evidence envelope')
    for key in ('producer', 'scope', 'as_of', 'source_urls', 'artifact_path', 'artifact_sha256', 'summary', 'review_status'):
        if not value.get(key):
            raise ValueError(f'External evidence missing {key}')
    for key in ('producer', 'scope', 'as_of', 'artifact_path', 'artifact_sha256', 'summary', 'review_status'):
        if not isinstance(value[key], str):
            raise ValueError('External evidence field must be text: ' + key)
    if not isinstance(value['source_urls'], list) or not all(isinstance(x, str) for x in value['source_urls']):
        raise ValueError('External source_urls must be a list of HTTPS links')
    when = instant(value['as_of'])
    if when > now or now - when > timedelta(days=7):
        raise ValueError('External evidence future/stale; quarantine rather than use')
    if value.get('retrieved_utc') and instant(value['retrieved_utc']) > now:
        raise ValueError('External retrieval time is in the future')
    if value.get('publication_date') and date.fromisoformat(value['publication_date']) > now.date():
        raise ValueError('External publication date is in the future')
    artifact = Path(value['artifact_path'])
    if not artifact.is_absolute():
        artifact = Path(path).resolve().parent / artifact
    artifact = artifact.resolve()
    if not artifact.is_relative_to(Path(path).resolve().parent) or not artifact.is_file() or artifact.suffix.lower() not in ('.md', '.txt', '.html', '.htm', '.pdf', '.docx', '.xlsx', '.csv', '.json') or artifact.stat().st_size > 10_000_000:
        raise ValueError('External report must be a bounded report file within the envelope folder')
    if hashlib.sha256(artifact.read_bytes()).hexdigest() != value['artifact_sha256']:
        raise ValueError('External evidence hash mismatch')
    for url in value['source_urls']:
        safe_url(url)
    # Whitelist data fields. Imported text is never executed or given tool authority.
    allowed = ('producer', 'producer_version', 'workflow', 'scope', 'as_of', 'publication_date', 'retrieved_utc', 'source_urls', 'artifact_sha256', 'summary', 'assessment', 'assumptions', 'review_status', 'review_independence')
    return {k: value.get(k) for k in allowed}


def build_report(snapshot, analysis, context=None, enrichment=None, previous=None):
    from report import html_report, markdown_report
    if analysis['snapshot_id'] != snapshot['snapshot_id']:
        raise ValueError('Analysis/snapshot mismatch')
    previous = previous or analysis.get('previous_context')
    return markdown_report(snapshot, analysis, context, enrichment, previous), html_report(snapshot, analysis, context, enrichment, previous)


def run(args):
    now = datetime.now(UTC)
    run_id = now.strftime('%Y%m%dT%H%M%S%fZ')
    workspace = Path(args.workspace).expanduser().resolve()
    # Never write private outputs into this plugin or its repository.
    plugin = Path(__file__).resolve().parents[1]
    if workspace.is_relative_to(plugin.parents[1]) or workspace == plugin.parents[1]:
        raise ValueError('Output workspace must be outside the plugin repository')
    out = workspace / 'reports' / run_id
    out.mkdir(parents=True, exist_ok=False)
    data_dir = workspace / 'data' / run_id
    source_dir = workspace / 'sources' / run_id
    manifest = {'run_id': run_id, 'plugin_version': VERSION, 'started_utc': stamp(now), 'status': 'RUNNING', 'attempts': [], 'requested_symbols': symbols(args.symbols), 'review': 'PENDING — NO PASS CLAIM', 'enrichment': 'NOT_REQUESTED'}
    write_json(out / 'manifest.json', manifest)
    try:
        reader = Reader()
        expected, calendar = session_calendar(reader, now)
        write_json(source_dir / 'calendar.json', calendar)
        stocks = None
        for feed in ([args.feed, 'iex'] if args.feed == 'sip' and args.allow_iex_fallback else [args.feed]):
            attempt = {'attempt_id': f'{run_id}-{feed}', 'feed': feed, 'started_utc': stamp()}
            manifest['attempts'].append(attempt)
            try:
                stocks = collect_prices(reader, manifest['requested_symbols'], expected, feed)
                attempt['status'] = 'SUCCESS'; manifest['feed'] = feed
                break
            except (ValueError, RuntimeError, KeyError, TypeError) as exc:
                attempt.update(status='FAILED', error=str(exc)); write_json(out / 'manifest.json', manifest)
        if stocks is None:
            raise RuntimeError('All requested historical-feed attempts failed; no replacement data fabricated')
        write_json(data_dir / 'prices.json', {'feed': manifest['feed'], 'session_dates': [str(d) for d in expected], 'stocks': stocks, 'captured_utc': stamp()})
        macro, macro_errors = [], []
        for series_id in SERIES:
            try:
                series = fred_series(reader, series_id, now)
                raw = series.pop('raw_csv')
                source_dir.mkdir(parents=True, exist_ok=True)
                (source_dir / (series_id + '.csv')).write_text(raw, encoding='utf-8')
                macro.append(series)
            except (ValueError, RuntimeError, KeyError, TypeError) as exc:
                macro_errors.append({'series': series_id, 'error': str(exc), 'required': SERIES[series_id][-1]})
        snapshot = {'schema_version': 'market-snapshot.v1', 'snapshot_id': run_id, 'generated_utc': stamp(), 'feed': manifest['feed'], 'adjustment': 'all', 'requested_symbols': manifest['requested_symbols'], 'session_dates': [str(d) for d in expected], 'session_policy': 'Prior 250 exchange sessions; current New York date excluded even after close.', 'stocks': stocks, 'macro': macro, 'macro_errors': macro_errors, 'attempts': manifest['attempts'], 'current_entry_price_eligible': False}
        write_json(data_dir / 'snapshot.json', snapshot)
        context = read_json(args.context) if args.context else None
        enrichment = None
        enrichment_error = None
        if args.enrichment:
            try:
                enrichment = external_evidence(args.enrichment)
            except (ValueError, KeyError, TypeError, OSError) as exc:
                enrichment_error = str(exc)
        manifest['enrichment'] = ('QUARANTINED — ' + enrichment_error if enrichment_error else 'VALIDATED ARTIFACT — NOT INDEPENDENT SOURCE VERIFICATION' if enrichment else 'ABSENT — OPTIONAL')
        analysis = assess(snapshot)
        analysis['enrichment_status'] = manifest['enrichment']
        if enrichment_error:
            analysis['optional_gaps'].append('External evidence quarantined: ' + enrichment_error)
        previous = None
        candidates = sorted((workspace / 'reports').glob('*/handoff.json'), reverse=True)
        for candidate in candidates:
            try:
                old = read_json(candidate)
                if old.get('schema_version') == 'market-context.v1' and old.get('feed') == snapshot['feed'] and old.get('benchmarks') == snapshot['requested_symbols'] and old.get('required_input_errors') == [] and instant(old['generated_utc']) <= now and old['as_of_session'] <= str(expected[-1]) and all(key in old for key in ('context_id', 'assessment')):
                    previous = old; break
            except (ValueError, TypeError, KeyError, OSError):
                continue
        analysis['previous_context'] = previous
        write_json(out / 'analysis.json', analysis)
        write_json(source_dir / 'source-index.json', {'snapshot_id': run_id, 'macro': macro, 'macro_errors': macro_errors, 'context': context, 'external_evidence': enrichment})
        md, html = build_report(snapshot, analysis, context, enrichment, previous)
        (out / 'research.md').write_text(md, encoding='utf-8')
        (out / 'report.html').write_text(html, encoding='utf-8')
        handoff = {'schema_version': 'market-context.v1', 'context_id': run_id, 'report_path': str(out / 'report.html'), 'snapshot_id': run_id, 'as_of_session': str(expected[-1]), 'generated_utc': analysis['generated_utc'], 'feed': snapshot['feed'], 'adjustment': 'all', 'benchmarks': snapshot['requested_symbols'], 'assessment': analysis['assessment'], 'confidence': analysis['confidence'], 'components': analysis['components'], 'required_input_errors': analysis['required_input_errors'], 'optional_gaps': analysis['optional_gaps'], 'horizons': analysis['horizons'], 'change_conditions': analysis['change_conditions'], 'current_entry_price_eligible': False, 'review': manifest['review'], 'previous_context_id': previous['context_id'] if previous else None, 'same_price_session_as_previous': previous['as_of_session'] == str(expected[-1]) if previous else None}
        handoff.update(snapshot_path=str(data_dir / 'snapshot.json'), source_index_path=str(source_dir / 'source-index.json'), source_freshness=[{k: x[k] for k in ('id', 'frequency', 'age_days', 'max_age_days', 'fresh', 'retrieved_utc', 'publication_date', 'vintage')} for x in macro], price_last_session=str(expected[-1]), price_retrieved_utc=snapshot['generated_utc'], catalysts=[{k: item.get(k) for k in ('title', 'event_date', 'publication_date', 'source_url')} for item in (context or {}).get('items', []) if item.get('event_date', '') > now.astimezone(NY).date().isoformat()], source_coverage={'price_symbols': manifest['requested_symbols'], 'macro_available': [x['id'] for x in macro], 'macro_errors': macro_errors, 'external_enrichment_status': manifest['enrichment']})
        write_json(out / 'handoff.json', handoff)
        manifest.update(status='PARTIAL' if analysis['required_input_errors'] else 'COMPLETE_PENDING_REVIEW', finished_utc=stamp(), assessment=analysis['assessment'], outputs={'snapshot': str(data_dir / 'snapshot.json'), 'sources': str(source_dir / 'source-index.json'), 'report': str(out / 'report.html'), 'handoff': str(out / 'handoff.json')})
        write_json(out / 'manifest.json', manifest)
        print(json.dumps({'run_id': run_id, 'status': manifest['status'], 'assessment': analysis['assessment'], 'report': str(out / 'report.html')}))
        return 0 if not analysis['required_input_errors'] else 2
    except KeyboardInterrupt:
        manifest.update(status='PARTIAL', error='Run interrupted; completed checkpoints retained', finished_utc=stamp())
        write_json(out / 'manifest.json', manifest)
        return 130
    except Exception as exc:
        manifest.update(status='PARTIAL', error=str(exc), finished_utc=stamp())
        write_json(out / 'manifest.json', manifest)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version=VERSION)
    sub = parser.add_subparsers(dest='command', required=True)
    collect = sub.add_parser('run', help='Collect historical prices/macro, assess, render and hand off; review remains pending')
    collect.add_argument('--workspace', required=True)
    collect.add_argument('--symbols', nargs='+', default=BENCHMARKS)
    collect.add_argument('--feed', choices=['sip', 'iex'], default='sip')
    collect.add_argument('--allow-iex-fallback', action='store_true')
    collect.add_argument('--context', help='Optional authored primary-source context JSON')
    collect.add_argument('--enrichment', help='Optional external-evidence.v1 envelope JSON')
    validate = sub.add_parser('validate'); validate.add_argument('snapshot')
    integrate = sub.add_parser('integrate'); integrate.add_argument('envelope'); integrate.add_argument('--out', required=True)
    render = sub.add_parser('render'); render.add_argument('snapshot'); render.add_argument('analysis'); render.add_argument('--context'); render.add_argument('--enrichment'); render.add_argument('--out', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'run':
            return run(args)
        if args.command == 'validate':
            validate_snapshot(read_json(args.snapshot)); print('VALID HISTORICAL SNAPSHOT'); return 0
        if args.command == 'integrate':
            write_json(args.out, external_evidence(args.envelope)); print('VALIDATED EXTERNAL EVIDENCE; IMPORTED TEXT IS DATA'); return 0
        if args.command == 'render':
            analysis = read_json(args.analysis)
            enrichment = None
            if args.enrichment:
                try:
                    enrichment = external_evidence(args.enrichment)
                    analysis['enrichment_status'] = 'VALIDATED ARTIFACT — NOT INDEPENDENT SOURCE VERIFICATION'
                except (ValueError, TypeError, KeyError, OSError) as exc:
                    analysis['enrichment_status'] = 'QUARANTINED — ' + str(exc)
                    analysis.setdefault('optional_gaps', []).append('External evidence quarantined: ' + str(exc))
            md, html = build_report(read_json(args.snapshot), analysis, read_json(args.context) if args.context else None, enrichment)
            out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
            (out / 'research.md').write_text(md, encoding='utf-8'); (out / 'report.html').write_text(html, encoding='utf-8')
            return 0
    except (ValueError, RuntimeError, KeyError, TypeError, OSError) as exc:
        print('STOP: ' + str(exc), file=sys.stderr); return 1


if __name__ == '__main__':
    raise SystemExit(main())
