---
name: html-research-report
description: Turn a completed Coinbase research Markdown report and its matching snapshot into a polished standalone HTML report with embedded price charts, readable metrics, and preserved source links. Use after coinbase-research or when formatting an existing crypto report.
---

# Standalone research report

Read the completed research report and matching snapshot. This is a presentation step: preserve conclusions, qualifications, numeric values, timestamps, and sources. Do not add investment claims or silently replace the snapshot.

Run the bundled renderer from the permanent research workspace:

```sh
python3 <this-skill-directory>/scripts/render_report.py --report reports/<report>.md --snapshot data/<snapshot-id>/snapshot.json --out reports/<report>.html
```

The renderer uses the Python standard library. It supports Markdown headings, paragraphs, flat lists, tables, fenced code, links, bold text, and inline code. If the input uses other constructs, simplify them without losing meaning before rendering; never silently omit content. It embeds CSS and SVG charts, and needs no remote assets or JavaScript. Source links require internet when opened. Historical snapshots can be formatted, but must never be represented as current quotes.

Inspect the output at desktop and phone widths. Ensure the numbers match, links remain usable, charts label the data window and dollars, and no local files or remote assets are required to read it. Keep the original Markdown and snapshot.

After rendering, delegate to the plugin's `report-reviewer` agent when the host supports it. Provide this SKILL.md, `../../agents/report-reviewer.md`, the research Markdown, snapshot JSON, and HTML paths. On hosts without named-agent support, perform that same checklist directly and disclose that review was not independent. Repair confirmed formatting defects and rerun review before sharing the HTML. A research failure requires returning to coinbase-research; do not invent a visual fix for missing evidence. Return links to the HTML, Markdown, and review result.
