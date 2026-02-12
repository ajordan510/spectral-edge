import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from spectral_edge.gui.psd_window import PSDAnalysisWindow
from spectral_edge.utils.signal_conditioning import apply_robust_filtering


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


@pytest.fixture(autouse=True)
def _disable_psd_context_menu_styler(monkeypatch):
    monkeypatch.setattr(
        "spectral_edge.gui.psd_window.apply_context_menu_style",
        lambda *_args, **_kwargs: None,
    )


def _seed_window_with_channel(window: PSDAnalysisWindow, sample_rate: float = 1000.0):
    time_full = np.arange(0.0, 5.0, 1.0 / sample_rate)
    signal_full = 2.0 + np.sin(2.0 * np.pi * 25.0 * time_full)
    decimate = 10
    time_display = time_full[::decimate]
    signal_display = signal_full[::decimate]

    window.channel_names = ["Accel_X"]
    window.channel_units = ["g"]
    window.channel_flight_names = ["flight_001"]
    window.channel_sample_rates = [sample_rate]
    window.sample_rate = sample_rate

    window.channel_time_full = [time_full]
    window.channel_signal_full = [signal_full]
    window.channel_time_display = [time_display]
    window.channel_signal_display = [signal_display]

    window.time_data_full = time_full
    window.signal_data_full = signal_full.reshape(-1, 1)
    window.time_data_display = time_display
    window.signal_data_display = signal_display.reshape(-1, 1)

    window._create_channel_checkboxes()
    window._update_filter_info_display()
    window._build_time_history_cache()
    window._plot_time_history()


def test_filter_info_display_updates_with_sample_rate(app):
    window = PSDAnalysisWindow()
    window.sample_rate = 1000.0
    window._update_filter_info_display()
    assert "1.00 Hz" in window.baseline_highpass_label.text()
    assert "450.00 Hz" in window.baseline_lowpass_label.text()
    assert "Nyquist: 500.00 Hz" in window.baseline_rate_label.text()
    window.close()


def test_time_history_cache_supports_four_states_and_title_updates(app):
    window = PSDAnalysisWindow()
    _seed_window_with_channel(window, sample_rate=1000.0)

    cache = window.time_history_cache[0]
    assert "signal_decimated_raw" in cache
    assert "signal_decimated_filtered" in cache
    assert "signal_full_raw" in cache
    assert "signal_full_filtered" in cache or cache["full_filter_deferred"] is True

    assert window.time_resolution_mode == "decimated"
    assert window.time_filtering_mode == "filtered"
    assert "Decimated, Filtered" in window.time_plot_widget.plotItem.titleLabel.text

    window.full_resolution_radio.setChecked(True)
    window.raw_radio.setChecked(True)
    app.processEvents()

    assert window.time_resolution_mode == "full"
    assert window.time_filtering_mode == "raw"
    assert "Full Resolution, Raw" in window.time_plot_widget.plotItem.titleLabel.text
    assert "Showing" in window.time_points_label.text()
    window.close()


def test_compute_channel_psd_applies_robust_clamping(monkeypatch, app):
    window = PSDAnalysisWindow()
    _seed_window_with_channel(window, sample_rate=1000.0)
    window.maximax_checkbox.setChecked(False)
    window.enable_filter_checkbox.setChecked(True)
    window.low_cutoff_spin.setValue(0.5)
    window.high_cutoff_spin.setValue(600.0)

    monkeypatch.setattr(
        "spectral_edge.gui.psd_window.calculate_psd_welch",
        lambda data, sr, **kwargs: (np.array([1.0, 2.0]), np.array([0.1, 0.2])),
    )

    _freq, _psd, hp, lp, messages = window._compute_channel_psd(
        window.channel_signal_full[0],
        window.sample_rate,
    )
    assert hp == pytest.approx(1.0)
    assert lp == pytest.approx(450.0)
    assert any("Highpass of 0.5 Hz" in msg for msg in messages)
    assert any("Lowpass of 600 Hz" in msg for msg in messages)
    window.close()


def test_statistics_filter_settings_expose_user_override_keys(app):
    window = PSDAnalysisWindow()
    window.enable_filter_checkbox.setChecked(True)
    window.low_cutoff_spin.setValue(8.0)
    window.high_cutoff_spin.setValue(60.0)

    settings = window._get_statistics_filter_settings()
    assert settings["enabled"] is True
    assert settings["user_highpass_hz"] == pytest.approx(8.0)
    assert settings["user_lowpass_hz"] == pytest.approx(60.0)
    window.close()


def test_decimated_filtered_is_derived_from_full_filtered_signal(app):
    window = PSDAnalysisWindow()
    sample_rate = 1000.0
    time_full = np.arange(0.0, 5.0, 1.0 / sample_rate)
    signal_full = (
        np.sin(2.0 * np.pi * 5.0 * time_full)
        + 0.8 * np.sin(2.0 * np.pi * 180.0 * time_full)
        + 0.1 * time_full
    )
    decimate = 10
    time_display = time_full[::decimate]
    signal_display = signal_full[::decimate]

    window.channel_names = ["Accel_X"]
    window.channel_units = ["g"]
    window.channel_flight_names = ["flight_001"]
    window.channel_sample_rates = [sample_rate]
    window.sample_rate = sample_rate
    window.channel_time_full = [time_full]
    window.channel_signal_full = [signal_full]
    window.channel_time_display = [time_display]
    window.channel_signal_display = [signal_display]
    window.time_data_full = time_full
    window.signal_data_full = signal_full.reshape(-1, 1)
    window.time_data_display = time_display
    window.signal_data_display = signal_display.reshape(-1, 1)
    window._create_channel_checkboxes()

    window.enable_filter_checkbox.setChecked(True)
    window.low_cutoff_spin.setValue(1.0)
    window.high_cutoff_spin.setValue(20.0)
    window._build_time_history_cache()

    cache = window.time_history_cache[0]
    assert cache["signal_full_filtered"] is not None
    assert cache["signal_decimated_filtered"] is not None
    assert "display_indices" in cache

    expected_decimated = cache["signal_full_filtered"][cache["display_indices"]]
    assert np.allclose(cache["signal_decimated_filtered"], expected_decimated, rtol=1e-9, atol=1e-9)

    decimated_direct, _hp, _lp, _msgs = apply_robust_filtering(
        cache["signal_decimated_raw"],
        cache["sample_rate"],
        user_highpass=window.low_cutoff_spin.value(),
        user_lowpass=window.high_cutoff_spin.value(),
    )
    assert not np.allclose(cache["signal_decimated_filtered"], decimated_direct, rtol=1e-4, atol=1e-4)
    window.close()


def test_psd_defaults_and_buttons_render_with_expected_labels_and_icons(app):
    from PyQt6.QtWidgets import QLabel

    window = PSDAnalysisWindow()
    assert window.df_spin.value() == pytest.approx(5.0)
    assert window.actual_df_label.text() == "(df = 5.0 Hz)"
    assert any(label.text() == "\u0394f (Hz):" for label in window.findChildren(QLabel))

    assert not window.statistics_button.icon().isNull()
    assert not window.report_button.icon().isNull()
    assert window.statistics_button.text() == "Statistics Analysis"
    assert window.report_button.text() == "Generate Report"

    stylesheet = window.styleSheet()
    assert "QRadioButton" in stylesheet
    assert "color: #ffffff;" in stylesheet
    assert "QScrollBar:vertical" in stylesheet
    assert "background: #111827;" in stylesheet
    window.close()
