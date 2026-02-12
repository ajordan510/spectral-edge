"""Shared signal conditioning utilities for PSD/statistics workflows."""

from __future__ import annotations

from typing import Mapping, Optional, Tuple

import numpy as np
from scipy import signal as scipy_signal
from scipy.ndimage import uniform_filter1d

RUNNING_MEAN_REMOVED_TEMPLATE = "Running Mean Removed ({window_seconds}s)"
RUNNING_MEAN_NOT_REMOVED = "Running Mean Not Removed"

BASELINE_HIGHPASS_HZ = 1.0
BASELINE_LOWPASS_FRACTION = 0.45
BASELINE_FILTER_ORDER = 4


def _coerce_optional_float(value) -> Optional[float]:
    """Convert a value to float when possible, else None."""
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(numeric):
        return None
    return numeric


def calculate_baseline_filters(sample_rate: float) -> dict:
    """
    Calculate baseline sample-rate adaptive filtering settings.

    Returns
    -------
    dict
        Dict with `highpass`, `lowpass`, and `nyquist` in Hz.
    """
    fs = float(sample_rate)
    if not np.isfinite(fs) or fs <= 0:
        return {"highpass": BASELINE_HIGHPASS_HZ, "lowpass": 0.0, "nyquist": 0.0}
    nyquist = fs / 2.0
    return {
        "highpass": BASELINE_HIGHPASS_HZ,
        "lowpass": BASELINE_LOWPASS_FRACTION * fs,
        "nyquist": nyquist,
    }


def _extract_user_cutoffs(filter_settings: Optional[Mapping[str, object]]) -> Tuple[Optional[float], Optional[float]]:
    """Read preferred and legacy cutoff fields from a settings mapping."""
    settings = dict(filter_settings or {})
    user_highpass = _coerce_optional_float(settings.get("user_highpass_hz"))
    user_lowpass = _coerce_optional_float(settings.get("user_lowpass_hz"))

    enabled = bool(settings.get("enabled", False))
    filter_type = str(settings.get("filter_type", "bandpass")).strip().lower()

    legacy_low = _coerce_optional_float(settings.get("cutoff_low"))
    legacy_high = _coerce_optional_float(settings.get("cutoff_high"))

    if enabled:
        if user_highpass is None and filter_type in {"highpass", "bandpass"}:
            user_highpass = legacy_low
        if user_lowpass is None and filter_type in {"lowpass", "bandpass"}:
            user_lowpass = legacy_high

    return user_highpass, user_lowpass


def apply_robust_filtering(
    data: np.ndarray,
    sample_rate: float,
    user_highpass: Optional[float] = None,
    user_lowpass: Optional[float] = None,
) -> Tuple[np.ndarray, float, float, list[str]]:
    """
    Apply baseline + optional user filtering with robust clamping.

    Returns
    -------
    tuple
        `(filtered_data, applied_highpass_hz, applied_lowpass_hz, info_messages)`
    """
    signal_arr = np.asarray(data, dtype=np.float64)
    if signal_arr.size == 0:
        baseline = calculate_baseline_filters(sample_rate)
        return signal_arr.copy(), baseline["highpass"], baseline["lowpass"], []

    baseline = calculate_baseline_filters(sample_rate)
    baseline_highpass = float(baseline["highpass"])
    baseline_lowpass = float(baseline["lowpass"])
    nyquist = float(baseline["nyquist"])
    info_messages: list[str] = []

    if nyquist <= 0 or baseline_lowpass <= 0:
        return signal_arr.copy(), baseline_highpass, baseline_lowpass, [
            "Invalid sample rate for baseline filtering. Returning unfiltered signal."
        ]

    parsed_user_highpass = _coerce_optional_float(user_highpass)
    parsed_user_lowpass = _coerce_optional_float(user_lowpass)

    if parsed_user_highpass is None:
        applied_highpass = baseline_highpass
    else:
        applied_highpass = max(parsed_user_highpass, baseline_highpass)
        if parsed_user_highpass < baseline_highpass:
            info_messages.append(
                f"Highpass of {parsed_user_highpass:g} Hz is below baseline "
                f"{baseline_highpass:.1f} Hz minimum. Using {baseline_highpass:.1f} Hz."
            )

    if parsed_user_lowpass is None:
        applied_lowpass = baseline_lowpass
    else:
        applied_lowpass = min(parsed_user_lowpass, baseline_lowpass)
        if parsed_user_lowpass > baseline_lowpass:
            info_messages.append(
                f"Lowpass of {parsed_user_lowpass:g} Hz exceeds maximum of "
                f"{baseline_lowpass:g} Hz (0.45xfs). Using {baseline_lowpass:g} Hz."
            )

    if applied_highpass >= applied_lowpass:
        adjusted_highpass = max(0.01, applied_lowpass * 0.5)
        info_messages.append(
            f"Adjusted highpass from {applied_highpass:g} Hz to {adjusted_highpass:g} Hz "
            "to preserve a valid passband."
        )
        applied_highpass = adjusted_highpass

    highpass_norm = min(max(applied_highpass / nyquist, 1e-5), 0.999)
    lowpass_norm = min(max(applied_lowpass / nyquist, 1e-5), 0.999)

    if highpass_norm >= lowpass_norm:
        info_messages.append("Unable to build valid passband after clamping. Returning unfiltered signal.")
        return signal_arr.copy(), applied_highpass, applied_lowpass, info_messages

    filtered = signal_arr.copy()
    try:
        high_sos = scipy_signal.butter(
            BASELINE_FILTER_ORDER,
            highpass_norm,
            btype="highpass",
            output="sos",
        )
        filtered = scipy_signal.sosfiltfilt(high_sos, filtered)
    except Exception as exc:
        info_messages.append(f"Highpass filtering failed ({exc}). Returning unfiltered signal.")
        return signal_arr.copy(), applied_highpass, applied_lowpass, info_messages

    try:
        low_sos = scipy_signal.butter(
            BASELINE_FILTER_ORDER,
            lowpass_norm,
            btype="lowpass",
            output="sos",
        )
        filtered = scipy_signal.sosfiltfilt(low_sos, filtered)
    except Exception as exc:
        info_messages.append(f"Lowpass filtering failed ({exc}). Returning highpass-only signal.")

    return filtered, applied_highpass, applied_lowpass, info_messages


def apply_optional_filter(
    signal: np.ndarray,
    sample_rate: Optional[float],
    filter_settings: Optional[Mapping[str, object]],
) -> np.ndarray:
    """Apply optional settings with robust baseline-aware behavior."""
    signal_arr = np.asarray(signal, dtype=np.float64)
    if signal_arr.size == 0:
        return signal_arr
    if sample_rate is None or sample_rate <= 0:
        return signal_arr.copy()

    settings = filter_settings or {}
    if not bool(settings.get("enabled", False)):
        return signal_arr.copy()

    user_highpass, user_lowpass = _extract_user_cutoffs(settings)
    filtered, _high, _low, _messages = apply_robust_filtering(
        signal_arr,
        float(sample_rate),
        user_highpass=user_highpass,
        user_lowpass=user_lowpass,
    )
    return filtered


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
    """Apply baseline robust filtering, then optional running-mean removal."""
    signal_arr = np.asarray(signal, dtype=np.float64)
    if signal_arr.size == 0:
        return signal_arr
    if sample_rate is None or sample_rate <= 0:
        return signal_arr.copy()

    settings = dict(filter_settings or {})
    user_highpass = None
    user_lowpass = None
    if bool(settings.get("enabled", False)) or "user_highpass_hz" in settings or "user_lowpass_hz" in settings:
        user_highpass, user_lowpass = _extract_user_cutoffs(settings)

    processed, _hp, _lp, _messages = apply_robust_filtering(
        signal_arr,
        float(sample_rate),
        user_highpass=user_highpass,
        user_lowpass=user_lowpass,
    )
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
    applied_highpass = _coerce_optional_float(settings.get("applied_highpass_hz"))
    applied_lowpass = _coerce_optional_float(settings.get("applied_lowpass_hz"))
    if applied_highpass is not None and applied_lowpass is not None:
        filter_note = (
            f"Filter: baseline+user (HP {applied_highpass:g} Hz, "
            f"LP {applied_lowpass:g} Hz)"
        )
    else:
        user_highpass, user_lowpass = _extract_user_cutoffs(settings)
        if user_highpass is not None or user_lowpass is not None:
            hp_text = f"{user_highpass:g}" if user_highpass is not None else "baseline"
            lp_text = f"{user_lowpass:g}" if user_lowpass is not None else "baseline"
            filter_note = f"Filter: baseline+user (HP {hp_text} Hz, LP {lp_text} Hz)"
        else:
            filter_note = "Filter: baseline (HP 1.0 Hz, LP 0.45xfs)"

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
