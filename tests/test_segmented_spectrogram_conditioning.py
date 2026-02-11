import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication

from spectral_edge.gui import segmented_spectrogram_viewer as segmented_module


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


class _DummySignal:
    def connect(self, _callback):
        return None


def test_segmented_viewer_applies_conditioning_before_generation(monkeypatch, app):
    captured = {}

    class _FakeGenerator:
        def __init__(self, signal_data, sample_rate, nperseg, noverlap, window):
            captured["signal_data"] = np.asarray(signal_data, dtype=np.float64)
            captured["sample_rate"] = sample_rate
            captured["nperseg"] = nperseg
            captured["noverlap"] = noverlap
            captured["window"] = window
            self.segment_idx = 0
            self.generation_complete = _DummySignal()
            self.generation_error = _DummySignal()

        def start(self):
            return None

    monkeypatch.setattr(segmented_module, "SpectrogramGenerator", _FakeGenerator)

    window = segmented_module.SegmentedSpectrogramViewer()
    window.show()
    app.processEvents()

    signal_data = 5.0 + np.sin(np.linspace(0.0, 20.0 * np.pi, 4000))
    window.signal_data = signal_data
    window.sample_rate = 200.0
    window.channel_name = "Test_Channel"
    window.segments = [(0, signal_data.size)]
    window.current_segment_idx = 0

    window.conditioning_filter_checkbox.setChecked(False)
    window.conditioning_remove_mean_checkbox.setChecked(True)
    app.processEvents()

    filter_settings = window._build_conditioning_filter_settings()
    assert filter_settings["filter_order"] == 6

    window._display_segment(0)
    app.processEvents()

    assert "signal_data" in captured
    conditioned = captured["signal_data"]
    assert conditioned.shape == signal_data.shape
    assert not np.allclose(conditioned, signal_data)
    assert abs(np.mean(conditioned)) < abs(np.mean(signal_data))

    window.close()
