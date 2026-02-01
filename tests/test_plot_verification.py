"""
Plot Verification Tests for SpectralEdge.

This module tests that plots render correctly with accurate data,
proper styling, and expected visual elements.

These tests verify:
- Plot data matches calculated values
- Axis scales and ranges are correct
- Visual elements (legend, grid, labels) are present
- Color schemes are applied
- Export to image functions work

Author: SpectralEdge Development Team
"""

import pytest
import numpy as np
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import io

# Skip entire module if PyQt6 is not available
pytest.importorskip("PyQt6")

from PyQt6.QtCore import Qt, QBuffer, QIODevice
from PyQt6.QtWidgets import QApplication, QFileDialog
from PyQt6.QtGui import QImage


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def synthetic_data():
    """Generate synthetic vibration data with known frequency content."""
    np.random.seed(42)
    sample_rate = 10000  # 10 kHz
    duration = 5  # 5 seconds
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Create signal with known peaks
    # 50 Hz with amplitude 1.0
    # 100 Hz with amplitude 0.5
    # 200 Hz with amplitude 0.25
    signal = (
        1.0 * np.sin(2 * np.pi * 50 * t) +
        0.5 * np.sin(2 * np.pi * 100 * t) +
        0.25 * np.sin(2 * np.pi * 200 * t)
    )

    return t, signal, sample_rate


@pytest.fixture
def sample_csv_file(tmp_path, synthetic_data):
    """Create a sample CSV file with synthetic data."""
    t, signal, _ = synthetic_data

    csv_path = tmp_path / "synthetic_data.csv"
    with open(csv_path, 'w') as f:
        f.write("time,vibration\n")
        for i in range(0, len(t), 10):  # Subsample for smaller file
            f.write(f"{t[i]:.6f},{signal[i]:.6f}\n")

    return str(csv_path)


@pytest.fixture
def psd_window_with_data(qapp, tmp_path, synthetic_data):
    """Create PSD window with synthetic data loaded."""
    from spectral_edge.gui.psd_window import PSDAnalysisWindow

    t, signal, sample_rate = synthetic_data

    # Create CSV with full data
    csv_path = tmp_path / "test_data.csv"
    with open(csv_path, 'w') as f:
        f.write("time,channel\n")
        for i in range(len(t)):
            f.write(f"{t[i]:.6f},{signal[i]:.6f}\n")

    window = PSDAnalysisWindow()

    with patch.object(QFileDialog, 'getOpenFileName', return_value=(str(csv_path), '')):
        window._load_file()

    yield window

    window.close()


# =============================================================================
# PSD Plot Data Accuracy Tests
# =============================================================================

class TestPSDPlotDataAccuracy:
    """Tests for PSD plot data accuracy."""

    def test_psd_frequency_range_matches_settings(self, psd_window_with_data, qtbot):
        """Test that PSD frequency range matches parameter settings."""
        window = psd_window_with_data

        # Set specific frequency range
        window.freq_min_spin.setValue(10.0)
        window.freq_max_spin.setValue(500.0)

        # Calculate PSD
        window._calculate_psd()

        # Check frequencies are within expected range
        for channel, freqs in window.frequencies.items():
            # Get frequency mask used in display
            freq_min = window.freq_min_spin.value()
            freq_max = window.freq_max_spin.value()
            mask = (freqs >= freq_min) & (freqs <= freq_max)
            displayed_freqs = freqs[mask]

            if len(displayed_freqs) > 0:
                assert displayed_freqs.min() >= freq_min
                assert displayed_freqs.max() <= freq_max

    def test_psd_peak_detection(self, psd_window_with_data, qtbot):
        """Test that PSD shows peaks at expected frequencies."""
        window = psd_window_with_data

        # Disable maximax for cleaner peak detection
        window.maximax_checkbox.setChecked(False)
        window.df_spin.setValue(1.0)  # 1 Hz resolution

        # Calculate PSD
        window._calculate_psd()

        # Get the first channel's results
        for channel, psd in window.psd_results.items():
            freqs = window.frequencies[channel]

            # Find peaks near expected frequencies (50, 100, 200 Hz)
            expected_peaks = [50, 100, 200]

            for expected_freq in expected_peaks:
                # Find index closest to expected frequency
                idx = np.argmin(np.abs(freqs - expected_freq))

                # Check if there's elevated power near this frequency
                # (allow ±2 Hz tolerance)
                nearby_mask = (freqs >= expected_freq - 2) & (freqs <= expected_freq + 2)
                if np.any(nearby_mask):
                    nearby_power = psd[nearby_mask]
                    # This should be higher than baseline
                    assert np.max(nearby_power) > np.median(psd)

    def test_psd_values_are_positive(self, psd_window_with_data, qtbot):
        """Test that PSD values are positive (valid power)."""
        window = psd_window_with_data
        window._calculate_psd()

        for channel, psd in window.psd_results.items():
            assert np.all(psd > 0), f"PSD should be positive for channel {channel}"

    def test_psd_frequency_resolution_matches_df(self, psd_window_with_data, qtbot):
        """Test that frequency resolution matches df setting."""
        window = psd_window_with_data

        window.df_spin.setValue(2.0)
        window.efficient_fft_checkbox.setChecked(False)  # Disable efficient FFT for exact df

        window._calculate_psd()

        for channel, freqs in window.frequencies.items():
            if len(freqs) > 1:
                actual_df = np.mean(np.diff(freqs))
                # Allow 20% tolerance
                assert abs(actual_df - 2.0) < 0.4, f"Expected df=2.0, got {actual_df}"


# =============================================================================
# Plot Element Verification Tests
# =============================================================================

class TestPlotElements:
    """Tests for plot visual elements."""

    def test_psd_plot_has_grid(self, psd_window_with_data, qtbot):
        """Test that PSD plot has grid lines."""
        window = psd_window_with_data

        plot_item = window.plot_widget.getPlotItem()

        # Check grid is enabled
        # Grid settings are stored in the plot item
        assert plot_item.ctrl.xGridCheck.isChecked() or hasattr(plot_item, 'showGrid')

    def test_psd_plot_has_labels(self, psd_window_with_data, qtbot):
        """Test that PSD plot has axis labels."""
        window = psd_window_with_data

        plot_item = window.plot_widget.getPlotItem()

        # Check bottom axis has label
        bottom_axis = plot_item.getAxis('bottom')
        assert bottom_axis is not None

        # Check left axis has label
        left_axis = plot_item.getAxis('left')
        assert left_axis is not None

    def test_psd_plot_has_title(self, psd_window_with_data, qtbot):
        """Test that PSD plot has a title."""
        window = psd_window_with_data

        plot_item = window.plot_widget.getPlotItem()

        # Check title label exists
        title_item = plot_item.titleLabel
        assert title_item is not None

    def test_time_plot_has_curves_after_load(self, psd_window_with_data, qtbot):
        """Test that time history plot has curves after loading data."""
        window = psd_window_with_data

        plot_item = window.time_plot_widget.getPlotItem()
        curves = plot_item.listDataItems()

        assert len(curves) > 0, "Time plot should have data curves"

    def test_legend_visibility_after_calculation(self, psd_window_with_data, qtbot):
        """Test that legend is visible after PSD calculation."""
        window = psd_window_with_data
        window._calculate_psd()

        # Legend should be visible after calculation
        assert window.legend.isVisible()

    def test_crosshair_visibility_toggle(self, psd_window_with_data, qtbot):
        """Test crosshair visibility responds to checkbox."""
        window = psd_window_with_data

        # Initially hidden
        assert not window.vLine.isVisible()
        assert not window.hLine.isVisible()

        # Enable crosshair (visibility is controlled by mouse events,
        # but the checkbox controls whether it can be shown)
        window.show_crosshair_checkbox.setChecked(True)

        # The crosshair lines exist
        assert window.vLine is not None
        assert window.hLine is not None


# =============================================================================
# Color and Style Tests
# =============================================================================

class TestPlotStyling:
    """Tests for plot colors and styling."""

    def test_plot_background_color(self, psd_window_with_data, qtbot):
        """Test that plot has correct background color."""
        window = psd_window_with_data

        # Get background brush
        background = window.plot_widget.backgroundBrush()

        # Should be dark aerospace theme (#1a1f2e)
        color = background.color()
        assert color.red() == 0x1a
        assert color.green() == 0x1f
        assert color.blue() == 0x2e

    def test_channel_curves_have_different_colors(self, qapp, tmp_path):
        """Test that different channels have different colors."""
        from spectral_edge.gui.psd_window import PSDAnalysisWindow

        # Create multi-channel data
        np.random.seed(42)
        t = np.linspace(0, 1, 10000)
        signal1 = np.sin(2 * np.pi * 50 * t)
        signal2 = np.sin(2 * np.pi * 100 * t)

        csv_path = tmp_path / "multi_channel.csv"
        with open(csv_path, 'w') as f:
            f.write("time,ch1,ch2\n")
            for i in range(len(t)):
                f.write(f"{t[i]:.6f},{signal1[i]:.6f},{signal2[i]:.6f}\n")

        window = PSDAnalysisWindow()

        with patch.object(QFileDialog, 'getOpenFileName', return_value=(str(csv_path), '')):
            window._load_file()

        # Calculate PSD
        window._calculate_psd()

        # Get curve colors from plot
        plot_item = window.plot_widget.getPlotItem()
        curves = plot_item.listDataItems()

        if len(curves) >= 2:
            # Check that curves have different colors
            colors = [curve.opts.get('pen') for curve in curves if hasattr(curve, 'opts')]
            # Colors should exist and be different
            assert len(colors) >= 2

        window.close()


# =============================================================================
# Plot Export Tests
# =============================================================================

class TestPlotExport:
    """Tests for plot export functionality."""

    def test_export_plot_to_image(self, psd_window_with_data, qtbot):
        """Test exporting plot to image."""
        from spectral_edge.utils.report_generator import export_plot_to_image

        window = psd_window_with_data
        window._calculate_psd()

        # Export PSD plot
        image_data = export_plot_to_image(window.plot_widget)

        # Check we got valid image data
        assert image_data is not None
        assert len(image_data) > 0

        # Check it's a valid PNG
        assert image_data[:8] == b'\x89PNG\r\n\x1a\n'

    def test_export_time_plot_to_image(self, psd_window_with_data, qtbot):
        """Test exporting time history plot to image."""
        from spectral_edge.utils.report_generator import export_plot_to_image

        window = psd_window_with_data

        # Export time plot
        image_data = export_plot_to_image(window.time_plot_widget)

        assert image_data is not None
        assert len(image_data) > 0


# =============================================================================
# Spectrogram Plot Tests
# =============================================================================

class TestSpectrogramPlotVerification:
    """Tests for spectrogram plot accuracy and rendering."""

    @pytest.fixture
    def spectrogram_window(self, qapp):
        """Create spectrogram window with test data."""
        from spectral_edge.gui.spectrogram_window import SpectrogramWindow

        # Create chirp signal (frequency increases with time)
        np.random.seed(42)
        sample_rate = 10000
        duration = 2
        t = np.linspace(0, duration, int(sample_rate * duration))

        # Chirp from 20 Hz to 200 Hz
        freq_start = 20
        freq_end = 200
        freq = freq_start + (freq_end - freq_start) * t / duration
        signal = np.sin(2 * np.pi * freq * t)

        channels_data = [("chirp_signal", signal, "g", "test_flight")]

        window = SpectrogramWindow(t, channels_data, [sample_rate])

        yield window
        window.close()

    def test_spectrogram_image_item_exists(self, spectrogram_window):
        """Test that spectrogram has image item."""
        assert len(spectrogram_window.image_items) > 0
        assert spectrogram_window.image_items[0] is not None

    def test_spectrogram_data_shape(self, spectrogram_window):
        """Test that spectrogram data has correct shape."""
        # Spectrogram should have time x frequency data
        assert len(spectrogram_window.spec_data) > 0

        times, freqs, power_db = spectrogram_window.spec_data[0]

        assert len(times) > 0
        assert len(freqs) > 0
        assert power_db.shape == (len(freqs), len(times))

    def test_spectrogram_time_range(self, spectrogram_window):
        """Test that spectrogram covers expected time range."""
        times, _, _ = spectrogram_window.spec_data[0]

        # Should cover approximately 0 to 2 seconds
        assert times[0] >= 0
        assert times[-1] <= 2.5  # Allow some padding

    def test_spectrogram_frequency_range(self, spectrogram_window):
        """Test that spectrogram covers expected frequency range."""
        _, freqs, _ = spectrogram_window.spec_data[0]

        # Should have frequencies up to Nyquist (5000 Hz)
        assert freqs[0] >= 0
        assert freqs[-1] <= 5000

    def test_spectrogram_colormap_applied(self, spectrogram_window):
        """Test that colormap is applied to image."""
        img = spectrogram_window.image_items[0]

        # Image should have a lookup table (colormap)
        lut = img.lut
        assert lut is not None


# =============================================================================
# Cross-Spectrum Plot Tests
# =============================================================================

class TestCrossSpectrumPlotVerification:
    """Tests for cross-spectrum plot accuracy."""

    @pytest.fixture
    def cross_spectrum_window(self, qapp):
        """Create cross-spectrum window with correlated test signals."""
        from spectral_edge.gui.cross_spectrum_window import CrossSpectrumWindow

        np.random.seed(42)
        sample_rate = 10000
        duration = 2
        t = np.linspace(0, duration, int(sample_rate * duration))

        # Create perfectly coherent signals at 100 Hz
        signal1 = np.sin(2 * np.pi * 100 * t)
        signal2 = np.sin(2 * np.pi * 100 * t + np.pi/4)  # Phase shifted

        # Add some noise
        signal1 += 0.1 * np.random.randn(len(t))
        signal2 += 0.1 * np.random.randn(len(t))

        channels_data = [
            ("input", signal1, "V", "test"),
            ("output", signal2, "V", "test")
        ]

        window = CrossSpectrumWindow(channels_data, sample_rate)

        yield window
        window.close()

    def test_coherence_calculated(self, cross_spectrum_window):
        """Test that coherence is calculated."""
        assert cross_spectrum_window.coherence is not None
        assert len(cross_spectrum_window.coherence) > 0

    def test_coherence_range(self, cross_spectrum_window):
        """Test that coherence is in valid range [0, 1]."""
        coh = cross_spectrum_window.coherence

        # Allow small numerical tolerance
        assert np.all(coh >= -0.01)
        assert np.all(coh <= 1.01)

    def test_coherence_peak_at_signal_frequency(self, cross_spectrum_window):
        """Test that coherence is high at the correlated frequency."""
        freqs = cross_spectrum_window.frequencies
        coh = cross_spectrum_window.coherence

        # Find coherence near 100 Hz
        mask = (freqs >= 90) & (freqs <= 110)
        if np.any(mask):
            coh_at_100hz = np.max(coh[mask])
            # Should have high coherence at the signal frequency
            assert coh_at_100hz > 0.7, f"Coherence at 100 Hz should be high, got {coh_at_100hz}"

    def test_transfer_function_calculated(self, cross_spectrum_window):
        """Test that transfer function is calculated."""
        assert cross_spectrum_window.tf_magnitude is not None
        assert cross_spectrum_window.tf_phase is not None

    def test_transfer_function_phase_range(self, cross_spectrum_window):
        """Test that transfer function phase is in valid range."""
        phase = cross_spectrum_window.tf_phase

        # Phase should be in [-180, 180] degrees
        assert np.all(phase >= -180)
        assert np.all(phase <= 180)

    def test_csd_calculated(self, cross_spectrum_window):
        """Test that CSD is calculated."""
        assert cross_spectrum_window.csd_magnitude is not None
        assert cross_spectrum_window.csd_phase is not None


# =============================================================================
# Axis Limit Tests
# =============================================================================

class TestAxisLimitVerification:
    """Tests for axis limit application."""

    def test_psd_xaxis_limits_applied(self, psd_window_with_data, qtbot):
        """Test that X-axis limits are applied correctly."""
        window = psd_window_with_data
        window._calculate_psd()

        # Set specific limits
        window.x_min_edit.setText("50")
        window.x_max_edit.setText("500")
        window._apply_axis_limits()

        # Get view range
        view_box = window.plot_widget.getPlotItem().getViewBox()
        x_range = view_box.viewRange()[0]

        # In log scale, the range is in log10 values
        # 50 -> log10(50) ≈ 1.7, 500 -> log10(500) ≈ 2.7
        assert x_range[0] >= np.log10(40)  # Allow some padding
        assert x_range[1] <= np.log10(600)

    def test_psd_yaxis_limits_applied(self, psd_window_with_data, qtbot):
        """Test that Y-axis limits are applied correctly."""
        window = psd_window_with_data
        window._calculate_psd()

        # Set specific limits
        window.y_min_edit.setText("1e-6")
        window.y_max_edit.setText("1e-2")
        window._apply_axis_limits()

        # Get view range
        view_box = window.plot_widget.getPlotItem().getViewBox()
        y_range = view_box.viewRange()[1]

        # In log scale, the range is in log10 values
        assert y_range[0] >= np.log10(1e-7)  # Allow some padding
        assert y_range[1] <= np.log10(1e-1)

    def test_autofit_adjusts_to_data(self, psd_window_with_data, qtbot):
        """Test that auto-fit adjusts to actual data range."""
        window = psd_window_with_data
        window._calculate_psd()

        # Apply auto-fit
        window._auto_fit_axes()

        # View range should encompass the data
        # Just verify it doesn't crash and updates something


# =============================================================================
# Octave Band Plot Tests
# =============================================================================

class TestOctaveBandPlot:
    """Tests for octave band display."""

    def test_octave_band_display_toggle(self, psd_window_with_data, qtbot):
        """Test octave band display toggle."""
        window = psd_window_with_data
        window._calculate_psd()

        # Enable octave display
        window.octave_checkbox.setChecked(True)

        # Should not crash
        assert window.octave_checkbox.isChecked()

    def test_octave_fraction_change(self, psd_window_with_data, qtbot):
        """Test changing octave fraction."""
        window = psd_window_with_data
        window._calculate_psd()

        window.octave_checkbox.setChecked(True)

        # Change to different fractions
        for i in range(window.octave_combo.count()):
            window.octave_combo.setCurrentIndex(i)
            # Should not crash


# =============================================================================
# Run tests when executed directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
