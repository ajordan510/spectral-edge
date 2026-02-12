import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication, QWidget
import matplotlib.pyplot as plt

from spectral_edge.batch.statistics import compute_statistics, plot_pdf
from spectral_edge.gui import psd_window as psd_module
from spectral_edge.gui.statistics_window import create_statistics_window
from spectral_edge.utils.signal_conditioning import build_processing_note


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


@pytest.fixture(autouse=True)
def _disable_psd_context_menu_styler(monkeypatch):
    monkeypatch.setattr(psd_module, "apply_context_menu_style", lambda *_args, **_kwargs: None)


class _StatsConfig:
    pdf_bins = 50
    running_window_seconds = 1.0
    max_plot_points = 5000
    show_mean = True
    show_std = True
    show_skewness = True
    show_kurtosis = True
    show_normal = False
    show_rayleigh = True
    show_uniform = False


def test_build_processing_note_uses_standard_running_mean_wording():
    note_on = build_processing_note(
        filter_settings={"enabled": True, "filter_type": "lowpass", "cutoff_high": 200},
        remove_mean=True,
        mean_window_seconds=1.0,
    )
    note_off = build_processing_note(
        filter_settings={"enabled": False},
        remove_mean=False,
        mean_window_seconds=1.0,
    )

    assert "Running Mean Removed (1.0s)" in note_on
    assert note_off.endswith("Running Mean Not Removed")


def test_batch_rayleigh_overlay_is_drawn_with_finite_data():
    rng = np.random.default_rng(42)
    signal = rng.normal(loc=0.0, scale=1.0, size=8000)
    stats_dict = compute_statistics(signal, 100.0, _StatsConfig())
    fig, ax = plot_pdf(stats_dict["pdf"], _StatsConfig())
    try:
        lines = {line.get_label(): line for line in ax.get_lines()}
        assert "Rayleigh" in lines
        rayleigh_line = lines["Rayleigh"]
        assert np.all(np.isfinite(rayleigh_line.get_xdata()))
        assert np.all(np.isfinite(rayleigh_line.get_ydata()))
        assert np.all(rayleigh_line.get_xdata() >= 0.0)
    finally:
        plt.close(fig)


def test_statistics_window_shows_conditioning_note_and_dark_channel_panel(app):
    signal = np.sin(np.linspace(0, 40.0 * np.pi, 4000))
    window = create_statistics_window(
        channels_data=[("Accel_X", signal, "g", "flight_001")],
        sample_rate=100.0,
        processing_note="Filter: lowpass (200 Hz) | Running Mean Removed (1.0s)",
        processing_flags={"filter_enabled": True, "running_mean_removed": True},
    )
    window.show()
    app.processEvents()

    assert "Signal Conditioning:" in window.conditioning_note_label.text()
    channel_widget = window.findChild(QWidget, "channelWidget")
    assert channel_widget is not None
    assert "QWidget#channelWidget" in window.styleSheet()
    window.close()


def test_psd_statistics_window_receives_conditioned_signal(monkeypatch, app):
    captured = {}

    class _FakeStatisticsWindow:
        def __init__(self):
            self._visible = False

        def show(self):
            self._visible = True

        def isVisible(self):
            return self._visible

        def raise_(self):
            pass

        def activateWindow(self):
            pass

    def _fake_factory(channels_data, sample_rate, parent=None, processing_note="", processing_flags=None):
        captured["channels_data"] = channels_data
        captured["sample_rate"] = sample_rate
        captured["processing_note"] = processing_note
        captured["processing_flags"] = processing_flags or {}
        return _FakeStatisticsWindow()

    monkeypatch.setattr(psd_module, "create_statistics_window", _fake_factory)

    window = psd_module.PSDAnalysisWindow()
    signal = 5.0 + np.sin(np.linspace(0.0, 20.0 * np.pi, 5000))
    time = np.arange(signal.size) / 100.0
    window.channel_names = ["Accel_X"]
    window.channel_units = ["g"]
    window.channel_flight_names = ["flight_001"]
    window.channel_signal_full = [signal]
    window.channel_time_full = [time]
    window.channel_sample_rates = [100.0]
    window.sample_rate = 100.0
    window.enable_filter_checkbox.setChecked(False)

    window._open_statistics()
    app.processEvents()

    conditioned_signal = captured["channels_data"][0][1]
    assert conditioned_signal.shape == signal.shape
    assert not np.allclose(conditioned_signal, signal)
    assert abs(np.mean(conditioned_signal)) < abs(np.mean(signal))
    assert "Running Mean Not Removed" in captured["processing_note"]
    assert captured["processing_flags"]["running_mean_removed"] is False
    window.close()
