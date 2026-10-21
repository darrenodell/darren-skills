# Stock buying research report

Use the matching Alpaca snapshot to write a general US-stock or ETF buying report, unless the user supplied their own horizon and constraints. Never assume a personal allocation, position, or loss tolerance. Report only; no account access, options selection or trades.

Start with a concise research judgment and the strongest countercase. State whether the conclusion is a technical watchlist, a fundamental assessment with specified coverage, or incomplete. Allow “wait” or “insufficient evidence.” Distinguish facts from interpretation.

Record snapshot ID, capture and analysis start UTC, observation age, market state, feed, adjustment, last included New York session, exclusion of current NY day and quality flags. Capture older than five minutes requires refresh at analysis start. Closed-market/stale quotes must not support current entry-price claims. Ticker/quote observations are unadjusted and have different timestamps from the all-adjusted daily bars.

Include a table of latest trade and bid/ask when available, spread bps, latest completed adjusted close, SMA20/50/200 and close distances, 7/30-session adjusted-price returns, 30-session annualized log-return volatility using sqrt(252), 90-session close drawdown, and 20-session average feed volume. Use the calculated snapshot metrics. Explain feed scope and that historical drawdown is not a maximum possible loss. Verify any additional arithmetic with tools.

Explain business or ETF exposure, economic drivers, financial quality, valuation, earnings/guidance and timing, material company-specific news, dividends/splits, balance-sheet or dilution risks, and macro/sector dependencies where evidenced. Use dated SEC filings, company IR releases or official fund disclosures. Do not invent consensus, P/E, earnings dates, price targets, revenue, flows or valuation conclusions. Explicitly mark unresearched areas. Alpaca prices do not supply audited fundamentals.

Give bullish, base and bearish scenarios, conditional entry evidence, invalidation and reasons to wait, without invented probabilities. Historical levels and averages are references, not guaranteed floors or forecast targets. Include liquidity, spread, actual applicable commissions/fees, execution slippage, gap risk around earnings, and missing personal context. Do not claim IEX volume is total-market volume or that adjusted closes equal a live quote. No leverage, options or short-selling assumptions unless explicitly requested in a separate scoped workflow.

Cite the API URLs, snapshot ID and times, and current primary-source links near the claims. Distinguish an announced event from a completed development. Finish with a short verification checklist for the user's own decision. A report that cannot verify earnings or current company news must say so prominently; never fabricate a complete diligence result.
