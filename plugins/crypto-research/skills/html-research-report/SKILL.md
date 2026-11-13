---
name: html-research-report
description: Turn a completed Coinbase buying brief (Markdown) and its matching snapshot into a clean standalone HTML report with one card per product, each grouping the price chart, verdict, key metrics, and entry and exit levels. Use after coinbase-research or when formatting an existing crypto report.
---

# Standalone research report

Read the completed brief and matching snapshot. This is a presentation step: preserve verdicts, levels, qualifications, and timestamps. Do not add investment claims or silently replace the snapshot.

Run the bundled renderer from the permanent research workspace:

```sh
python3 <this-skill-directory>/scripts/render_report.py --report reports/<report>.md --snapshot data/<snapshot-id>/snapshot.json --out reports/<report>.html
```

The renderer needs the structure defined in `../coinbase-research/report-prompt.md`:

- The Markdown must cite the snapshot ID and have one `## <PRODUCT-ID>` section for every product in the snapshot.
- Each product section needs five bullets: `**Verdict:**`, `**Why:**`, `**News:**`, `**Buy only if:**` and `**Exit if:**`. The last two each need a dollar level, which the chart draws as a dashed line. The News line is shown as plain text; any link in it is reduced to its label.
- A verdict starting with Buy or Watch is shown green, Wait amber, and Avoid red.
- `## Bottom line` is shown above the cards. Any other section is shown below them.
- `## Sources` is left out of the HTML on purpose; source links stay in the Markdown.

For a brief written by the `bounce-finder` skill, add `--mode bounce`. In that mode each product section needs only `**Verdict:**`, `**Why:**` and `**News:**`; the entry trigger, stop, target, reward-to-risk, oversold checks, reversal signals and history come from the snapshot's `bounce` data, and the chart shows the last 90 days. A verdict starting with Buy is rejected unless the snapshot shows a confirmed setup that meets the minimum reward-to-risk. The snapshot must come from the current collector; older snapshots have no bounce data.

In the default mode, each card groups one product's ticker price, verdict, reason, news line, 250-day close chart, 7- and 30-day returns, volatility, 90-day drawdown, distance from the 200-day average, and the two action lines. The metrics come from the snapshot, not from the Markdown. Other Markdown constructs supported in extra sections are paragraphs, flat lists, tables, fenced code, links, bold text and inline code. The renderer stops with an error instead of dropping a product or a missing field. It uses the Python standard library, embeds CSS and SVG charts, follows the reader's light or dark setting, and needs no remote assets or JavaScript. It refuses to overwrite an existing output file; choose a new name for a corrected render. Historical snapshots can be formatted, but must never be represented as current quotes.

Inspect the output at desktop and phone widths. Ensure the numbers match, each chart shows its date window and both levels, and no local files or remote assets are required to read it. Keep the original Markdown and snapshot.

After rendering, delegate to the plugin's `report-reviewer` agent when the host supports it. Provide this SKILL.md, `../../agents/report-reviewer.md`, the research Markdown, snapshot JSON, HTML path, and an output folder. On hosts without named-agent support, perform that same checklist directly and disclose that review was not independent. Repair confirmed formatting defects and rerun review before sharing the HTML. A research failure requires returning to coinbase-research; do not invent a visual fix for missing evidence. Return links to the HTML, Markdown, and review result. When the user asks for a quick result, deliver the HTML first and say that review has not run.
