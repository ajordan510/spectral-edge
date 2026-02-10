import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication, QFileDialog

from spectral_edge.gui.file_converter_window import FileConverterWindow


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


def test_marvin_mode_visible_and_toggles_sections(app):
    window = FileConverterWindow()
    window.show()
    app.processEvents()

    assert hasattr(window, "hdf5_to_marvin_mode_radio")

    window.hdf5_to_marvin_mode_radio.setChecked(True)
    app.processEvents()

    assert not window.splitting_group.isVisible()
    assert not window.channel_group.isVisible()
    assert not window.hdf5_split_group.isVisible()
    assert not window.format_combo.isEnabled()
    assert "MATLAB files" in window.output_path_edit.placeholderText()

    window.close()


def test_marvin_mode_output_browse_uses_directory_dialog(app, monkeypatch, tmp_path):
    window = FileConverterWindow()
    window.show()
    app.processEvents()

    selected_dir = str(tmp_path / "marvin_out")

    def fake_get_existing_directory(*args, **kwargs):
        return selected_dir

    def fake_get_save_file_name(*args, **kwargs):
        raise AssertionError("Save-file dialog should not be used for HDF5->MARVIN mode")

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(fake_get_existing_directory))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(fake_get_save_file_name))

    window.hdf5_to_marvin_mode_radio.setChecked(True)
    app.processEvents()
    window._on_browse_output_clicked()

    assert window.output_path_edit.text() == selected_dir
    window.close()


def test_marvin_mode_dispatches_to_marvin_conversion_path(app):
    window = FileConverterWindow()
    window.show()
    app.processEvents()

    called = {"marvin": False}

    def fake_start():
        called["marvin"] = True

    window._start_hdf5_to_marvin_conversion = fake_start
    window.hdf5_to_marvin_mode_radio.setChecked(True)
    window.input_file_path = "input.hdf5"
    window.output_path_edit.setText("out_dir")

    window._on_convert_clicked()

    assert called["marvin"] is True
    window.close()
