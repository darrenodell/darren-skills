# darren-skills

Personal skills packaged as a Claude plugin marketplace for Claude Code and the Claude desktop app's Cowork mode. Every plugin also has a Codex marketplace catalog entry and a portable plugin manifest. Skills with scripts need a runtime that can execute those scripts.

## Skills

| Plugin | Skill | What it does |
|---|---|---|
| `bible-study` | `morning-bible-study` | Writes a short daily Bible study (passage, reflection, two questions, prayer) with a BibleGateway link. A bundled script checks every candidate passage against a log so nothing repeats, including single verses from passages already used. |
| `crypto-research` | `coinbase-research` | Fetches public Coinbase USD-pair data, validates daily candles, calculates indicators, and prepares buying research reports, standalone HTML companions, or ChatGPT upload packets. Python 3.10+; no API keys or order tools. |
| `crypto-research` | `html-research-report` | Formats completed research into an offline HTML report, then requests inspection by `report-reviewer`. |
| `stock-research` | `alpaca-stock-research` | Uses Alpaca for validated stock/ETF snapshots, buying research, and an HTML/review handoff. Uses your own environment credentials. |
| `stock-research` | `html-stock-report` | Formats completed stock research into standalone HTML and requests `stock-report-reviewer` inspection. |
| `market-release-watch` | `market-release-watch` | Verifies U.S. economic releases, retries missing reports every three minutes, and uses a dedicated analyst to produce a 1–5 BUY/SELL/WAIT signal in a standalone HTML report. |
| `market-conditions` | `market-conditions`, `market-context-integration`, `html-market-report` | Historical SIP/IEX benchmarks, primary macro evidence, a transparent market-backdrop rubric, optional attributed equity-research handoffs, standalone HTML and reviewer inspection. |

See [market-conditions setup and source limits](plugins/market-conditions/README.md).

## Download the crypto starter

[Download crypto-research-starter.zip (v1.1.0)](https://github.com/darrenodell/darren-skills/releases/download/v1.1.0/crypto-research-starter.zip)

The starter includes the crypto plugin, MacBook and Windows setup instructions, collector, HTML renderer, reviewer agent, and tests. It retains the `crypto-lab` marketplace name used by the included installation guides. Installing from this repository instead uses `darren-skills` as shown below.

## Install

**Claude Code**

```
/plugin marketplace add darrenodell/darren-skills
/plugin install bible-study@darren-skills
/plugin install crypto-research@darren-skills
/plugin install stock-research@darren-skills
/plugin install market-release-watch@darren-skills
/plugin install market-conditions@darren-skills
```

The skill triggers on its own when you ask for a Bible study, or run it directly with `/bible-study:morning-bible-study`.

**Claude desktop app (Cowork)**

Cowork does not see plugins installed through the Claude Code CLI; it uses the plugins on your claude.ai account. In the desktop app, open the plugin settings, add a marketplace from GitHub with `darrenodell/darren-skills`, then install `bible-study` (and any other plugin you want). Start a new Cowork task afterwards so it picks up the skill.

**Codex (bible study)**

From a local clone of this repository:

```bash
codex plugin marketplace add .
codex plugin add bible-study@darren-skills
```

Without memory tools, the skill keeps its log in `bible-study-log.md` in the working folder, so run it from the same folder each day.

**Crypto research usage**

In Claude Code, run `/crypto-research:coinbase-research XRP-USD buying report`.
For a comparison, request `XRP-USD, BTC-USD, and ETH-USD buying reports and comparison`.
The collector supports up to 10 Coinbase USD pairs per run, with 250 complete daily candles required for each pair.
Reports and snapshots belong in your working folder, outside the installed plugin cache.

**Codex (crypto plugin)**

From a local clone of this repository:

```bash
codex plugin marketplace add .
codex plugin add crypto-research@darren-skills
```

Start a fresh Codex session, select your preferred available reasoning model and High effort, and ask:

```text
$crypto-research:coinbase-research XRP-USD buying report
```

Python 3.10 or newer is required. The helper uses the Python standard library and public Coinbase Exchange endpoints; it does not need a Coinbase account or keys. Research includes timestamp validation, trend, volatility, scenarios, reasons to wait, and current primary-source news where browsing is available. It never places trades.

**claude.ai**

Download `morning-bible-study.skill` from the latest release and add it to your skills, or zip the folder `plugins/bible-study/skills/morning-bible-study/` and upload that.

## Download the stock starter

[Download stock-research-starter.zip (v1.0.0)](https://github.com/darrenodell/darren-skills/releases/download/stock-research-v1.0.0/stock-research-starter.zip)

The starter includes installation instructions for Mac/Windows, the stock plugin, HTML renderer, reviewer agent and 11 stock tests. Bring your own Alpaca keys. The standalone ZIP uses `stock-lab`; installation from this collection uses `darren-skills`.

## Alpaca stock research

[Stock plugin setup and usage](plugins/stock-research/README.md). From a local clone:

```sh
codex plugin marketplace add .
codex plugin add stock-research@darren-skills
```

Use your own `ALPACA_KEY` and `ALPACA_SECRET` in the inherited environment, as Wheel does. Never paste or commit keys. The collector reads Alpaca daily bars, stock snapshots and US calendar; it does not access accounts, holdings or orders. The default is IEX; SIP requires suitable access. Python 3.10+; Windows may also need `python -m pip install tzdata`.

```text
$stock-research:alpaca-stock-research AAPL buying report
$stock-research:alpaca-stock-research Compare AAPL, MSFT and NVDA
```

The workflow is stock research → standalone HTML → stock-report-reviewer inspection. It uses 250 prior US trading sessions, adjusted daily bars and 252-day annualized volatility. The current New York day is always excluded, including after close. It labels IEX's single-exchange coverage and withholds current entry-price judgments for stale/closed-session observations. Company news, earnings, financials and valuation need current primary sources; missing work is explicitly labeled. This does not run Wheel or apply its candidate gates.

## Market release watch

From a local clone, install the plugin in Codex:

```sh
codex plugin marketplace add .
codex plugin add market-release-watch@darren-skills
```

Run a fresh status check:

```text
$market-release-watch:market-release-watch Check today's U.S. economic releases, including Michigan sentiment.
```

In Claude Code, use `/market-release-watch:market-release-watch`. You can also ask for a timed watch or automatic release alerts. Automatic alerts require a host with scheduling support and must be requested separately; installing or invoking the skill does not create a background task. For local scheduled checks, keep the app running and the computer awake. One-minute polling is best effort and does not guarantee immediate notification or a trading advantage.

The final output is a self-contained HTML report and matching JSON evidence snapshot, styled like the stock/crypto reports. A prominent signal leads the report: **1 STRONG SELL, 2 SELL, 3 WAIT, 4 BUY, 5 STRONG BUY**, followed by confidence, a simple action, reasons and the condition that changes the call. The default scope is SPY / broad U.S. equities over the next 30–120 minutes after a release, subject to the next major catalyst.

The bundled `market-release-analyst` agent evaluates source-backed actuals versus expectations, inflation/rate and growth implications, revisions, and fresh price confirmation when available. Hosts without delegation use the same rubric inline and disclose the fallback. Pending or unverifiable releases get WAIT. A report-only best guess can be provisional BUY/SELL with Low confidence; strong scores require primary verification and fresh market confirmation. This qualitative rubric has not been backtested and its score is not a win probability.

The collector verifies date, period and preliminary/final vintage, preserves pre-release forecasts, and tracks Michigan inflation expectations separately from sentiment. If a scheduled release is due but not verified, it retries that report every **three minutes** until verification or the watch deadline. A deterministic polling helper prevents one-minute heartbeat wakes from repeatedly fetching the missing report. Quotes and HTML generation never delay the first factual release alert.

Release checks use public sources; connected market data is optional and may require a subscription. The plugin can help users find and interpret new information quickly in a workflow similar to professional release monitoring, but public sources, polling and notifications may lag professional news/data feeds. It does not place trades. Runtime state, personal automation settings and generated reports stay outside the plugin.

The HTML renderer uses the Python standard library (Python 3.10+ recommended; install `tzdata` if the host lacks IANA timezones). It validates signal/evidence consistency and embeds its source snapshot without external assets. Run it on the skill-generated JSON:

```sh
python3 plugins/market-release-watch/skills/market-release-watch/scripts/render_report.py --input /path/to/market-release-report.json --out /path/to/market-release-report.html
```

## HTML reports and inspection

A normal buying-report request now runs `coinbase-research`, then the sibling `html-research-report` skill. It saves the original Markdown and a self-contained HTML companion with inline SVG price charts, source links, timestamps, and the full embedded snapshot. No remote fonts, assets, or JavaScript are required to read it. Source links require internet access.

The `report-reviewer` agent checks the source data, content preservation, offline resources, and desktop/phone rendering before delivery. Claude Code can discover its agent definition in `agents/`; other hosts may need explicit delegation or can perform the same checklist directly. A review must say when visual or independent checks could not be performed. This is an explicit skill handoff, not a global hook. Request “Markdown only” to skip it.

Both HTML generation and review can also be invoked for an existing completed report and its matching snapshot. The renderer uses only Python's standard library. Test artifacts and personal reports stay outside this repository.

## Repository layout

```
.claude-plugin/marketplace.json     the catalog Claude Code reads
plugins/
  bible-study/
    plugin.json                     portable Codex plugin manifest
    .claude-plugin/plugin.json      Claude plugin manifest
    skills/
      morning-bible-study/
        SKILL.md                    instructions Claude follows
        scripts/passage_tool.py     repeat checker and URL builder
  crypto-research/
    plugin.json                     portable Codex plugin manifest
    .claude-plugin/plugin.json      Claude plugin manifest
    agents/report-reviewer.md       inspection agent
    skills/coinbase-research/
      SKILL.md                      research workflow
      report-prompt.md              report requirements
      scripts/fetch_snapshot.py     public Coinbase data collector
    skills/html-research-report/
      SKILL.md                      HTML and review handoff
      scripts/render_report.py      standalone HTML renderer
  stock-research/
    plugin.json                     Codex manifest
    .claude-plugin/plugin.json      Claude manifest
    README.md                       setup and credentials guidance
    agents/stock-report-reviewer.md
    skills/alpaca-stock-research/
      SKILL.md
      report-prompt.md
      references.md
      scripts/fetch_snapshot.py
    skills/html-stock-report/
      SKILL.md
      scripts/render_report.py
  market-release-watch/
    plugin.json                     Codex manifest (v1.1.0)
    .claude-plugin/plugin.json      Claude manifest
    agents/market-release-analyst.md
    skills/market-release-watch/
      SKILL.md                      release verification, retries and report workflow
      agents/openai.yaml            skill display metadata
      references/sources.md         publisher and calendar entrypoints
      references/signal-rubric.md    signal and evidence contract
      scripts/poll_plan.py          three-minute retry gate
      scripts/render_report.py      standalone HTML renderer
.agents/plugins/marketplace.json   Codex catalog (all plugins)
tests/                              unit tests (kept out of the skill so it stays lean)
```

## Development

```bash
python -m unittest discover -s tests -v       # run tests
claude plugin validate .                      # check marketplace and plugin
```

To release a change, bump `version` in `plugin.json`. Installed copies stay on the old version until it changes.

To add a skill, create `plugins/<plugin>/skills/<skill-name>/SKILL.md`. To add a plugin, create its folder under `plugins/` and add an entry to `marketplace.json`.

## License

MIT
