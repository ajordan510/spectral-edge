"""
Headless GUI tests for SpectralEdge.

These tests can run without a display using:
    xvfb-run pytest tests/test_gui_headless.py

Or with pytest-qt's built-in offscreen support:
    QT_QPA_PLATFORM=offscreen pytest tests/test_gui_headless.py

Requirements:
    pip install pytest-qt
"""

import pytest
import numpy as np
import sys
import os

# Set offscreen platform before importing Qt
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

# Skip all tests if PyQt6 is not available
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


@pytest.fixture(scope="session")
def qapp():
    """Create a QApplication instance for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def sample_signal_data():
    """Generate sample signal data for testing."""
    sample_rate = 1000.0
    duration = 10.0
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Create multi-channel data with known frequencies
    signal1 = np.sin(2 * np.pi * 50 * t) + 0.1 * np.random.randn(len(t))
    signal2 = np.sin(2 * np.pi * 100 * t) + 0.1 * np.random.randn(len(t))

    return {
        'time': t,
        'signals': np.column_stack([signal1, signal2]),
        'sample_rate': sample_rate,
        'channel_names': ['Channel_50Hz', 'Channel_100Hz'],
        'channel_units': ['g', 'g']
    }


class TestCrossSpectrumWindow:
    """Tests for the CrossSpectrumWindow."""

    def test_window_initialization(self, qapp, sample_signal_data):
        """Test that CrossSpectrumWindow initializes without errors."""
        from spectral_edge.gui.cross_spectrum_window import CrossSpectrumWindow

        # Prepare channel data in expected format
        channels_data = []
        for i, name in enumerate(sample_signal_data['channel_names']):
            signal = sample_signal_data['signals'][:, i]
            unit = sample_signal_data['channel_units'][i]
            channels_data.append((name, signal, unit, 'test_flight'))

        # Create window
        window = CrossSpectrumWindow(
            channels_data=channels_data,
            sample_rate=sample_signal_data['sample_rate'],
            window_type='hann',
            df=1.0,
            overlap_percent=50,
            freq_min=20.0,
            freq_max=200.0
        )

        assert window is not None
        assert window.windowTitle() == "SpectralEdge - Cross-Spectrum Analysis"

        # Verify UI elements exist
        assert window.ref_combo is not None
        assert window.resp_combo is not None
        assert window.coherence_plot is not None

        window.close()

    def test_channel_selection(self, qapp, sample_signal_data):
        """Test channel selection dropdowns."""
        from spectral_edge.gui.cross_spectrum_window import CrossSpectrumWindow

        channels_data = [
            (name, sample_signal_data['signals'][:, i], 'g', 'flight')
            for i, name in enumerate(sample_signal_data['channel_names'])
        ]

        window = CrossSpectrumWindow(
            channels_data=channels_data,
            sample_rate=sample_signal_data['sample_rate']
        )

        # Check combo boxes have correct items
        assert window.ref_combo.count() == 2
        assert window.resp_combo.count() == 2

        # Verify different channels selected by default
        assert window.ref_combo.currentIndex() != window.resp_combo.currentIndex()

        window.close()

    def test_calculation_runs(self, qapp, sample_signal_data):
        """Test that calculation completes without errors."""
        from spectral_edge.gui.cross_spectrum_window import CrossSpectrumWindow

        channels_data = [
            (name, sample_signal_data['signals'][:, i], 'g', 'flight')
            for i, name in enumerate(sample_signal_data['channel_names'])
        ]

        window = CrossSpectrumWindow(
            channels_data=channels_data,
            sample_rate=sample_signal_data['sample_rate'],
            df=1.0
        )

        # Calculation should run automatically on init
        # Verify results are populated
        assert window.frequencies is not None
        assert window.coherence is not None
        assert len(window.frequencies) > 0

        window.close()

    def test_coherence_values_valid(self, qapp, sample_signal_data):
        """Test that coherence values are in valid range [0, 1]."""
        from spectral_edge.gui.cross_spectrum_window import CrossSpectrumWindow

        channels_data = [
            (name, sample_signal_data['signals'][:, i], 'g', 'flight')
            for i, name in enumerate(sample_signal_data['channel_names'])
        ]

        window = CrossSpectrumWindow(
            channels_data=channels_data,
            sample_rate=sample_signal_data['sample_rate']
        )

        assert np.all(window.coherence >= 0)
        assert np.all(window.coherence <= 1)

        window.close()


class TestReportGenerator:
    """Tests for the ReportGenerator (no GUI needed)."""

    def test_report_creation(self):
        """Test basic report creation."""
        pytest.importorskip("pptx")
        from spectral_edge.utils.report_generator import ReportGenerator, PPTX_AVAILABLE

        if not PPTX_AVAILABLE:
            pytest.skip("python-pptx not available")

        report = ReportGenerator(title="Test Report")
        assert report.slide_count == 0

        report.add_title_slide(subtitle="Test Subtitle")
        assert report.slide_count == 1

    def test_summary_table(self):
        """Test summary table creation."""
        pytest.importorskip("pptx")
        from spectral_edge.utils.report_generator import ReportGenerator, PPTX_AVAILABLE

        if not PPTX_AVAILABLE:
            pytest.skip("python-pptx not available")

        report = ReportGenerator(title="Test Report")

        channels = ['Channel_A', 'Channel_B', 'Channel_C']
        rms_values = {'Channel_A': 1.234, 'Channel_B': 2.345, 'Channel_C': 3.456}

        report.add_summary_table(channels, rms_values, units='g')
        assert report.slide_count == 1

    def test_save_to_bytes(self):
        """Test saving report to bytes."""
        pytest.importorskip("pptx")
        from spectral_edge.utils.report_generator import ReportGenerator, PPTX_AVAILABLE

        if not PPTX_AVAILABLE:
            pytest.skip("python-pptx not available")

        report = ReportGenerator(title="Test Report")
        report.add_title_slide()
        report.add_text_slide("Test", "Content", ["Point 1", "Point 2"])

        data = report.save_to_bytes()
        assert len(data) > 0
        # PPTX files start with PK (ZIP format)
        assert data[:2] == b'PK'


class TestComparisonCurvesLogic:
    """Tests for comparison curves logic (extracted from GUI)."""

    def test_csv_parsing_two_columns(self, tmp_path):
        """Test parsing a simple two-column CSV."""
        import pandas as pd

        # Create test CSV
        csv_path = tmp_path / "reference.csv"
        csv_path.write_text("frequency,psd\n10,0.001\n100,0.01\n1000,0.1\n")

        df = pd.read_csv(csv_path)
        frequencies = df.iloc[:, 0].values.astype(float)
        psd = df.iloc[:, 1].values.astype(float)

        assert len(frequencies) == 3
        assert len(psd) == 3
        assert frequencies[0] == 10
        assert psd[2] == 0.1

    def test_csv_parsing_with_header(self, tmp_path):
        """Test parsing CSV with custom header names."""
        import pandas as pd

        csv_path = tmp_path / "spec_limit.csv"
        csv_path.write_text("freq_hz,amplitude\n20,0.05\n2000,0.05\n")

        df = pd.read_csv(csv_path)
        assert df.shape[1] >= 2

        frequencies = df.iloc[:, 0].values
        psd = df.iloc[:, 1].values

        assert len(frequencies) == 2


class TestCrossSpectrumFunctions:
    """Unit tests for cross-spectrum core functions."""

    def test_csd_with_correlated_signals(self):
        """Test CSD with two correlated signals."""
        from spectral_edge.core.psd import calculate_csd

        sample_rate = 1000.0
        t = np.linspace(0, 10, 10000)
        freq = 50.0

        signal1 = np.sin(2 * np.pi * freq * t)
        signal2 = np.sin(2 * np.pi * freq * t + np.pi/4)

        frequencies, csd = calculate_csd(signal1, signal2, sample_rate, df=1.0)

        # Find peak
        peak_idx = np.argmax(np.abs(csd))
        peak_freq = frequencies[peak_idx]

        # Peak should be near 50 Hz
        assert abs(peak_freq - freq) < 2.0

    def test_coherence_identical_signals(self):
        """Test coherence of identical signals should be 1.0."""
        from spectral_edge.core.psd import calculate_coherence

        sample_rate = 1000.0
        t = np.linspace(0, 10, 10000)
        signal = np.sin(2 * np.pi * 50 * t)

        frequencies, coherence = calculate_coherence(signal, signal, sample_rate, df=1.0)

        # Coherence should be very close to 1.0 everywhere
        assert np.all(coherence > 0.99)

    def test_coherence_uncorrelated_signals(self):
        """Test coherence of uncorrelated signals should be low."""
        from spectral_edge.core.psd import calculate_coherence

        np.random.seed(42)
        sample_rate = 1000.0
        n_samples = 10000

        signal1 = np.random.randn(n_samples)
        signal2 = np.random.randn(n_samples)

        frequencies, coherence = calculate_coherence(signal1, signal2, sample_rate, df=1.0)

        # Mean coherence should be low for uncorrelated noise
        assert np.mean(coherence) < 0.3

    def test_transfer_function_unity_gain(self):
        """Test transfer function with identical signals has unity gain."""
        from spectral_edge.core.psd import calculate_transfer_function

        sample_rate = 1000.0
        t = np.linspace(0, 10, 10000)
        signal = np.sin(2 * np.pi * 50 * t) + 0.01 * np.random.randn(len(t))

        frequencies, magnitude, phase = calculate_transfer_function(
            signal, signal, sample_rate, df=1.0
        )

        # At the signal frequency, magnitude should be ~1.0
        idx_50hz = np.argmin(np.abs(frequencies - 50))
        assert abs(magnitude[idx_50hz] - 1.0) < 0.1

    def test_transfer_function_phase_shift(self):
        """Test transfer function detects phase shift."""
        from spectral_edge.core.psd import calculate_transfer_function

        sample_rate = 1000.0
        t = np.linspace(0, 10, 10000)
        freq = 50.0
        phase_shift = 45.0  # degrees

        signal1 = np.sin(2 * np.pi * freq * t)
        signal2 = np.sin(2 * np.pi * freq * t + np.radians(phase_shift))

        frequencies, magnitude, phase = calculate_transfer_function(
            signal1, signal2, sample_rate, df=1.0
        )

        # Find phase at 50 Hz
        idx = np.argmin(np.abs(frequencies - freq))
        measured_phase = phase[idx]

        # Phase should be close to expected
        assert abs(measured_phase - phase_shift) < 5.0


class TestPSDWindowLogic:
    """Test PSD window logic without full GUI instantiation."""

    def test_comparison_curve_data_structure(self):
        """Test the comparison curve data structure."""
        curve = {
            'name': 'Spec Limit',
            'frequencies': np.array([10, 100, 1000]),
            'psd': np.array([0.001, 0.01, 0.1]),
            'color': '#ff6b6b',
            'line_style': 'dash',
            'visible': True,
            'file_path': '/path/to/file.csv'
        }

        assert curve['name'] == 'Spec Limit'
        assert len(curve['frequencies']) == 3
        assert curve['visible'] is True

    def test_frequency_mask_logic(self):
        """Test frequency masking for plot range."""
        frequencies = np.array([1, 10, 100, 1000, 10000])
        psd = np.array([0.1, 0.2, 0.3, 0.4, 0.5])

        freq_min = 20
        freq_max = 2000

        mask = (frequencies >= freq_min) & (frequencies <= freq_max)

        filtered_freqs = frequencies[mask]
        filtered_psd = psd[mask]

        assert len(filtered_freqs) == 2
        assert 100 in filtered_freqs
        assert 1000 in filtered_freqs


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
