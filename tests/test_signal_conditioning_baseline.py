import numpy as np
import pytest

from spectral_edge.utils.signal_conditioning import (
    apply_processing_pipeline,
    apply_robust_filtering,
    calculate_baseline_filters,
)


def test_calculate_baseline_filters_formula():
    baseline = calculate_baseline_filters(1000.0)
    assert baseline["highpass"] == pytest.approx(1.0)
    assert baseline["lowpass"] == pytest.approx(450.0)
    assert baseline["nyquist"] == pytest.approx(500.0)


def test_apply_robust_filtering_clamps_user_cutoffs_and_reports_messages():
    signal = np.sin(np.linspace(0.0, 20.0 * np.pi, 4000))
    filtered, hp, lp, messages = apply_robust_filtering(
        signal,
        1000.0,
        user_highpass=0.3,
        user_lowpass=600.0,
    )
    assert filtered.shape == signal.shape
    assert hp == pytest.approx(1.0)
    assert lp == pytest.approx(450.0)
    assert any("Highpass of 0.3 Hz" in msg for msg in messages)
    assert any("Lowpass of 600 Hz" in msg for msg in messages)


def test_apply_robust_filtering_keeps_valid_user_cutoffs():
    signal = np.sin(np.linspace(0.0, 10.0 * np.pi, 2000))
    filtered, hp, lp, messages = apply_robust_filtering(
        signal,
        1000.0,
        user_highpass=5.0,
        user_lowpass=300.0,
    )
    assert filtered.shape == signal.shape
    assert hp == pytest.approx(5.0)
    assert lp == pytest.approx(300.0)
    assert messages == []


def test_apply_robust_filtering_low_sample_rate_auto_adjusts_passband():
    signal = np.sin(np.linspace(0.0, 4.0 * np.pi, 1000))
    _filtered, hp, lp, messages = apply_robust_filtering(signal, 1.0)
    assert hp < lp
    assert any("Adjusted highpass" in msg for msg in messages)


def test_apply_processing_pipeline_applies_baseline_by_default():
    signal = 5.0 + np.sin(np.linspace(0.0, 30.0 * np.pi, 6000))
    processed = apply_processing_pipeline(
        signal,
        sample_rate=1000.0,
        filter_settings={"enabled": False},
        remove_mean=False,
    )
    assert processed.shape == signal.shape
    assert abs(np.mean(processed)) < abs(np.mean(signal))
