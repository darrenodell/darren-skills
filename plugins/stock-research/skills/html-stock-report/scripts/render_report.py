#!/usr/bin/env python3
"""Render Alpaca stock Markdown research and matching JSON as standalone HTML. Stdlib only."""
import argparse
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


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
            table = ['<div class="table-wrap" role="region" aria-label="Research metrics table" tabindex="0"><table><thead><tr>']
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


def chart(product):
    bars = product['bars']; values = [b['close'] for b in bars]
    low, high = min(values), max(values)
    pad = (high-low)*.09 or high*.05
    low -= pad; high += pad
    def x(i): return 72 + i/(len(values)-1)*800
    def y(value): return 260 - (value-low)/(high-low)*215
    points = ' '.join(f'{x(i):.2f},{y(v):.2f}' for i,v in enumerate(values))
    title = escape(product['symbol']) + ' • 250 prior trading-session adjusted closes'
    grid = ''.join(f'<line x1="72" x2="872" y1="{y(low+(high-low)*i/4):.2f}" y2="{y(low+(high-low)*i/4):.2f}" stroke="#dbe4ef"/><text x="60" y="{y(low+(high-low)*i/4)+4:.2f}" text-anchor="end">${low+(high-low)*i/4:,.0f}</text>' for i in range(5))
    return f'''<figure><figcaption>{title}</figcaption><div class="chart-scroll" role="region" aria-label="Scrollable daily close chart" tabindex="0"><svg viewBox="0 0 920 310" role="img" aria-label="{title}. Prices in US dollars. Full values in embedded snapshot."><rect width="920" height="310" fill="#f5f8fc"/>{grid}<polyline points="{points}" fill="none" stroke="#3156b8" stroke-width="3"/><text x="72" y="291">{escape(bars[0]['session_date'])}</text><text x="872" y="291" text-anchor="end">{escape(bars[-1]['session_date'])}</text></svg></div><p class="caption">On narrow screens, scroll the chart horizontally. Alpaca adjusted daily close • USD • current New York day excluded. Spacing is by trading session. This chart shows history, not a forecast.</p></figure>'''


CSS = '''
:root{color-scheme:light;--ink:#172b4d;--blue:#3156b8;--muted:#526782;--line:#dbe4ef}*{box-sizing:border-box}body{margin:0;background:#eaf0f7;color:var(--ink);font:17px/1.65 "Avenir Next","Segoe UI",sans-serif}header{background:#172b4d;color:white;padding:55px max(24px,calc((100vw - 1100px)/2)) 42px}header p{color:#cddbf2;margin:12px 0}h1{font:600 clamp(36px,5vw,62px)/1.12 Georgia,serif;margin:14px 0 20px;max-width:850px}.brand{font-size:16px;color:#a8c5ff}main{max-width:1150px;margin:auto;background:#fff;padding:42px 50px 65px}h2{font:600 29px/1.25 Georgia,serif;margin:46px 0 18px;padding-top:18px;border-top:2px solid var(--line)}h3{font-size:20px;margin:28px 0 12px}p,li{max-width:80ch}a{color:#2448a4;text-underline-offset:3px;overflow-wrap:anywhere}a:focus-visible,summary:focus-visible,.table-wrap:focus-visible{outline:3px solid #a45a00;outline-offset:4px}.summary{background:#edf3ff;border-left:5px solid var(--blue);padding:20px 25px;margin-bottom:32px}.summary p{margin:4px 0}.meta{font-size:14px;overflow-wrap:anywhere}.report-title{font-weight:650;font-size:22px}.table-wrap{overflow:auto;max-width:100%;margin:22px 0;border:1px solid var(--line)}table{border-collapse:collapse;width:100%;font-size:15px}th,td{text-align:left;padding:12px 16px;border-bottom:1px solid var(--line);vertical-align:top}th{background:#edf3ff;white-space:nowrap}thead{position:sticky;top:0}figure{margin:30px 0}figcaption{font-weight:650;margin-bottom:12px}.chart-scroll{overflow:auto;max-width:100%}.chart-scroll:focus-visible{outline:3px solid #a45a00;outline-offset:4px}svg{width:100%;min-width:920px;height:auto}svg text{font:13px "Segoe UI",sans-serif;fill:#526782}.caption{font-size:13px;color:var(--muted)}code,pre{font:13px/1.6 ui-monospace,monospace}pre{overflow:auto;background:#edf3ff;padding:20px}details{margin:30px 0;padding:16px;border:1px solid var(--line)}summary{cursor:pointer;font-weight:650}footer{color:var(--muted);font-size:13px;margin-top:45px;border-top:1px solid var(--line);padding-top:18px}li{margin:9px 0}@media(max-width:600px){body{font-size:16px}main{padding:25px 20px}header{padding:32px 22px}h2{font-size:26px}th,td{padding:10px;min-width:110px}.summary{padding:16px}}@media print{body{background:white;font-size:11pt}header{background:white;color:var(--ink);padding:0 0 20px}header p,.brand{color:var(--muted)}main{padding:0;max-width:none}h1{font-size:32pt}h2{break-after:avoid}figure,tr{break-inside:avoid}.table-wrap{overflow:visible}details{display:none}a{color:inherit}thead{position:static}}
'''


def render(report, snapshot):
    if snapshot['snapshot_id'] not in report:
        raise ValueError('Report must cite the matching snapshot ID')
    if not snapshot.get('stocks'):
        raise ValueError('Snapshot contains no stocks')
    for p in snapshot['stocks']:
        if p['symbol'] not in report or len(p['bars']) != 250:
            raise ValueError('Symbol missing in report or incomplete session count')
    title = next((line[2:] for line in report.splitlines() if line.startswith('# ')), 'Stock research report')
    products = ', '.join(p['symbol'] for p in snapshot['stocks'])
    captured = snapshot['generated_utc']
    match = re.search(r'^## Research judgment\s*\n+([^\n]+)', report, re.M)
    summary = inline(match[1]) if match else 'Research conclusions, conditional scenarios, and limitations are preserved below.'
    raw = escape(json.dumps(snapshot,indent=2,ensure_ascii=False))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'"><title>{escape(title)}</title><style>{CSS}</style></head><body><header><div class="brand">Darren’s research collection</div><h1>{escape(title)}</h1><p>{escape(products)} · Alpaca {escape(snapshot['feed'])} · Adjusted stock/ETF research</p><p class="meta">Snapshot captured {escape(captured)} · adjustment=all<br>Historical snapshot, not a live quote. IEX is one venue; SIP is consolidated. Refresh before a new buying decision.</p></header><main><aside class="summary"><p>{summary}</p></aside>{''.join(chart(p) for p in snapshot['stocks'])}<article>{markdown(report)}</article><details><summary>Inspect the complete source snapshot</summary><pre>{raw}</pre></details><footer>Self-contained report. Styling, charts, research text, and snapshot are embedded. Source links need an internet connection. Rendered {datetime.now(timezone.utc).isoformat()}.</footer></main></body></html>'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.resolve() in (args.report.resolve(),args.snapshot.resolve()):
        parser.error('Output must not overwrite an input')
    html=render(args.report.read_text(encoding='utf-8'),json.loads(args.snapshot.read_text(encoding='utf-8')))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as stream: stream.write(html)
    print(args.out.resolve())


if __name__=='__main__': main()
