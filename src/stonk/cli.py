"""Offline-first commands with machine-readable, reproducible output."""

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from stonk import __version__
from stonk.backtest import run_backtest
from stonk.broker import paper_account_summary
from stonk.config import load_config
from stonk.data import load_bars, synthetic_bars
from stonk.walkforward import evaluate


def main(argv=None):
    parser = argparse.ArgumentParser(description="Stonk paper-only research tools")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Run a deterministic synthetic-data backtest")
    demo.add_argument("--seed", type=int, default=42)
    demo.add_argument("--bars", type=int, default=504)
    demo.add_argument("--config", default=None)
    demo.add_argument("--output", default="reports/demo")
    for command in ("backtest", "walk-forward"):
        sub = commands.add_parser(command)
        sub.add_argument("--data", required=True)
        sub.add_argument("--config", default=None)
        sub.add_argument("--output", default=f"reports/{command}")
        if command == "walk-forward":
            sub.add_argument("--train-bars", type=int, default=252)
            sub.add_argument("--test-bars", type=int, default=63)
    commands.add_parser("paper-account", help="Read an Alpaca paper account; sends no orders")
    args = parser.parse_args(argv)
    try:
        if args.command == "paper-account":
            try:
                summary = paper_account_summary()
            except ValueError:
                raise
            except Exception:
                # SDK errors can contain request details; do not print credentials or raw payloads.
                raise ValueError("Paper account request failed; check credentials and connectivity")
            print(json.dumps(summary, indent=2))
            return
        config = load_config(args.config)
        bars = (
            synthetic_bars(args.bars, args.seed) if args.command == "demo" else load_bars(args.data)
        )
        output = Path(args.output)
        output.mkdir(parents=True, exist_ok=True)
        metadata = {
            "version": __version__,
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "command": vars(args),
            "data_sha256": hashlib.sha256(bars.to_csv(index=False).encode()).hexdigest(),
        }
        if args.command == "walk-forward":
            folds = evaluate(bars, config, args.train_bars, args.test_bars)
            folds.to_csv(output / "folds.csv", index=False)
            metadata["config"] = vars(config)
            print(folds.to_string(index=False))
        else:
            result = run_backtest(bars, config)
            result.equity.to_csv(output / "equity.csv", index=False)
            result.trades.to_csv(output / "trades.csv", index=False)
            metadata.update(
                {
                    "config": result.config,
                    "metrics": result.metrics,
                    "synthetic": args.command == "demo",
                }
            )
            print(json.dumps(result.metrics, indent=2, allow_nan=False))
        (output / "run.json").write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n")
        print(f"Reports: {output.resolve()}")
    except (ValueError, TypeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
