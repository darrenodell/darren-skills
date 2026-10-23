---
name: market-release-watch
description: Check today's U.S. economic releases, especially University of Michigan sentiment and inflation expectations, against schedules and consensus; report verified results and timestamped market reaction. Use for release status, economic-calendar checks, and requested release alerts. Does not execute trades.
---

# Market Release Watch

Give a fast, source-linked answer to: what is due, has it actually appeared, what surprised, and how markets have moved since the release? Default to U.S. macroeconomic reports. Include company earnings only for companies the user specifies. Never promise an execution advantage over professional feeds.

## Choose the requested mode

- **Check now** (default): one fresh check, then return the result. Creating or invoking this skill alone does not activate monitoring.
- **Timed watch**: when requested, check targeted sources on a best-effort 60-second cadence for the user's duration. If no duration is given, use 20 minutes and state the end time. Reuse the verified calendar and consensus rather than researching them every minute. Keep waits at 60 seconds or less and respect cancellation.
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

For Michigan final releases, the preliminary result from the same month is a separate comparison from the previous month's final. Do not label the preliminary result as the new final. Report the sentiment revision versus preliminary as well as the monthly change where available. Treat 1-year and long-run inflation expectations separately; express changes in percentage points or basis points, not relative percent. If components are missing, alert on the verified headline first and label missing items pending.

Lead a release alert with the verified result, consensus, numerical surprise (`actual - consensus` in matching units), and prior/revisions. Do not wait for an entire market-analysis essay or complete quote panel before reporting a new release. Then add one or two sentences of conditional interpretation. Avoid a mechanical "beat = bullish" rule: growth, inflation, and the current rate regime can conflict.

## Measure market reaction accurately

After the first result alert, retrieve current, timestamped observations for SPY/QQQ (or explicitly identified S&P/Nasdaq futures), 2-year and 10-year Treasury yields, and the dollar when available. Use a connected market-data tool for supported instruments; discover its actual capabilities first. Alpaca's exchange-session calendar is not an economic-release calendar. Identify ETF proxies as proxies; do not label ETFs as futures, spot indices, the dollar index, or Treasury yields.

For post-release changes, compare observations from the same provider/feed and instrument immediately before the scheduled release to observations after it. State the interval and timestamps. Use bars only with their actual aggregation window; do not present a minute OHLC bar as an exact release-second trade. If the baseline was not captured, retrieve historical data or report that the change cannot be measured. A day-over-day or previous-close move is context, not an event reaction. Label feed coverage, delay, stale timestamps, extended-hours trading, and unavailable instruments honestly; partial data must not prevent the result alert. If SIP access is denied, try supported IEX data and identify its limited venue coverage. Reject zero/missing/crossed quote sides when computing a midpoint; an old premarket quote must not become a fresh baseline.

Give observed changes separately from inferred causes. Concurrent releases and headlines can confound attribution. Yield changes use basis points; asset-price changes use percent. In a timed or automatic watch, provide one follow-up around five minutes after each release group when data are available, rather than a new alert for every price tick. Do not place orders or connect this skill to trade execution.

## Keep output compact

For a check, lead with **as-of ET / local time** and the next relevant release. Use a small table:

`Release / period & vintage | Due ET / local | Status | Actual | Consensus | Prior / revision`

Link each result/schedule and consensus close to the claim. Add a short "What matters" paragraph and timestamped reaction only when available. State unresolved source gaps and next check/end time when monitoring. Say explicitly whether automatic alerts are active, merely requested, or failed to set up.

For an alert, lead with **NEW RELEASE** or **CORRECTION**, event and vintage, then actual/consensus/prior, the inflation or growth detail that matters, source link, observed-at time, and any available reaction. Do not claim publication-to-alert latency if the publisher's precise release time is unknown.

## Preserve monitoring state

For repeated checks, use a small JSON file under the current workspace's `work/market-release-watch/`, keyed by U.S. session date and chat/monitor identity. Use the same path in the automation prompt. Record calendar URLs, expected timestamps, pre-release consensus snapshot, last checked time, results with source/period/vintage/units, baseline quote timestamps/feed, source failures, and event fingerprints already reported in this chat. Record "reported in chat", not "notification delivered" unless delivery is confirmed.

Fingerprint by event, period, vintage, metric and verified values, not the whole HTML page. Keep preliminary and final events distinct. A repeated unchanged value is not a duplicate of an older vintage; a correction to the same vintage merits a correction alert. If state is missing or inconsistent, recover from this chat and sources and disclose uncertainty rather than claiming exactly-once delivery. Avoid overlapping watch runs; write state atomically. Keep runtime state outside the installed skill and exclude it from shared skill bundles.

Automatic prompts must specify the date, selected reports, ET/local times, check windows, state path, cadence requested, quiet-on-unchanged behavior, source fallback, reaction follow-up, and stop condition. After the deadline, report any unresolved releases once and stop. Use finite scheduler expiry when available; otherwise disable only this monitor through the automation tool. Do not archive the user's chat as a cleanup step.
