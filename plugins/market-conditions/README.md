# Market conditions 1.0.0
Historical US equity-market and technology-sector context using six ETF benchmarks, primary macro series, a transparent heuristic, optional research handoffs, offline HTML and review. No trades or live entry prices.

## Run
Python3.10+ standard library; runtime Alpaca credentials configured securely outside this repository. No FRED key or premium consensus subscription required.
```sh
python3 plugins/market-conditions/scripts/market.py run --workspace /absolute/research-workspace --feed sip --allow-iex-fallback --context /absolute/context.json
```
The workspace must be outside the plugin repository. The run writes data/<id>/snapshot.json, sources/<id>/ raw macro CSVs/source-index.json, reports/<id>/ research.md/report.html/analysis.json/handoff.json/manifest.json. Review is PENDING until actually inspected. A PARTIAL run is preserved with its errors; exit2 means missing required coverage, exit1 a collection/input error.

Use the three bundled skills for research, optional context integration and HTML/review. Delegate the reviewer with matching artifacts. Without independent review label self-review honestly. See [methodology](references/methodology.md) and [handoff contracts](references/handoff.md).

## Install
Add darrenodell/darren-skills to the host marketplace and install market-conditions. In Claude Code use /plugin marketplace add darrenodell/darren-skills then /plugin install market-conditions@darren-skills; invoke /market-conditions:market-conditions. Codex: codex plugin marketplace add darrenodell/darren-skills then codex plugin add market-conditions@darren-skills. Restart/start a fresh session if required by the host. Publication, installation, loading, runtime keys/network, and availability in another host are separate checks.

## Public Equity Investing
Optional separately produced event/catalyst/scenario/thesis/earnings/valuation reports can be accepted with attribution. No proprietary skills, templates, scripts or private assets are included, no dependency is auto-installed, and no cross-host availability is promised. Core reporting works without it. Missing paid consensus/transcripts/OPRA do not become fabricated data. Host-specific coordination must be tested; portable report-envelope handoff works independently of upstream installation.

SIP historical access does not imply latest SIP snapshots. IEX fallback is explicit whole-set and retains failed attempts. ETF ratios are proxies, not actual breadth or flows. Macro observations have separate period/freshness/vintage labels. Heuristic is unvalidated and distinct from individual-stock conclusions. No schedule/hooks installed.

License: MIT for this plugin's original code; source data and third-party reports retain their own terms.
