import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "options-pin-zone"
    / "skills"
    / "max-pain-pin-zone"
    / "scripts"
    / "max_pain.py"
)
spec = importlib.util.spec_from_file_location("max_pain", SCRIPT)
max_pain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(max_pain)

# SOFI chain, 2026-11-13 expiration, data dated 2026-11-11 (strikes 14 to 18.5).
SOFI = [
    (14.0, 1782, 14084), (14.5, 1265, 6386), (15.0, 1281, 8228),
    (15.5, 3031, 10513), (16.0, 8812, 8577), (16.5, 9311, 3552),
    (17.0, 30120, 3361), (17.5, 23082, 1755), (18.0, 23011, 528),
    (18.5, 8161, 220),
]


def rows_from(triples):
    return [{"strike": k, "call_oi": c, "put_oi": p} for k, c, p in triples]


class MaxPainTests(unittest.TestCase):
    def test_payout_formula(self):
        rows = max_pain.normalize_rows(
            [
                {"strike": 10, "call_oi": 100, "put_oi": 0},
                {"strike": 12, "call_oi": 0, "put_oi": 50},
            ]
        )
        # Settle 11: calls at 10 owe 1 x 100, puts at 12 owe 1 x 50, times 100.
        self.assertEqual(max_pain.payout_at(rows, 11), 15000)
        self.assertEqual(max_pain.payout_at(rows, 10), 10000)
        self.assertEqual(max_pain.payout_at(rows, 12), 20000)

    def test_max_pain_and_ratio(self):
        result = max_pain.analyze(max_pain.normalize_rows(rows_from(SOFI)), price=16.18)
        self.assertEqual(result["max_pain"], 16)
        self.assertEqual(result["lowest_payouts"][0]["settle"], 16)
        self.assertEqual(result["top_open_interest"][0]["strike"], 17)
        self.assertEqual(result["top_open_interest"][0]["total_oi"], 33481)
        self.assertEqual(result["nearest_strike"], 16)
        self.assertEqual(result["strike_above"], 16.5)
        self.assertAlmostEqual(result["distance_to_max_pain"], 0.18)
        self.assertAlmostEqual(
            result["put_call_oi_ratio"],
            sum(p for _, _, p in SOFI) / sum(c for _, c, _ in SOFI),
            places=4,
        )
        self.assertNotIn("quotes", result)

    def test_quotes_and_time_value_warning(self):
        rows = rows_from(SOFI)
        for row in rows:
            if row["strike"] == 16.0:
                row.update(call_bid=0.42, call_ask=0.45, put_bid=0.16, put_ask=0.17)
        quotes = max_pain.analyze(max_pain.normalize_rows(rows), price=16.18)["quotes"]
        self.assertAlmostEqual(quotes["implied_spot"], 16.27)
        self.assertAlmostEqual(quotes["straddle"], 0.6)
        self.assertAlmostEqual(quotes["lower_breakeven"], 15.4)
        self.assertFalse(quotes["low_time_value_warning"])

        stripped = [
            {"strike": 139, "call_oi": 589, "put_oi": 940},
            {"strike": 140, "call_oi": 2523, "put_oi": 5999,
             "call_bid": 0.10, "call_ask": 0.12, "put_bid": 0.20, "put_ask": 0.26},
            {"strike": 141, "call_oi": 2391, "put_oi": 1231},
        ]
        quotes = max_pain.analyze(max_pain.normalize_rows(stripped), price=139.83)["quotes"]
        self.assertTrue(quotes["low_time_value_warning"])

    def test_rejects_bad_input(self):
        with self.assertRaises(max_pain.ChainError):
            max_pain.normalize_rows([{"strike": 10, "call_oi": 1, "put_oi": 1}])
        with self.assertRaises(max_pain.ChainError):
            max_pain.normalize_rows(
                [{"strike": 10, "call_oi": 1, "put_oi": 1}, {"strike": 10, "call_oi": 2, "put_oi": 2}]
            )
        with self.assertRaises(max_pain.ChainError):
            max_pain.normalize_rows(
                [{"strike": 10, "call_oi": "n/a", "put_oi": 1}, {"strike": 11, "call_oi": 2, "put_oi": 2}]
            )
        with self.assertRaises(max_pain.ChainError):
            max_pain.normalize_rows(
                [{"strike": 10, "call_oi": -1, "put_oi": 1}, {"strike": 11, "call_oi": 2, "put_oi": 2}]
            )

    def test_cli_json_and_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "chain.json"
            json_path.write_text(
                json.dumps({"ticker": "SOFI", "expiration": "2026-11-13", "rows": rows_from(SOFI)})
            )
            out = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(json_path), "--price", "16.18"],
                capture_output=True, text=True, check=True,
            )
            data = json.loads(out.stdout)
            self.assertEqual(data["ticker"], "SOFI")
            self.assertEqual(data["max_pain"], 16)

            csv_path = Path(tmp) / "chain.csv"
            lines = ["strike,call_oi,put_oi"] + [f'{k},"{c:,}",{p}' for k, c, p in SOFI]
            csv_path.write_text("\n".join(lines))
            out = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(csv_path)],
                capture_output=True, text=True, check=True,
            )
            self.assertEqual(json.loads(out.stdout)["max_pain"], 16)

            bad = Path(tmp) / "bad.json"
            bad.write_text("[]")
            fail = subprocess.run(
                [sys.executable, str(SCRIPT), "--input", str(bad)], capture_output=True, text=True
            )
            self.assertEqual(fail.returncode, 1)
            self.assertIn("error:", fail.stderr)


if __name__ == "__main__":
    unittest.main()
