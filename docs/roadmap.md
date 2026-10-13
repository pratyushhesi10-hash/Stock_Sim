# Roadmap and acceptance gates

## Phase 1 — Research and data

Delivered: Python package, sample generator, CSV checks, baseline, cost accounting, risk controls,
chronological evaluation, reports, CI, and development configuration.

Next: select the market, frequency, and licensed data source; document calendars, missing bars,
price adjustments, and point-in-time universe membership. Require reproducible real-data runs,
a buy-and-hold comparison using matching costs, and a reserved untouched final holdout.

## Phase 2 — Mathematical prototyping

Delivered primitives: OU fit and seeded GBM scenarios.

Next: estimate hedge ratios only on training data; select pairs using cointegration tests with
multiple-testing controls; implement a two-leg simulator with borrow costs and leg risk.
Fit an HMM on training features and use causal filtered probabilities during evaluation.
Reject unstable/nonstationary spreads, ill-conditioned fits, and short regime samples.
Gate: rolling train/test evaluation, cost sensitivity, stability diagnostics, and uncertainty estimates.

## Phase 3 — Agent core

Build a target-position interface and portfolio risk authority. Add concentration/exposure caps,
daily loss limits, stale-data guards, portfolio covariance and persisted state.
Use rules as the benchmark. Add a Gymnasium environment and PPO only after its timing,
reward accounting, fees, and risk enforcement pass independent tests.
Gate: held-out comparison against baseline across seeds, regimes, and stress scenarios.

## Phase 4 — Paper integration

Delivered: optional read-only Alpaca paper account check.

Next: paper-only order adapter, mock broker, idempotency, reconciliation, exchange calendar,
partial-fill handling, kill switch, dry-run preview, and restart recovery. Select Alpaca or
Interactive Brokers deliberately; an IB adapter is not implemented.
Gate: no live endpoint path; all failure-path tests pass; reconciled scheduled paper sessions.

## Phase 5 — Monitoring and iteration

Add a lightweight Streamlit dashboard, persistent metrics, feed/position alerts, and experiment
tracking. Compare paper fills with backtest assumptions and revise fill/cost models.
Gate: repeatable runs, stable operations, explainable risk events, and a documented review cadence.
Paper trading remains the project's scope.

## Suggested first real experiment

Select one liquid instrument and daily data, freeze the baseline configuration, record the source
and date range, run the baseline and walk-forward commands, and inspect every trade around
stops and drawdown events. Do not tune repeatedly against the final holdout.
