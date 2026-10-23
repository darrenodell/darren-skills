---
name: market-release-watch
description: Check U.S. economic releases, retry missing due reports every three minutes, and produce a standalone HTML report led by an analyst's 1–5 BUY/SELL/WAIT signal. Use for Michigan sentiment, macro-release status, market read-through, and requested alerts. Does not execute trades.
---

# Market Release Watch

Give a fast, source-linked answer to: what is due, has it actually appeared, what surprised, and how markets have moved since the release? Default to U.S. macroeconomic reports. Include company earnings only for companies the user specifies. Never promise an execution advantage over professional feeds.

The standard final deliverable is a self-contained HTML file plus its matching evidence/assessment JSON. Lead it with a beginner-readable 1–5 BUY/SELL/WAIT signal from `market-release-analyst`, then show the reports and sources. A chat-only response is available when explicitly requested. Keep initial release alerts short; creating the final HTML must not delay announcing a new verified result.

## Choose the requested mode

- **Check now** (default): one fresh check, then return the result. Creating or invoking this skill alone does not activate monitoring.
- **Timed watch**: when requested, use best-effort 60-second checks around release times for the user's duration. Once a due report has been checked without a verified result, switch that report to a three-minute retry interval as described below. If no duration is given, use 20 minutes and state the end time. Reuse the verified calendar and consensus rather than researching them every minute. Keep waits at 60 seconds or less and respect cancellation.
- **Automatic alerts**: only when requested, use the host's automation tool to create or update a heartbeat in this chat. Inspect matching automations first. Use the supported minute cadence around verified release windows, a finite expiry for a request about today, and a durable prompt invoking this skill. Confirm the schedule returned by the tool; if it rejects or changes the cadence, explain the actual limitation. Do not substitute a hidden daemon or system scheduler. A saved automation is not proof of a successful run or delivered notification.

For monitoring, report newly verified results, material corrections, one concise initial source failure and its recovery, and a requested reaction follow-up. Stay quiet on unchanged/non-actionable checks. Do not turn a one-day watch into an indefinite daily task. Explain any requirement to keep the local app running and computer awake. Minute polling is best effort: source publication, caching, task runtime, and notification delivery add latency.

## Establish the session and calendar

1. Read the current clock. Use `America/New_York` for the U.S. release date and ET schedule, and convert each timestamp into the user's timezone from session context. Include both dates if they differ. Use timezone-aware conversion, not a fixed EST offset. When a local request for "today" crosses the U.S. date boundary, state the selected U.S. session explicitly.
2. Read [references/sources.md](references/sources.md) to locate the relevant publishers. Discover today's high/medium-impact U.S. releases from a current financial calendar, then verify named releases and times with their publishers where accessible. Check for cancellations, holiday changes, and postponements. Do not claim the calendar is exhaustive when sources are incomplete.
3. Include Michigan consumer sentiment, current conditions, consumer expectations, and 1-year and long-run inflation expectations when scheduled. Include that day's material PMI, inflation, jobs, consumption, growth, housing, and Fed releases as applicable. Mark lower-impact sector reports as such. A speech or Treasury auction is a separate event, not an economic result. Do not hard-code today's events or values into future runs.
4. Before the release, capture consensus, its source and retrieval time, and the appropriate prior observation. Consensus normally comes from a financial calendar or survey, not the statistical publisher. If forecasts differ, identify the source or show a range. A dash/blank is unknown, never zero. Keep any pre-release snapshot immutable when later calendars change their forecasts.

## Confirm publication, then alert promptly

Fetch the exact publisher release or data page afresh. Prefer supported direct retrieval or the browser when search/open results may be cached; record retrieval time and any visible publication time separately. Search snippets and countdown completion are insufficient evidence of publication. If freshness cannot be established, say so.

Verify the report's country, reference period, publication date, release vintage (preliminary/flash/final/revision), units, and seasonal basis before reading its result. An older report still being visible after the expected time is **due, not verified**, not proof of delay or a new result. A changed page/hash is only a reason to inspect it.

Use these statuses precisely:

- **Scheduled**: future release time verified; no result claimed.
- **Released — primary verified**: correct period and vintage found in the publisher's new release.
- **Released — secondary reported**: a reputable, timestamped source explicitly reports the correct new release while the publisher is inaccessible. Name the source and the missing primary verification; corroborate when possible without delaying an explicitly qualified first alert.
- **Due, not verified**: time has passed but no fresh matching result is established.
- **Rescheduled/cancelled**: explicitly announced by the publisher.
- **Unable to verify**: access, freshness, or conflicting-source problem prevents a reliable status.

### Missing-release retry rule

Make the first result check at the scheduled time. If the report is due but the correct new result is absent, stale, blocked, or unverified, retry that report **every three minutes** until it is verified or the watch's agreed end time. Do not poll its sources every minute just because the chat heartbeat wakes every minute. Other reports with different due times still get their first check on time.

Record the report's `last_attempt_at_utc` after each actual retrieval attempt and `next_retry_at_utc = last_attempt_at_utc + 180 seconds` when it remains unverified. Record status `due_not_verified` or `unable_to_verify`. Use `scripts/poll_plan.py --state <monitor-state.json>` before repeated result fetches; it prints the event IDs ready for a source check. State events use `id`, `scheduled_at_utc` (or legacy `due_et`), `status`, and `last_attempt_at_utc`; an optional `watch_end_at_utc` stops the plan at the deadline. If a heartbeat wakes less than 60 seconds before the next retry, it may wait the remaining seconds and re-evaluate the plan once, rather than adding another full minute of delay. Pre-release calendar/forecast reads do not delay the first check at the release time. If a host cannot schedule an exact three-minute retry, report the actual cadence and the next feasible retry rather than promising exact timing.

Announce a missing due result once with WAIT and its next retry time. Repeated unchanged checks stay quiet. If a morning report is still unresolved, keep its three-minute retries going through the authorized watch window instead of sleeping until an unrelated afternoon release. Stop at the stated deadline, mark unresolved results, and do not turn "not found" into a fabricated release or announced postponement.

For Michigan final releases, the preliminary result from the same month is a separate comparison from the previous month's final. Do not label the preliminary result as the new final. Report the sentiment revision versus preliminary as well as the monthly change where available. Treat 1-year and long-run inflation expectations separately; express changes in percentage points or basis points, not relative percent. If components are missing, alert on the verified headline first and label missing items pending.

Lead a release alert with the verified result, consensus, numerical surprise (`actual - consensus` in matching units), and prior/revisions. Do not wait for an entire market-analysis essay or complete quote panel before reporting a new release. Then add one or two sentences of conditional interpretation. Avoid a mechanical "beat = bullish" rule: growth, inflation, and the current rate regime can conflict.

## Measure market reaction accurately

After the first result alert, retrieve current, timestamped observations for SPY/QQQ (or explicitly identified S&P/Nasdaq futures), 2-year and 10-year Treasury yields, and the dollar when available. Use a connected market-data tool for supported instruments; discover its actual capabilities first. Alpaca's exchange-session calendar is not an economic-release calendar. Identify ETF proxies as proxies; do not label ETFs as futures, spot indices, the dollar index, or Treasury yields.

For post-release changes, compare observations from the same provider/feed and instrument immediately before the scheduled release to observations after it. State the interval and timestamps. Use bars only with their actual aggregation window; do not present a minute OHLC bar as an exact release-second trade. If the baseline was not captured, retrieve historical data or report that the change cannot be measured. A day-over-day or previous-close move is context, not an event reaction. Label feed coverage, delay, stale timestamps, extended-hours trading, and unavailable instruments honestly; partial data must not prevent the result alert. If SIP access is denied, try supported IEX data and identify its limited venue coverage. Reject zero/missing/crossed quote sides when computing a midpoint; an old premarket quote must not become a fresh baseline.

Give observed changes separately from inferred causes. Concurrent releases and headlines can confound attribution. Yield changes use basis points; asset-price changes use percent. In a timed or automatic watch, provide one follow-up around five minutes after each release group when data are available, rather than a new alert for every price tick. Do not place orders or connect this skill to trade execution.

## Evaluate the signal and render the final report

Read [references/signal-rubric.md](references/signal-rubric.md) for the five signal levels and evidence/assessment JSON contract. Save the verified collector evidence under the current working folder, outside the installed plugin. Keep original facts and source qualifications intact.

Delegate the judgment to the bundled `market-release-analyst` agent defined in [../../agents/market-release-analyst.md](../../agents/market-release-analyst.md) when the host supports agent delegation. A standalone skill can instead carry the same definition at `agents/market-release-analyst.md`. Supply the evidence JSON path and the rubric, not a desired BUY/SELL answer. Ask it to return only the assessment object. Claude Code can discover the plugin's `agents/` definition. Other hosts may need an explicit delegated task that reads the definition. If delegation is unavailable, evaluate the same rubric inline and set `evaluator` to `inline fallback`; never claim that an independent agent ran. A standalone skill installation without the plugin agent file can use this documented fallback.

Use 1 STRONG SELL, 2 SELL, 3 WAIT, 4 BUY, 5 STRONG BUY. Default to SPY / broad U.S. equities over 30–120 minutes after the relevant release. Provide confidence, provisional/confirmed state, a simple action, reasons, a contrary risk, and a concrete condition that changes the call. Pending/unverified releases get WAIT. A verified report can support a provisional 2/5 or 4/5 before quotes are available; don't make quotes a requirement to provide a useful best guess. Reserve 1/5 and 5/5 for primary verified releases with material aligned evidence and fresh price confirmation. The score is not a win probability or an instruction to execute a trade.

Combine the agent's assessment with the evidence as specified by the rubric. Run:

```sh
python3 <skill-folder>/scripts/render_report.py --input <working-folder>/market-release-report.json --out <output-folder>/market-release-report.html
```

Choose the user's requested output directory or the host's deliverables directory. Use a new snapshot filename instead of overwriting an earlier report. The renderer uses the Python standard library; Python 3.10+ is recommended, with `tzdata` installed if the host lacks IANA timezone data. It validates the input, escapes content, embeds the full JSON, and includes no remote assets or scripts. Preserve the matching JSON beside the HTML. Verify the actual file and inspect desktop and narrow-screen rendering when browser tools are available; disclose unavailable visual checks. Open/show the HTML and provide a direct file link. Do not substitute a chat table for the requested file.

## Keep alerts and handoffs compact

For the chat handoff and the HTML, lead with **BUY / SELL / WAIT — score/5**, confidence, as-of ET/local time, and the simple reason. The full file includes a release table:

`Release / period & vintage | Due ET / local | Status | Actual | Consensus | Prior / revision`

Link each result/schedule and consensus close to the claim. Add a short "What matters" paragraph and timestamped reaction only when available. State unresolved source gaps and next check/end time when monitoring. Say explicitly whether automatic alerts are active, merely requested, or failed to set up.

For a first release alert, announce **NEW RELEASE** or **CORRECTION**, event/vintage and actual/consensus/prior promptly. Run the analyst immediately and follow with its prominent signal, source links and the HTML report; label the assessment pending until it returns. At the five-minute follow-up, reevaluate against fresh price evidence and issue a signal update when the score/label/confirmation materially changes. Do not claim publication-to-alert latency if the publisher's precise release time is unknown.

## Preserve monitoring state

For repeated checks, use a small JSON file under the current workspace's `work/market-release-watch/`, keyed by U.S. session date and chat/monitor identity. Use the same path in the automation prompt. Record calendar URLs, expected timestamps, pre-release consensus snapshot, last checked time, per-event retrieval attempts/next three-minute retry times, results with source/period/vintage/units, baseline quote timestamps/feed, source failures, last assessment with its expiry, report paths, and event/signal fingerprints already reported in this chat. Record "reported in chat", not "notification delivered" unless delivery is confirmed.

Fingerprint by event, period, vintage, metric and verified values, not the whole HTML page. Keep preliminary and final events distinct. A repeated unchanged value is not a duplicate of an older vintage; a correction to the same vintage merits a correction alert. If state is missing or inconsistent, recover from this chat and sources and disclose uncertainty rather than claiming exactly-once delivery. Avoid overlapping watch runs; write state atomically. Keep runtime state outside the installed skill and exclude it from shared skill bundles.

Automatic prompts must specify the date, selected reports, ET/local times, check windows, state path, cadence requested, quiet-on-unchanged behavior, source fallback, reaction follow-up, and stop condition. After the deadline, report any unresolved releases once and stop. Use finite scheduler expiry when available; otherwise disable only this monitor through the automation tool. Do not archive the user's chat as a cleanup step.
