"""Tests for plugins/bible-study/skills/morning-bible-study/scripts/passage_tool.py.

Run from the repo root:  python -m unittest discover -s tests -v
Many cases come from real repeats that slipped through before this tool existed.
"""

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins" / "bible-study" / "skills" / "morning-bible-study" / "scripts"))

import passage_tool as pt  # noqa: E402

LOG = (ROOT / "tests" / "fixtures" / "sample_log.md").read_text(encoding="utf-8")
USED = pt.extract_references(LOG)


def status(ref: str) -> str:
    return pt.check([ref], USED)[0]["status"]


class BookNames(unittest.TestCase):
    def test_aliases(self):
        cases = {
            "Ps": "Psalm", "Psalms": "Psalm", "psa.": "Psalm",
            "1 Thess": "1 Thessalonians", "I Cor": "1 Corinthians", "2nd Tim": "2 Timothy",
            "Song of Solomon": "Song of Songs", "Rev": "Revelation", "Revelations": "Revelation",
            "Jn": "John", "1 Jn": "1 John", "Phil": "Philippians", "Phlm": "Philemon",
            "Gen": "Genesis", "Zeph": "Zephaniah",
            # regression: "Isaiah" was once read as roman numeral I + "saiah"
            "Isaiah": "Isaiah", "Isa": "Isaiah", "II Timothy": "2 Timothy", "1Cor": "1 Corinthians",
        }
        for raw, want in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(pt.resolve_book(raw), want)

    def test_ambiguous_and_unknown(self):
        with self.assertRaises(pt.ParseError):
            pt.resolve_book("Jo")  # Joshua, Job, Joel, John, Jonah
        with self.assertRaises(pt.ParseError):
            pt.resolve_book("Hezekiah")


class LogParsing(unittest.TestCase):
    def test_every_logged_passage_found(self):
        labels = {p.label for p in USED}
        for want in ["Isaiah 40:28-31", "Psalm 46:1-3, 10", "1 Kings 19:11-13",
                     "Revelation 13", "Song of Songs 2:10-13", "1 Thessalonians 5:16-18"]:
            with self.subTest(want=want):
                self.assertIn(want, labels)

    def test_two_refs_on_one_line_and_dates_merged(self):
        isaiah = next(p for p in USED if p.label == "Isaiah 40:28-31")
        self.assertEqual(isaiah.dates, ["2026-09-10", "2026-09-24"])

    def test_ignores_plain_words(self):
        self.assertFalse(any(p.label.startswith(("Name", "Description")) for p in USED))


class RepeatDetection(unittest.TestCase):
    def test_exact_repeat(self):
        self.assertEqual(status("Isaiah 40:28-31"), "REPEAT")

    def test_single_verse_inside_logged_list(self):
        self.assertEqual(status("Psalm 46:10"), "REPEAT")

    def test_whole_chapter_logged_catches_any_verse(self):
        self.assertEqual(status("Revelation 13:1-3"), "REPEAT")

    def test_whole_chapter_candidate(self):
        self.assertEqual(status("Psalms 46"), "REPEAT")

    def test_partial_overlap(self):
        self.assertEqual(status("Colossians 3:14-17"), "REPEAT")

    def test_alias_and_alternate_title(self):
        self.assertEqual(status("Song of Songs 2:12"), "REPEAT")
        self.assertEqual(status("1 Thess 5:16"), "REPEAT")

    def test_same_chapter_different_verses(self):
        self.assertEqual(status("Psalm 46:4-7"), "SAME_CHAPTER")

    def test_numbered_books_kept_apart(self):
        self.assertEqual(status("1 John 1:9"), "OK")  # must not match John
        self.assertEqual(status("2 Kings 19:11"), "OK")  # must not match 1 Kings

    def test_fresh_passage(self):
        self.assertEqual(status("Psalm 23:1-6"), "OK")

    def test_cross_chapter_range(self):
        self.assertEqual(status("Zephaniah 2:15-3:1"), "SAME_CHAPTER")
        self.assertEqual(status("Zephaniah 2:15-3:17"), "REPEAT")

    def test_unparseable(self):
        self.assertEqual(status("Hezekiah 3:1"), "PARSE_ERROR")


class Urls(unittest.TestCase):
    def test_niv_url(self):
        self.assertEqual(
            pt.biblegateway_url("Psalm 92:1-4", "NIV"),
            "https://www.biblegateway.com/passage/?search=Psalm+92%3A1-4&version=NIV",
        )

    def test_url_normalizes_book(self):
        self.assertIn("search=1+Thessalonians+5%3A16-18", pt.biblegateway_url("1 thess 5:16-18"))


class Cli(unittest.TestCase):
    def test_exit_codes(self):
        log = str(ROOT / "tests" / "fixtures" / "sample_log.md")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(pt.main(["check", "--log", log, "Psalm 23:1-6"]), 0)
            self.assertEqual(pt.main(["check", "--log", log, "Psalm 46:4-7"]), 1)
            self.assertEqual(pt.main(["check", "--log", log, "Psalm 23", "Psalm 46:10"]), 2)


if __name__ == "__main__":
    unittest.main()
