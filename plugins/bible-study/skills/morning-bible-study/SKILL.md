---
name: morning-bible-study
description: Write a short daily Bible study (passage, reflection, two questions, prayer) with a BibleGateway link, after checking a log so the passage is never a repeat. Use whenever the user asks for a Bible study, morning devotional, daily verse or passage, scripture reflection, quiet time, or "today's study", including scheduled morning runs and requests for a specific passage or theme, even if they never mention a skill.
---

# Morning Bible Study

Produce one short devotional study a day from a passage the user has not seen recently, and record it so future runs stay fresh.

The repeat check is the reason this skill exists. Comparing a new passage against a long log by eye fails in practice: exact repeats slipped through, and so did near repeats such as a single verse from a passage already used. The bundled script does that comparison mechanically, so always run it before presenting a passage.

## Defaults

- **Version:** NIV, unless the user names another (ESV, NLT, KJV, and so on).
- **Log:** the memory file `/topics/bible-study.md` when memory tools are available. Without memory, use a `bible-study-log.md` file in the working folder, creating it if needed.
- **Date:** get today's date from a clock tool or code, in the user's time zone. Do not infer it.

## Workflow

### 1. Load the log

Read the log and write its text to a scratch file, because the script reads from a file (or from stdin with `--log -`). Entries look like `- 2026-10-21: Psalm 92:1-4`, with optional notes in parentheses. The script finds references anywhere in a line, so annotated or multi-passage lines are fine.

### 2. Choose a candidate

Pick 2 to 8 verses that form a complete thought. Rotate between Old and New Testament and across genres (psalms, prophets, gospels, letters, narrative), and avoid books used in the last week or so; reading the recent end of the log is enough for this. If the user names a passage or a theme, honor it.

### 3. Check it

Run the bundled script from this skill's folder. Checking two or three candidates in one call saves a round trip:

```bash
python scripts/passage_tool.py check --log <log-file> "1 Peter 5:6-7" "Psalm 27:1-5"
```

| Status | Meaning | Action |
|---|---|---|
| `OK` | No overlap with the log | Use it |
| `REPEAT` | Shares verses with a logged passage | Choose another |
| `SAME_CHAPTER` | Same chapter, different verses | Choose another; the user has flagged these as too similar before |
| `PARSE_ERROR` | Book or reference not understood | Spell the book name out in full |

A passage the user explicitly asked for is used even if it repeats; mention the earlier date in one line.

### 4. Read the passage on BibleGateway

Build the link with the script so the reference format is always one BibleGateway accepts:

```bash
python scripts/passage_tool.py url "1 Peter 5:6-7" --version NIV
```

Open that URL in a new browser tab, read the page text, then close the tab. The user reads the passage through the link in the study, not through a tab left open. Confirm the page shows the passage you asked for; "No results found" usually means a verse number is out of range.

If no browser is available (for example an unattended scheduled run), fetch the same URL with a web-fetch tool. If that also fails, write the study from your knowledge of the passage and keep the link.

### 5. Write the study

Use this structure, about 200 to 250 words in total:

```markdown
**1 Peter 5:6-7 (NIV)**
[Read on BibleGateway](<url from step 4>)

> <one key phrase from the passage, under 15 words>

**Reflection**
One or two short paragraphs. Ground it in context: who wrote it, to whom, and what
situation they faced, then bring it to today.

**Questions to sit with**
1. <a personal, specific question>
2. <a second question that leads toward action>

**Prayer**
Two or three sentences in the first person, ending with "Amen."
```

Quote only a short phrase. Most modern translations (NIV, ESV, NLT, NASB) are copyrighted, and the full text is one click away through the link. Public-domain versions (KJV, ASV, WEB) may be quoted in full if the user prefers.

Follow the user's saved style preferences, such as how they like to be addressed and punctuation rules.

### 6. Log it

Append one line to the log only after the study is delivered:

```
- 2026-10-22: 1 Peter 5:6-7
```

Add `(requested)` when the user chose the passage. Log only what the user actually received.

## When the user rejects a passage

If the user says they have seen it recently, believe them; the log may be missing an entry. Log the rejected passage with `(flagged as seen)` so it is caught next time, then repeat steps 2 to 6 and log the new one with `(replacement)`.
