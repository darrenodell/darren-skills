import importlib.util
import math
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "plugins/crypto-research/skills/coinbase-research/scripts/fetch_snapshot.py"
spec = importlib.util.spec_from_file_location("fetch_snapshot", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SnapshotTests(unittest.TestCase):
    def test_sorts_deduplicates_and_excludes_unfinished_day(self):
        day = module.DAY
        rows = [[0, 9, 11, 10, 10, 1], [day, 10, 12, 11, 11, 2]]
        extra = [2 * day, 11, 13, 12, 12, 3]
        result = module.clean_candles([extra, rows[1], rows[0], rows[0]], 0, 2 * day)
        self.assertEqual([bar["time"] for bar in result], [0, day])

    def test_rejects_missing_days_and_nonfinite_prices(self):
        with self.assertRaisesRegex(ValueError, "Missing"):
            module.clean_candles([[0, 9, 11, 10, 10, 1]], 0, 2 * module.DAY)
        with self.assertRaises(ValueError):
            module.clean_candles([[0, 9, math.inf, 10, 10, 1]], 0, module.DAY)

    def test_constant_market_has_zero_return_volatility_drawdown(self):
        result = module.metrics([{"close": 100.0}] * 250)
        self.assertEqual(result["return_7d_pct"], 0)
        self.assertEqual(result["volatility_30d_annualized_pct"], 0)
        self.assertEqual(result["max_drawdown_90d_pct"], 0)
        self.assertEqual(result["sma_200"], 100)

    def test_return_windows_and_drawdown_have_correct_sign(self):
        bars = [{"close": 100 + index} for index in range(250)]
        result = module.metrics(bars)
        self.assertAlmostEqual(result["return_7d_pct"], (349 / 342 - 1) * 100)
        self.assertEqual(result["max_drawdown_90d_pct"], 0)
        declining = module.metrics([{"close": 400 - index} for index in range(250)])
        self.assertAlmostEqual(declining["max_drawdown_90d_pct"], (151 / 240 - 1) * 100)


if __name__ == "__main__":
    unittest.main()
