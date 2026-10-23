#!/usr/bin/env python3
"""Render a validated Market Release Watch decision JSON as offline HTML. Stdlib only."""
import argparse
from datetime import datetime, timedelta, timezone
from html import escape
import json
import math
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

LABELS = {1: 'STRONG SELL', 2: 'SELL', 3: 'WAIT', 4: 'BUY', 5: 'STRONG BUY'}
STATUSES = {'scheduled', 'primary_verified', 'secondary_reported', 'due_not_verified',
            'unable_to_verify', 'rescheduled', 'cancelled'}
RELEASED = {'primary_verified', 'secondary_reported'}


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timezone missing from timestamp')
    return parsed.astimezone(timezone.utc)


def number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate(data):
    require(data['schema_version'] == 1, 'Unsupported report schema')
    asof = timestamp(data['as_of_utc'])
    ZoneInfo(data['local_timezone'])
    a = data['assessment']
    score = a['score']
    require(type(score) is int and score in LABELS, 'Score must be an integer from 1 to 5')
    require(a['label'] == LABELS[score], 'Signal label does not match score')
    require(a['confidence'] in {'Low', 'Medium', 'High'}, 'Invalid confidence')
    require(a['phase'] in {'pre_release', 'provisional', 'confirmed', 'expired'}, 'Invalid phase')
    evaluated = timestamp(a['evaluated_at_utc'])
    require(evaluated >= asof, 'Assessment predates its evidence')
    require(timestamp(a['reassess_at_utc']) > evaluated, 'Reassessment must follow evaluation')
    for field in ('scope', 'horizon', 'summary', 'action', 'contrary_risk', 'invalidation', 'evaluator'):
        require(isinstance(a[field], str) and a[field].strip(), f'Missing assessment {field}')
    require(2 <= len(a['reasons']) <= 3, 'Supply two or three reasons')
    require(all(isinstance(reason, str) and reason.strip() for reason in a['reasons']), 'Invalid reason')
    sources = {s['id']: s for s in data['sources']}
    require(len(sources) == len(data['sources']), 'Duplicate source IDs')
    for source in sources.values():
        url = urlsplit(source['url'])
        require(url.scheme in {'https', 'http'} and bool(url.netloc) and not url.username
                and not url.password, 'Source URL must be public HTTP(S) without credentials')
        timestamp(source['retrieved_at_utc'])
    events = {e['id']: e for e in data['events']}
    require(len(events) == len(data['events']) and bool(events), 'Missing or duplicate event IDs')
    for event in events.values():
        require(event['status'] in STATUSES, 'Invalid release status')
        due = timestamp(event['scheduled_at_utc'])
        require(event['source_ids'] and all(key in sources for key in event['source_ids']), 'Unknown event source')
        if event.get('next_retry_at_utc'):
            timestamp(event['next_retry_at_utc'])
        for metric in event['metrics']:
            for key in ('actual', 'consensus', 'prior'):
                require(metric[key] is None or number(metric[key]), 'Metric must be finite numeric or null')
            if event['status'] not in RELEASED:
                require(metric['actual'] is None, 'Unverified release cannot contain actuals')
        if event['status'] in RELEASED:
            require(due <= asof, 'Future report cannot be released')
            require(any(number(m['actual']) for m in event['metrics']), 'Released event lacks a verified actual')
    ids = a['evidence_event_ids']
    require(all(key in events for key in ids), 'Unknown signal evidence event')
    evidence = [events[key] for key in ids]
    if a['phase'] in {'pre_release', 'expired'}:
        require(score == 3, 'Pre-release or expired evidence requires WAIT')
    if score != 3:
        require(evidence and all(e['status'] in RELEASED for e in evidence), 'Directional signal needs released evidence')
        latest = max(timestamp(e['scheduled_at_utc']) for e in evidence)
        require(0 <= (asof - latest).total_seconds() <= 7200, 'Directional evidence is outside the two-hour horizon')
        require(timestamp(a['reassess_at_utc']) <= latest + timedelta(hours=2), 'Signal exceeds two-hour expiry')
        pending = [timestamp(e['scheduled_at_utc']) for e in events.values()
                   if e['status'] not in RELEASED | {'cancelled'} and timestamp(e['scheduled_at_utc']) > asof]
        if pending:
            require(timestamp(a['reassess_at_utc']) <= min(pending), 'Reassess before the next pending report')
        has_consensus = any(number(m['consensus']) and number(m['actual']) for e in evidence for m in e['metrics'])
        limited = any(e['status'] == 'secondary_reported' for e in evidence) or not has_consensus
        if a['phase'] == 'provisional' or limited:
            require(score in {2, 4} and a['confidence'] == 'Low', 'Provisional evidence permits only Low-confidence SELL/BUY')
        if limited:
            require(a['phase'] == 'provisional', 'Secondary-only or no-consensus call must be provisional')
        if score in {1, 5}:
            require(a['phase'] == 'confirmed' and not limited, 'Extreme score needs primary confirmed evidence')
        require(a['phase'] in {'provisional', 'confirmed'}, 'Invalid directional phase')
    reaction = data['market_reaction']
    require(reaction['equity_confirmation'] in {'bullish', 'bearish', 'mixed', 'unavailable'}, 'Invalid confirmation')
    fresh_equity = []
    for obs in reaction['observations']:
        require(obs['change'] is None or number(obs['change']), 'Invalid market change')
        if obs['baseline_at_utc'] and obs['observed_at_utc']:
            baseline, observed = timestamp(obs['baseline_at_utc']), timestamp(obs['observed_at_utc'])
            require(baseline < observed <= asof, 'Invalid reaction interval')
            if obs['instrument'] in {'SPY', 'QQQ'} and number(obs['change']) and obs['feed']:
                if (asof - observed).total_seconds() <= 300 and evidence:
                    due = max(timestamp(e['scheduled_at_utc']) for e in evidence)
                    if 0 <= (due - baseline).total_seconds() <= 300 and due <= observed:
                        fresh_equity.append(obs['change'])
    if score != 3 and a['phase'] == 'confirmed':
        direction = 'bullish' if score > 3 else 'bearish'
        require(reaction['equity_confirmation'] == direction, 'Confirmed call contradicts equity confirmation')
        require(any(value > 0 if score > 3 else value < 0 for value in fresh_equity), 'Confirmed call needs fresh comparable equity evidence')
    if a['confidence'] == 'High' and score != 3:
        require(a['phase'] == 'confirmed' and all(e['status'] == 'primary_verified' for e in evidence), 'High confidence requires primary confirmation')


def text(value):
    return escape(str(value), quote=True)


def fmt(value):
    return 'Pending / unavailable' if value is None else f'{value:g}'


def time_pair(value, local_zone):
    instant = timestamp(value)
    et = instant.astimezone(ZoneInfo('America/New_York')).strftime('%b %d, %I:%M %p ET')
    local_label = 'Manila' if local_zone == 'Asia/Manila' else local_zone
    local = instant.astimezone(ZoneInfo(local_zone)).strftime('%b %d, %I:%M %p') + ' ' + local_label
    return f'{text(et)}<br><span class="muted">{text(local)}</span>'


CSS = '''
:root{color-scheme:light;--ink:#172b4d;--muted:#526782;--line:#dbe4ef;--blue:#3156b8}*{box-sizing:border-box}body{margin:0;background:#eaf0f7;color:var(--ink);font:17px/1.65 "Avenir Next","Segoe UI",sans-serif}header{background:#172b4d;color:#fff;padding:42px max(24px,calc((100vw - 1100px)/2)) 38px}.brand{font-size:14px;letter-spacing:.08em;text-transform:uppercase;color:#a8c5ff}h1{font:600 clamp(32px,5vw,54px)/1.15 Georgia,serif;margin:14px 0 18px}header p{margin:8px 0;color:#d4e0f2}header .muted{color:#d4e0f2}main{max-width:1150px;margin:auto;background:#fff;padding:34px 46px 56px}.signal{border:2px solid var(--tone);border-left:9px solid var(--tone);background:var(--wash);padding:26px 28px;border-radius:6px}.buy{--tone:#14623c;--wash:#edf8f0}.sell{--tone:#a32729;--wash:#fff1f0}.wait{--tone:#805100;--wash:#fff7e6}.eyebrow{font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}.call{font-size:clamp(40px,7vw,72px);font-weight:750;line-height:1.06;color:var(--tone);margin:12px 0}.call small{font-size:.44em;white-space:nowrap}.badges{display:flex;gap:8px;flex-wrap:wrap;margin:15px 0}.badge{font-size:13px;border:1px solid currentColor;border-radius:4px;padding:3px 9px}.signal .action{font-size:20px;font-weight:650;line-height:1.5;margin-bottom:0}.scale{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px;margin:22px 0 8px}.scale div{padding:8px 4px;border:1px solid var(--line);text-align:center;font-size:12px;line-height:1.35}.scale .active{background:var(--tone);color:#fff;border-color:var(--tone);font-weight:700}.scale b{display:block;font-size:19px}.meta{font-size:13px;overflow-wrap:anywhere}.grid{display:grid;grid-template-columns:1fr 1fr;gap:26px;margin:24px 0}.panel{padding:20px 22px;border:1px solid var(--line);border-radius:5px}.panel h2{margin:0 0 12px;font-size:22px;border:0;padding:0}.panel p{margin:8px 0}h2{font:600 28px/1.3 Georgia,serif;margin:38px 0 16px;border-top:2px solid var(--line);padding-top:22px}p,li{max-width:82ch}ul{padding-left:22px}li{margin:8px 0}a{color:#2448a4;text-underline-offset:3px;overflow-wrap:anywhere}a:focus-visible,summary:focus-visible,.table-wrap:focus-visible{outline:3px solid #a45a00;outline-offset:4px}.muted{color:var(--muted)}.table-wrap{overflow:auto;max-width:100%;border:1px solid var(--line);margin:18px 0}table{width:100%;border-collapse:collapse;font-size:14px;min-width:770px}caption{text-align:left;font-weight:650;padding:12px;background:#edf3ff}th,td{padding:11px 13px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}th{background:#f5f8fc}td small{display:block;color:var(--muted);font-size:12px}.status{font-size:12px;font-weight:650}.sources li{margin-bottom:14px}.source-note{display:block;color:var(--muted);font-size:13px}details{margin:28px 0;border:1px solid var(--line);padding:16px}summary{font-weight:650;cursor:pointer}pre{background:#f5f8fc;padding:16px;overflow:auto;max-height:450px;font:12px/1.6 ui-monospace,monospace}footer{margin-top:36px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}.note{background:#edf3ff;padding:14px 18px;border-left:4px solid var(--blue)}@media(max-width:650px){body{font-size:16px}header{padding:30px 21px}main{padding:24px 19px}.signal{padding:20px 18px}.grid{grid-template-columns:1fr;gap:16px}.scale div{font-size:10px}.signal .action{font-size:18px}h2{font-size:25px}}@media print{body{background:#fff;font-size:10pt}header{background:#fff;color:var(--ink);padding:0 0 20px}header p,.brand{color:var(--muted)}main{padding:0;max-width:none}h1{font-size:28pt}.signal{break-inside:avoid}.grid{display:block}.panel{margin:12px 0}table{min-width:0;font-size:9pt}.table-wrap{overflow:visible}tr{break-inside:avoid}details{display:none}a{color:inherit}}
'''


def render(data):
    validate(data)
    a, zone = data['assessment'], data['local_timezone']
    tone = 'buy' if a['score'] > 3 else 'sell' if a['score'] < 3 else 'wait'
    badges = ''.join(f'<span class="badge">{text(item)}</span>' for item in
                     (f"{a['confidence']} confidence", a['phase'].replace('_', ' ').title(), a['scope']))
    scale = ''.join(f'<div class="{"active" if n == a["score"] else ""}"><b>{n}</b>{text(label.title())}</div>' for n, label in LABELS.items())
    reasons = ''.join(f'<li>{text(item)}</li>' for item in a['reasons'])
    rows = []
    for event in data['events']:
        status = event['status'].replace('_', ' ').title()
        if event['status'] in {'scheduled', 'due_not_verified', 'unable_to_verify'}:
            status = 'Not released' if event['status'] == 'scheduled' else status
        for metric in event['metrics']:
            actual = metric['actual']
            surprise = actual - metric['consensus'] if number(actual) and number(metric['consensus']) else None
            source_links = ' · '.join(f'<a href="#source-{text(key)}">Source {index}</a>' for index, key in enumerate(event['source_ids'], 1))
            retry = f'<small>Retry: {time_pair(event["next_retry_at_utc"], zone)}</small>' if event.get('next_retry_at_utc') else ''
            rows.append(f'<tr><td><strong>{text(event["title"])}</strong><small>{text(event["period"])} · {text(event["vintage"])}</small><small>{text(metric["name"])} · {text(metric["unit"])}</small>{source_links}</td><td>{time_pair(event["scheduled_at_utc"], zone)}</td><td><span class="status">{text(status)}</span>{retry}</td><td>{text(fmt(actual))}</td><td>{text(fmt(metric["consensus"]))}</td><td>{text(fmt(metric["prior"]))}<small>{text(metric["comparison"])}</small></td><td>{text(fmt(surprise))}</td></tr>')
    source_items = ''.join(f'<li id="source-{text(s["id"])}"><a href="{text(s["url"])}" rel="noopener noreferrer">{text(s["title"])}</a><span class="source-note">Retrieved {time_pair(s["retrieved_at_utc"], zone)} · {text(s["note"])}</span></li>' for s in data['sources'])
    event_notes = ''.join(f'<li><strong>{text(e["title"])}:</strong> {text(e["notes"])}</li>' for e in data['events'] if e['notes'])
    reaction = data['market_reaction']
    observations = ''.join(f'<li><strong>{text(o["instrument"])}</strong> {text(fmt(o["change"]))} {text(o["unit"])} · {text(o["feed"])}<span class="source-note">{time_pair(o["baseline_at_utc"], zone) if o["baseline_at_utc"] else "No baseline"} → {time_pair(o["observed_at_utc"], zone) if o["observed_at_utc"] else "No fresh observation"} · {text(o["note"])}</span></li>' for o in reaction['observations'])
    limitations = ''.join(f'<li>{text(value)}</li>' for value in data['limitations'])
    checks = ''.join(f'<li>{text(value)}</li>' for value in data['next_checks'])
    raw = text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>{text(data['title'])}</title><style>{CSS}</style></head><body>
<header><div class="brand">Darren’s research collection · Market Release Watch</div><h1>{text(data['title'])}</h1><p>Economic releases → a plain-English market judgment</p><p class="meta">As of {time_pair(data['as_of_utc'], zone)} · U.S. session {text(data['session_date_et'])}</p></header>
<main><section class="signal {tone}" aria-labelledby="signal-title"><div class="eyebrow">Best-guess market signal</div><div class="call" id="signal-title">{text(a['label'])} <small>{a['score']} / 5</small></div><div class="badges">{badges}</div><p>{text(a['summary'])}</p><p class="action">What to do now: {text(a['action'])}</p><div class="scale" aria-label="Signal scale from strong sell to strong buy">{scale}</div><p class="meta">Horizon: {text(a['horizon'])}<br>Reassess: {time_pair(a['reassess_at_utc'], zone)}<br>Evaluated by {text(a['evaluator'])} · {time_pair(a['evaluated_at_utc'], zone)}</p></section>
<div class="grid"><section class="panel"><h2>Why this call</h2><ul>{reasons}</ul></section><section class="panel"><h2>What would change the call?</h2><p>{text(a['invalidation'])}</p><p class="muted"><strong>Main contrary risk:</strong> {text(a['contrary_risk'])}</p></section></div>
<p class="note">This is a static research judgment, not a live quote or an automatic order. The 1–5 score is direction and strength, not a measured chance of profit. SELL means a bearish view; it does not automatically mean shorting the market.</p>
<h2>Today’s release board</h2><div class="table-wrap" role="region" aria-label="Scrollable economic release table" tabindex="0"><table><caption>Published actuals versus pre-release expectations. Blank evidence stays unavailable.</caption><thead><tr><th scope="col">Report / metric</th><th scope="col">Due ET / local</th><th scope="col">Status</th><th scope="col">Actual</th><th scope="col">Forecast</th><th scope="col">Prior</th><th scope="col">Surprise</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div><ul>{event_notes}</ul>
<h2>Did the market agree?</h2><p>{text(reaction['status'])}</p><ul>{observations}</ul><h2>Next checks</h2><ul>{checks}</ul><h2>Source gaps and limitations</h2><ul>{limitations}</ul><h2>Sources</h2><ol class="sources">{source_items}</ol><details><summary>Inspect the complete evidence and assessment</summary><pre>{raw}</pre></details><footer>Snapshot {text(data['report_id'])}. Self-contained HTML; no remote fonts, scripts or automatic refresh. Source links need internet access. Rendered {text(datetime.now(timezone.utc).isoformat())}.</footer></main></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.out.resolve():
        parser.error('Output must not overwrite its input')
    try:
        html = render(json.loads(args.input.read_text(encoding='utf-8')))
    except (ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as stream:
        stream.write(html)
    print(args.out.resolve())


if __name__ == '__main__':
    main()
