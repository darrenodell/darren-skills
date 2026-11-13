import importlib.util
import math
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "plugins/crypto-research/skills/coinbase-research/scripts/fetch_snapshot.py"
spec = importlib.util.spec_from_file_location("fetch_snapshot", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def bars_from(closes, volume=100.0):
    bars, previous = [], closes[0]
    for index, close in enumerate(closes):
        bars.append({"start_utc": f"day-{index}", "open": previous, "close": close, "high": max(previous, close) * 1.01, "low": min(previous, close) * 0.99, "volume": volume})
        previous = close
    return bars


def selloff(days=6):
    closes = [100.0] * 244
    for _ in range(days):
        closes.append(closes[-1] * 0.96)
    return bars_from(closes)


class BounceTests(unittest.TestCase):
    def test_rsi_extremes(self):
        self.assertEqual(module.rsi_series([100.0] * 30)[-1], 50)
        self.assertEqual(module.rsi_series([100.0 + i for i in range(30)])[-1], 100)
        self.assertEqual(module.rsi_series([100.0 - i for i in range(30)])[-1], 0)
        self.assertIsNone(module.rsi_series([1.0] * 30)[13])

    def test_flat_market_is_not_oversold(self):
        result = module.bounce(bars_from([100.0] * 250))
        self.assertEqual(result["state"], "not_oversold")
        self.assertEqual(result["oversold"]["score"], 0)
        self.assertEqual(result["history"]["setups"], 0)

    def test_selloff_without_reversal_is_oversold_and_falling(self):
        result = module.bounce(selloff())
        self.assertEqual(result["state"], "oversold_falling")
        self.assertTrue(result["oversold"]["rsi_below_30"])
        self.assertTrue(result["oversold"]["below_lower_band"])
        self.assertTrue(result["oversold"]["three_down_days"])
        self.assertEqual(result["reversal"]["count"], 0)

    def test_hammer_on_heavy_volume_confirms_setup_and_plan(self):
        bars = selloff()
        last = bars[-1]["close"]
        hammer = {"start_utc": "hammer", "open": last, "close": last * 1.005, "high": last * 1.006, "low": last * 0.9, "volume": 300.0}
        bars = bars[1:] + [hammer]
        result = module.bounce(bars)
        self.assertEqual(result["state"], "bounce_setup")
        self.assertTrue(result["reversal"]["reversal_candle"])
        self.assertTrue(result["reversal"]["capitulation_volume"])
        plan = result["plan"]
        self.assertAlmostEqual(plan["entry"], hammer["high"])
        self.assertAlmostEqual(plan["stop"], hammer["low"])
        self.assertAlmostEqual(plan["target"], sum(bar["close"] for bar in bars[-20:]) / 20)
        self.assertAlmostEqual(plan["reward_to_risk"], (plan["target"] - plan["entry"]) / (plan["entry"] - plan["stop"]))
        self.assertEqual(plan["meets_minimum"], plan["reward_to_risk"] >= 1.5)

    def test_history_uses_no_future_data(self):
        closes = [100 + 20 * math.sin(i / 7) + 8 * math.sin(i / 2.3) for i in range(250)]
        bars = bars_from(closes)
        rsi = module.rsi_series(closes)
        for index in (60, 120, 200):
            past = module.bounce(bars[:index + 1])
            self.assertEqual(past["state"], module.bounce_at(bars, closes, rsi, index)[3])


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
