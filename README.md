# darren-skills

Personal skills for Claude, packaged as a Claude Code plugin marketplace. The crypto plugin also includes a Codex marketplace catalog and portable plugin manifest. Skills with scripts need a runtime that can execute those scripts.

## Skills

| Plugin | Skill | What it does |
|---|---|---|
| `bible-study` | `morning-bible-study` | Writes a short daily Bible study (passage, reflection, two questions, prayer) with a BibleGateway link. A bundled script checks every candidate passage against a log so nothing repeats, including single verses from passages already used. |
| `crypto-research` | `coinbase-research` | Fetches public Coinbase USD-pair data, validates daily candles, calculates indicators, and prepares buying research reports or ChatGPT upload packets. Python 3.10+; no API keys or order tools. |

## Install

**Claude Code**

```
/plugin marketplace add darrenodell/darren-skills
/plugin install bible-study@darren-skills
/plugin install crypto-research@darren-skills
```

The skill triggers on its own when you ask for a Bible study, or run it directly with `/bible-study:morning-bible-study`.

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

## Repository layout

```
.claude-plugin/marketplace.json     the catalog Claude Code reads
plugins/
  bible-study/
    .claude-plugin/plugin.json      plugin name, version, author
    skills/
      morning-bible-study/
        SKILL.md                    instructions Claude follows
        scripts/passage_tool.py     repeat checker and URL builder
  crypto-research/
    plugin.json                     portable Codex plugin manifest
    .claude-plugin/plugin.json      Claude plugin manifest
    skills/coinbase-research/
      SKILL.md                      research workflow
      report-prompt.md              report requirements
      scripts/fetch_snapshot.py     public Coinbase data collector
.agents/plugins/marketplace.json   Codex catalog (crypto plugin)
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
