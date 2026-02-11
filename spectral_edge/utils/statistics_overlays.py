"""Shared helpers for statistical distribution overlays."""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from scipy import stats


def fit_rayleigh_from_signal(signal: np.ndarray) -> Tuple[Optional[float], Optional[float]]:
    """
    Estimate Rayleigh scale and x-extent from signal amplitude domain.

    Returns
    -------
    (scale, x_max)
        Returns (None, None) when a robust fit cannot be computed.
    """
    values = np.asarray(signal, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size < 2:
        return None, None

    amplitudes = np.abs(values)
    amplitudes = amplitudes[np.isfinite(amplitudes)]
    if amplitudes.size < 2:
        return None, None

    rms_amp = float(np.sqrt(np.mean(amplitudes ** 2)))
    scale = rms_amp / np.sqrt(2.0)
    if not np.isfinite(scale) or scale <= 0:
        return None, None

    x_max = float(max(np.max(amplitudes), scale * 6.0))
    if not np.isfinite(x_max) or x_max <= 0:
        return None, None

    return scale, x_max


def build_rayleigh_curve(
    scale: Optional[float],
    x_max: Optional[float],
    n_points: int = 400,
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """Build a finite, nonnegative Rayleigh curve for plotting."""
    if scale is None or x_max is None:
        return None, None
    if not np.isfinite(scale) or not np.isfinite(x_max) or scale <= 0 or x_max <= 0:
        return None, None

    x = np.linspace(0.0, float(x_max), max(50, int(n_points)))
    y = stats.rayleigh.pdf(x, scale=float(scale))
    mask = np.isfinite(x) & np.isfinite(y) & (y >= 0)
    if np.count_nonzero(mask) < 2:
        return None, None
    return x[mask], y[mask]
