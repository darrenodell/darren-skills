# Bounce finder brief prompt

Use the attached Coinbase data packet to write a short, actionable brief on which coins are oversold and which, if any, show a bounce setup.

My maximum position size and maximum loss per trade: [fill in, or leave blank for a general brief]. This is an unleveraged spot-research request; I make the trading decisions.

First verify the snapshot capture time, last trade time, candle coverage, and all quality flags. If the snapshot is stale (more than five minutes old), has gaps, or contains errors, stop and ask for a refreshed packet. Do not describe the snapshot as a live feed.

Be brief. The HTML report adds the chart, the oversold checks, the reversal signals, the entry, stop, target, reward-to-risk and history to each card from the snapshot, so do not repeat any of those numbers in the Markdown except where one is the deciding fact in a "Why" sentence.

Use exactly this Markdown structure, with one section per product, headed by its product ID:

```markdown
# Crypto Bounce Finder

Bounce horizon: days · snapshot `<snapshot-id>` captured <UTC time>

## Bottom line

1. **<How many bounce setups there are, and which.>** <One supporting sentence.>
2. <Which coins are oversold but still falling, and what would confirm them.>
3. <Up to three more actions or dated events inside the next few days.>

## BTC-USD

- **Verdict:** <Buy setup, Skip, Watch, Wait or Avoid, plus a few words>
- **Why:** <One sentence with the deciding fact.>
- **News:** <Date and the single most material headline for this product, or "No dated news found in the last 7 days.">

## What is unverified

- <Each news or event check that could not be confirmed, one line each. Omit the section if there is none.>

## Sources

- <Snapshot ID, capture time and endpoint URLs; dated links for any news used.>
```

Rules for the content:

- Start each verdict with one of the five words, chosen from the product's `state` and plan in the packet:
  - Buy setup: `bounce_setup` and `meets_minimum` is true.
  - Skip: `bounce_setup` but reward-to-risk is below the minimum or absent, or `ticker_below_stop` is true (the live price has already broken the setup; say to rerun after the next daily close).
  - Watch: `oversold_falling`. Name the reversal signal that would change it.
  - Wait: `not_oversold`.
  - Avoid: news gives a reason for the fall, whatever the state.
- The verdict may be more cautious than the signal and never more bullish.
- Order the bottom line by quality of setup: confirmed setups with the best reward-to-risk first.
- Run at least one news search for each product by name, covering the seven days before the snapshot. Look first for a reason the coin deserves to be down (hack, protocol bug, delisting, enforcement, large unlock). Put the single most material item on the News line as a date and one plain sentence with no link, and the dated link under Sources. If nothing dated turns up, write "No dated news found in the last 7 days." If browsing is unavailable, write "News not checked." and say so under "What is unverified".
- Do not change, re-derive or add to the computed levels. Do not invent probabilities, price targets, expected returns, or a personal allocation. The history counts are a small sample; refer to them as counts only.
- If I gave a maximum loss, add one extra bullet per Buy setup with the position size that loses that amount at the stop, calculated with a calculation tool from the packet's entry and stop.
- The Sources section stays in the Markdown and is left out of the HTML.

Before sending this prompt, select an available reasoning model and High or Extra High effort in ChatGPT Work/Codex, or the strongest relevant Thinking setting available in your ChatGPT client. This instruction does not itself change the selected model or effort.
