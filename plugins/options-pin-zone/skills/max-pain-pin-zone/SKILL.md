---
name: max-pain-pin-zone
description: Find the max pain strike and likely pin or magnet zone for a ticker and option expiration from open interest. Use when the user gives a ticker and expiry and asks for max pain, pin zone, magnet zones, or open interest walls. Research only; never places trades.
---
# Max pain and pin zone

Produce a max pain and pin zone read for one ticker and one option expiration, using the open interest on the full chain. Resolve scripts relative to this skill folder, never a cached machine-specific location.

## Inputs

- Ticker (required)
- Expiration date (required)
- Current stock price (strongly preferred)

If the price is missing, ask for it or read it from a quote source the host can reach. The chain page does not show a price. Never guess one.

## Step 1: Get the chain

Try these in order and stop at the first that returns a full table.

1. **Direct fetch (default).** Fetch:
   `https://optioncharts.io/options/{TICKER}/option-chain?option_type=all&expiration_dates={YYYY-MM-DD}:w&view=list&strike_range=all`
   - `:w` is the suffix for weekly expirations. Monthly expirations are believed to use `:m`. If the first suffix returns no table, try the other.
   - Request every row: strike, call open interest, call volume, call bid, call ask, put bid, put ask, put volume, put open interest, plus the page's data date.
2. **Browser tool (backup).** If the host has a browser tool, open the same URL and read the rendered table.
3. **Screenshot or paste (last resort).** Ask the user for a screenshot or pasted copy of the chain. Note any rows that are cut off.

Mention the route only if the default failed.

## Step 2: Sanity checks

- Record the data date on the page. Open interest is as of the prior close.
- Confirm the expiration on the page matches the one requested.
- Compare the chain-implied spot with the supplied price. A gap means the quotes are stale.
- If near-the-money premiums show almost no time value, treat bid, ask, IV and delta as unusable. Open interest and volume remain usable.

## Step 3: Calculations

Run all math in code. Do not do it mentally.

Preferred: save the chain as JSON or CSV in a working folder outside this plugin, then run the bundled helper:

```sh
python3 scripts/max_pain.py --input /path/to/chain.json --price 16.18
```

Input rows need `strike`, `call_oi` and `put_oi`. Optional fields: `call_bid`, `call_ask`, `put_bid`, `put_ask`, `call_volume`, `put_volume`. The helper uses only the Python standard library and prints JSON.

If the host cannot run the helper, compute the same values in any code tool:

- **Max pain.** For each strike S as the settle price:
  `payout(S) = 100 x [ sum(call OI x max(S - K, 0)) + sum(put OI x max(K - S, 0)) ]`
  Max pain is the S with the lowest payout. Report the four lowest.
- **Open interest map.** Total, call and put open interest by strike. List the top six or seven by total.
- **Put/call open interest ratio** for the whole chain.
- **Distance** from the current price to the nearest strikes.
- **Chain-implied spot** at the nearest strike: `S = K + call mid - put mid`.
- **ATM straddle and breakevens**, only if the quotes carry real time value.

If no code tool is available, say so and label every figure as unverified.

## Step 4: Judgment

- **Pin candidate:** the strike nearest the current price with high open interest, ideally with calls and puts roughly balanced. Agreement with max pain strengthens it.
- **Alternate magnet:** the next high open interest strike in the direction of drift.
- **Call wall:** heavy call open interest above the price. Treat as resistance.
- **Put wall and support:** heavy put open interest below the price.
- **Pin zone:** a band around the pin candidate. State that the band edges are judgment, not a calculation.
- If the price is far from max pain, say so and name the strikes that matter at the actual price.

## Output format

Keep it concise.

1. **Summary:** the likely pin, the zone and the alternate, in two or three sentences.
2. **Key Factors:** a table of top strikes (total, call and put open interest, role), the current price, max pain with the payout table, and the put/call ratio.
3. **Analysis:** pin case, upside, downside, expected range if available, data quality notes.
4. **Conclusion:** one or two sentences.
5. **Next Actions:** what to recheck and when.

If the user asks for a short write-up, give it in a code block: pin, zone, why, levels, cautions.

## Rules

- Flag uncertainty explicitly. Separate facts from interpretation.
- Never invent a price, a strike row or an open interest figure.
- Before stating any date, time or days to expiry, check the current time with code. State times in the user's timezone and in US Eastern market time.
- State these caveats when relevant: open interest is the prior day's figure and heavy volume will change it, pinning is strongest late on expiration day, and a settle beyond the walls needs a catalyst.
- Max pain is a heuristic, not a forecast. Do not present it as a probability.
- Do not explain basic options concepts unless asked.
- Never place, stage or recommend an order through any tool.
