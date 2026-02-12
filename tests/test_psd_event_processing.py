import os
from types import SimpleNamespace

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from spectral_edge.gui import psd_window as psd_module
from spectral_edge.gui.event_manager import Event


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


def _build_window_with_channel():
    window = psd_module.PSDAnalysisWindow()
    sample_rate = 200.0
    time = np.arange(0.0, 10.0, 1.0 / sample_rate)
    signal = np.sin(2.0 * np.pi * 12.0 * time)

    window.channel_names = ["Accel_X"]
    window.channel_units = ["g"]
    window.channel_flight_names = ["flight_001"]
    window.channel_time_full = [time]
    window.channel_signal_full = [signal]
    window.channel_sample_rates = [sample_rate]
    window.sample_rate = sample_rate
    return window


def test_event_psd_uses_maximax_when_enabled(monkeypatch, app):
    window = _build_window_with_channel()
    window.maximax_checkbox.setChecked(True)
    window.efficient_fft_checkbox.setChecked(True)
    monkeypatch.setattr(window, "_update_plot_with_events", lambda: None)

    maximax_calls = []
    monkeypatch.setattr(
        psd_module,
        "calculate_psd_maximax",
        lambda data, sr, **kwargs: (
            maximax_calls.append(kwargs) or np.array([1.0, 2.0]),
            np.array([0.1, 0.2]),
        ),
    )
    monkeypatch.setattr(
        psd_module,
        "calculate_psd_welch",
        lambda *_args, **_kwargs: pytest.fail("Welch should not be used when maximax is enabled"),
    )

    window._calculate_event_psds(events=[Event("E1", 1.0, 3.0)])

    assert len(maximax_calls) == 1
    assert maximax_calls[0]["use_efficient_fft"] is True
    window.close()


def test_event_psd_uses_welch_when_maximax_disabled(monkeypatch, app):
    window = _build_window_with_channel()
    window.maximax_checkbox.setChecked(False)
    window.efficient_fft_checkbox.setChecked(True)
    monkeypatch.setattr(window, "_update_plot_with_events", lambda: None)

    welch_calls = []
    monkeypatch.setattr(
        psd_module,
        "calculate_psd_welch",
        lambda data, sr, **kwargs: (
            welch_calls.append(kwargs) or np.array([1.0, 2.0]),
            np.array([0.1, 0.2]),
        ),
    )
    monkeypatch.setattr(
        psd_module,
        "calculate_psd_maximax",
        lambda *_args, **_kwargs: pytest.fail("Maximax should not be used when disabled"),
    )

    window._calculate_event_psds(events=[Event("E1", 1.0, 3.0)])

    assert len(welch_calls) == 1
    assert welch_calls[0]["use_efficient_fft"] is True
    window.close()


def test_calculate_psd_prefers_enabled_events_from_manager(monkeypatch, app):
    window = _build_window_with_channel()
    event = Event("Event A", 1.0, 2.5)
    window.event_manager = SimpleNamespace(events=[event], get_enabled_events=lambda: [event])

    captured = {}
    monkeypatch.setattr(window, "_calculate_event_psds", lambda events=None: captured.setdefault("events", events))

    window._calculate_psd()

    assert captured["events"] == [event]
    window.close()


def test_calculate_psd_blocks_when_event_manager_has_no_enabled_events(monkeypatch, app):
    window = _build_window_with_channel()
    event = Event("Event A", 1.0, 2.5)
    window.event_manager = SimpleNamespace(events=[event], get_enabled_events=lambda: [])

    warnings = []
    monkeypatch.setattr(psd_module, "show_warning", lambda *_args: warnings.append(_args[1]))
    monkeypatch.setattr(window, "_compute_channel_psd", lambda *_args, **_kwargs: pytest.fail("Should not compute"))

    window._calculate_psd()

    assert "No Events Enabled" in warnings
    window.close()


def test_calculate_psd_full_path_forwards_efficient_fft(monkeypatch, app):
    window = _build_window_with_channel()
    window.efficient_fft_checkbox.setChecked(True)
    window.maximax_checkbox.setChecked(False)
    window.events = []
    monkeypatch.setattr(window, "_update_plot", lambda: None)

    welch_calls = []
    monkeypatch.setattr(
        psd_module,
        "calculate_psd_welch",
        lambda data, sr, **kwargs: (
            welch_calls.append(kwargs) or np.array([1.0, 2.0]),
            np.array([0.1, 0.2]),
        ),
    )

    window._calculate_psd()

    assert len(welch_calls) == 1
    assert welch_calls[0]["use_efficient_fft"] is True
    window.close()
