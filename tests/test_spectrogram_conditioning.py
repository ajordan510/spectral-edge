import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication, QCheckBox

from spectral_edge.gui import psd_window as psd_module
from spectral_edge.gui.spectrogram_window import SpectrogramWindow


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


def test_spectrogram_window_conditioning_defaults_and_note(app):
    time_data = np.linspace(0.0, 10.0, 2000, endpoint=False)
    signal = 2.0 + np.sin(2.0 * np.pi * 12.0 * time_data)
    channels = [("Ch1", signal, "g", "flight_001")]

    window = SpectrogramWindow(
        time_data=time_data,
        channels_data=channels,
        sample_rates=[200.0],
        filter_settings={
            "enabled": True,
            "filter_type": "highpass",
            "cutoff_low": 5.0,
            "cutoff_high": 80.0,
        },
        remove_mean=True,
        mean_window_seconds=1.0,
    )
    window.show()
    app.processEvents()

    assert window.minimumWidth() >= 1680
    assert window.conditioning_filter_checkbox.isChecked()
    assert window.conditioning_filter_type_combo.currentText() == "Highpass"
    assert window.conditioning_remove_mean_checkbox.isChecked()
    note_text = window.conditioning_note_label.text()
    assert "Signal Conditioning:" in note_text
    assert "Running Mean Removed (1.0s)" in note_text
    assert "Filter: highpass (5.0 Hz)" in note_text

    window.close()


def test_psd_open_spectrogram_passes_conditioning(monkeypatch, app):
    captured = {}

    class _FakeSpectrogramWindow:
        def __init__(self, *args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs

        def show(self):
            pass

        def raise_(self):
            pass

        def activateWindow(self):
            pass

    monkeypatch.setattr(psd_module, "SpectrogramWindow", _FakeSpectrogramWindow)

    window = psd_module.PSDAnalysisWindow()
    signal = np.sin(np.linspace(0.0, 40.0 * np.pi, 4000))
    time_data = np.arange(signal.size) / 200.0

    select_checkbox = QCheckBox()
    select_checkbox.setChecked(True)
    window.channel_checkboxes = [select_checkbox]
    window.channel_names = ["Accel_X"]
    window.channel_units = ["g"]
    window.channel_flight_names = ["flight_001"]
    window.channel_signal_full = [signal]
    window.channel_time_full = [time_data]
    window.channel_sample_rates = [200.0]
    window.sample_rate = 200.0

    window.enable_filter_checkbox.setChecked(True)
    window.filter_type_combo.setCurrentText("Bandpass")
    window.low_cutoff_spin.setValue(8.0)
    window.high_cutoff_spin.setValue(60.0)
    window.remove_mean_checkbox.setChecked(True)

    window._open_spectrogram()
    app.processEvents()

    kwargs = captured["kwargs"]
    assert kwargs["remove_mean"] is True
    assert kwargs["mean_window_seconds"] == 1.0
    assert kwargs["filter_settings"]["enabled"] is True
    assert kwargs["filter_settings"]["filter_type"] == "bandpass"
    assert kwargs["filter_settings"]["cutoff_low"] == pytest.approx(8.0)
    assert kwargs["filter_settings"]["cutoff_high"] == pytest.approx(60.0)

    window.close()


def test_psd_open_spectrogram_reused_window_syncs_conditioning_defaults(monkeypatch, app):
    captured = {"create_kwargs": [], "update_calls": []}

    class _FakeSpectrogramWindow:
        def __init__(self, *args, **kwargs):
            captured["create_kwargs"].append(kwargs)

        def update_conditioning_defaults(self, filter_settings, remove_mean, mean_window_seconds, recalculate=True):
            captured["update_calls"].append(
                {
                    "filter_settings": dict(filter_settings),
                    "remove_mean": remove_mean,
                    "mean_window_seconds": mean_window_seconds,
                    "recalculate": recalculate,
                }
            )

        def show(self):
            pass

        def raise_(self):
            pass

        def activateWindow(self):
            pass

    monkeypatch.setattr(psd_module, "SpectrogramWindow", _FakeSpectrogramWindow)

    window = psd_module.PSDAnalysisWindow()
    signal = np.sin(np.linspace(0.0, 40.0 * np.pi, 4000))
    time_data = np.arange(signal.size) / 200.0

    select_checkbox = QCheckBox()
    select_checkbox.setChecked(True)
    window.channel_checkboxes = [select_checkbox]
    window.channel_names = ["Accel_X"]
    window.channel_units = ["g"]
    window.channel_flight_names = ["flight_001"]
    window.channel_signal_full = [signal]
    window.channel_time_full = [time_data]
    window.channel_sample_rates = [200.0]
    window.sample_rate = 200.0

    window.enable_filter_checkbox.setChecked(False)
    window.remove_mean_checkbox.setChecked(False)
    window._open_spectrogram()
    app.processEvents()

    window.enable_filter_checkbox.setChecked(True)
    window.filter_type_combo.setCurrentText("Lowpass")
    window.high_cutoff_spin.setValue(90.0)
    window.remove_mean_checkbox.setChecked(True)
    window._open_spectrogram()
    app.processEvents()

    assert len(captured["create_kwargs"]) == 1
    assert len(captured["update_calls"]) == 1
    update_call = captured["update_calls"][0]
    assert update_call["filter_settings"]["enabled"] is True
    assert update_call["filter_settings"]["filter_type"] == "lowpass"
    assert update_call["filter_settings"]["cutoff_high"] == pytest.approx(90.0)
    assert update_call["remove_mean"] is True
    assert update_call["mean_window_seconds"] == 1.0
    assert update_call["recalculate"] is True

    window.close()
