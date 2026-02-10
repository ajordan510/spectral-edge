import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication, QAbstractSpinBox

from spectral_edge.gui.segmented_spectrogram_viewer import SegmentedSpectrogramViewer


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()
    if application is None:
        application = QApplication([])
    return application


def test_segmented_viewer_spinboxes_use_up_down_and_df_controls(app):
    window = SegmentedSpectrogramViewer()
    window.show()
    app.processEvents()

    spinboxes = window.findChildren(QAbstractSpinBox)
    assert spinboxes
    assert all(
        spin.buttonSymbols() == QAbstractSpinBox.ButtonSymbols.UpDownArrows
        for spin in spinboxes
    )

    assert hasattr(window, "df_spin")
    assert hasattr(window, "efficient_fft_checkbox")
    assert hasattr(window, "actual_df_label")
    assert not hasattr(window, "nfft_spin")

    window.close()


def test_segmented_viewer_uses_large_popup_with_nav_below_plot(app):
    window = SegmentedSpectrogramViewer()
    window.show()
    app.processEvents()

    window._ensure_display_window()
    app.processEvents()

    popup = window.display_window
    assert popup is not None
    assert popup.minimumWidth() >= 1400
    assert popup.minimumHeight() >= 900

    layout = popup.centralWidget().layout()
    assert layout.indexOf(popup.spectrogram_plot) < layout.indexOf(popup.nav_container)

    window.close()


def test_segmented_viewer_display_controls_replot_without_errors(app):
    window = SegmentedSpectrogramViewer()
    window.show()
    app.processEvents()

    window._ensure_display_window()
    window.sample_rate = 100.0
    window.channel_name = "Temperature"
    window.signal_data = np.random.randn(1000)
    window.segments = [(0, 1000)]
    window.current_segment_idx = 0

    freqs = np.linspace(0.0, 50.0, 51)
    times = np.linspace(0.0, 10.0, 100)
    sxx = np.abs(np.random.randn(51, 100)) + 1e-6
    window.spectrogram_cache.put(0, (freqs, times, sxx))

    window.auto_limits_checkbox.setChecked(False)
    app.processEvents()
    assert window.time_min_edit.isEnabled()

    window.time_min_edit.setText("0")
    window.time_max_edit.setText("8")
    window.freq_axis_min_edit.setText("1")
    window.freq_axis_max_edit.setText("40")

    window.colormap_combo.setCurrentText("plasma")
    window.snr_spin.setValue(55)
    window.show_colorbar_checkbox.setChecked(True)
    window._replot_current_from_cache()
    assert window.display_window.colorbar_item is not None

    window._apply_manual_axis_limits()

    window.show_colorbar_checkbox.setChecked(False)
    window._replot_current_from_cache()
    assert window.display_window.colorbar_item is None

    window.close()
