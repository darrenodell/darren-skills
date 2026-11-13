# Options pin zone 1.0.0

Finds the max pain strike and the likely pin or magnet zone for one ticker and one option expiration, using open interest from the full chain. Research only. It never places trades.

## What you give it

- Ticker
- Expiration date
- Current stock price (the chain page does not show one)

Example: `SOFI, Nov 13, price 16.18, pin zone`

## What you get

- Max pain strike with the payout table
- Open interest map: top strikes, call walls, put walls
- Put/call open interest ratio
- Likely pin, the zone around it, and the alternate magnet
- Data quality notes and what to recheck

## Install

**Claude Code**

```
/plugin marketplace add darrenodell/darren-skills
/plugin install options-pin-zone@darren-skills
```

Run it with `/options-pin-zone:max-pain-pin-zone SOFI 2026-11-13 price 16.18`, or just ask for a max pain or pin zone read.

**Claude desktop app and claude.ai**

Open the plugin settings, add a marketplace from GitHub with `darrenodell/darren-skills`, then install `options-pin-zone`. Start a new chat afterwards so it picks up the skill.

**Codex**

```sh
codex plugin marketplace add darrenodell/darren-skills
codex plugin add options-pin-zone@darren-skills
```

## Use it with ChatGPT, Grok or another chatbot

The skill is plain-text instructions, so any capable chatbot can follow it.

1. Open the [raw SKILL.md](https://raw.githubusercontent.com/darrenodell/darren-skills/main/plugins/options-pin-zone/skills/max-pain-pin-zone/SKILL.md) and copy all of it.
2. Paste it at the start of a chat, or save it in the bot's custom instructions or project instructions so it persists.
3. Ask: `SOFI, Nov 13, price 16.18, pin zone`.
4. If the bot can run Python, also upload [max_pain.py](skills/max-pain-pin-zone/scripts/max_pain.py) so the math is computed, not estimated.

If the bot cannot open the chain page, send it a screenshot of the option chain instead. The instructions cover that fallback.

## The helper script

Python 3.10+ standard library. No keys and no network access.

```sh
python3 plugins/options-pin-zone/skills/max-pain-pin-zone/scripts/max_pain.py --input chain.json --price 16.18
```

Input is JSON or CSV with `strike`, `call_oi` and `put_oi` on each row. Bid, ask and volume columns are optional. It prints JSON with max pain, the lowest payouts, the open interest map and, when quotes are present, the chain-implied spot, the nearest straddle and a low time value warning.

## Limits

- Chain data comes from optioncharts.io and is end of day. Open interest is as of the prior close and changes with each session's volume. The site's own terms apply to its data.
- Some free chain views strip time value from quotes. The skill then ignores bid, ask, IV and delta and relies on open interest.
- Max pain and pinning are heuristics, not forecasts. Pinning is strongest late on expiration day, and news can override it.
- Whether a given chatbot can fetch the chain page or run code depends on that host. The URL suffix for monthly expirations is not yet confirmed.

License: MIT for this plugin's original code and instructions.
