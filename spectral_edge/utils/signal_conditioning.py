"""Shared signal conditioning utilities for PSD/statistics workflows."""

from __future__ import annotations

from typing import Mapping, Optional

import numpy as np
from scipy import signal as scipy_signal
from scipy.ndimage import uniform_filter1d

RUNNING_MEAN_REMOVED_TEMPLATE = "Running Mean Removed ({window_seconds}s)"
RUNNING_MEAN_NOT_REMOVED = "Running Mean Not Removed"


def apply_optional_filter(
    signal: np.ndarray,
    sample_rate: Optional[float],
    filter_settings: Optional[Mapping[str, object]],
) -> np.ndarray:
    """Apply optional filter settings and return a filtered copy."""
    signal_arr = np.asarray(signal, dtype=np.float64)
    if signal_arr.size == 0:
        return signal_arr

    settings = filter_settings or {}
    if not bool(settings.get("enabled", False)):
        return signal_arr.copy()
    if sample_rate is None or sample_rate <= 0:
        return signal_arr.copy()

    filter_type = str(settings.get("filter_type", "lowpass")).strip().lower()
    filter_design = str(settings.get("filter_design", "butterworth")).strip().lower()
    filter_order = int(settings.get("filter_order", 4))

    cutoff_low = settings.get("cutoff_low", None)
    cutoff_high = settings.get("cutoff_high", None)
    nyquist = float(sample_rate) / 2.0
    if nyquist <= 0:
        return signal_arr.copy()

    try:
        if filter_type == "lowpass":
            if cutoff_high is None:
                return signal_arr.copy()
            wn = min(float(cutoff_high) / nyquist, 0.95)
            btype = "lowpass"
        elif filter_type == "highpass":
            if cutoff_low is None:
                return signal_arr.copy()
            wn = max(float(cutoff_low) / nyquist, 0.01)
            btype = "highpass"
        elif filter_type == "bandpass":
            if cutoff_low is None or cutoff_high is None:
                return signal_arr.copy()
            low = max(float(cutoff_low) / nyquist, 0.01)
            high = min(float(cutoff_high) / nyquist, 0.95)
            if low >= high:
                return signal_arr.copy()
            wn = [low, high]
            btype = "bandpass"
        else:
            return signal_arr.copy()
    except (TypeError, ValueError):
        return signal_arr.copy()

    try:
        if filter_design == "chebyshev":
            sos = scipy_signal.cheby1(filter_order, 0.5, wn, btype=btype, output="sos")
        elif filter_design == "bessel":
            sos = scipy_signal.bessel(filter_order, wn, btype=btype, output="sos")
        else:
            sos = scipy_signal.butter(filter_order, wn, btype=btype, output="sos")
        return scipy_signal.sosfiltfilt(sos, signal_arr)
    except Exception:
        # Keep workflows non-fatal if filter design/application fails.
        return signal_arr.copy()


def remove_running_mean(
    signal: np.ndarray,
    sample_rate: Optional[float],
    window_seconds: float = 1.0,
) -> np.ndarray:
    """Remove running mean from a signal and return a processed copy."""
    signal_arr = np.asarray(signal, dtype=np.float64)
    if signal_arr.size == 0:
        return signal_arr
    if sample_rate is None or sample_rate <= 0:
        return signal_arr.copy()
    if window_seconds <= 0:
        return signal_arr.copy()

    window_samples = max(1, int(float(sample_rate) * float(window_seconds)))
    if signal_arr.size < window_samples:
        return signal_arr - np.mean(signal_arr)

    running_mean = uniform_filter1d(signal_arr, size=window_samples, mode="nearest")
    return signal_arr - running_mean


def apply_processing_pipeline(
    signal: np.ndarray,
    sample_rate: Optional[float],
    filter_settings: Optional[Mapping[str, object]] = None,
    remove_mean: bool = False,
    mean_window_seconds: float = 1.0,
) -> np.ndarray:
    """Apply the shared conditioning pipeline (filter, then running-mean removal)."""
    processed = apply_optional_filter(signal, sample_rate, filter_settings)
    if remove_mean:
        processed = remove_running_mean(processed, sample_rate, mean_window_seconds)
    return processed


def build_processing_note(
    filter_settings: Optional[Mapping[str, object]],
    remove_mean: bool,
    mean_window_seconds: float = 1.0,
) -> str:
    """Create a deterministic single-line conditioning summary."""
    settings = filter_settings or {}
    if bool(settings.get("enabled", False)):
        filter_type = str(settings.get("filter_type", "lowpass")).strip().lower()
        if filter_type == "bandpass":
            low = settings.get("cutoff_low", "N/A")
            high = settings.get("cutoff_high", "N/A")
            filter_note = f"Filter: bandpass ({low} to {high} Hz)"
        elif filter_type == "highpass":
            low = settings.get("cutoff_low", "N/A")
            filter_note = f"Filter: highpass ({low} Hz)"
        else:
            high = settings.get("cutoff_high", "N/A")
            filter_note = f"Filter: lowpass ({high} Hz)"
    else:
        filter_note = "Filter: off"

    if remove_mean:
        window_seconds_value = float(mean_window_seconds)
        if window_seconds_value.is_integer():
            window_seconds = f"{window_seconds_value:.1f}"
        else:
            window_seconds = f"{window_seconds_value:g}"
        mean_note = RUNNING_MEAN_REMOVED_TEMPLATE.format(window_seconds=window_seconds)
    else:
        mean_note = RUNNING_MEAN_NOT_REMOVED

    return f"{filter_note} | {mean_note}"
