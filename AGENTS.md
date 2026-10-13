# Agent development instructions

- Scope is simulated money only. Do not add live trading endpoints or a live-mode switch.
- Never commit credentials, downloaded market data, trained models, or generated reports.
- Keep the offline demo runnable without network access or secrets.
- Preserve next-bar execution and train-only feature/model fitting. Test future-data perturbations.
- Strategy and RL policies emit targets; the independent risk authority approves execution.
- Before committing, run `python -m unittest discover -s tests -v`, `ruff check .`,
  `ruff format --check .`, and `stonk demo --config config/default.toml`.
- Update README and roadmap when behavior or completion status changes.
- Do not describe research scaffolding as production functionality or synthetic returns as evidence.
