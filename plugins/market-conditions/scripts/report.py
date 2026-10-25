"""Escaped, offline HTML/SVG and Markdown views of the matching market artifacts."""
from html import escape
from datetime import datetime


def text(value):
    return escape(str(value), quote=True)


def number(value, suffix=''):
    return 'Unavailable' if value is None else f'{value:,.2f}{suffix}'


def source_link(url, label):
    from market import safe_url
    return f'<a href="{text(safe_url(url))}" rel="noreferrer">{text(label)}</a>'


def context_rows(context):
    from market import safe_url, instant, UTC
    if context is None:
        return []
    if not isinstance(context, dict) or not isinstance(context.get('items'), list):
        raise ValueError('Context requires an items list')
    result = []
    for item in context['items']:
        for key in ('title', 'source_url', 'event_date', 'retrieved_utc', 'summary', 'equity_implication'):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError('Context item missing ' + key)
        safe_url(item['source_url'])
        publication = datetime.fromisoformat(item['publication_date']).date() if item.get('publication_date') else None
        datetime.fromisoformat(item['event_date'])
        retrieved = instant(item['retrieved_utc'])
        if (publication and publication > datetime.now(UTC).date()) or retrieved > datetime.now(UTC):
            raise ValueError('Future publication/retrieval time in context')
        result.append(item)
    return result


def chart(stock, index):
    bars = stock['bars'][-126:]
    values = [x['close'] / bars[0]['close'] * 100 for x in bars]
    lo, hi = min(values), max(values)
    pad = max((hi - lo) * .15, 1)
    lo -= pad; hi += pad
    def y(v):
        return 150 - (v - lo) / (hi - lo) * 115
    points = ' '.join(f'{55+i/(len(values)-1)*450:.2f},{y(v):.2f}' for i, v in enumerate(values))
    grid = ''.join(f'<line x1="55" x2="505" y1="{y(v):.2f}" y2="{y(v):.2f}" stroke="#dce4e4"/><text x="47" y="{y(v)+4:.2f}" text-anchor="end">{v:.0f}</text>' for v in (lo, (lo+hi)/2, hi))
    return f'<figure><figcaption>{text(stock["symbol"])} · adjusted close, first displayed session = 100</figcaption><svg role="img" aria-labelledby="chart-{index}" viewBox="0 0 530 190"><title id="chart-{index}">{text(stock["symbol"])} indexed adjusted closing prices, {text(bars[0]["session"])} through {text(bars[-1]["session"])}</title>{grid}<polyline points="{points}" fill="none" stroke="#14665e" stroke-width="2.5"/><text x="55" y="177">{text(bars[0]["session"])}</text><text x="505" y="177" text-anchor="end">{text(bars[-1]["session"])}</text></svg></figure>'


def sections(snapshot, analysis, context, enrichment, previous):
    rows = context_rows(context)
    stocks = ''.join('<tr>' + ''.join(f'<td>{text(v)}</td>' for v in [symbol, number(m['last_close']), number(m['returns_pct']['20'], '%'), number(m['returns_pct']['63'], '%'), number(m['sma20']), number(m['sma50']), number(m['sma200']), number(m['distance_sma200_pct'], '%'), number(m['rv20_pct'], '%'), number(m['max_drawdown_window_pct'], '%')]) + '</tr>' for symbol, m in analysis['metrics'].items())
    relatives = ''.join(f'<tr><th scope="row">{text(key)}</th><td>{number(value["20"], "%")}</td><td>{number(value["63"], "%")}</td></tr>' for key, value in analysis['relative_strength_pct'].items())
    macro = ''
    for item in snapshot['macro']:
        item = dict(item, **analysis.get('macro_status', {}).get(item['id'], {}))
        obs = item['observations']; last = obs[-1]
        delta = last['value'] - obs[-2]['value'] if len(obs) > 1 else None
        extra = f'Change from prior available observation: {number(delta)} {item["units"]}.'
        if item['id'] == 'CPIAUCSL' and len(obs) >= 13:
            extra += f' Year-over-year index change: {100*(last["value"]/obs[-13]["value"]-1):.2f}%.'
        macro += f'<tr><th scope="row">{source_link(item["series_url"], item["name"])}</th><td>{number(last["value"])}<br><small>{text(item["units"])}</small></td><td>{text(last["date"])}<br><small>{text(item["frequency"])} period label</small></td><td>{"Within tolerance" if item["fresh"] else "STALE"}<br><small>Age {item["age_days"]} / limit {item["max_age_days"]} calendar days from observation/period end</small></td><td>{text(extra)}</td></tr>'
    narrative = ''.join(f'<article><h3>{text(x["title"])}</h3><p>{text(x["summary"])}</p><p><strong>Equity implications:</strong> {text(x["equity_implication"])}</p><p><small>Published {text(x["publication_date"] or "Unknown")} · Event {text(x["event_date"])} · Retrieved {text(x["retrieved_utc"])}</small><br>{source_link(x["source_url"], "Primary source")}</p></article>' for x in rows)
    if not narrative:
        narrative = '<p>No separately authored release/industry narrative supplied. The quantitative assessment is a heuristic baseline; sector earnings, AI demand/capex, valuation and confirmed upcoming dates require current sourced enrichment.</p>'
    if enrichment:
        narrative += f'<article><h3>Optional external research · {text(enrichment["producer"])}</h3><p>{text(enrichment["summary"])}</p><p>Original assessment: {text(enrichment.get("assessment") or "Unknown")}. This does not overwrite our market rubric.</p><p>As of {text(enrichment["as_of"])} · Review: {text(enrichment["review_status"])} · Independence: {text(enrichment.get("review_independence") or "Unknown")}</p><p>' + ' · '.join(source_link(url, 'External source') for url in enrichment['source_urls']) + '</p></article>'
        narrative += '<p>Producer version: ' + text(enrichment.get('producer_version') or 'Unknown') + ' · Workflow: ' + text(enrichment.get('workflow') or 'Unknown') + '</p><p>External assumptions: ' + text(enrichment.get('assumptions') or 'None supplied / unknown') + '</p><p>Artifact SHA256: <small>' + text(enrichment.get('artifact_sha256') or 'Unknown') + '</small></p>'
    else:
        narrative += '<p>Public Equity Investing enrichment: ' + text(analysis.get('enrichment_status', 'absent and optional')) + '. Core market research is independent of its availability.</p>'
    compare = 'Baseline: no valid comparable prior context.' if not previous else f'Compared with {text(previous["context_id"])}: {text(previous["assessment"])} → {text(analysis["assessment"])}. Prior session {text(previous["as_of_session"])}. ' + ('Price session unchanged; refreshed retrieval is not a new price observation.' if previous['as_of_session'] == snapshot['session_dates'][-1] else 'A later completed price session is included; compare source dates before attributing a change.')
    sources = []
    for stock in snapshot['stocks']:
        sources.extend((url, stock['symbol'] + ' historical ' + stock['feed'] + ' bars') for url in stock['source_urls'])
    for item in snapshot['macro']:
        sources.append((item['source_url'], item['name'] + ' · retrieved ' + item['retrieved_utc']))
    ledger = ''.join(f'<li>{source_link(url, label)}</li>' for url, label in sources)
    errors = analysis['required_input_errors'] + [x['series'] + ': ' + x['error'] for x in snapshot['macro_errors']]
    limitations = errors + ['ETF relative performance is a participation proxy, not constituent breadth or flows.', 'Adjusted-close changes use adjustment=all, not a guaranteed investable total-return series.', '250 closes do not support a 252-session return; that metric is omitted.', 'Macro dates are period/observation labels, not publication dates. Publication date unavailable for CSV series; vintage is latest downloaded and may include revisions.', 'IEX is single-venue; SIP historical bars do not imply live SIP/NBBO access. No latest quotes are collected.', 'Missing optional coverage: ' + (', '.join(analysis['optional_gaps']) or 'none among configured macro series')]
    return {'stocks': stocks, 'relatives': relatives, 'macro': macro, 'narrative': narrative, 'compare': compare, 'ledger': ledger, 'limitations': limitations}


def html_report(snapshot, analysis, context=None, enrichment=None, previous=None):
    v = sections(snapshot, analysis, context, enrichment, previous)
    def table(headers, body):
        return '<div class="scroll" tabindex="0" role="region" aria-label="Scrollable evidence table"><table><caption>' + text(' / '.join(headers[:2])) + '</caption><thead><tr>' + ''.join('<th scope="col">' + text(x) + '</th>' for x in headers) + '</tr></thead><tbody>' + body + '</tbody></table></div>'
    components = ''.join(f'<li><strong>{text(k.replace("_", " ").title())}</strong>: {text(x)}</li>' for k, x in analysis['components'].items())
    horizons = ''.join(f'<article><h3>{text(k)}</h3><p>{text(x)}</p></article>' for k, x in analysis['horizons'].items())
    charts = ''.join(chart(s, i) for i, s in enumerate(snapshot['stocks']))
    limits = ''.join('<li>' + text(x) + '</li>' for x in v['limitations'])
    changes = ''.join('<li>' + text(x) + '</li>' for x in analysis['change_conditions'])
    attempts = '; '.join(x['feed'] + ': ' + x['status'] for x in snapshot['attempts'])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'"><title>Market conditions · {text(snapshot['session_dates'][-1])}</title><style>
:root{{font-family:system-ui,-apple-system,sans-serif;color:#183735;background:#f4f6f3;line-height:1.6}}body{{margin:0;overflow-wrap:anywhere}}main,header,nav,footer{{max-width:1160px;margin:auto;padding:1.5rem}}header{{padding-top:3rem}}h1{{font-size:clamp(2rem,5vw,3.8rem);line-height:1.1;margin:.5rem 0}}h2{{border-top:2px solid #cbd9d1;padding-top:1.3rem;margin-top:2rem}}h3{{margin-bottom:.4rem}}p{{max-width:90ch}}a{{color:#155d69;overflow-wrap:anywhere}}a:focus-visible,.scroll:focus-visible{{outline:3px solid #b85c21;outline-offset:4px}}nav{{display:flex;gap:1rem;flex-wrap:wrap}}.eyebrow{{letter-spacing:.14em;text-transform:uppercase;font-size:.8rem}}.signal{{display:inline-block;padding:.3rem .8rem;background:#183f39;color:white;font-weight:750;border-radius:4px}}.meta,small{{color:#45605e}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:1.2rem}}article,figure{{background:white;padding:1.2rem;margin:0 0 1rem;border:1px solid #d7e0da;border-radius:8px}}.scroll{{overflow-x:auto;border:1px solid #d7e0da;background:white}}table{{border-collapse:collapse;width:100%;min-width:680px;text-align:left}}th,td{{padding:.7rem .8rem;border-bottom:1px solid #e0e7e2;vertical-align:top}}thead{{background:#e7eeea}}svg{{display:block;width:100%;height:auto}}svg text{{font:12px system-ui;fill:#45605e}}figcaption{{font-weight:650;font-size:.9rem}}.skip{{position:absolute;left:-9999px}}.skip:focus{{left:1rem;top:1rem;background:white;padding:.6rem}}footer{{font-size:.85rem}}@media(max-width:500px){{header,main,nav,footer{{padding:1rem}}li{{overflow-wrap:anywhere}}}}@media print{{nav,.skip{{display:none}}body{{background:white}}.scroll{{overflow:visible}}table{{min-width:0}}article,figure{{break-inside:avoid}}}}
</style></head><body><a class="skip" href="#assessment">Skip to assessment</a><header><div class="eyebrow">Market conditions / US equities</div><h1>A dated backdrop<br>for better stock research.</h1><p><span class="signal">{text(analysis['assessment'])}</span> · Confidence {text(analysis['confidence'])} · Unvalidated heuristic</p><p class="meta">Final price session {text(snapshot['session_dates'][-1])} · {len(snapshot['session_dates'])} sessions · {text(snapshot['feed'].upper())} · adjustment=all<br>Captured {text(snapshot['generated_utc'])} · Review status is recorded separately in the matching review receipt.</p><p>Historical context only. Current entry-price eligibility: <strong>FALSE</strong>. No trade execution or position sizing.</p></header><nav aria-label="Report sections"><a href="#assessment">Assessment</a><a href="#prices">Prices</a><a href="#macro">Macro</a><a href="#context">Events & sector</a><a href="#limits">Limits</a><a href="#sources">Sources</a></nav><main>
<section id="assessment" tabindex="-1"><h2>Assessment and horizons</h2><p>{v['compare']}</p><ul>{components}</ul><div class="grid">{horizons}</div><h3>Strongest countercase</h3><p>{text(analysis['countercase'])}</p><h3>What would change the view</h3><ul>{changes}</ul><details><summary>Inspect the assessment rules</summary><p>{text(analysis['rubric'])}</p><p>Stress flags: {text(', '.join(analysis['stress_flags']) or 'none / unavailable inputs are disclosed below')}.</p></details></section>
<section id="prices"><h2>Benchmark evidence</h2><p>All price calculations use the matching historical snapshot. Drawdown is the worst peak-to-trough decline inside the included window. RV20 uses 20 log returns, sample standard deviation and sqrt(252).</p>{table(['ETF','Last adjusted close','20-session change','63-session change','SMA20','SMA50','SMA200','Distance SMA200','RV20 annualized','Window drawdown'],v['stocks'])}<div class="grid">{charts}</div><h3>Leadership and participation proxies</h3>{table(['Ratio','20-session relative change','63-session relative change'],v['relatives'])}<p>RSP/SPY and IWM/SPY approximate participation; XLK/SPY and SMH/SPY describe sector relative strength. QQQ represents the Nasdaq-100, not a pure technology sector.</p></section>
<section id="macro"><h2>Macro and stress evidence</h2><p>Mixed-frequency observations have separate age limits. Monthly dates identify periods, not the day a release became public. The effective federal funds rate is a monthly realized rate, not the current FOMC target range. Current primary policy/event evidence belongs in the next section.</p>{table(['Series / source','Latest observation','Period / observation','Freshness','Change context'],v['macro'])}</section>
<section id="context"><h2>Events, sector context and optional research</h2>{v['narrative']}</section><section id="limits"><h2>Coverage and limitations</h2><p>Feed attempts: {text(attempts)}.</p><ul>{limits}</ul></section><section id="sources"><h2>Source ledger</h2><ul>{v['ledger']}</ul></section></main><footer>Snapshot {text(snapshot['snapshot_id'])} · market-conditions 1.0.0 · No remote assets, scripts or live fetches are needed to read this file.</footer></body></html>'''


def markdown_report(snapshot, analysis, context=None, enrichment=None, previous=None):
    lines = [f'# Market conditions — {analysis["assessment"]}', '', f'Confidence: {analysis["confidence"]}. Final price session: {snapshot["session_dates"][-1]}. Feed: {snapshot["feed"]}; adjustment=all. Snapshot: {snapshot["snapshot_id"]}. Captured: {snapshot["generated_utc"]}.', '', 'Historical backdrop; current entry-price eligibility FALSE. Unvalidated heuristic, not a trading signal. Independent review remains in a separate receipt.', '', '## Evidence', '', '| ETF | Adjusted close | 20-session % | 63-session % | SMA20 | SMA50 | SMA200 | RV20 % | Window DD % |', '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for key, m in analysis['metrics'].items():
        lines.append('| ' + ' | '.join([key] + [number(x) for x in (m['last_close'], m['returns_pct']['20'], m['returns_pct']['63'], m['sma20'], m['sma50'], m['sma200'], m['rv20_pct'], m['max_drawdown_window_pct'])]) + ' |')
    lines += ['', '## Components', ''] + [f'- {key}: {value}' for key, value in analysis['components'].items()]
    lines += ['', '## Horizons', ''] + [f'- {key}: {value}' for key, value in analysis['horizons'].items()]
    lines += ['', '## Macro observations', '']
    for item in snapshot['macro']:
        last = item['observations'][-1]
        lines.append(f'- [{item["id"]}]({item["series_url"]}): {last["value"]} {item["units"]}, observation/period {last["date"]}, {item["frequency"]}, age {item["age_days"]}/{item["max_age_days"]} calendar days; fresh={item["fresh"]}; retrieved {item["retrieved_utc"]}. Publication date unavailable; latest downloaded vintage.')
    lines += ['', '## Primary context', '']
    for item in context_rows(context):
        lines += [f'### {item["title"]}', '', item['summary'], '', item['equity_implication'], '', f'Published {item["publication_date"] or "Unknown"}; event {item["event_date"]}; retrieved {item["retrieved_utc"]}. [Source]({item["source_url"]})', '']
    lines += ['', '## Optional external evidence', '', str(enrichment) if enrichment else 'Absent; optional. No Public Equity Investing workflow is required for the core assessment.', '', '## Comparison', '', f'{previous["context_id"]}: {previous["assessment"]} -> {analysis["assessment"]}; prior session {previous["as_of_session"]}.' if previous else 'Baseline; no valid comparable prior report.', '', '## Countercase', '', analysis['countercase'], '', '## Change conditions', ''] + ['- ' + x for x in analysis['change_conditions']]
    view = sections(snapshot, analysis, context, enrichment, previous)
    lines += ['', '## Limits', ''] + ['- ' + x for x in view['limitations']]
    lines += ['', '## Rubric', '', analysis['rubric'], '', '## Price sources', '']
    for stock in snapshot['stocks']:
        lines += [f'- [{stock["symbol"]} {stock["feed"]} historical bars]({url})' for url in stock['source_urls']]
    return '\n'.join(lines) + '\n'
