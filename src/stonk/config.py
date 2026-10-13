"""Validated immutable configuration; there is no live trading mode."""

import math
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    fast_window: int = 10
    slow_window: int = 30
    max_position_fraction: float = 0.20
    target_annual_volatility: float = 0.10
    volatility_window: int = 20
    stop_loss_fraction: float = 0.05
    max_drawdown_fraction: float = 0.10
    initial_cash: float = 100_000.0
    commission_bps: float = 1.0
    slippage_bps: float = 5.0
    bars_per_year: int = 252

    def __post_init__(self):
        for name in ("fast_window", "slow_window", "volatility_window", "bars_per_year"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if not 1 <= self.fast_window < self.slow_window:
            raise ValueError("Require fast_window < slow_window")
        if self.volatility_window < 2:
            raise ValueError("volatility_window must be at least 2")
        for name in ("max_position_fraction", "stop_loss_fraction", "max_drawdown_fraction"):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0 < value < 1:
                raise ValueError(f"{name} must be strictly between 0 and 1")
        for name in ("initial_cash", "target_annual_volatility"):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive and finite")
        for name in ("commission_bps", "slippage_bps"):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0 <= value < 1000:
                raise ValueError(f"{name} must be in [0, 1000)")


def load_config(path: str | Path | None = None) -> Config:
    if path is None:
        return Config()
    with Path(path).open("rb") as handle:
        raw = tomllib.load(handle)
    groups = {
        "strategy": {"fast_window", "slow_window"},
        "risk": {
            "max_position_fraction",
            "target_annual_volatility",
            "volatility_window",
            "stop_loss_fraction",
            "max_drawdown_fraction",
        },
        "backtest": {"initial_cash", "commission_bps", "slippage_bps", "bars_per_year"},
    }
    values = {}
    for group, settings in raw.items():
        if group not in groups or not isinstance(settings, dict):
            raise ValueError(f"Unknown configuration group: {group}")
        unknown = settings.keys() - groups[group]
        if unknown:
            raise ValueError(f"Unknown configuration settings: {sorted(unknown)}")
        values.update(settings)
    return Config(**values)
