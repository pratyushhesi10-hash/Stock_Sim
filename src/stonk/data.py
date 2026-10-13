"""Single-symbol, daily OHLCV validation. Reject bad input instead of silently sorting."""

from pathlib import Path

import numpy as np
import pandas as pd


def validate_bars(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(frame.columns))}")
    bars = frame.copy()
    if bars.empty:
        raise ValueError("No price bars")
    bars["timestamp"] = pd.to_datetime(bars["timestamp"], utc=True, errors="raise")
    dates = bars["timestamp"]
    if dates.isna().any() or dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise ValueError("Timestamps must be unique, valid, and increasing")
    if "symbol" in bars and (bars["symbol"].isna().any() or bars["symbol"].nunique() != 1):
        raise ValueError("Each input file must contain exactly one symbol")
    columns = ["open", "high", "low", "close", "volume"]
    bars[columns] = bars[columns].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(bars[columns].to_numpy(dtype=float)).all():
        raise ValueError("Prices and volume must be finite")
    if (bars[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Prices must be positive")
    if (bars["volume"] < 0).any():
        raise ValueError("Volume must be nonnegative")
    if (bars["high"] < bars[["open", "close", "low"]].max(axis=1)).any() or (
        bars["low"] > bars[["open", "close", "high"]].min(axis=1)
    ).any():
        raise ValueError("Inconsistent OHLC values")
    return bars.reset_index(drop=True)


def load_bars(path: str | Path) -> pd.DataFrame:
    return validate_bars(pd.read_csv(path))


def synthetic_bars(count: int = 504, seed: int = 42) -> pd.DataFrame:
    """Deterministic demonstration data, never presented as market evidence."""
    if count < 2:
        raise ValueError("At least two bars required")
    rng = np.random.default_rng(seed)
    returns = 0.0002 + 0.002 * np.sin(np.arange(count) / 35) + rng.normal(0, 0.012, count)
    close = 100 * np.exp(np.cumsum(returns))
    opening = np.r_[100.0, close[:-1]] * np.exp(rng.normal(0, 0.002, count))
    width = rng.uniform(0.001, 0.015, count)
    return validate_bars(
        pd.DataFrame(
            {
                "timestamp": pd.bdate_range("2022-01-03", periods=count, tz="UTC"),
                "open": opening,
                "high": np.maximum(opening, close) * (1 + width),
                "low": np.minimum(opening, close) * (1 - width),
                "close": close,
                "volume": rng.integers(100_000, 1_000_000, count),
            }
        )
    )
