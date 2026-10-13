"""Close-time long/flat moving average baseline."""

import pandas as pd

from stonk.config import Config


def signals(close: pd.Series, config: Config) -> pd.Series:
    fast = close.rolling(config.fast_window, min_periods=config.fast_window).mean()
    slow = close.rolling(config.slow_window, min_periods=config.slow_window).mean()
    return ((fast > slow) & slow.notna()).astype(int)
