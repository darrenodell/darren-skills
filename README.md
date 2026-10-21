# darren-skills

Personal skills for Claude, packaged as a Claude Code plugin marketplace. Each skill also works on its own in claude.ai.

## Skills

| Plugin | Skill | What it does |
|---|---|---|
| `bible-study` | `morning-bible-study` | Writes a short daily Bible study (passage, reflection, two questions, prayer) with a BibleGateway link. A bundled script checks every candidate passage against a log so nothing repeats, including single verses from passages already used. |

## Install

**Claude Code**

```
/plugin marketplace add darrenodell/darren-skills
/plugin install bible-study@darren-skills
```

The skill triggers on its own when you ask for a Bible study, or run it directly with `/bible-study:morning-bible-study`.

**claude.ai**

Download `morning-bible-study.skill` from the latest release and add it to your skills, or zip the folder `plugins/bible-study/skills/morning-bible-study/` and upload that.

## Repository layout

```
.claude-plugin/marketplace.json     the catalog Claude Code reads
plugins/
  bible-study/
    .claude-plugin/plugin.json      plugin name, version, author
    skills/
      morning-bible-study/
        SKILL.md                    instructions Claude follows
        scripts/passage_tool.py     repeat checker and URL builder
tests/                              unit tests (kept out of the skill so it stays lean)
```

## Development

```bash
python -m unittest discover -s tests -v       # run tests
claude plugin validate .                      # check marketplace and plugin
```

To release a change, bump `version` in `plugin.json`. Installed copies stay on the old version until it changes.

To add a skill, create `plugins/<plugin>/skills/<skill-name>/SKILL.md`. To add a plugin, create its folder under `plugins/` and add an entry to `marketplace.json`.

## License

MIT
