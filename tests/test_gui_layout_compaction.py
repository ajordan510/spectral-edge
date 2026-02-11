import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication, QAbstractSpinBox, QComboBox

from spectral_edge.gui.file_converter_window import FileConverterWindow
from spectral_edge.gui.psd_window import PSDAnalysisWindow
from spectral_edge.gui.spectrogram_window import SpectrogramWindow


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


def test_spectrogram_spinboxes_use_up_down_arrows(app):
    time_data = np.linspace(0.0, 1.0, 200, endpoint=False)
    signal = np.sin(2.0 * np.pi * 10.0 * time_data)
    channels = [("Ch1", signal, "g", "")]

    window = SpectrogramWindow(
        time_data=time_data,
        channels_data=channels,
        sample_rates=[200.0],
    )
    window.show()
    app.processEvents()

    assert window.minimumWidth() >= 1680
    spinboxes = window.findChildren(QAbstractSpinBox)
    assert spinboxes
    assert all(
        spin.buttonSymbols() == QAbstractSpinBox.ButtonSymbols.UpDownArrows
        for spin in spinboxes
    )

    window.close()


def test_psd_parameter_controls_are_compact(app):
    window = PSDAnalysisWindow()
    window.show()
    app.processEvents()

    compact_controls = [
        window.freq_min_spin,
        window.freq_max_spin,
        window.preset_combo,
        window.window_combo,
        window.df_spin,
        window.overlap_spin,
        window.maximax_window_spin,
        window.maximax_overlap_spin,
    ]

    assert window.preset_combo.sizeAdjustPolicy() == (
        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
    )
    assert window.preset_combo.minimumContentsLength() == 18
    assert all(control.maximumWidth() <= 220 for control in compact_controls)

    window.close()


def _minimum_height_for_visible_rows(table, visible_rows=5):
    header_height = max(table.horizontalHeader().height(), 28)
    row_height = max(table.verticalHeader().defaultSectionSize(), 24)
    frame_height = table.frameWidth() * 2
    return header_height + (visible_rows * row_height) + frame_height + 2


def test_file_converter_table_height_shows_five_rows(app):
    window = FileConverterWindow()
    window.show()
    app.processEvents()

    assert window.minimumHeight() >= 900

    dxd_required_height = _minimum_height_for_visible_rows(window.slices_table, visible_rows=5)
    hdf5_required_height = _minimum_height_for_visible_rows(window.hdf5_slices_table, visible_rows=5)

    assert window.slices_table.minimumHeight() >= dxd_required_height
    assert window.hdf5_slices_table.minimumHeight() >= hdf5_required_height

    window.close()
