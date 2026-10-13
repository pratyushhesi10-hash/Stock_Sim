# Contributing

Create a focused branch, implement one milestone, run the checks below, and open a pull request.
Keep `main` runnable. Document changes to timing, accounting, validation, or model assumptions.

```bash
python -m pip install -e ".[dev]"
python -m unittest discover -s tests -v
ruff check .
ruff format --check .
stonk demo --config config/default.toml
```

For formatting changes, use `ruff format .`. For new strategy work add tests for future-data
leakage, fees, risk boundaries, and failure behavior. Use synthetic or licensed redistribution-safe
fixtures. Record data provenance and experimental settings; retain an untouched final holdout.
