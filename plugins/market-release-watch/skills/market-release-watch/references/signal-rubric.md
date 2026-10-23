# Market judgment and report contract

Use this rubric for the plugin's `market-release-analyst` agent and for an explicitly disclosed inline fallback. It is a qualitative research rubric, not a backtested strategy. Score is direction/strength, not success probability, position size, or leverage.

## The five calls

| Score | Exact label | Meaning |
| --- | --- | --- |
| 1 | STRONG SELL | Strong bearish read-through with material, coherent released evidence and fresh market confirmation. |
| 2 | SELL | Bearish lean; explain whether the call is provisional or confirmed. |
| 3 | WAIT | Pending/unverified/expired evidence, mixed signals, or no useful edge. State the exact reason and next trigger. |
| 4 | BUY | Bullish lean; explain whether the call is provisional or confirmed. |
| 5 | STRONG BUY | Strong bullish read-through with material, coherent released evidence and fresh market confirmation. |

Default scope is SPY / broad U.S. equities. SELL means a bearish bias or reason to consider reducing long exposure; it does not authorize shorting, options, or an order. BUY is a bullish bias, not a universal call on every stock. Do not infer the user's holdings or portfolio size. Default horizon is 30–120 minutes after a material release. Reassess at the next material release or earlier evidence reversal, with an outer expiry two hours after the relevant release. An expired call becomes WAIT until refreshed.

## Reasoning that must precede the call

1. **Can this evidence be used?** Check date, reference period, vintage, units, source qualification and as-of time. If the target release is pending or its actual result cannot be verified, assign 3/5 WAIT for that release. Do not use Michigan preliminary results as today's final, or an empty actual as zero. A pre-release scenario is conditional, not a live BUY/SELL.
2. **What actually surprised?** Compare matching actual versus the captured pre-release consensus and relevant revisions. Explain whether a move is material in context; do not invent a standard deviation or use a universal threshold. Missing consensus permits only a labeled comparison with the prior, with Low confidence and no extreme score. A tiny Michigan final revision is not automatically an important new macro catalyst.
3. **Why could stocks care?** Weigh growth/earnings support against inflation and borrowing-cost pressure in the current, sourced policy regime. Strong growth plus hotter prices can hurt rate-sensitive equities; weaker growth plus cooler inflation is not automatically bullish if recession risk dominates. If the regime is not established, say so and lower confidence. Long-run inflation expectations deserve separate attention from one-year expectations. PMI above 50 is expansion versus the prior month, not proof of a bullish surprise. Services, manufacturing and composite are related, not three independent votes. Michigan sentiment, conditions and expectations are related too.
4. **Did the market agree?** Use same-instrument, same-feed observations before and after the release, with timestamps and interval. Distinguish equity confirmation from Treasury-yield/dollar context; correlation is not proof of cause. Missing/stale prices permit provisional 2/5 or 4/5 with Low confidence, but not 1/5 or 5/5. A fresh price move in the opposite direction generally warrants WAIT or an explanation of why an opposite signal is still justified; never silently ignore it. Secondary-only results remain provisional with Low confidence and no extreme score until the primary is verified.
5. **What dominates?** Give one overall call for broad equities rather than averaging correlated headlines. Low-impact reports such as rig counts alone normally do not establish a broad-market BUY/SELL; keep WAIT or explicitly label a separate energy-sector assessment. Preserve an earlier call only if its evidence is still within horizon and subsequent releases have been considered. A pending next major release limits the current call's reassessment time.

Use 1/5 or 5/5 only when actuals are primary verified, expectations are sourced, multiple distinct material channels align, comparable fresh equity reaction confirms direction, and no major contrary fact is unresolved. Strong scores should be uncommon. High confidence needs those conditions too; never manufacture a numerical win rate. A decisive but report-only best guess is 2/5 or 4/5, phase `provisional`, confidence `Low`. Label all predictions as research judgment. Do not claim the rubric has predictive accuracy without an actual separate backtest.

## Assessment object

Return these JSON fields (not a fenced Markdown document):

- `score`: integer 1–5, with `label` exactly as the table above.
- `confidence`: `Low`, `Medium`, or `High`; `phase`: `pre_release`, `provisional`, `confirmed`, or `expired`.
- `scope`: instrument and market; `horizon`: a short human-readable time horizon.
- `evaluated_at_utc`: timezone-aware ISO timestamp no earlier than the evidence snapshot; `reassess_at_utc`: timezone-aware ISO timestamp after the snapshot, usually the next material release or within two hours of the assessed release. If the old call expired, issue a new WAIT assessment with the next check time.
- `evidence_event_ids`: IDs of the released events supporting a directional call; may be empty for pre-release WAIT.
- `summary`: one plain-English sentence connecting evidence to the call.
- `action`: what a beginner should take away now, without an order, position size, or fabricated price. Keep a provisional signal distinct from a confirmed entry.
- `reasons`: two or three concise reasons; `contrary_risk`: the most important evidence or risk against the call; `invalidation`: the concrete condition that changes the call.
- `evaluator`: actual agent name, or `inline fallback` when delegation was unavailable. Do not claim an independent review for an inline call.

## HTML input contract

The caller combines the assessment unchanged with the original evidence in a single JSON file:

- `schema_version`: `1`; `report_id`: unique snapshot ID; `title`; `session_date_et`: YYYY-MM-DD.
- `as_of_utc`: timezone-aware snapshot timestamp; `local_timezone`: IANA zone from the user's session.
- `assessment`: the object above.
- `events`: list of objects with `id`, `title`, `period`, `vintage`, `scheduled_at_utc`, `status`, `metrics`, `source_ids`, and `notes`. Status is `scheduled`, `primary_verified`, `secondary_reported`, `due_not_verified`, `unable_to_verify`, `rescheduled`, or `cancelled`. Each metric has `name`, numeric-or-null `actual`, numeric-or-null `consensus`, numeric-or-null `prior`, `unit`, and `comparison`. An optional `next_retry_at_utc` makes the three-minute retry visible for a missing due report. Forecast-only or prior-only metrics are never treated as published actuals.
- `sources`: objects with unique `id`, `title`, HTTP(S) `url`, timezone-aware `retrieved_at_utc`, and `note`. Tie event source IDs to these entries.
- `market_reaction`: an object with `status`, `observations`, and `equity_confirmation`. Confirmation is `bullish`, `bearish`, `mixed`, or `unavailable`. Each observation has `instrument`, numeric-or-null `change`, `unit`, `baseline_at_utc`, `observed_at_utc`, `feed`, and `note`. Missing timestamps are null, not fabricated. A confirmed directional assessment requires at least one fresh, comparable SPY/QQQ equity observation consistent with its stated direction; rates and dollar observations are optional context.
- `limitations`: concise strings; `next_checks`: concise strings.

Save this JSON alongside the generated HTML. Use `scripts/render_report.py --input <json> --out <html>` from the skill folder. It validates the signal and evidence boundary, escapes data, rejects unsafe source URLs, and embeds the full JSON. It does not calculate an investment thesis or repair bad evidence by inventing values.

The HTML must lead with the score/label, confidence, provisional/confirmed state, scope, horizon, as-of and reassessment times, and a beginner-readable action. Show reasons, contrary risk and invalidation before the release table. Use a text label as well as green/red/amber color. Preserve source links and any missing-data qualification. Do not use blinking/flashing animation. This is a static as-of report, not a live trading terminal.

Context sources for these interpretation distinctions: [Cleveland Fed on inflation expectations](https://www.clevelandfed.org/center-for-inflation-research/measures-expected-inflation), [BIS on PMIs and financial conditions](https://www.bis.org/publications/financial-conditions-and-purchasing-managers-indices-exploring-links). These explain mechanisms; they do not validate this signal rubric.
