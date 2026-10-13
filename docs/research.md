# Quantitative research specification

## Ornstein–Uhlenbeck spread

Model a training-estimated spread X with dX = theta * (mean - X) dt + sigma dW.
For equal spacing, fit X[t+1] = a + phi X[t] + epsilon. `fit_ou` maps:

- theta = -log(phi) / dt
- mean = a / (1 - phi)
- sigma² = residual_variance * 2 theta / (1 - phi²)
- half-life = log(2) / theta

It rejects phi outside (0, 1). A successful fit does not establish cointegration or profitability.
Spread construction, pair selection, hedge ratios, z-score normalization, and parameter updates
must use training observations only. Define entry/exit rules before test evaluation; model both legs,
borrow availability, costs, and spread breakdown. dt=1 returns parameters in units of one bar.

## Hidden Markov Model

Planned: Gaussian HMM using lagged returns, trailing volatility, and other defensible features.
Fit scalers and emissions only in each training window. Select state count in inner chronological
validation. Resolve label switching by train-period state characteristics rather than state IDs.
During evaluation use filtered P(state[t] | observations through t); full-sequence smoothing and
whole-test Viterbi decoding leak future information. Treat regimes as uncertain weights, not facts.

## Brownian risk approximation

`gbm_paths` uses exact log-price increments:
log(S[t+dt]/S[t]) = (mu - sigma²/2)dt + sigma sqrt(dt) Z.
This is a scenario baseline. Brownian models omit jumps, heavy tails, changing volatility, and
liquidity disruptions. Add historical stress, block bootstrap, and gap scenarios before portfolio use.
Estimate inputs on training history; record random seeds and units. No derivative pricing is implemented.

## Position sizing

Current entry fraction = min(exposure cap, target annual volatility / trailing annual volatility).
Invalid or unavailable volatility blocks entry. Sizing includes commission and adverse slippage,
uses whole shares, and never borrows. Current implementation is single-asset and entry-only.
Portfolio volatility targeting requires covariance estimates, correlated exposure caps, and rebalancing.
Kelly sizing is deferred until return estimates and uncertainty justify conservative fractional Kelly.

## Evaluation and PPO

Freeze strategy choices before outer test folds. When training is added, use nested chronological
splits with an embargo/purge appropriate to label overlap. Keep the final holdout untouched.
Report fold returns/drawdown, costs, turnover, exposure, seed dispersion, and parameter stability.
Current folds provide warm-up for a fixed baseline, not model training or parameter selection.

PPO reward should derive from net portfolio changes after realistic costs, with explicit risk and
turnover penalties. Enforce limits outside the policy, and test observation/action timing. Compare
against rules and passive benchmarks on identical unseen periods. Reinforcement learning, HMM,
and the complete OU pairs strategy are roadmap items, not required to run the current demo.

## Primary references

- Alpaca paper environment: https://docs.alpaca.markets/us/docs/paper-trading
- Alpaca Python client: https://alpaca.markets/sdks/python/api_reference/trading/trading-client.html
- HMM filtering foundation: Rabiner (1989), DOI 10.1109/5.18626
- PPO paper: https://arxiv.org/abs/1707.06347
- Stable-Baselines3: https://stable-baselines3.readthedocs.io/
