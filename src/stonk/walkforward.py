"""Non-overlapping evaluation folds with preceding history for warm-up."""

import pandas as pd

from stonk.backtest import run_backtest
from stonk.config import Config
from stonk.data import validate_bars


def evaluate(
    frame: pd.DataFrame, config: Config, train_bars: int = 252, test_bars: int = 63
) -> pd.DataFrame:
    bars = validate_bars(frame)
    if train_bars < max(config.slow_window, config.volatility_window + 1):
        raise ValueError("Training history too short for warm-up")
    if test_bars < 2 or len(bars) < train_bars + test_bars:
        raise ValueError("Insufficient data or invalid fold length")
    rows = []
    for start in range(train_bars, len(bars) - test_bars + 1, test_bars):
        sample = bars.iloc[start - train_bars : start + test_bars]
        result = run_backtest(sample, config, start_index=train_bars)
        rows.append(
            {
                "fold": len(rows) + 1,
                "train_start": sample.timestamp.iloc[0],
                "test_start": bars.timestamp.iloc[start],
                "test_end": bars.timestamp.iloc[start + test_bars - 1],
                **result.metrics,
            }
        )
    return pd.DataFrame(rows)
