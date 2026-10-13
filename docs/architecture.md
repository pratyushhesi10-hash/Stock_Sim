# Architecture

## Current executable flow

CSV or seeded sample → bar validation → causal baseline signal → independent risk sizing
→ simulated fills → equity and ledger → metrics and reproducibility metadata.

| Module | Responsibility |
| --- | --- |
| `data.py` | Enforce positive consistent OHLC, nonnegative volume, finite data, chronological timestamps |
| `strategy.py` | Emit close-time long/flat signals without broker access |
| `risk.py` | Cap entry exposure, scale by trailing volatility, latch drawdown breaches |
| `backtest.py` | Next-open execution, cash accounting, stop simulation, fees and reports |
| `walkforward.py` | Chronological fixed-baseline evaluation with historical warm-up |
| `models.py` | Training-only OU fitting and seeded Brownian scenario primitives |
| `broker.py` | Read-only paper account connectivity |
| `cli.py` | User commands and experiment output |

## Target agent boundaries

1. Data ingestion: historical adapter and WebSocket collector; immutable raw data, timestamps,
   exchange calendars, adjustments, provenance, reconnect and stale-data handling.
2. Features/models: lagged features, train-only scalers, HMM filtered probabilities,
   cointegrated spread selection, OU fit, model version registry.
3. Decision engine: transparent rules first; later PPO returns target positions, never orders.
4. Risk service: authoritative exposure, volatility, concentration, daily loss, drawdown,
   stale-data, and spread-breakdown checks. Strategy code cannot bypass this service.
5. Paper execution: translate approved targets into idempotent orders, validate instrument and
   session constraints, reconcile partial fills and cancellations, recover from restarts.
6. Observability: structured credential-free logs, fill latency, risk events, feed health,
   equity dashboard, and persisted state. Start with SQLite and local reports before adding services.

## Execution invariants before broker orders

- Hard-code/allowlist the paper endpoint, use paper keys, and expose no live-mode flag.
- Verify broker state before submitting any order; ambiguous state blocks new orders.
- Persist an intent with a unique client order ID before submission; reconcile before retrying.
- Use the exchange session calendar and broker asset rules rather than business-day assumptions.
- Halt on stale data, mismatched positions, excessive losses, or invalid model output.
- A manual kill switch cancels outstanding orders and uses a controlled flatten procedure.
- Test restart, duplicate event, rejection, partial fill, disconnect, and cancel/fill races with mocks.

## Runtime and secrets

GitHub Actions runs offline tests and demo checks. It is not an always-on trading host.
Codespaces is for development. A later paper agent needs a separate persistent runtime,
an explicit session schedule, restart recovery, and stored state. No deployment is configured yet.

Use environment variables or an appropriate secret manager. Raw market data, models, and output
reports stay outside version control; keep small synthetic fixtures in tests. CI uses no broker keys.
