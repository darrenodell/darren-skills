#!/usr/bin/env python3
"""Max pain and open interest map for one option expiration.

Standard library only. Reads a chain from JSON or CSV and prints JSON.

Input rows need: strike, call_oi, put_oi.
Optional: call_bid, call_ask, put_bid, put_ask, call_volume, put_volume.

JSON input is either a list of rows or an object with a "rows" list
(and optionally "ticker", "expiration", "price").
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

CONTRACT_MULTIPLIER = 100
OPTIONAL_FIELDS = ("call_bid", "call_ask", "put_bid", "put_ask", "call_volume", "put_volume")


class ChainError(ValueError):
    """Raised when the chain input is missing or malformed."""


def _number(value, field, strike=None):
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("$", "").strip())
    except ValueError as exc:
        where = f" at strike {strike}" if strike is not None else ""
        raise ChainError(f"{field}{where} is not a number: {value!r}") from exc


def normalize_rows(raw_rows):
    rows = []
    seen = set()
    for raw in raw_rows:
        strike = _number(raw.get("strike"), "strike")
        if strike is None:
            raise ChainError("a row is missing its strike")
        if strike in seen:
            raise ChainError(f"duplicate strike {strike}")
        seen.add(strike)
        call_oi = _number(raw.get("call_oi"), "call_oi", strike)
        put_oi = _number(raw.get("put_oi"), "put_oi", strike)
        if call_oi is None or put_oi is None:
            raise ChainError(f"strike {strike} needs both call_oi and put_oi")
        if call_oi < 0 or put_oi < 0:
            raise ChainError(f"strike {strike} has negative open interest")
        row = {"strike": strike, "call_oi": call_oi, "put_oi": put_oi}
        for field in OPTIONAL_FIELDS:
            row[field] = _number(raw.get(field), field, strike)
        rows.append(row)
    if len(rows) < 2:
        raise ChainError("need at least two strikes")
    rows.sort(key=lambda r: r["strike"])
    return rows


def load_chain(path):
    path = Path(path)
    meta = {}
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as handle:
            raw_rows = list(csv.DictReader(handle))
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            raw_rows = data.get("rows")
            meta = {k: data[k] for k in ("ticker", "expiration", "price") if k in data}
        else:
            raw_rows = data
    if not isinstance(raw_rows, list):
        raise ChainError("input has no rows")
    return normalize_rows(raw_rows), meta


def payout_at(rows, settle):
    """Total intrinsic value owed to option holders if the stock settles at `settle`."""
    total = 0.0
    for row in rows:
        total += row["call_oi"] * max(settle - row["strike"], 0.0)
        total += row["put_oi"] * max(row["strike"] - settle, 0.0)
    return total * CONTRACT_MULTIPLIER


def _mid(bid, ask):
    if bid is None or ask is None:
        return None
    return (bid + ask) / 2


def _clean(value):
    if isinstance(value, float):
        value = round(value, 4)
        if value == int(value):
            return int(value)
    return value


def analyze(rows, price=None, top=7):
    payouts = sorted(
        ({"settle": r["strike"], "payout": payout_at(rows, r["strike"])} for r in rows),
        key=lambda item: (item["payout"], item["settle"]),
    )
    call_total = sum(r["call_oi"] for r in rows)
    put_total = sum(r["put_oi"] for r in rows)
    by_total = sorted(rows, key=lambda r: (-(r["call_oi"] + r["put_oi"]), r["strike"]))
    result = {
        "strikes": len(rows),
        "strike_range": [rows[0]["strike"], rows[-1]["strike"]],
        "max_pain": payouts[0]["settle"],
        "lowest_payouts": payouts[:4],
        "call_oi_total": call_total,
        "put_oi_total": put_total,
        "put_call_oi_ratio": (put_total / call_total) if call_total else None,
        "top_open_interest": [
            {
                "strike": r["strike"],
                "total_oi": r["call_oi"] + r["put_oi"],
                "call_oi": r["call_oi"],
                "put_oi": r["put_oi"],
            }
            for r in by_total[:top]
        ],
        "top_call_oi": [
            {"strike": r["strike"], "call_oi": r["call_oi"]}
            for r in sorted(rows, key=lambda r: (-r["call_oi"], r["strike"]))[:3]
        ],
        "top_put_oi": [
            {"strike": r["strike"], "put_oi": r["put_oi"]}
            for r in sorted(rows, key=lambda r: (-r["put_oi"], r["strike"]))[:3]
        ],
    }
    if price is not None:
        nearest = min(rows, key=lambda r: (abs(r["strike"] - price), r["strike"]))
        below = [r["strike"] for r in rows if r["strike"] <= price]
        above = [r["strike"] for r in rows if r["strike"] > price]
        result["price"] = price
        result["nearest_strike"] = nearest["strike"]
        result["strike_below"] = below[-1] if below else None
        result["strike_above"] = above[0] if above else None
        result["distance_to_max_pain"] = price - result["max_pain"]
        call_mid = _mid(nearest["call_bid"], nearest["call_ask"])
        put_mid = _mid(nearest["put_bid"], nearest["put_ask"])
        if call_mid is not None and put_mid is not None:
            implied = nearest["strike"] + call_mid - put_mid
            straddle = call_mid + put_mid
            intrinsic = abs(price - nearest["strike"])
            time_value = straddle - intrinsic
            result["quotes"] = {
                "strike": nearest["strike"],
                "implied_spot": implied,
                "implied_spot_gap": implied - price,
                "straddle": straddle,
                "lower_breakeven": nearest["strike"] - straddle,
                "upper_breakeven": nearest["strike"] + straddle,
                "straddle_time_value": time_value,
                # Under 0.5% of price in the nearest straddle usually means the
                # feed strips time value or the quotes are unusable.
                "low_time_value_warning": time_value < 0.005 * price,
            }
    return json.loads(json.dumps(result), parse_float=lambda s: _clean(float(s)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", required=True, help="chain file (.json or .csv)")
    parser.add_argument("--price", type=float, help="current stock price")
    parser.add_argument("--top", type=int, default=7, help="how many top strikes to list")
    args = parser.parse_args(argv)
    try:
        rows, meta = load_chain(args.input)
        price = args.price if args.price is not None else _number(meta.get("price"), "price")
        if price is not None and price <= 0:
            raise ChainError("price must be positive")
        result = analyze(rows, price=price, top=args.top)
    except (ChainError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for key in ("ticker", "expiration"):
        if key in meta:
            result = {key: meta[key], **result}
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
