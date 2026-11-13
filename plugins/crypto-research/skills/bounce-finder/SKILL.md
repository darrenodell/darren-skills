---
name: bounce-finder
description: Find deeply oversold Coinbase crypto that may be setting up for a short-term bounce. Scores how oversold each coin is, checks for reversal signals, and gives an entry trigger, stop, target and reward-to-risk on a concise card per coin. Use when the user asks for a bottom finder, oversold coins, a dip to buy, capitulation, a likely bounce, or a mean-reversion entry; never execute trades.
---

# Coinbase bounce finder

This is a counter-trend companion to `coinbase-research`. That skill waits for price to recover above an average; this one looks for coins that have fallen too far, too fast, and waits for evidence that selling is exhausted. It uses public market data only, with no account access and no orders.

The collector computes every number. Do not recalculate, adjust, or round the levels differently, and do not add indicators of your own.

1. Confirm the Coinbase USD product IDs, such as BTC-USD and ETH-USD. The horizon is days, not weeks. Ask for a budget or maximum loss only if the user wants sizing; otherwise produce a general brief.
2. Choose a permanent workspace outside the installed plugin/cache directory and fetch a new snapshot from it, resolving the collector relative to this SKILL.md:
   `python3 <skill-directory>/../coinbase-research/scripts/fetch_snapshot.py --products BTC-USD ETH-USD --out data`
   Report validation errors instead of writing a brief from incomplete data. Refresh if a ticker is stale or if analysis starts more than five minutes after retrieval.
3. Read the "Oversold and reversal metrics" block for each product in the saved `chatgpt-packet.md`. The same data is under `bounce` in `snapshot.json`. Each product has a `state`:
   - `bounce_setup`: oversold on at least one of the last three days and at least one reversal signal.
   - `oversold_falling`: oversold with no reversal signal yet.
   - `not_oversold`: no setup.
4. Run at least one news search for every product by name, covering the seven days before the snapshot; send the searches together. Look first for a reason the coin deserves to be down: a hack or exploit, a protocol bug, a delisting, enforcement action, or a large unlock. A reason like that overrides a bounce signal, because oversold on bad news often stays oversold.
5. Write the brief by following `report-prompt.md` exactly, and save it under the workspace's `reports/` directory with a timestamp, the snapshot ID and `bounce` in the name. Never overwrite earlier runs.
6. Read and follow the sibling skill at `../html-research-report/SKILL.md`, adding `--mode bounce` to the renderer command. Then run the `report-reviewer` inspection it describes and return both report links and the review result. When the user asks for a quick result, deliver the HTML first and say that review has not run.

Rules for the verdict:

- **Buy setup** only when the state is `bounce_setup` and the plan's `meets_minimum` is true. The renderer rejects it otherwise.
- **Skip** when the state is `bounce_setup` but reward-to-risk is below the minimum or there is none, or when the plan's `ticker_below_stop` is true. The levels come from completed daily candles, so a live price under the stop means today's selling has already broken the setup; say to rerun after the next daily close at 00:00 UTC.
- **Watch** when the state is `oversold_falling`; the action is to wait for a reversal signal, not to buy.
- **Wait** when the state is `not_oversold`.
- **Avoid** when news gives a reason for the fall, whatever the state.
- The verdict may be more cautious than the signal and never more bullish.

A bounce setup is a condition, not a prediction. The history line counts how earlier setups in the same 250 days resolved; it is a handful of cases, so never turn it into a probability or an expected return. Say plainly that buying into a falling market can lose the whole stop distance quickly, that the stop is a daily level which price can gap through, and that the entry needs a daily close above the trigger, not an intraday touch. Never invent price targets, probabilities, or a personal allocation.
