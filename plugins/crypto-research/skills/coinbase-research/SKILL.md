---
name: coinbase-research
description: Fetch Coinbase Exchange spot data, validate a timestamped snapshot, and prepare a crypto buying research report or a ChatGPT upload packet. Use for Coinbase crypto research; never execute trades.
---

# Coinbase crypto buying research

Use the bundled Python helper for data retrieval and calculations. Use judgment for the report. This package uses public Exchange market-data endpoints; it does not access accounts or place orders.

1. Confirm requested Coinbase USD product IDs, such as BTC-USD and ETH-USD. For buying research, obtain the user's horizon, budget or risk limits, and relevant constraints before tailoring a conclusion. Missing context can instead produce an explicitly general comparison.
2. Choose a permanent workspace outside the installed plugin/cache directory. Run the following from that workspace, resolving the helper relative to this SKILL.md:
   `python3 <skill-directory>/scripts/fetch_snapshot.py --products BTC-USD ETH-USD --out data`
3. Read the saved `snapshot.json` and `chatgpt-packet.md`. Report validation errors instead of making a recommendation from incomplete data. A ticker older than five minutes is marked stale. For a buying report, refresh if stale or if analysis begins more than five minutes after retrieval. Daily candles must cover the prior 250 complete UTC days without gaps. Today's unfinished candle is excluded.
4. Distinguish retrieval time, last-trade time, and last completed candle. The ticker is a Coinbase venue snapshot, not a guaranteed executable price. The moving averages and other metrics use daily closes, not the live ticker. Explain that distinction when comparing them.
5. If reporting here, ask the user to select High or Extra High reasoning in the client if they want deeper analysis. Instructions cannot change the user's model or reasoning setting. If using ordinary ChatGPT web, provide the packet for upload there; do not claim that a local plugin grants the web chat access to local Python or files.
6. Follow `report-prompt.md`. Cite the captured API URLs and capture time. Use only supported facts. For news, regulatory developments, or upcoming events, browse current primary sources and link them; otherwise mark that context unverified. State that judgment uses a snapshot, not a live market feed.
7. Save the report under the permanent workspace's `reports/` directory with a timestamp and the snapshot ID. Never overwrite earlier runs or read credentials. For account-specific features added later, use separate read-only credentials outside the package; this version needs none.

The moving averages describe trend; they are not a profitable trading strategy by themselves. Give bullish, base, and bearish scenarios, conditions that would invalidate the thesis, and reasons to wait. Never invent forecast probabilities, returns, prices, or missing personal context. No order submission is part of this workflow.
