import json
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from stonk.backtest import run_backtest
from stonk.broker import paper_account_summary
from stonk.cli import main
from stonk.config import Config, load_config
from stonk.data import synthetic_bars, validate_bars
from stonk.models import fit_ou, gbm_paths
from stonk.risk import DrawdownGuard, position_fraction
from stonk.strategy import signals
from stonk.walkforward import evaluate


def fixture(closes, opens=None, lows=None):
    close = np.asarray(closes, dtype=float)
    opening = close if opens is None else np.asarray(opens, dtype=float)
    return pd.DataFrame(
        {
            "timestamp": pd.bdate_range("2024-01-01", periods=len(close), tz="UTC"),
            "open": opening,
            "high": np.maximum(opening, close) + 1,
            "low": np.minimum(opening, close) - 1 if lows is None else lows,
            "close": close,
            "volume": 100_000,
        }
    )


SMALL = Config(
    fast_window=2,
    slow_window=3,
    volatility_window=2,
    stop_loss_fraction=0.5,
    max_drawdown_fraction=0.5,
    initial_cash=10_000,
    commission_bps=0,
    slippage_bps=0,
)


class DataTests(unittest.TestCase):
    def test_rejects_bad_data(self):
        good = synthetic_bars(60)
        bad_frames = [
            good.iloc[::-1],
            pd.concat([good, good.iloc[-1:]]),
            good.iloc[:0],
            good.drop(columns="open"),
        ]
        for column, value in [
            ("close", np.nan),
            ("volume", -1),
            ("open", 0),
            ("high", 1),
            ("low", 99999),
            ("close", np.inf),
        ]:
            frame = good.copy()
            frame.loc[0, column] = value
            bad_frames.append(frame)
        frame = good.copy()
        frame["symbol"] = "AAA"
        frame.loc[0, "symbol"] = "BBB"
        bad_frames.append(frame)
        for frame in bad_frames:
            with self.subTest(frame=frame.head(1).to_dict()), self.assertRaises(ValueError):
                validate_bars(frame)

    def test_synthetic_is_seeded(self):
        pd.testing.assert_frame_equal(synthetic_bars(), synthetic_bars())


class ConfigTests(unittest.TestCase):
    def test_invalid_settings_fail(self):
        for settings in [
            {"fast_window": 30},
            {"initial_cash": -1},
            {"slippage_bps": np.nan},
            {"max_position_fraction": 1},
            {"volatility_window": 1},
            {"slow_window": 3.5},
        ]:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                Config(**settings)

    def test_unknown_configuration_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text("[risk]\nmax_drawdwon = 0.1\n")
            with self.assertRaises(ValueError):
                load_config(path)


class BacktestTests(unittest.TestCase):
    def test_signal_fills_next_open(self):
        bars = fixture([100, 102, 105, 109, 110], [100, 102, 105, 107, 110])
        result = run_backtest(bars, SMALL)
        self.assertEqual(result.trades.iloc[0].timestamp, bars.timestamp.iloc[3])
        self.assertEqual(result.trades.iloc[0].price, 107)
        self.assertTrue((result.equity.cash >= 0).all())
        self.assertLessEqual(result.trades.iloc[0].shares * 107, 2000)

    def test_future_changes_do_not_change_past(self):
        bars = synthetic_bars(160)
        changed = bars.copy()
        changed.loc[100:, ["open", "high", "low", "close"]] *= 2
        config = Config()
        first, second = run_backtest(bars, config), run_backtest(changed, config)
        pd.testing.assert_frame_equal(first.equity.iloc[:100], second.equity.iloc[:100])
        cutoff = bars.timestamp.iloc[100]
        pd.testing.assert_frame_equal(
            first.trades[first.trades.timestamp < cutoff],
            second.trades[second.trades.timestamp < cutoff],
        )
        pd.testing.assert_series_equal(
            signals(bars.close, config).iloc[:100], signals(changed.close, config).iloc[:100]
        )

    def test_commissions_and_slippage(self):
        bars = fixture([100, 102, 105, 109, 110])
        result = run_backtest(bars, replace(SMALL, commission_bps=10, slippage_bps=20))
        trade = result.trades.iloc[0]
        self.assertAlmostEqual(trade.price, bars.open.iloc[3] * 1.002)
        self.assertAlmostEqual(trade.commission, trade.shares * trade.price * 0.001)
        expected = SMALL.initial_cash - trade.shares * trade.price - trade.commission
        self.assertAlmostEqual(result.equity.iloc[3].cash, expected)

    def test_gap_stop_uses_open_not_stop_level(self):
        bars = fixture([100, 102, 105, 109, 80, 90], [100, 102, 105, 108, 80, 90])
        result = run_backtest(bars, replace(SMALL, stop_loss_fraction=0.1))
        sell = result.trades[result.trades.side == "sell"].iloc[0]
        self.assertEqual(sell.reason, "stop_gap")
        self.assertEqual(sell.price, 80)

    def test_intrabar_stop(self):
        bars = fixture(
            [100, 102, 105, 109, 110], [100, 102, 105, 108, 110], [99, 101, 104, 90, 109]
        )
        result = run_backtest(bars, replace(SMALL, stop_loss_fraction=0.1))
        sell = result.trades[result.trades.side == "sell"].iloc[0]
        self.assertEqual(sell.reason, "stop_intrabar")
        self.assertAlmostEqual(sell.price, 108 * 0.9)

    def test_drawdown_halts_and_liquidates_next_open(self):
        bars = fixture([100, 102, 105, 90, 85, 110, 115], [100, 102, 105, 108, 85, 110, 115])
        result = run_backtest(bars, replace(SMALL, max_drawdown_fraction=0.01))
        self.assertTrue(result.metrics["halted"])
        self.assertEqual(result.trades.iloc[-1].reason, "drawdown")
        self.assertEqual(result.trades.iloc[-1].timestamp, bars.timestamp.iloc[4])
        self.assertEqual(sum(result.trades.side == "buy"), 1)
        self.assertEqual(result.metrics["open_shares"], 0)

    def test_flat_prices_have_no_orders_or_nan_metrics(self):
        result = run_backtest(fixture([100] * 100), Config())
        self.assertEqual(result.metrics["orders"], 0)
        self.assertEqual(result.metrics["max_drawdown"], 0)
        self.assertEqual(result.metrics["total_return"], 0)
        json.dumps(result.metrics, allow_nan=False)


class RiskTests(unittest.TestCase):
    def test_position_sizing_fails_closed(self):
        self.assertEqual(position_fraction(np.nan, Config()), 0)
        self.assertEqual(position_fraction(0, Config()), 0)
        self.assertEqual(position_fraction(1, Config()), 0.1)
        self.assertEqual(position_fraction(0.1, Config()), 0.2)

    def test_breaker_stays_halted_after_recovery(self):
        guard = DrawdownGuard(0.1, 100)
        self.assertFalse(guard.update(110))
        self.assertTrue(guard.update(90))
        self.assertTrue(guard.update(200))


class WalkForwardTests(unittest.TestCase):
    def test_folds_are_separate_and_warmup_does_not_trade(self):
        bars = synthetic_bars(504)
        folds = evaluate(bars, Config())
        self.assertEqual(len(folds), 4)
        self.assertTrue((folds.bars == 63).all())
        self.assertTrue((folds.initial_equity == 100_000).all())
        for i in range(1, len(folds)):
            self.assertGreater(folds.test_start.iloc[i], folds.test_end.iloc[i - 1])
        result = run_backtest(bars.iloc[:315], Config(), start_index=252)
        self.assertTrue((result.trades.timestamp >= bars.timestamp.iloc[252]).all())
        self.assertEqual(result.equity.iloc[0].timestamp, bars.timestamp.iloc[252])

    def test_future_folds_do_not_change_earlier_fold(self):
        bars = synthetic_bars(504)
        changed = bars.copy()
        changed.loc[315:, ["open", "high", "low", "close"]] *= 2
        pd.testing.assert_series_equal(
            evaluate(bars, Config()).iloc[0], evaluate(changed, Config()).iloc[0]
        )


class ModelTests(unittest.TestCase):
    def test_ou_recovers_known_process(self):
        rng = np.random.default_rng(9)
        spread = np.zeros(20_000)
        for i in range(1, len(spread)):
            spread[i] = 0.4 + 0.8 * spread[i - 1] + rng.normal(0, 0.2)
        fit = fit_ou(spread)
        self.assertAlmostEqual(fit.mean, 2, delta=0.05)
        self.assertAlmostEqual(fit.theta, -np.log(0.8), delta=0.02)
        self.assertGreater(fit.sigma, 0)
        with self.assertRaises(ValueError):
            fit_ou(np.ones(100))

    def test_brownian_paths_seed_and_deterministic_limit(self):
        np.testing.assert_array_equal(gbm_paths(100, 0.1, 0.2), gbm_paths(100, 0.1, 0.2))
        paths = gbm_paths(100, 0.1, 0, steps=10, paths=2, dt=0.1)
        self.assertEqual(paths.shape, (2, 11))
        self.assertAlmostEqual(paths[0, -1], 100 * np.exp(0.1))


class IntegrationTests(unittest.TestCase):
    def test_cli_produces_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("builtins.print"):
                main(["demo", "--output", directory])
            report = json.loads((Path(directory) / "run.json").read_text())
            self.assertTrue(report["synthetic"])
            self.assertEqual(len(report["data_sha256"]), 64)
            self.assertTrue((Path(directory) / "trades.csv").exists())
            bars_path = Path(directory) / "sample.csv"
            synthetic_bars().to_csv(bars_path, index=False)
            with patch("builtins.print"):
                main(["walk-forward", "--data", str(bars_path), "--output", directory])
            self.assertEqual(len(pd.read_csv(Path(directory) / "folds.csv")), 4)

    def test_missing_credentials_fail_before_network(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            paper_account_summary()

    def test_alpaca_client_is_explicitly_paper_and_read_only(self):
        client = MagicMock()
        with patch.dict(
            "sys.modules",
            {"alpaca": MagicMock(), "alpaca.trading": MagicMock(), "alpaca.trading.client": client},
        ):
            with patch.dict(os.environ, {"ALPACA_API_KEY": "test", "ALPACA_SECRET_KEY": "test"}):
                summary = paper_account_summary()
        client.TradingClient.assert_called_once_with(api_key="test", secret_key="test", paper=True)
        client.TradingClient.return_value.get_account.assert_called_once()
        client.TradingClient.return_value.submit_order.assert_not_called()
        self.assertEqual(summary["mode"], "paper")


if __name__ == "__main__":
    unittest.main()
