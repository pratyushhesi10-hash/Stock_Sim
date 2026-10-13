"""Independent entry sizing and a latched drawdown circuit breaker."""

import math
from dataclasses import dataclass

from stonk.config import Config


def position_fraction(annual_volatility: float, config: Config) -> float:
    if not math.isfinite(annual_volatility) or annual_volatility <= 0:
        return 0.0
    return min(config.max_position_fraction, config.target_annual_volatility / annual_volatility)


@dataclass
class DrawdownGuard:
    limit: float
    peak: float
    halted: bool = False

    def update(self, equity: float) -> bool:
        if not math.isfinite(equity) or equity <= 0:
            self.halted = True
        else:
            self.peak = max(self.peak, equity)
            self.halted |= 1 - equity / self.peak >= self.limit
        return self.halted
