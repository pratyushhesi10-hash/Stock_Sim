# Stonk

A **paper-only** quantitative trading research project. Start with a reproducible baseline,
then add OU pairs trading, HMM regimes, and an optional PPO experiment after validation.

## What works now

- Strict single-symbol OHLCV CSV validation and seeded synthetic sample data.
- Long/flat moving-average baseline: close-time signals execute at the next bar's open.
- Entry sizing capped at 20% of equity and reduced for high realized volatility.
- Stop-loss simulation, adverse gap fills, fees, slippage, and a latched drawdown breaker.
- Equity, trade ledger, metrics, input hash, configuration, and runtime version reports.
- Separate chronological evaluation folds with historical warm-up.
- Research helpers for OU parameter fitting and geometric Brownian scenario generation.
- Optional **read-only** Alpaca paper account check.
- Automated tests and GitHub Actions; Codespaces setup and development guidance.

**Status:** runnable research foundation. HMM, a complete pairs strategy, PPO, streaming data,
broker order routing, and monitoring are planned work, not completed features.

## Quick start

Use Python 3.11 or 3.12. From the repository directory:

```bash
python -m venv .venv
```

Activate the environment:

- macOS/Linux: `source .venv/bin/activate`
- Windows PowerShell: `.venv\Scripts\Activate.ps1`

```bash
python -m pip install -e ".[dev]"
stonk demo --config config/default.toml
python -m unittest discover -s tests -v
ruff check .
```

The demo uses **synthetic prices**, requires no API keys, and writes `reports/demo/`.
Its returns demonstrate software behavior, not strategy profitability.

For a browser environment: **Code → Codespaces → Create codespace on main**.
The dev container installs the package and development tools automatically.

## Your historical data

CSV schema (one symbol, chronological unique timestamps; all OHLC prices adjusted consistently):

```csv
timestamp,open,high,low,close,volume
2024-01-02T00:00:00Z,100,102,99,101,1000000
2024-01-03T00:00:00Z,101,103,100,102,1200000
```

Put downloaded data in `data/raw/` (ignored by Git). Use enough history for warm-up and
evaluation; the two-row example illustrates format only.

```bash
stonk backtest --data data/raw/prices.csv --config config/default.toml
stonk walk-forward --data data/raw/prices.csv --config config/default.toml --train-bars 252 --test-bars 63
```

Outputs include `equity.csv`, `trades.csv`, and `run.json`, or `folds.csv` for evaluation.
Reports are ignored by Git. The configuration assumes daily bars and 252 bars per year;
change annualization and windows before using another frequency.

## Optional paper account check

```bash
python -m pip install -e ".[paper]"
stonk paper-account
```

First set `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` using **paper credentials** in your
environment or Codespaces secrets. `.env.example` documents the variable names;
`.env` is ignored and is not automatically loaded. Never paste credentials into code,
GitHub issues, or reports. No API keys are needed for CI or offline research.

The adapter always selects Alpaca's paper environment and only reads account status.
It exposes no order-submission command.

## Assumptions you should understand

- Long-only, one symbol, whole shares, one position; sizing occurs at entry, not daily rebalancing.
- Fills ignore volume constraints and use fixed bps costs. Stops are approximations from OHLC;
  a gap exit uses the open, otherwise a crossed stop uses its trigger price minus slippage.
- Drawdown checks occur at the open and close. A close-time breach exits next open, so realized
  drawdown can exceed the configured threshold. The breaker never automatically resets.
- End-of-test positions remain open and are marked to the final close; exit costs are not charged.
- Walk-forward currently evaluates a **fixed, predeclared** baseline. Each fold resets capital
  and positions; warm-up history does not trade. It does not optimize parameters or combine
  the folds into one continuous equity curve. Partial final folds are omitted.
- Feed licensing, missing sessions, corporate actions, universe survivorship, and data adjustment
  remain research responsibilities. Schema checks alone cannot validate those properties.

## Development path

Read [the architecture](docs/architecture.md), [the roadmap](docs/roadmap.md),
[the research specification](docs/research.md), and [contributing guidance](CONTRIBUTING.md).
Install heavy extras only when that phase needs them: `research`, `rl`, or `dashboard`.
Dependency ranges define compatibility; each run records installed versions. Before comparing
serious experiments, capture an exact environment with `pip freeze > reports/environment.txt`.

This repository does not yet include an open-source license; visibility alone does not grant
reuse rights. Choose a license deliberately before distributing the project for reuse.
