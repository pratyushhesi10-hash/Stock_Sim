"""Daily, long-only simulator: yesterday's signal executes at today's open."""

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from stonk.config import Config
from stonk.data import validate_bars
from stonk.risk import DrawdownGuard, position_fraction
from stonk.strategy import signals


@dataclass
class Result:
    equity: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict
    config: dict


def run_backtest(frame: pd.DataFrame, config: Config, start_index: int = 0) -> Result:
    bars = validate_bars(frame)
    if type(start_index) is not int or not 0 <= start_index < len(bars):
        raise ValueError("start_index outside price history")
    if len(bars) - start_index < 2:
        raise ValueError("At least two evaluation bars required")
    signal = signals(bars.close, config)
    volatility = bars.close.pct_change().rolling(config.volatility_window).std(ddof=1)
    volatility *= np.sqrt(config.bars_per_year)
    cash, shares, entry = config.initial_cash, 0, 0.0
    guard = DrawdownGuard(config.max_drawdown_fraction, cash)
    slip, fee = config.slippage_bps / 10_000, config.commission_bps / 10_000
    ledger, history = [], []

    def sell(row, reference, reason):
        nonlocal cash, shares, entry
        price = reference * (1 - slip)
        commission = shares * price * fee
        cash += shares * price - commission
        ledger.append(
            {
                "timestamp": row.timestamp,
                "side": "sell",
                "shares": shares,
                "price": price,
                "commission": commission,
                "reason": reason,
            }
        )
        shares, entry = 0, 0.0

    for i in range(start_index, len(bars)):
        row = bars.iloc[i]
        exited = False
        guard.update(cash + shares * row.open)
        desired = int(signal.iloc[i - 1]) if i > 0 else 0
        if shares:
            stop = entry * (1 - config.stop_loss_fraction)
            if guard.halted:
                sell(row, row.open, "drawdown")
                exited = True
            elif row.open <= stop:
                sell(row, row.open, "stop_gap")
                exited = True
            elif not desired:
                sell(row, row.open, "signal")
                exited = True
        if not shares and not exited and desired and not guard.halted:
            fraction = position_fraction(float(volatility.iloc[i - 1]), config)
            price = row.open * (1 + slip)
            shares = int(cash * fraction / (price * (1 + fee)))
            if shares > 0:
                commission = shares * price * fee
                cash -= shares * price + commission
                entry = price
                ledger.append(
                    {
                        "timestamp": row.timestamp,
                        "side": "buy",
                        "shares": shares,
                        "price": price,
                        "commission": commission,
                        "reason": "signal",
                    }
                )
        if shares and row.low <= entry * (1 - config.stop_loss_fraction):
            sell(row, entry * (1 - config.stop_loss_fraction), "stop_intrabar")
        equity = cash + shares * row.close
        guard.update(equity)
        # A close-time drawdown breach is liquidated at the next bar's open.
        history.append(
            {
                "timestamp": row.timestamp,
                "equity": equity,
                "cash": cash,
                "shares": shares,
                "halted": guard.halted,
            }
        )
    equity_frame = pd.DataFrame(history)
    trade_frame = pd.DataFrame(
        ledger, columns=["timestamp", "side", "shares", "price", "commission", "reason"]
    )
    curve = np.r_[config.initial_cash, equity_frame.equity.to_numpy()]
    returns = curve[1:] / curve[:-1] - 1
    std = float(np.std(returns, ddof=1))
    metrics = {
        "initial_equity": config.initial_cash,
        "final_equity": float(curve[-1]),
        "total_return": float(curve[-1] / curve[0] - 1),
        "max_drawdown": float(np.max(1 - curve / np.maximum.accumulate(curve))),
        "annualized_volatility": float(std * np.sqrt(config.bars_per_year)),
        "sharpe_zero_risk_free": float(np.mean(returns) / std * np.sqrt(config.bars_per_year))
        if std > 0
        else None,
        "orders": len(trade_frame),
        "commission_paid": float(trade_frame.commission.sum()),
        "open_shares": int(shares),
        "halted": bool(guard.halted),
        "bars": len(history),
    }
    return Result(equity_frame, trade_frame, metrics, asdict(config))
