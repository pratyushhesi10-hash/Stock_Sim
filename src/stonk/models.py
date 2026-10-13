"""Research primitives; neither function emits executable trading signals."""

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class OUFit:
    theta: float
    mean: float
    sigma: float
    half_life: float


def fit_ou(spread, dt: float = 1.0) -> OUFit:
    """OLS AR(1) mapped to exact OU transitions; units follow dt.

    Fit only a training spread with its hedge ratio already estimated on training data.
    Stationarity and cointegration must be tested independently.
    """
    values = np.asarray(spread, dtype=float)
    if values.ndim != 1 or len(values) < 30 or not np.isfinite(values).all():
        raise ValueError("Need at least 30 finite spread observations")
    if not math.isfinite(dt) or dt <= 0 or np.std(values[:-1]) == 0:
        raise ValueError("Invalid time step or constant spread")
    design = np.column_stack([np.ones(len(values) - 1), values[:-1]])
    intercept, phi = np.linalg.lstsq(design, values[1:], rcond=None)[0]
    if not 0 < phi < 1:
        raise ValueError("Fitted process is not a stationary positive AR(1)")
    theta = -np.log(phi) / dt
    variance = np.sum((values[1:] - design @ [intercept, phi]) ** 2) / (len(values) - 3)
    return OUFit(
        float(theta),
        float(intercept / (1 - phi)),
        float(np.sqrt(variance * 2 * theta / (1 - phi**2))),
        float(np.log(2) / theta),
    )


def gbm_paths(
    initial: float,
    mu: float,
    sigma: float,
    steps: int = 252,
    paths: int = 1000,
    dt: float = 1 / 252,
    seed: int = 42,
) -> np.ndarray:
    """Seeded geometric Brownian scenarios, including the initial price column."""
    if not all(math.isfinite(x) for x in (initial, mu, sigma, dt)):
        raise ValueError("Parameters must be finite")
    if initial <= 0 or sigma < 0 or dt <= 0 or steps < 1 or paths < 1:
        raise ValueError("Invalid scenario parameters")
    rng = np.random.default_rng(seed)
    increments = (mu - sigma**2 / 2) * dt + sigma * np.sqrt(dt) * rng.normal(size=(paths, steps))
    return initial * np.exp(np.column_stack([np.zeros(paths), np.cumsum(increments, axis=1)]))
