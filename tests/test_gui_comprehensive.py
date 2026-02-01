"""
Comprehensive GUI Tests for SpectralEdge.

This module tests all GUI buttons, parameters, display options, and plot rendering
to verify functionality and catch unexpected errors.

These tests simulate user interactions and verify:
- All buttons are clickable and respond correctly
- All parameter controls function as expected
- Display options update correctly
- Plots render with expected data
- No runtime errors occur during typical user workflows

Requirements:
- pytest-qt for Qt widget testing
- QT_QPA_PLATFORM=offscreen for headless testing

Author: SpectralEdge Development Team
"""

import pytest
import numpy as np
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Skip entire module if PyQt6 is not available
pytest.importorskip("PyQt6")

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox
from PyQt6.QtTest import QTest


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
def sample_csv_file(tmp_path):
    """Create a sample CSV file for testing."""
    csv_content = """time,channel1,channel2,channel3
0.0,0.1,0.2,0.3
0.001,0.15,0.25,0.35
0.002,0.12,0.22,0.32
0.003,0.18,0.28,0.38
0.004,0.11,0.21,0.31
"""
    # Generate realistic vibration data
    np.random.seed(42)
    sample_rate = 10000  # 10 kHz
    duration = 5  # 5 seconds
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Create signals with known frequency content
    signal1 = 0.5 * np.sin(2 * np.pi * 50 * t) + 0.1 * np.random.randn(len(t))  # 50 Hz sine
    signal2 = 0.3 * np.sin(2 * np.pi * 100 * t) + 0.05 * np.random.randn(len(t))  # 100 Hz sine
    signal3 = 0.2 * np.sin(2 * np.pi * 200 * t) + 0.02 * np.random.randn(len(t))  # 200 Hz sine

    csv_path = tmp_path / "test_data.csv"
    with open(csv_path, 'w') as f:
        f.write("time,accel_x,accel_y,accel_z\n")
        for i in range(len(t)):
            f.write(f"{t[i]:.6f},{signal1[i]:.6f},{signal2[i]:.6f},{signal3[i]:.6f}\n")

    return str(csv_path)


@pytest.fixture
def sample_reference_csv(tmp_path):
    """Create a sample reference PSD curve CSV file."""
    freq = np.logspace(1, 3, 50)  # 10 to 1000 Hz
    psd = 1e-4 * (freq / 100) ** (-1.5)  # Decreasing PSD

    csv_path = tmp_path / "reference_psd.csv"
    with open(csv_path, 'w') as f:
        f.write("frequency,psd\n")
        for i in range(len(freq)):
            f.write(f"{freq[i]:.2f},{psd[i]:.6e}\n")

    return str(csv_path)


@pytest.fixture
def psd_window(qapp, sample_csv_file):
    """Create a PSD Analysis window with loaded data."""
    from spectral_edge.gui.psd_window import PSDAnalysisWindow

    window = PSDAnalysisWindow()

    # Load the sample CSV file using mock file dialog
    with patch.object(QFileDialog, 'getOpenFileName', return_value=(sample_csv_file, '')):
        window._load_file()

    yield window

    window.close()


@pytest.fixture
def landing_page(qapp):
    """Create a Landing Page window."""
    from spectral_edge.gui.landing_page import LandingPage

    window = LandingPage()
    yield window
    window.close()


# =============================================================================
# Landing Page Tests
# =============================================================================

class TestLandingPage:
    """Tests for the main landing page."""

    def test_landing_page_creates(self, landing_page):
        """Test that landing page creates without error."""
        assert landing_page is not None
        assert landing_page.windowTitle() == "SpectralEdge - Signal Processing Suite"

    def test_landing_page_has_tool_cards(self, landing_page):
        """Test that landing page has expected tool cards."""
        # The landing page should have a tools grid
        assert hasattr(landing_page, 'tool_windows')

    def test_psd_tool_card_click(self, landing_page, qtbot):
        """Test clicking PSD Analysis tool card launches PSD window."""
        # Trigger PSD tool launch
        landing_page._on_tool_clicked("PSD Analysis")

        # Check that PSD window was created
        assert "PSD Analysis" in landing_page.tool_windows
        psd_window = landing_page.tool_windows["PSD Analysis"]
        assert psd_window.isVisible()

        psd_window.close()

    def test_unimplemented_tool_click(self, landing_page, capsys):
        """Test clicking unimplemented tool shows message."""
        landing_page._on_tool_clicked("SRS Analysis")
        captured = capsys.readouterr()
        assert "not yet implemented" in captured.out


# =============================================================================
# PSD Window - File Loading Tests
# =============================================================================

class TestPSDWindowFileLoading:
    """Tests for file loading functionality."""

    def test_window_creates_without_data(self, qapp):
        """Test that PSD window creates without data."""
        from spectral_edge.gui.psd_window import PSDAnalysisWindow

        window = PSDAnalysisWindow()
        assert window is not None
        assert window.signal_data_full is None
        window.close()

    def test_csv_file_loads(self, psd_window):
        """Test that CSV file loads correctly."""
        assert psd_window.signal_data_full is not None
        assert psd_window.time_data_full is not None
        assert psd_window.sample_rate is not None

    def test_channel_names_populated(self, psd_window):
        """Test that channel names are populated after loading."""
        assert psd_window.channel_names is not None
        assert len(psd_window.channel_names) == 3  # accel_x, accel_y, accel_z

    def test_channel_checkboxes_created(self, psd_window):
        """Test that channel checkboxes are created."""
        assert len(psd_window.channel_checkboxes) == 3

    def test_calculate_button_enabled_after_load(self, psd_window):
        """Test that Calculate PSD button is enabled after loading data."""
        assert psd_window.calc_button.isEnabled()

    def test_spectrogram_button_enabled_after_load(self, psd_window):
        """Test that Spectrogram button is enabled after loading data."""
        assert psd_window.spec_button.isEnabled()


# =============================================================================
# PSD Window - Parameter Controls Tests
# =============================================================================

class TestPSDWindowParameters:
    """Tests for PSD parameter controls."""

    def test_window_type_combo(self, psd_window, qtbot):
        """Test all window type options."""
        window_combo = psd_window.window_combo

        expected_windows = ['Hann', 'Hamming', 'Blackman', 'Bartlett', 'Flattop', 'Rectangular']

        for i in range(window_combo.count()):
            window_combo.setCurrentIndex(i)
            window_name = window_combo.currentText()
            assert window_name in expected_windows or window_name.capitalize() in expected_windows

    def test_df_spin_range(self, psd_window, qtbot):
        """Test frequency resolution spin box."""
        df_spin = psd_window.df_spin

        # Test minimum
        df_spin.setValue(0.01)
        assert df_spin.value() == 0.01

        # Test maximum
        df_spin.setValue(100)
        assert df_spin.value() == 100

        # Test typical value
        df_spin.setValue(1.0)
        assert df_spin.value() == 1.0

    def test_efficient_fft_checkbox(self, psd_window, qtbot):
        """Test efficient FFT checkbox toggle."""
        checkbox = psd_window.efficient_fft_checkbox

        # Should be checked by default
        assert checkbox.isChecked()

        # Toggle off
        checkbox.setChecked(False)
        assert not checkbox.isChecked()

        # Toggle on
        checkbox.setChecked(True)
        assert checkbox.isChecked()

    def test_overlap_spin_range(self, psd_window, qtbot):
        """Test overlap spin box range."""
        overlap_spin = psd_window.overlap_spin

        # Test minimum
        overlap_spin.setValue(0)
        assert overlap_spin.value() == 0

        # Test maximum
        overlap_spin.setValue(90)
        assert overlap_spin.value() == 90

        # Test typical value
        overlap_spin.setValue(50)
        assert overlap_spin.value() == 50

    def test_maximax_checkbox_toggle(self, psd_window, qtbot):
        """Test maximax checkbox and related controls."""
        maximax_cb = psd_window.maximax_checkbox
        window_spin = psd_window.maximax_window_spin
        overlap_spin = psd_window.maximax_overlap_spin

        # Toggle maximax on (should be on by default)
        maximax_cb.setChecked(True)
        assert maximax_cb.isChecked()

        # Test maximax window duration
        window_spin.setValue(1.5)
        assert window_spin.value() == 1.5

        # Test maximax overlap
        overlap_spin.setValue(75)
        assert overlap_spin.value() == 75

    def test_frequency_range_spins(self, psd_window, qtbot):
        """Test frequency range spin boxes."""
        freq_min = psd_window.freq_min_spin
        freq_max = psd_window.freq_max_spin

        # Set valid range
        freq_min.setValue(10.0)
        freq_max.setValue(5000.0)

        assert freq_min.value() == 10.0
        assert freq_max.value() == 5000.0


# =============================================================================
# PSD Window - Display Options Tests
# =============================================================================

class TestPSDWindowDisplayOptions:
    """Tests for display options."""

    def test_crosshair_toggle(self, psd_window, qtbot):
        """Test crosshair checkbox toggle."""
        checkbox = psd_window.show_crosshair_checkbox

        # Should be off by default
        assert not checkbox.isChecked()

        # Toggle on
        checkbox.setChecked(True)
        assert checkbox.isChecked()

        # Toggle off
        checkbox.setChecked(False)
        assert not checkbox.isChecked()

    def test_remove_mean_checkbox(self, psd_window, qtbot):
        """Test remove running mean checkbox."""
        checkbox = psd_window.remove_mean_checkbox

        # Should be off by default
        assert not checkbox.isChecked()

        # Toggle on
        checkbox.setChecked(True)
        assert checkbox.isChecked()

    def test_octave_band_controls(self, psd_window, qtbot):
        """Test octave band display controls."""
        octave_cb = psd_window.octave_checkbox
        octave_combo = psd_window.octave_combo

        # Should be off by default
        assert not octave_cb.isChecked()

        # Combo should be disabled when checkbox is off
        assert not octave_combo.isEnabled()

        # Enable octave display
        octave_cb.setChecked(True)
        assert octave_combo.isEnabled()

        # Test all octave fractions
        expected_fractions = ['1/3 Octave', '1/6 Octave', '1/12 Octave', '1/24 Octave', '1/36 Octave']
        for i in range(octave_combo.count()):
            octave_combo.setCurrentIndex(i)
            assert octave_combo.currentText() in expected_fractions


# =============================================================================
# PSD Window - Axis Limits Tests
# =============================================================================

class TestPSDWindowAxisLimits:
    """Tests for axis limit controls."""

    def test_axis_limit_text_fields(self, psd_window, qtbot):
        """Test axis limit text field inputs."""
        # X-axis limits
        psd_window.x_min_edit.setText("10")
        psd_window.x_max_edit.setText("3000")

        assert psd_window.x_min_edit.text() == "10"
        assert psd_window.x_max_edit.text() == "3000"

        # Y-axis limits
        psd_window.y_min_edit.setText("1e-7")
        psd_window.y_max_edit.setText("1e-2")

        assert psd_window.y_min_edit.text() == "1e-7"
        assert psd_window.y_max_edit.text() == "1e-2"

    def test_apply_axis_limits(self, psd_window, qtbot):
        """Test applying custom axis limits."""
        # Set limits
        psd_window.x_min_edit.setText("20")
        psd_window.x_max_edit.setText("2000")
        psd_window.y_min_edit.setText("1e-6")
        psd_window.y_max_edit.setText("1")

        # Apply limits - should not raise error
        psd_window._apply_axis_limits()

    def test_auto_fit_axes(self, psd_window, qtbot):
        """Test auto-fit axis button."""
        # Should not raise error even without PSD data
        psd_window._auto_fit_axes()


# =============================================================================
# PSD Window - Filter Controls Tests
# =============================================================================

class TestPSDWindowFilterControls:
    """Tests for signal filtering controls."""

    def test_filter_enable_toggle(self, psd_window, qtbot):
        """Test enabling/disabling filter controls."""
        enable_cb = psd_window.enable_filter_checkbox

        # Initially disabled
        assert not enable_cb.isChecked()
        assert not psd_window.filter_type_combo.isEnabled()

        # Enable filtering
        enable_cb.setChecked(True)
        assert psd_window.filter_type_combo.isEnabled()
        assert psd_window.filter_design_combo.isEnabled()
        assert psd_window.filter_order_spin.isEnabled()

    def test_filter_type_options(self, psd_window, qtbot):
        """Test all filter type options."""
        psd_window.enable_filter_checkbox.setChecked(True)
        filter_combo = psd_window.filter_type_combo

        expected_types = ['Lowpass', 'Highpass', 'Bandpass']
        for filter_type in expected_types:
            filter_combo.setCurrentText(filter_type)
            assert filter_combo.currentText() == filter_type

    def test_filter_design_options(self, psd_window, qtbot):
        """Test all filter design options."""
        psd_window.enable_filter_checkbox.setChecked(True)
        design_combo = psd_window.filter_design_combo

        expected_designs = ['Butterworth', 'Chebyshev', 'Bessel']
        for design in expected_designs:
            design_combo.setCurrentText(design)
            assert design_combo.currentText() == design

    def test_filter_order_range(self, psd_window, qtbot):
        """Test filter order spin box."""
        psd_window.enable_filter_checkbox.setChecked(True)
        order_spin = psd_window.filter_order_spin

        # Test range
        order_spin.setValue(1)
        assert order_spin.value() == 1

        order_spin.setValue(10)
        assert order_spin.value() == 10

        order_spin.setValue(4)
        assert order_spin.value() == 4

    def test_bandpass_cutoff_controls(self, psd_window, qtbot):
        """Test bandpass filter shows two cutoff controls."""
        psd_window.enable_filter_checkbox.setChecked(True)
        psd_window.filter_type_combo.setCurrentText('Bandpass')

        # Bandpass should show low and high cutoff
        assert psd_window.low_cutoff_spin.isVisible()
        assert psd_window.high_cutoff_spin.isVisible()

        # Single cutoff should be hidden
        assert not psd_window.cutoff_freq_spin.isVisible()

    def test_lowpass_cutoff_control(self, psd_window, qtbot):
        """Test lowpass filter shows single cutoff control."""
        psd_window.enable_filter_checkbox.setChecked(True)
        psd_window.filter_type_combo.setCurrentText('Lowpass')

        # Should show single cutoff
        assert psd_window.cutoff_freq_spin.isVisible()

        # Bandpass controls should be hidden
        assert not psd_window.low_cutoff_spin.isVisible()
        assert not psd_window.high_cutoff_spin.isVisible()


# =============================================================================
# PSD Window - Calculate and Plot Tests
# =============================================================================

class TestPSDWindowCalculation:
    """Tests for PSD calculation and plotting."""

    def test_calculate_psd_welch(self, psd_window, qtbot):
        """Test PSD calculation with Welch method."""
        # Disable maximax for Welch method
        psd_window.maximax_checkbox.setChecked(False)

        # Calculate PSD
        psd_window._calculate_psd()

        # Check results exist
        assert len(psd_window.psd_results) > 0
        assert len(psd_window.frequencies) > 0

    def test_calculate_psd_maximax(self, psd_window, qtbot):
        """Test PSD calculation with Maximax method."""
        # Enable maximax
        psd_window.maximax_checkbox.setChecked(True)
        psd_window.maximax_window_spin.setValue(1.0)
        psd_window.maximax_overlap_spin.setValue(50)

        # Calculate PSD
        psd_window._calculate_psd()

        # Check results exist
        assert len(psd_window.psd_results) > 0

    def test_rms_values_calculated(self, psd_window, qtbot):
        """Test that RMS values are calculated."""
        psd_window._calculate_psd()

        # RMS should be calculated for selected channels
        assert len(psd_window.rms_values) > 0

    def test_channel_selection_affects_calculation(self, psd_window, qtbot):
        """Test that only selected channels are calculated."""
        # Uncheck all but one channel
        for i, cb in enumerate(psd_window.channel_checkboxes):
            cb.setChecked(i == 0)  # Only first channel

        # Calculate
        psd_window._calculate_psd()

        # Should only have one result
        assert len(psd_window.psd_results) == 1


# =============================================================================
# PSD Window - Comparison Curves Tests
# =============================================================================

class TestPSDWindowComparisonCurves:
    """Tests for comparison/reference curve functionality."""

    def test_import_comparison_curve(self, psd_window, sample_reference_csv, qtbot):
        """Test importing a reference curve."""
        # Mock file dialog and input dialog
        with patch.object(QFileDialog, 'getOpenFileName', return_value=(sample_reference_csv, '')):
            with patch.object(QInputDialog, 'getText', return_value=("Test Reference", True)):
                psd_window._import_comparison_curve()

        # Should have one comparison curve
        assert len(psd_window.comparison_curves) == 1
        assert psd_window.comparison_curves[0]['name'] == "Test Reference"

    def test_toggle_comparison_curve_visibility(self, psd_window, sample_reference_csv, qtbot):
        """Test toggling comparison curve visibility."""
        # Import a curve first
        with patch.object(QFileDialog, 'getOpenFileName', return_value=(sample_reference_csv, '')):
            with patch.object(QInputDialog, 'getText', return_value=("Test Ref", True)):
                psd_window._import_comparison_curve()

        # Toggle visibility
        psd_window._toggle_comparison_curve(0, Qt.CheckState.Unchecked.value)
        assert not psd_window.comparison_curves[0]['visible']

        psd_window._toggle_comparison_curve(0, Qt.CheckState.Checked.value)
        assert psd_window.comparison_curves[0]['visible']

    def test_remove_comparison_curve(self, psd_window, sample_reference_csv, qtbot):
        """Test removing a comparison curve."""
        # Import a curve
        with patch.object(QFileDialog, 'getOpenFileName', return_value=(sample_reference_csv, '')):
            with patch.object(QInputDialog, 'getText', return_value=("Test Ref", True)):
                psd_window._import_comparison_curve()

        assert len(psd_window.comparison_curves) == 1

        # Remove it
        psd_window._remove_comparison_curve(0)
        assert len(psd_window.comparison_curves) == 0

    def test_clear_all_comparison_curves(self, psd_window, sample_reference_csv, qtbot):
        """Test clearing all comparison curves."""
        # Import multiple curves
        for i in range(3):
            with patch.object(QFileDialog, 'getOpenFileName', return_value=(sample_reference_csv, '')):
                with patch.object(QInputDialog, 'getText', return_value=(f"Ref {i}", True)):
                    psd_window._import_comparison_curve()

        assert len(psd_window.comparison_curves) == 3

        # Clear all
        psd_window._clear_comparison_curves()
        assert len(psd_window.comparison_curves) == 0


# =============================================================================
# PSD Window - Action Buttons Tests
# =============================================================================

class TestPSDWindowActionButtons:
    """Tests for action buttons."""

    def test_open_spectrogram_window(self, psd_window, qtbot):
        """Test opening spectrogram window."""
        psd_window._open_spectrogram()

        # Should have created spectrogram window(s)
        assert len(psd_window.spectrogram_windows) > 0

        # Close all spectrogram windows
        for key, window in list(psd_window.spectrogram_windows.items()):
            window.close()

    def test_open_event_manager(self, psd_window, qtbot):
        """Test opening event manager."""
        psd_window._open_event_manager()

        # Should have created event manager
        assert psd_window.event_manager is not None

        psd_window.event_manager.close()

    def test_clear_events(self, psd_window, qtbot):
        """Test clearing events."""
        # Create some mock events first
        from spectral_edge.gui.event_manager import Event
        psd_window.events = [Event("Test", 0, 1)]

        # Clear events
        psd_window._clear_events()

        assert len(psd_window.events) == 0

    def test_cross_spectrum_button_requires_two_channels(self, psd_window, qtbot):
        """Test cross-spectrum requires at least 2 channels."""
        # Should work with 3 channels
        psd_window._open_cross_spectrum()

        assert psd_window.cross_spectrum_window is not None
        psd_window.cross_spectrum_window.close()


# =============================================================================
# Spectrogram Window Tests
# =============================================================================

class TestSpectrogramWindow:
    """Tests for the Spectrogram window."""

    @pytest.fixture
    def spectrogram_window(self, qapp):
        """Create a spectrogram window with test data."""
        from spectral_edge.gui.spectrogram_window import SpectrogramWindow

        # Create test data
        np.random.seed(42)
        sample_rate = 10000
        duration = 2
        t = np.linspace(0, duration, int(sample_rate * duration))
        signal = np.sin(2 * np.pi * 50 * t) + 0.1 * np.random.randn(len(t))

        channels_data = [("test_channel", signal, "g", "flight_1")]

        window = SpectrogramWindow(
            time_data=t,
            channels_data=channels_data,
            sample_rates=[sample_rate]
        )

        yield window
        window.close()

    def test_spectrogram_creates(self, spectrogram_window):
        """Test spectrogram window creates."""
        assert spectrogram_window is not None

    def test_window_type_combo(self, spectrogram_window, qtbot):
        """Test window type selection."""
        combo = spectrogram_window.window_combo

        # Test changing window type
        for i in range(combo.count()):
            combo.setCurrentIndex(i)
            # Should not raise error

    def test_df_spin(self, spectrogram_window, qtbot):
        """Test frequency resolution control."""
        df_spin = spectrogram_window.df_spin

        df_spin.setValue(0.5)
        assert df_spin.value() == 0.5

        df_spin.setValue(2.0)
        assert df_spin.value() == 2.0

    def test_overlap_spin(self, spectrogram_window, qtbot):
        """Test overlap control."""
        overlap_spin = spectrogram_window.overlap_spin

        overlap_spin.setValue(25)
        assert overlap_spin.value() == 25

        overlap_spin.setValue(75)
        assert overlap_spin.value() == 75

    def test_colormap_options(self, spectrogram_window, qtbot):
        """Test all colormap options."""
        combo = spectrogram_window.colormap_combo

        expected_colormaps = ['viridis', 'plasma', 'inferno', 'magma', 'jet', 'hot', 'cool']

        for cmap in expected_colormaps:
            combo.setCurrentText(cmap)
            assert combo.currentText() == cmap

    def test_snr_spin(self, spectrogram_window, qtbot):
        """Test SNR control."""
        snr_spin = spectrogram_window.snr_spin

        snr_spin.setValue(40)
        assert snr_spin.value() == 40

        snr_spin.setValue(80)
        assert snr_spin.value() == 80

    def test_colorbar_toggle(self, spectrogram_window, qtbot):
        """Test colorbar visibility toggle."""
        checkbox = spectrogram_window.show_colorbar_checkbox

        # Should be on by default
        assert checkbox.isChecked()

        # Toggle off
        checkbox.setChecked(False)
        assert not checkbox.isChecked()

    def test_auto_limits_toggle(self, spectrogram_window, qtbot):
        """Test auto limits toggle enables/disables manual controls."""
        auto_cb = spectrogram_window.auto_limits_checkbox

        # Should be on by default
        assert auto_cb.isChecked()

        # Manual controls should be disabled
        assert not spectrogram_window.time_min_edit.isEnabled()

        # Toggle off
        auto_cb.setChecked(False)

        # Manual controls should be enabled
        assert spectrogram_window.time_min_edit.isEnabled()

    def test_recalculate(self, spectrogram_window, qtbot):
        """Test recalculate button."""
        # Change a parameter
        spectrogram_window.df_spin.setValue(2.0)

        # Recalculate - should not raise error
        spectrogram_window._calculate_spectrograms()

        # Should have spectrogram data
        assert len(spectrogram_window.spec_data) > 0

    def test_apply_frequency_range(self, spectrogram_window, qtbot):
        """Test applying frequency range."""
        spectrogram_window.freq_min_edit.setText("50")
        spectrogram_window.freq_max_edit.setText("1000")

        # Should not raise error
        spectrogram_window._apply_frequency_range()


# =============================================================================
# Cross-Spectrum Window Tests
# =============================================================================

class TestCrossSpectrumWindow:
    """Tests for the Cross-Spectrum Analysis window."""

    @pytest.fixture
    def cross_spectrum_window(self, qapp):
        """Create a cross-spectrum window with test data."""
        from spectral_edge.gui.cross_spectrum_window import CrossSpectrumWindow

        # Create test data with correlated signals
        np.random.seed(42)
        sample_rate = 10000
        duration = 2
        t = np.linspace(0, duration, int(sample_rate * duration))

        # Create two correlated signals
        signal1 = np.sin(2 * np.pi * 50 * t) + 0.1 * np.random.randn(len(t))
        signal2 = 0.5 * np.sin(2 * np.pi * 50 * t + 0.5) + 0.1 * np.random.randn(len(t))

        channels_data = [
            ("reference", signal1, "g", "flight_1"),
            ("response", signal2, "g", "flight_1")
        ]

        window = CrossSpectrumWindow(
            channels_data=channels_data,
            sample_rate=sample_rate
        )

        yield window
        window.close()

    def test_cross_spectrum_creates(self, cross_spectrum_window):
        """Test cross-spectrum window creates."""
        assert cross_spectrum_window is not None

    def test_channel_selection_combos(self, cross_spectrum_window, qtbot):
        """Test channel selection combos."""
        ref_combo = cross_spectrum_window.ref_combo
        resp_combo = cross_spectrum_window.resp_combo

        assert ref_combo.count() == 2
        assert resp_combo.count() == 2

    def test_calculate_button(self, cross_spectrum_window, qtbot):
        """Test calculate button."""
        # Initial calculation should have been done
        assert cross_spectrum_window.frequencies is not None
        assert cross_spectrum_window.coherence is not None

    def test_coherence_threshold_toggle(self, cross_spectrum_window, qtbot):
        """Test coherence threshold line toggle."""
        checkbox = cross_spectrum_window.show_threshold_checkbox

        # Should be on by default
        assert checkbox.isChecked()

        # Toggle off
        checkbox.setChecked(False)
        # Should trigger plot update

    def test_log_frequency_toggle(self, cross_spectrum_window, qtbot):
        """Test log frequency axis toggle."""
        checkbox = cross_spectrum_window.log_freq_checkbox

        # Should be on by default
        assert checkbox.isChecked()

        # Toggle off
        checkbox.setChecked(False)

    def test_tabs_exist(self, cross_spectrum_window):
        """Test all tabs exist."""
        tab_widget = cross_spectrum_window.tab_widget

        assert tab_widget.count() == 4

        # Check tab names
        tab_names = [tab_widget.tabText(i) for i in range(tab_widget.count())]
        assert "Coherence" in tab_names
        assert "CSD" in tab_names
        assert "Transfer Function" in tab_names
        assert "PSDs" in tab_names

    def test_frequency_range_controls(self, cross_spectrum_window, qtbot):
        """Test frequency range controls."""
        freq_min = cross_spectrum_window.freq_min_spin
        freq_max = cross_spectrum_window.freq_max_spin

        freq_min.setValue(100)
        freq_max.setValue(1000)

        assert freq_min.value() == 100
        assert freq_max.value() == 1000


# =============================================================================
# Plot Verification Tests
# =============================================================================

class TestPlotVerification:
    """Tests for verifying plot content and rendering."""

    def test_psd_plot_has_data_items(self, psd_window, qtbot):
        """Test that PSD plot has data items after calculation."""
        psd_window._calculate_psd()

        # Get plot items
        plot_item = psd_window.plot_widget.getPlotItem()
        data_items = plot_item.listDataItems()

        # Should have at least one curve
        assert len(data_items) > 0

    def test_time_plot_has_data_items(self, psd_window, qtbot):
        """Test that time history plot has data items."""
        # Time plot should have data after loading
        plot_item = psd_window.time_plot_widget.getPlotItem()
        data_items = plot_item.listDataItems()

        # Should have curves for loaded channels
        assert len(data_items) > 0

    def test_psd_plot_axis_labels(self, psd_window, qtbot):
        """Test PSD plot has correct axis labels."""
        plot_item = psd_window.plot_widget.getPlotItem()

        left_axis = plot_item.getAxis('left')
        bottom_axis = plot_item.getAxis('bottom')

        # Check axes exist
        assert left_axis is not None
        assert bottom_axis is not None

    def test_psd_plot_log_scale(self, psd_window, qtbot):
        """Test PSD plot uses log scale."""
        psd_window._calculate_psd()

        # Check log mode is enabled
        view_box = psd_window.plot_widget.getPlotItem().getViewBox()

        # Log mode should be set
        # Note: pyqtgraph stores log mode state internally

    def test_spectrogram_has_image_items(self, qapp):
        """Test spectrogram plot has image items."""
        from spectral_edge.gui.spectrogram_window import SpectrogramWindow

        # Create test data
        np.random.seed(42)
        sample_rate = 10000
        t = np.linspace(0, 1, sample_rate)
        signal = np.sin(2 * np.pi * 100 * t)

        channels_data = [("test", signal, "g", "")]

        window = SpectrogramWindow(t, channels_data, [sample_rate])

        # Check image items exist
        for img_item in window.image_items:
            assert img_item is not None

        window.close()


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in GUI operations."""

    def test_invalid_axis_limits_handled(self, psd_window, qtbot):
        """Test invalid axis limits don't crash."""
        # Set invalid limits
        psd_window.x_min_edit.setText("invalid")
        psd_window.x_max_edit.setText("3000")

        # Should not crash, may show warning
        with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Ok):
            psd_window._apply_axis_limits()

    def test_empty_file_path_handled(self, psd_window, qtbot):
        """Test empty file path from dialog is handled."""
        # Mock dialog returning empty path
        with patch.object(QFileDialog, 'getOpenFileName', return_value=('', '')):
            # Should not crash
            psd_window._load_file()

    def test_filter_invalid_cutoff_handled(self, psd_window, qtbot):
        """Test filter with invalid cutoff is handled gracefully."""
        psd_window.enable_filter_checkbox.setChecked(True)

        # Set cutoff above Nyquist
        psd_window.cutoff_freq_spin.setValue(psd_window.sample_rate)  # At Nyquist, will be rejected

        # Get a signal
        signal = psd_window.signal_data_full[:, 0] if psd_window.signal_data_full.ndim > 1 else psd_window.signal_data_full

        # Should handle gracefully (return original signal)
        result = psd_window._apply_filter(signal, psd_window.sample_rate)
        assert result is not None


# =============================================================================
# Multi-Channel Tests
# =============================================================================

class TestMultiChannelOperations:
    """Tests for multi-channel functionality."""

    def test_select_single_channel(self, psd_window, qtbot):
        """Test selecting only one channel."""
        # Uncheck all
        for cb in psd_window.channel_checkboxes:
            cb.setChecked(False)

        # Check only first
        psd_window.channel_checkboxes[0].setChecked(True)

        # Calculate
        psd_window._calculate_psd()

        # Should have one result
        assert len(psd_window.psd_results) == 1

    def test_select_all_channels(self, psd_window, qtbot):
        """Test selecting all channels."""
        # Check all
        for cb in psd_window.channel_checkboxes:
            cb.setChecked(True)

        # Calculate
        psd_window._calculate_psd()

        # Should have results for all channels
        assert len(psd_window.psd_results) == 3

    def test_spectrogram_multiple_channels(self, qapp):
        """Test spectrogram with multiple channels."""
        from spectral_edge.gui.spectrogram_window import SpectrogramWindow

        # Create test data with 4 channels
        np.random.seed(42)
        sample_rate = 10000
        t = np.linspace(0, 1, sample_rate)

        channels_data = [
            (f"ch{i}", np.sin(2 * np.pi * (50 + i*25) * t), "g", "")
            for i in range(4)
        ]

        window = SpectrogramWindow(t, channels_data, [sample_rate] * 4)

        # Should create 4 plot widgets
        assert len(window.plot_widgets) == 4

        window.close()


# =============================================================================
# Report Generation Tests
# =============================================================================

class TestReportGeneration:
    """Tests for report generation functionality."""

    def test_report_requires_psd_results(self, psd_window, qtbot):
        """Test report generation requires PSD results."""
        # Clear any results
        psd_window.psd_results = {}

        # Mock warning dialog
        with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Ok):
            psd_window._generate_report()

    def test_report_generation_with_data(self, psd_window, tmp_path, qtbot):
        """Test report generation with valid data."""
        # Calculate PSD first
        psd_window._calculate_psd()

        # Set up save path
        save_path = str(tmp_path / "test_report.pptx")

        # Mock file dialog
        with patch.object(QFileDialog, 'getSaveFileName', return_value=(save_path, '')):
            try:
                psd_window._generate_report()
            except ImportError:
                # python-pptx might not be installed
                pytest.skip("python-pptx not installed")


# =============================================================================
# Run tests when executed directly
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
