import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication, QDialog

from spectral_edge.gui import segmented_spectrogram_viewer as segmented_module


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


class _LoaderStub:
    def __init__(self, _path):
        self.path = _path
        self.closed = False

    def close(self):
        self.closed = True

    def load_channel_data(self, _flight_key, _channel_key, decimate_for_display=False):
        assert decimate_for_display is False
        return {
            "data_full": [0.0, 1.0, 0.5, -0.2],
            "sample_rate": 200.0,
        }


class _NavigatorStub:
    DialogCode = QDialog.DialogCode
    next_dialog_result = QDialog.DialogCode.Rejected
    next_selected_items = []
    last_kwargs = None

    def __init__(self, loader, parent=None, max_selected_channels=None, selection_limit_message=None):
        _ = (loader, parent)
        _NavigatorStub.last_kwargs = {
            "max_selected_channels": max_selected_channels,
            "selection_limit_message": selection_limit_message,
        }
        self.selected_items = list(_NavigatorStub.next_selected_items)

    def setModal(self, _flag):
        return None

    def exec(self):
        return _NavigatorStub.next_dialog_result


def test_segmented_viewer_uses_enhanced_navigator_single_select(monkeypatch, app):
    monkeypatch.setattr(segmented_module, "HDF5FlightDataLoader", _LoaderStub)
    monkeypatch.setattr(segmented_module, "FlightNavigator", _NavigatorStub)
    monkeypatch.setattr(segmented_module.os.path, "getsize", lambda _path: 1024 * 1024)

    _NavigatorStub.next_dialog_result = QDialog.DialogCode.Accepted
    _NavigatorStub.next_selected_items = [
        ("flight_alpha", "Accel_X", SimpleNamespace(units="G")),
    ]

    window = segmented_module.SegmentedSpectrogramViewer()
    window.show()
    app.processEvents()

    window._load_hdf5_file("dummy.hdf5")
    app.processEvents()

    assert _NavigatorStub.last_kwargs["max_selected_channels"] == 1
    assert "one channel at a time" in _NavigatorStub.last_kwargs["selection_limit_message"]
    assert window.flight_key == "flight_alpha"
    assert window.channel_name == "Accel_X"
    assert window.selected_flight_value.text() == "flight_alpha"
    assert window.selected_channel_value.text() == "Accel_X"
    assert "200.000 Hz" in window.selected_sr_value.text()
    assert window.generate_button.isEnabled()
    assert window.segment_duration_spin.isEnabled()
    assert window.segment_overlap_spin.isEnabled()

    window.close()


def test_segmented_viewer_navigator_cancel_leaves_channel_unloaded(monkeypatch, app):
    monkeypatch.setattr(segmented_module, "HDF5FlightDataLoader", _LoaderStub)
    monkeypatch.setattr(segmented_module, "FlightNavigator", _NavigatorStub)
    monkeypatch.setattr(segmented_module.os.path, "getsize", lambda _path: 1024 * 1024)

    _NavigatorStub.next_dialog_result = QDialog.DialogCode.Rejected
    _NavigatorStub.next_selected_items = []

    window = segmented_module.SegmentedSpectrogramViewer()
    window.show()
    app.processEvents()

    window._load_hdf5_file("dummy.hdf5")
    app.processEvents()

    assert window.signal_data is None
    assert window.sample_rate is None
    assert window.channel_name is None
    assert window.selected_flight_value.text() == "None selected"
    assert window.selected_channel_value.text() == "None selected"
    assert not window.generate_button.isEnabled()
    assert not window.segment_duration_spin.isEnabled()
    assert not window.segment_overlap_spin.isEnabled()

    window.close()
