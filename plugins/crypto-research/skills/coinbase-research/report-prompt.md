# Concise buying brief prompt

Use the attached Coinbase data packet to write a short, actionable crypto buying brief.

My investment horizon: [fill in]. My budget or maximum position size: [fill in]. My loss tolerance and other constraints: [fill in]. This is an unleveraged spot-research request; I make the trading decisions.

First verify the snapshot capture time, last trade time, candle coverage, and all quality flags. If the snapshot is stale (more than five minutes old for this buying review), has gaps, or contains errors, stop and ask for a refreshed packet. Do not describe the snapshot as a live feed.

Be brief. The reader wants what to do, at which price, and why, in that order. Write one sentence where one will do, and leave out methodology, restated metrics, and scenario essays. The HTML report adds the chart and the standard metrics to each product on its own, so do not repeat them in a table.

Use exactly this Markdown structure, with one section per product, headed by its product ID:

```markdown
# Crypto Buying Brief

Short-term (days to weeks) · small speculative allocation · snapshot `<snapshot-id>` captured <UTC time>

## Bottom line

1. **<The overall call in a few words.>** <One supporting sentence.>
2. <Order of preference across the products.>
3. <Up to three more actions or dated events inside the horizon.>

## BTC-USD

- **Verdict:** <Buy, Watch, Wait or Avoid, plus a few words>
- **Why:** <One sentence with the deciding fact.>
- **News:** <Date and the single most material headline for this product, or "No dated news found in the last 7 days.">
- **Buy only if:** a daily close is above $<level> (<what the level is>)
- **Exit if:** a daily close is below $<level> (<what the level is>)

## What is unverified

- <Each news or event check that could not be confirmed, one line each. Omit the section if there is none.>

## Sources

- <Snapshot ID, capture time and endpoint URLs; dated links for any news used.>
```

Rules for the content:

- Start each verdict with Buy, Watch, Wait or Avoid; the report colours the card from that word.
- Take every entry and exit level from the snapshot: a moving average, or a recent low or high computed from the candles with a calculation tool. Name the level in parentheses. Each "Buy only if" and "Exit if" line needs one dollar figure.
- The levels are conditions to watch, not forecasts. Do not invent probabilities, price targets, returns, or a personal allocation.
- Judge trend from completed daily closes, and say so if the live ticker has already crossed a level.
- Run at least one news search for each product by name, separate from any general market search, looking for dated items from the seven days before the snapshot. Prefer primary sources. Put the single most material item on that product's News line as a date and one plain sentence, with no link; put the dated link under Sources. Let it change the verdict or the reason when it should.
- If a product's search finds nothing dated in that window, write "No dated news found in the last 7 days." Never fill the line with older or undated items, and never invent a headline. If browsing is unavailable, write "News not checked." on every News line and say so under "What is unverified".
- An optional extra bullet in a product section is allowed for one product-specific risk; keep it to one line.
- The Sources section stays in the Markdown and is left out of the HTML.

Before sending this prompt, select an available reasoning model and High or Extra High effort in ChatGPT Work/Codex, or the strongest relevant Thinking setting available in your ChatGPT client. This instruction does not itself change the selected model or effort.
