#!/usr/bin/env python3
"""Render a concise Coinbase buying brief (Markdown) and its snapshot as standalone HTML. Stdlib only."""
import argparse
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

REQUIRED_FIELDS = ('Verdict', 'Why', 'News', 'Buy only if', 'Exit if')
BOUNCE_FIELDS = ('Verdict', 'Why', 'News')
TONES = {'buy': 'good', 'watch': 'good', 'wait': 'wait', 'hold': 'wait', 'skip': 'wait', 'avoid': 'avoid', 'sell': 'avoid'}
STATES = {'bounce_setup': 'Bounce setup', 'oversold_falling': 'Oversold, still falling', 'not_oversold': 'Not oversold'}
OVERSOLD_CHECKS = (('rsi_below_30', 'RSI under 30'), ('below_lower_band', 'Below lower band'), ('deep_drop_from_30d_high', 'Deep drop from 30-day high'), ('three_down_days', '3+ down days'))
REVERSAL_SIGNALS = (('capitulation_volume', 'Volume spike'), ('reversal_candle', 'Reversal candle'), ('rsi_divergence', 'RSI divergence'))
OMITTED_SECTIONS = {'sources'}


def inline(text):
    pattern = r'\[([^\]]+)\]\(([^\s]+)\)|\*\*([^*]+)\*\*|`([^`]+)`'
    parts, last = [], 0
    for m in re.finditer(pattern, text):
        parts.append(escape(text[last:m.start()]))
        label, url, bold, code = m.groups()
        if label is not None:
            if urlsplit(url).scheme.lower() in ('https', 'http'):
                parts.append(f'<a href="{escape(url, quote=True)}" rel="noopener noreferrer">{escape(label)}</a>')
            else:
                parts.append(escape(label + ' (' + url + ')'))
        elif bold is not None:
            parts.append('<strong>' + escape(bold) + '</strong>')
        else:
            parts.append('<code>' + escape(code) + '</code>')
        last = m.end()
    parts.append(escape(text[last:]))
    return ''.join(parts)


def markdown(text):
    lines, result, i = text.splitlines(), [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith('```'):
            block = []; i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                block.append(lines[i]); i += 1
            if i == len(lines):
                raise ValueError('Unclosed fenced code block')
            result.append('<pre><code>' + escape('\n'.join(block)) + '</code></pre>'); i += 1
        elif line.startswith('#'):
            match = re.fullmatch(r'(#{1,6})\s+(.+)', line)
            if not match:
                raise ValueError('Malformed Markdown heading')
            level, title = len(match[1]), match[2]
            if level > 1:
                result.append(f'<h{level}>' + inline(title) + f'</h{level}>')
            else:
                result.append('<p class="report-title">' + inline(title) + '</p>')
            i += 1
        elif line.startswith('|') and i + 1 < len(lines) and re.fullmatch(r'[| :\-]+', lines[i+1]):
            cells = lambda row: [cell.strip() for cell in row.strip().strip('|').split('|')]
            headers = cells(line); i += 2
            table = ['<div class="table-wrap" role="region" aria-label="Table" tabindex="0"><table><thead><tr>']
            table += [f'<th scope="col">{inline(c)}</th>' for c in headers]
            table.append('</tr></thead><tbody>')
            while i < len(lines) and lines[i].startswith('|'):
                row = cells(lines[i])
                if len(row) != len(headers):
                    raise ValueError('Inconsistent Markdown table columns')
                table.append('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in row) + '</tr>'); i += 1
            result.append(''.join(table) + '</tbody></table></div>')
        elif re.match(r'^(?:[-*] |\d+\. )', line):
            ordered = bool(re.match(r'^\d+\. ', line)); tag = 'ol' if ordered else 'ul'
            pattern = r'^\d+\. (.*)' if ordered else r'^[-*] (.*)'
            result.append('<' + tag + '>')
            while i < len(lines) and (match := re.match(pattern, lines[i])):
                result.append('<li>' + inline(match[1]) + '</li>'); i += 1
            result.append('</' + tag + '>')
        else:
            paragraph = [line]; i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r'^(?:#|\||```|[-*] |\d+\. )', lines[i]):
                paragraph.append(lines[i]); i += 1
            result.append('<p>' + inline(' '.join(paragraph)) + '</p>')
    return '\n'.join(result)


def money(value):
    if value >= 1000:
        return f'${value:,.0f}'
    if value >= 10:
        return f'${value:,.2f}'
    text = f'{value:.4f}'.rstrip('0')
    return '$' + (text + '0' * (2 - len(text.split('.')[1])) if len(text.split('.')[1]) < 2 else text)


def split_sections(report):
    """Return (title, preamble, [(heading, body)]) using level-2 headings as section breaks."""
    title, preamble, sections, current = None, [], [], None
    fenced = False
    for line in report.splitlines():
        if line.startswith('```'):
            fenced = not fenced
        if not fenced and line.startswith('# ') and title is None:
            title = line[2:].strip()
        elif not fenced and line.startswith('## '):
            current = (line[3:].strip(), [])
            sections.append(current)
        else:
            (current[1] if current else preamble).append(line)
    return title or 'Crypto Buying Brief', '\n'.join(preamble).strip(), [(h, '\n'.join(b).strip()) for h, b in sections]


def parse_card(product, body, required=REQUIRED_FIELDS):
    fields, extra = {}, []
    for line in body.splitlines():
        match = re.match(r'^[-*] \*\*(.+?):\*\*\s*(.+)$', line)
        if match and match[1] in required and match[1] not in fields:
            fields[match[1]] = match[2].strip()
        elif line.strip():
            extra.append(line)
    missing = [name for name in required if name not in fields]
    if missing:
        raise ValueError(f'{product} section is missing: ' + ', '.join(missing))
    levels = {}
    for name in ('Buy only if', 'Exit if'):
        if name not in required:
            continue
        match = re.search(r'\$([\d,]*\.?\d+)', fields[name])
        if not match:
            raise ValueError(f'{product} "{name}" needs a dollar level, such as $73,080')
        levels[name] = float(match[1].replace(',', ''))
    return fields, levels, '\n'.join(extra)


def chart(product, entry, exit_level, target=None, days=None):
    bars = product['candles'][-days:] if days else product['candles']; closes = [b['close'] for b in bars]
    marks = [exit_level, entry] + ([target] if target is not None else [])
    low, high = min(closes + marks), max(closes + marks)
    pad = (high - low) * .06 or high * .05
    low -= pad; high += pad
    width, height, left, right, top, bottom = 640, 220, 8, 70, 10, 22
    def x(i): return left + i / (len(closes) - 1) * (width - left - right)
    def y(value): return top + (high - value) / (high - low) * (height - top - bottom)
    points = ' '.join(f'{x(i):.1f},{y(v):.1f}' for i, v in enumerate(closes))
    def level(value, kind):
        return (f'<line class="{kind}" x1="{left}" x2="{width-right}" y1="{y(value):.1f}" y2="{y(value):.1f}"/>'
                f'<text class="{kind}-label" x="{width-right+6}" y="{y(value)+4:.1f}">{money(value)}</text>')
    label = (f'{escape(product["product"])} daily closes in US dollars, {escape(bars[0]["start_utc"][:10])} to '
             f'{escape(bars[-1]["start_utc"][:10])}, with entry trigger {money(entry)} and exit level {money(exit_level)}'
             + (f' and target {money(target)}' if target is not None else ''))
    return (f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{label}">'
            f'{level(target, "target") if target is not None else ""}{level(entry, "entry")}{level(exit_level, "exit")}'
            f'<polyline class="price-line" points="{points}"/>'
            f'<circle class="price-dot" cx="{x(len(closes)-1):.1f}" cy="{y(closes[-1]):.1f}" r="3.5"/>'
            f'<text x="{left}" y="{height-5}">{escape(bars[0]["start_utc"][:10])}</text>'
            f'<text x="{width-right}" y="{height-5}" text-anchor="end">{escape(bars[-1]["start_utc"][:10])}</text></svg>')


def percent(value):
    return f'<b class="{"down" if value < 0 else "up"}">{value:+.1f}%</b>'


def card(product, body):
    fields, levels, extra = parse_card(product['product'], body)
    metrics = product['metrics']
    tone = TONES.get(re.split(r'\W+', fields['Verdict'].lower())[0], 'neutral')
    stats = ''.join(f'<div><dt>{name}</dt><dd>{value}</dd></div>' for name, value in (
        ('7 days', percent(metrics['return_7d_pct'])),
        ('30 days', percent(metrics['return_30d_pct'])),
        ('Volatility', f'<b>{metrics["volatility_30d_annualized_pct"]:.0f}%</b>'),
        ('90-day drawdown', percent(metrics['max_drawdown_90d_pct'])),
        ('vs 200-day avg', percent(metrics['close_vs_sma_200_pct']))))
    return f'''<article class="card">
<header><h2>{escape(product['product'].split('-')[0])}</h2><span class="price">{money(product['ticker']['last_trade_price'])}</span><span class="tag {tone}">{inline(fields['Verdict'])}</span></header>
<p class="why">{inline(fields['Why'])}</p>
{chart(product, levels['Buy only if'], levels['Exit if'])}
<div class="legend"><span><i class="key entry"></i>Entry trigger</span><span><i class="key exit"></i>Exit level</span></div>
<dl class="stats">{stats}</dl>
{news_line(fields['News'])}
<ul class="actions"><li><b>Buy only if</b> {inline(fields['Buy only if'])}</li><li><b>Exit if</b> {inline(fields['Exit if'])}</li></ul>
{f'<div class="extra">{markdown(extra)}</div>' if extra else ''}
</article>'''


def news_line(text):
    return '<p class="news"><b>News</b> ' + inline(re.sub(r'\[([^\]]+)\]\([^\s]+\)', r'\1', text)) + '</p>'


def bounce_card(product, body):
    name = product['product']
    if 'bounce' not in product:
        raise ValueError(f'{name} has no bounce metrics; fetch a new snapshot with the current collector')
    fields, _, extra = parse_card(name, body, BOUNCE_FIELDS)
    data = product['bounce']; plan = data['plan']; history = data['history']
    first_word = re.split(r'\W+', fields['Verdict'].lower())[0]
    broken = product['ticker']['last_trade_price'] < plan['stop']
    if first_word == 'buy' and (broken or not (data['state'] == 'bounce_setup' and plan['meets_minimum'])):
        raise ValueError(f'{name} verdict cannot start with Buy: the snapshot shows no confirmed bounce setup with enough reward for the risk, or the live price is already below the stop')
    warning = (f'<p class="warn">Live price {money(product["ticker"]["last_trade_price"])} is already below the stop. These levels are void until a new daily candle completes; run the report again after 00:00 UTC.</p>' if broken else '')
    chips = lambda items, source: ''.join(f'<span class="chip {"on" if source[key] else "off"}">{label}</span>' for key, label in items)
    stats = ''.join(f'<div><dt>{label}</dt><dd><b>{value}</b></dd></div>' for label, value in (
        ('RSI (14)', f'{data["rsi_14"]:.0f}'),
        ('vs 20-day avg', f'{data["zscore_20"]:+.1f}σ'),
        ('From 30-day high', f'{data["drop_from_30d_high_pct"]:+.1f}%'),
        ('Down days', str(data['consecutive_down_days'])),
        ('Volume', f'{data["volume_ratio_3d_max"]:.1f}×')))
    if plan['reward_to_risk'] is None:
        ratio = 'none: price is already at or above the 20-day average, or below the stop'
    elif plan['meets_minimum']:
        ratio = f'{plan["reward_to_risk"]:.1f} to 1'
    else:
        ratio = f'{plan["reward_to_risk"]:.1f} to 1, below the {plan["minimum_reward_to_risk"]:g} minimum: skip'
    if history['setups']:
        past = (f'{history["setups"]} earlier setup{"s" if history["setups"] != 1 else ""} in this window, {history["higher_after_5d"]} higher after 5 days '
                f'(average {history["average_5d_return_pct"]:+.1f}%, worst {history["worst_5d_return_pct"]:+.1f}%). Small sample, not a probability.')
    else:
        past = 'No earlier setups in this window.'
    return f'''<article class="card">
<header><h2>{escape(name.split('-')[0])}</h2><span class="price">{money(product['ticker']['last_trade_price'])}</span><span class="tag {'wait' if first_word == 'watch' else TONES.get(first_word, 'neutral')}">{inline(fields['Verdict'])}</span></header>
<p class="why">{inline(fields['Why'])}</p>
{chart(product, plan['entry'], plan['stop'], plan['target'], days=90)}
<div class="legend"><span><i class="key target"></i>Target</span><span><i class="key entry"></i>Entry trigger</span><span><i class="key exit"></i>Stop</span></div>
<p class="signal"><b>Signal</b> {STATES[data['state']]} · oversold {data['oversold']['peak_score_3d']} of 4 · reversal {data['reversal']['count']} of 3</p>
<div class="chips">{chips(OVERSOLD_CHECKS, data['oversold'])}{chips(REVERSAL_SIGNALS, data['reversal'])}</div>
<dl class="stats">{stats}</dl>
{news_line(fields['News'])}
{warning}
<ul class="actions">
<li><b>Entry</b> a daily close above {money(plan['entry'])} (latest day's high)</li>
<li><b>Stop</b> {money(plan['stop'])} (5-day low), {abs(plan['risk_pct']):.1f}% below entry</li>
<li><b>Target</b> {money(plan['target'])} (20-day average), {plan['reward_pct']:+.1f}% from entry</li>
<li><b>Reward to risk</b> {ratio}</li>
<li><b>History</b> {past}</li>
</ul>
{f'<div class="extra">{markdown(extra)}</div>' if extra else ''}
</article>'''


CSS = '''
:root{--bg:#f6f7f9;--card:#fff;--ink:#14181f;--muted:#667085;--line:#e4e7ec;--price:#2456d6;--up:#16794c;--down:#c0362c;--amber:#a15c00;--soft:#f0f2f5}
@media (prefers-color-scheme:dark){:root{--bg:#0f1216;--card:#181c22;--ink:#eceff3;--muted:#98a2b3;--line:#2a303a;--price:#7da2ff;--up:#4cc38a;--down:#f0766c;--amber:#e0a43c;--soft:#20252d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}
main{max-width:1080px;margin:0 auto;padding:32px 16px 48px}
h1{font-size:28px;margin:0 0 4px;letter-spacing:-.02em}.sub{color:var(--muted);margin:0 0 20px;font-size:14px}.sub p{margin:0}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin-bottom:20px}
.panel h2{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:0 0 8px}
.panel ol,.panel ul{margin:0;padding-left:20px}.panel li{margin:4px 0}.panel p{margin:6px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,440px),1fr));gap:20px;margin-bottom:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;min-width:0}
.card header{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap}.card h2{margin:0;font-size:22px}
.price{font-size:18px;color:var(--muted);font-variant-numeric:tabular-nums}
.tag{margin-left:auto;font-size:13px;font-weight:600;padding:3px 10px;border-radius:999px;background:var(--soft)}
.tag.good{color:var(--up)}.tag.wait{color:var(--amber)}.tag.avoid{color:var(--down)}
.why{margin:6px 0 10px;color:var(--muted);font-size:15px}
svg{width:100%;height:auto;display:block}.price-line{fill:none;stroke:var(--price);stroke-width:1.8;stroke-linejoin:round}.price-dot{fill:var(--price)}
line.entry{stroke:var(--up);stroke-dasharray:5 4}line.exit{stroke:var(--down);stroke-dasharray:5 4}
svg text{font-size:11px;fill:var(--muted)}svg text.entry-label{fill:var(--up);font-weight:600}svg text.exit-label{fill:var(--down);font-weight:600}
.legend{display:flex;gap:16px;font-size:12px;color:var(--muted);margin:4px 0 12px}
.key{display:inline-block;width:16px;border-top:2px dashed;margin-right:6px;vertical-align:middle}.key.entry{color:var(--up)}.key.exit{color:var(--down)}
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin:0 0 12px;padding:10px 0;border-block:1px solid var(--line)}
.stats div{min-width:0}dt{font-size:11px;color:var(--muted)}dd{margin:0;font-variant-numeric:tabular-nums}
.up{color:var(--up)}.down{color:var(--down)}
line.target{stroke:var(--amber);stroke-dasharray:5 4}svg text.target-label{fill:var(--amber);font-weight:600}.key.target{color:var(--amber)}
.signal{margin:0 0 8px;font-size:14px}.signal b{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-right:6px}
.warn{margin:0 0 10px;padding:8px 12px;border-radius:8px;background:var(--soft);color:var(--down);font-size:14px;font-weight:600}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}.chip{font-size:12px;padding:2px 9px;border-radius:999px;border:1px solid var(--line)}
.chip.on{background:var(--soft);color:var(--ink);font-weight:600}.chip.on::before{content:"✓ "}.chip.off{color:var(--muted);text-decoration:line-through}
.news{margin:0 0 10px;font-size:14px}.news b{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-right:6px}
.actions{margin:0;padding-left:18px;font-size:15px}.actions li{margin:3px 0}
.extra{font-size:14px;color:var(--muted);margin-top:8px}.extra ul,.extra ol{padding-left:18px;margin:4px 0}
a{color:var(--price);overflow-wrap:anywhere}code,pre{font:13px/1.5 ui-monospace,monospace}pre{overflow:auto;background:var(--soft);padding:12px;border-radius:8px}
.table-wrap{overflow:auto;max-width:100%}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line)}
footer{color:var(--muted);font-size:12px}
@media (max-width:480px){.stats{grid-template-columns:repeat(3,1fr)}.tag{margin-left:0}}
@media print{body{background:#fff}.card,.panel{break-inside:avoid}}
'''


def render(report, snapshot, mode='trend'):
    if snapshot['snapshot_id'] not in report:
        raise ValueError('Report must cite the matching snapshot ID')
    if not snapshot.get('products'):
        raise ValueError('Snapshot contains no products')
    title, preamble, sections = split_sections(report)
    by_heading = {heading: body for heading, body in sections}
    cards = []
    for product in snapshot['products']:
        if len(product['candles']) != 250:
            raise ValueError(f'{product["product"]} has an incomplete candle count')
        if product['product'] not in by_heading:
            raise ValueError(f'Report needs a "## {product["product"]}" section')
        cards.append((bounce_card if mode == 'bounce' else card)(product, by_heading[product['product']]))
    product_ids = {p['product'] for p in snapshot['products']}
    panels = {'top': [], 'bottom': []}
    for heading, body in sections:
        if heading in product_ids or heading.lower() in OMITTED_SECTIONS:
            continue
        place = 'top' if heading.lower() == 'bottom line' else 'bottom'
        panels[place].append(f'<section class="panel"><h2>{inline(heading)}</h2>{markdown(body)}</section>')
    captured = snapshot['generated_utc'][:16].replace('T', ' ')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'"><title>{escape(title)}</title><style>{CSS}</style></head><body><main>
<h1>{inline(title)}</h1>
<div class="sub">{markdown(preamble)}</div>
{''.join(panels['top'])}
<div class="grid">{''.join(cards)}</div>
{''.join(panels['bottom'])}
<footer>Coinbase Exchange snapshot captured {escape(captured)} UTC, not a live feed; check a current quote before acting. Charts and metrics use completed daily closes. Research only, not a prediction or an order.</footer>
</main></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--mode', choices=('trend', 'bounce'), default='trend', help='trend: entry and exit levels from the Markdown; bounce: oversold plan from the snapshot')
    args = parser.parse_args()
    if args.out.resolve() in (args.report.resolve(), args.snapshot.resolve()):
        parser.error('Output must not overwrite an input')
    html = render(args.report.read_text(encoding='utf-8'), json.loads(args.snapshot.read_text(encoding='utf-8')), args.mode)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as stream:
        stream.write(html)
    print(args.out.resolve())


if __name__ == '__main__':
    main()
