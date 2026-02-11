import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication, QAbstractSpinBox, QGroupBox

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
    assert not hasattr(window, "nfft_spin")
    assert hasattr(window, "conditioning_filter_checkbox")
    assert hasattr(window, "conditioning_filter_type_combo")
    assert hasattr(window, "conditioning_remove_mean_checkbox")
    assert hasattr(window, "conditioning_note_label")
    assert hasattr(window, "conditioning_design_label")
    assert "6th-order Butterworth" in window.conditioning_design_label.text()
    assert window.conditioning_filter_type_combo.currentText() == "bandpass"
    assert window.segment_overlap_spin.value() == 0
    assert window.minimumWidth() >= 920
    assert not hasattr(window, "update_current_button")
    assert not hasattr(window, "update_all_button")
    assert not hasattr(window, "time_min_edit")
    assert not hasattr(window, "time_max_edit")
    assert not hasattr(window, "auto_limits_checkbox")
    assert not hasattr(window, "flight_combo")
    assert not hasattr(window, "channel_combo")
    assert hasattr(window, "selected_flight_value")
    assert hasattr(window, "selected_channel_value")
    assert hasattr(window, "selected_sr_value")

    group_titles = {group.title() for group in window.findChildren(QGroupBox)}
    assert "Segmentation Settings" in group_titles
    assert "Spectrogram Parameters" in group_titles
    assert "Signal Conditioning" in group_titles
    assert "Display Parameters" in group_titles

    seg_group = next(group for group in window.findChildren(QGroupBox) if group.title() == "Segmentation Settings")
    spec_group = next(group for group in window.findChildren(QGroupBox) if group.title() == "Spectrogram Parameters")
    cond_group = next(group for group in window.findChildren(QGroupBox) if group.title() == "Signal Conditioning")
    disp_group = next(group for group in window.findChildren(QGroupBox) if group.title() == "Display Parameters")

    seg_layout = seg_group.layout()
    assert seg_layout.itemAtPosition(0, 1).widget() is window.segment_duration_spin
    assert seg_layout.itemAtPosition(0, 3).widget() is window.segment_overlap_spin
    # Generate button should be in bottom action bar, not inside segmentation group.
    assert window.generate_button.parentWidget() is not seg_group

    spec_layout = spec_group.layout()
    assert spec_layout.itemAtPosition(0, 1).widget() is window.window_combo
    assert spec_layout.itemAtPosition(0, 3).widget() is window.spec_overlap_spin
    assert spec_layout.itemAtPosition(1, 1).widget() is window.df_spin
    assert spec_layout.itemAtPosition(1, 3).widget() is window.efficient_fft_checkbox
    assert spec_layout.itemAtPosition(2, 1).widget() is window.freq_min_spin
    assert spec_layout.itemAtPosition(2, 3).widget() is window.freq_max_spin

    cond_layout = cond_group.layout()
    assert cond_layout.itemAtPosition(0, 1).widget() is window.conditioning_filter_checkbox
    assert cond_layout.itemAtPosition(0, 3).widget() is window.conditioning_filter_type_combo
    assert cond_layout.itemAtPosition(1, 1).widget() is window.conditioning_low_cutoff_spin
    assert cond_layout.itemAtPosition(1, 3).widget() is window.conditioning_high_cutoff_spin
    assert cond_layout.itemAtPosition(2, 1).widget() is window.conditioning_remove_mean_checkbox

    disp_layout = disp_group.layout()
    assert disp_layout.itemAtPosition(0, 1).widget() is window.show_colorbar_checkbox
    assert disp_layout.itemAtPosition(0, 3).widget() is window.colormap_combo
    assert disp_layout.itemAtPosition(1, 3).widget() is window.snr_spin

    window.sample_rate = 1000.0
    window._refresh_actual_df_preview()
    assert "actual df" in window.efficient_fft_checkbox.text().lower()
    assert "nperseg" not in window.efficient_fft_checkbox.text().lower()

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
    assert hasattr(popup, "conditioning_info_label")
    assert "Signal Conditioning:" in popup.conditioning_info_label.text()

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

    window.colormap_combo.setCurrentText("plasma")
    window.snr_spin.setValue(55)
    window.show_colorbar_checkbox.setChecked(True)
    window._replot_current_from_cache()
    assert window.display_window.colorbar_item is not None

    window.show_colorbar_checkbox.setChecked(False)
    window._replot_current_from_cache()
    assert window.display_window.colorbar_item is None

    window.conditioning_remove_mean_checkbox.setChecked(True)
    app.processEvents()
    assert "Running Mean Removed (1.0s)" in window.conditioning_note_label.text()
    assert "Running Mean Removed (1.0s)" in window.display_window.conditioning_info_label.text()

    window.close()


def test_segment_count_preview_updates_when_segment_controls_change(app):
    window = SegmentedSpectrogramViewer()
    window.show()
    app.processEvents()

    window.signal_data = np.zeros(1000)
    window.sample_rate = 100.0
    window.segment_duration_spin.setEnabled(True)
    window.segment_overlap_spin.setEnabled(True)

    window.segment_duration_spin.setValue(2.0)  # 200 samples -> 5 segments
    app.processEvents()
    assert window.total_segments_label.text() == "Total Segments: 5"

    window.segment_duration_spin.setValue(4.0)  # 400 samples -> 3 segments
    app.processEvents()
    assert window.total_segments_label.text() == "Total Segments: 3"

    window.segment_overlap_spin.setValue(50)  # step=200 samples -> 4 segments
    app.processEvents()
    assert window.total_segments_label.text() == "Total Segments: 4"

    window.close()
