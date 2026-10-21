# Alpaca stock research

Research 1–10 US stocks or ETFs using Alpaca market data, then produce Markdown, a standalone HTML report, and inspection. No account, holdings, options, or order access. Python 3.10+; on machines without timezone data, install `tzdata` with `python -m pip install tzdata`.

## Install from darren-skills

From the repository root:

```sh
codex plugin marketplace add .
codex plugin add stock-research@darren-skills
```

Or in Claude Code:

```text
/plugin marketplace add darrenodell/darren-skills
/plugin install stock-research@darren-skills
```

Start a fresh session. Your own Alpaca credentials must be in its inherited environment: `ALPACA_KEY` and `ALPACA_SECRET`. Wheel already uses these names on Darren's Mac. Do not paste keys in chat or save them inside this repository. The plugin does not need Wheel installed. SDK-style aliases `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` are also supported. For calendar requests, `ALPACA_BASE_URL` defaults to the paper host; use the official live host only if your credentials require it. The key must match that host. This setting never enables trading.

If needed, enter values locally in a Mac Terminal, then launch Codex from that same terminal:

```sh
read -r -s 'ALPACA_KEY?Alpaca key: '; export ALPACA_KEY
read -r -s 'ALPACA_SECRET?Alpaca secret: '; export ALPACA_SECRET
codex
```

On Windows PowerShell, use hidden local prompts:

```powershell
$env:ALPACA_KEY = [System.Net.NetworkCredential]::new('', (Read-Host 'Alpaca key' -AsSecureString)).Password
$env:ALPACA_SECRET = [System.Net.NetworkCredential]::new('', (Read-Host 'Alpaca secret' -AsSecureString)).Password
codex
```

These are process environment variables, not permanent setup. Close the session when finished. Other people must use their own keys and verify their data entitlement.

## Use

Select your available reasoning model and desired higher effort in the client. Then ask:

```text
$stock-research:alpaca-stock-research AAPL buying report
```

```text
$stock-research:alpaca-stock-research Compare AAPL, MSFT and NVDA buying reports
```

Claude Code uses `/stock-research:alpaca-stock-research` instead. The stock skill calls `html-stock-report`, then requests `stock-report-reviewer` inspection. This is an explicit handoff, not an event hook. Named-agent and browser support vary by host; unavailable independent/visual checks must be disclosed.

The normal default is general research. Supply horizon, budget, holdings and risk limits only when you want conclusions tailored to those inputs. Prices alone do not provide fundamentals or guarantee an investment outcome. News, earnings, company financials and valuation require current primary-source research; missing work is labeled incomplete. No Wheel scanning thresholds, options, leverage or orders are implied.

## Collector and output

From a permanent research workspace outside the installed cache:

```sh
python3 <plugin>/skills/alpaca-stock-research/scripts/fetch_snapshot.py --symbols AAPL MSFT --feed iex --out data
```

Each successful run writes `data/<snapshot-id>/snapshot.json` and `chatgpt-packet.md`. Research output belongs in `reports/`; review output in `review/`. Generated data, reports, credentials and caches are excluded from the distributable plugin.

The default IEX feed follows Wheel's implementation and covers one exchange. An explicit `--feed sip` requires suitable Alpaca access; failure never changes the feed silently. Quotes can be stale/missing or outside regular hours. Such a packet can support dated research but not current entry-price judgment. The helper always uses the 250 calendar-verified sessions before the current New York date, even after market close. It excludes the current NY day; return windows are trading sessions and volatility uses 252 trading days per year. Historical bars use `adjustment=all`; raw snapshots and adjusted prices are different series. IEX volume is not whole-market volume.

The standalone HTML embeds CSS, SVG charts, text and snapshot. Only navigation to source links needs internet. The inspection checks arithmetic, provenance, freshness, content preservation, offline resources, and desktop/phone layout when browser tools exist. It is not investment approval.
