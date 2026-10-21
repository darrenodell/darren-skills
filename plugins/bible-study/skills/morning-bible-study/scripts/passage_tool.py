#!/usr/bin/env python3
"""Bible passage helper for the morning-bible-study skill.

Subcommands
  check  Compare candidate passages against a log of passages already used.
  url    Build a BibleGateway URL for a passage in a given version.
  parse  Show how a reference is understood (for debugging).

Examples
  python passage_tool.py check --log log.md "Psalm 23:1-6" "Isaiah 40:28-31"
  python passage_tool.py url "Psalm 92:1-4" --version NIV
  python passage_tool.py parse "1 Thess 5:16-18"

Exit codes for `check`
  0  every candidate is clear
  1  at least one candidate shares a chapter with a logged passage (no verse overlap)
  2  at least one candidate overlaps verses already used
  4  a candidate could not be parsed

Standard library only, so it runs anywhere Python 3.8+ is available.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus

WHOLE = 10_000  # stands in for "to the end of the chapter"

BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges",
    "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles",
    "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job", "Psalm", "Proverbs",
    "Ecclesiastes", "Song of Songs", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel",
    "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum",
    "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts", "Romans", "1 Corinthians",
    "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus",
    "Philemon", "Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John",
    "3 John", "Jude", "Revelation",
]
_CANON = {b.lower(): b for b in BOOKS}

# Abbreviations and alternate names that a unique-prefix match would not resolve.
# Keys are the word part only (no leading number).
_WORD_ALIASES = {
    "ps": "psalm", "pss": "psalm", "psa": "psalm", "psalms": "psalm",
    "song of solomon": "song of songs", "canticles": "song of songs", "sos": "song of songs",
    "qoh": "ecclesiastes", "eccl": "ecclesiastes", "eccles": "ecclesiastes",
    "judg": "judges", "jdg": "judges",
    "jn": "john", "jhn": "john", "mt": "matthew", "mk": "mark", "lk": "luke",
    "phil": "philippians", "php": "philippians",
    "phlm": "philemon", "philem": "philemon", "phm": "philemon",
    "jas": "james", "jms": "james",
    "rev": "revelation", "revelations": "revelation", "apocalypse": "revelation",
    "kgs": "kings", "ki": "kings", "chr": "chronicles", "chron": "chronicles",
    "sam": "samuel", "sm": "samuel", "thess": "thessalonians", "thes": "thessalonians",
    "cor": "corinthians", "tim": "timothy", "pet": "peter", "pt": "peter",
    "jon": "jonah", "ex": "exodus", "dt": "deuteronomy", "ez": "ezekiel",
}
_NUM_WORDS = {"i": "1", "ii": "2", "iii": "3", "first": "1", "second": "2", "third": "3",
              "1st": "1", "2nd": "2", "3rd": "3"}


class ParseError(ValueError):
    pass


def resolve_book(raw: str) -> str:
    """Return the canonical book name for raw text such as 'Ps', '1 Thess', 'I Cor'."""
    s = re.sub(r"\.", "", raw.strip().lower())
    s = re.sub(r"\s+", " ", s)
    # Roman numerals and number words need a space after them ("I Cor"), so "Isaiah"
    # is not read as "I saiah". Digits may run straight into the name ("1Cor").
    m = re.match(r"^(?:(i{1,3}|first|second|third)\s+|([123])(?:st|nd|rd)?\s*)(.+)$", s)
    num, word = (None, s)
    if m:
        num = _NUM_WORDS.get(m.group(1), m.group(1)) if m.group(1) else m.group(2)
        word = m.group(3)
    word = _WORD_ALIASES.get(word, word)
    key = f"{num} {word}" if num else word
    if key in _CANON:
        return _CANON[key]
    matches = [b for b in _CANON if b.startswith(key)]
    if num is None:
        matches = [b for b in matches if not b[0].isdigit()]
    if len(matches) == 1:
        return _CANON[matches[0]]
    if not matches:
        raise ParseError(f"unknown book: {raw!r}")
    raise ParseError(f"ambiguous book {raw!r}: could be {', '.join(_CANON[x] for x in matches)}")


@dataclass
class Passage:
    book: str
    spans: List[Tuple[int, int, int]]  # (chapter, first verse, last verse)
    label: str
    dates: List[str] = field(default_factory=list)

    def overlaps(self, other: "Passage") -> bool:
        if self.book != other.book:
            return False
        for c1, a1, b1 in self.spans:
            for c2, a2, b2 in other.spans:
                if c1 == c2 and a1 <= b2 and a2 <= b1:
                    return True
        return False

    def same_chapter(self, other: "Passage") -> bool:
        if self.book != other.book:
            return False
        return bool({s[0] for s in self.spans} & {s[0] for s in other.spans})


def _clean_spec(spec: str) -> str:
    spec = spec.replace("–", "-").replace("—", "-")
    spec = re.sub(r"\s*-\s*", "-", spec)
    spec = re.sub(r"\s*,\s*", ", ", spec)
    spec = re.sub(r"\s*:\s*", ":", spec)
    return spec.strip()


def parse_spec(spec: str) -> List[Tuple[int, int, int]]:
    """Turn '46:1-3, 10' or '13' or '3:16-4:2' or '120-122' into spans."""
    spec = _clean_spec(spec)
    if not spec:
        raise ParseError("missing chapter")
    spans: List[Tuple[int, int, int]] = []
    if ":" not in spec:  # whole chapters, e.g. "13" or "120-122"
        for tok in spec.split(","):
            tok = tok.strip()
            if "-" in tok:
                a, b = (int(x) for x in tok.split("-", 1))
                spans += [(c, 1, WHOLE) for c in range(a, b + 1)]
            else:
                spans.append((int(tok), 1, WHOLE))
        return spans
    chapter: Optional[int] = None
    for tok in spec.split(","):
        tok = tok.strip()
        if not tok:
            continue
        start, _, end = tok.partition("-")
        if ":" in start:
            c, v = start.split(":", 1)
            chapter, first = int(c), int(v)
        elif chapter is None:
            raise ParseError(f"verse without chapter in {spec!r}")
        else:
            first = int(start)
        if not end:
            spans.append((chapter, first, first))
        elif ":" in end:  # crosses into a later chapter
            c2, v2 = (int(x) for x in end.split(":", 1))
            spans.append((chapter, first, WHOLE))
            spans += [(c, 1, WHOLE) for c in range(chapter + 1, c2)]
            spans.append((c2, 1, v2))
            chapter = c2
        else:
            spans.append((chapter, first, int(end)))
    return spans


_REF_RE = re.compile(
    r"(?<![A-Za-z0-9])"
    r"(?P<book>(?:[123]|I{1,3})[ \t]*[A-Z][a-z]+\.?|[A-Z][a-z]+\.?(?:[ \t]+of[ \t]+[A-Z][a-z]+)?)"
    r"[ \t]+(?P<spec>\d+(?:[ \t]*[-–:,][ \t]*\d+)*)"
)


def parse_reference(text: str) -> Passage:
    """Parse one reference typed by a person. Case-insensitive."""
    m = re.match(r"^\s*(?P<book>.+?)\s*(?P<spec>\d[\d\s,:\-–]*)\s*$", text)
    if not m:
        raise ParseError(f"cannot read reference: {text!r}")
    book = resolve_book(m.group("book"))
    spec = _clean_spec(m.group("spec"))
    return Passage(book, parse_spec(spec), f"{book} {spec}")


def extract_references(log_text: str) -> List[Passage]:
    """Find every reference in free-form log text; attach the line's date if present."""
    found: Dict[str, Passage] = {}
    for line in log_text.splitlines():
        dm = re.match(r"^\s*[-*]?\s*(\d{4}-\d{2}-\d{2})", line)
        date = dm.group(1) if dm else None
        for m in _REF_RE.finditer(line):
            try:
                book = resolve_book(m.group("book"))
                spec = _clean_spec(m.group("spec"))
                p = Passage(book, parse_spec(spec), f"{book} {spec}")
            except (ParseError, ValueError):
                continue  # ordinary words followed by numbers, etc.
            key = p.label
            if key not in found:
                found[key] = p
            if date and date not in found[key].dates:
                found[key].dates.append(date)
    return list(found.values())


def check(candidates: List[str], used: List[Passage]) -> List[dict]:
    results = []
    for text in candidates:
        try:
            cand = parse_reference(text)
        except (ParseError, ValueError) as e:
            results.append({"candidate": text, "status": "PARSE_ERROR", "detail": str(e), "matches": []})
            continue
        repeats = [u for u in used if cand.overlaps(u)]
        near = [u for u in used if u not in repeats and cand.same_chapter(u)]
        status = "REPEAT" if repeats else "SAME_CHAPTER" if near else "OK"
        hits = repeats or near
        results.append({
            "candidate": cand.label,
            "status": status,
            "matches": [{"passage": u.label, "dates": u.dates} for u in hits],
        })
    return results


def biblegateway_url(reference: str, version: str = "NIV") -> str:
    p = parse_reference(reference)
    return f"https://www.biblegateway.com/passage/?search={quote_plus(p.label)}&version={quote_plus(version.upper())}"


def _read_log(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as f:
        return f.read()


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="check candidates against the log")
    c.add_argument("--log", required=True, help="log file path, or - for stdin")
    c.add_argument("--json", action="store_true", help="machine-readable output")
    c.add_argument("candidates", nargs="+")

    u = sub.add_parser("url", help="BibleGateway URL for a passage")
    u.add_argument("reference")
    u.add_argument("--version", default="NIV")

    p = sub.add_parser("parse", help="show how a reference is understood")
    p.add_argument("reference")

    args = ap.parse_args(argv)

    if args.cmd == "url":
        try:
            print(biblegateway_url(args.reference, args.version))
        except ParseError as e:
            print(f"error: {e}", file=sys.stderr)
            return 4
        return 0

    if args.cmd == "parse":
        try:
            ref = parse_reference(args.reference)
        except ParseError as e:
            print(f"error: {e}", file=sys.stderr)
            return 4
        spans = [(c, a, "end" if b == WHOLE else b) for c, a, b in ref.spans]
        print(json.dumps({"label": ref.label, "book": ref.book, "spans": spans}))
        return 0

    used = extract_references(_read_log(args.log))
    results = check(args.candidates, used)
    if args.json:
        print(json.dumps({"log_entries_parsed": len(used), "results": results}, indent=2))
    else:
        for r in results:
            line = f"{r['status']:<13} {r['candidate']}"
            if r["status"] == "PARSE_ERROR":
                line += f"  ({r['detail']})"
            elif r["matches"]:
                parts = []
                for mt in r["matches"]:
                    when = f" ({', '.join(mt['dates'])})" if mt["dates"] else ""
                    parts.append(f"{mt['passage']}{when}")
                verb = "overlaps" if r["status"] == "REPEAT" else "same chapter as"
                line += f"  {verb} {'; '.join(parts)}"
            print(line)
    statuses = {r["status"] for r in results}
    if "PARSE_ERROR" in statuses:
        return 4
    if "REPEAT" in statuses:
        return 2
    if "SAME_CHAPTER" in statuses:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
