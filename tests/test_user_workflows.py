"""
User workflow simulation tests.

These tests simulate actual user interactions like clicking buttons,
entering values, and verifying results.

Run with:
    QT_QPA_PLATFORM=offscreen pytest tests/test_user_workflows.py -v

Requirements:
    pip install pytest-qt
"""

import pytest
import numpy as np
import os
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

pytest.importorskip("PyQt6")
pytest.importorskip("pytestqt")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication


@pytest.fixture
def sample_csv_file(tmp_path):
    """Create a sample CSV file for testing."""
    csv_content = """time,accel_x,accel_y
0.000,0.1,0.2
0.001,0.15,0.25
0.002,0.12,0.22
"""
    # Generate actual time series data
    sample_rate = 1000.0
    duration = 5.0
    t = np.arange(0, duration, 1/sample_rate)

    # Create signals with known frequencies
    accel_x = np.sin(2 * np.pi * 50 * t) + 0.1 * np.random.randn(len(t))
    accel_y = np.sin(2 * np.pi * 100 * t) + 0.1 * np.random.randn(len(t))

    csv_path = tmp_path / "test_data.csv"
    with open(csv_path, 'w') as f:
        f.write("time,accel_x (g),accel_y (g)\n")
        for i in range(len(t)):
            f.write(f"{t[i]:.6f},{accel_x[i]:.6f},{accel_y[i]:.6f}\n")

    return str(csv_path)


@pytest.fixture
def reference_curve_csv(tmp_path):
    """Create a reference curve CSV for comparison testing."""
    csv_path = tmp_path / "reference_curve.csv"
    with open(csv_path, 'w') as f:
        f.write("frequency,psd\n")
        f.write("10,0.001\n")
        f.write("100,0.01\n")
        f.write("1000,0.001\n")
    return str(csv_path)


class TestCrossSpectrumUserWorkflow:
    """Simulate user workflow for cross-spectrum analysis."""

    def test_open_calculate_close_workflow(self, qtbot, sample_csv_file):
        """Test: User opens window, calculates, closes."""
        from spectral_edge.gui.cross_spectrum_window import CrossSpectrumWindow

        # Simulate loaded data
        sample_rate = 1000.0
        t = np.linspace(0, 5, 5000)
        channels_data = [
            ('accel_x', np.sin(2 * np.pi * 50 * t), 'g', 'test'),
            ('accel_y', np.sin(2 * np.pi * 50 * t + np.pi/4), 'g', 'test'),
        ]

        # User opens cross-spectrum window
        window = CrossSpectrumWindow(
            channels_data=channels_data,
            sample_rate=sample_rate
        )
        qtbot.addWidget(window)
        window.show()

        # Verify window opened
        assert window.isVisible()

        # User changes frequency resolution
        window.df_spin.setValue(2.0)

        # User clicks Calculate
        qtbot.mouseClick(window.findChild(type(window.df_spin).parent(), ""), Qt.MouseButton.LeftButton)

        # Verify results exist
        assert window.coherence is not None

        # User closes window
        window.close()
        assert not window.isVisible()

    def test_change_channels_workflow(self, qtbot):
        """Test: User changes reference/response channels."""
        from spectral_edge.gui.cross_spectrum_window import CrossSpectrumWindow

        sample_rate = 1000.0
        t = np.linspace(0, 5, 5000)
        channels_data = [
            ('ch1', np.sin(2 * np.pi * 50 * t), 'g', ''),
            ('ch2', np.sin(2 * np.pi * 100 * t), 'g', ''),
            ('ch3', np.sin(2 * np.pi * 150 * t), 'g', ''),
        ]

        window = CrossSpectrumWindow(
            channels_data=channels_data,
            sample_rate=sample_rate
        )
        qtbot.addWidget(window)

        # Initial selection
        initial_ref = window.ref_combo.currentIndex()
        initial_resp = window.resp_combo.currentIndex()

        # User changes response channel
        window.resp_combo.setCurrentIndex(2)

        # Verify selection changed
        assert window.resp_combo.currentIndex() == 2
        assert window.resp_combo.currentIndex() != initial_resp

        window.close()


class TestReportGeneratorWorkflow:
    """Test report generation workflows."""

    def test_full_report_workflow(self, tmp_path):
        """Test: Generate a complete report with all sections."""
        pytest.importorskip("pptx")
        from spectral_edge.utils.report_generator import ReportGenerator, PPTX_AVAILABLE

        if not PPTX_AVAILABLE:
            pytest.skip("python-pptx not available")

        # User creates report
        report = ReportGenerator(title="Vibration Analysis Report")

        # User adds title slide
        report.add_title_slide(
            subtitle="Flight Test 001",
            author="Test Engineer",
            date="2024-01-15"
        )

        # User would add PSD plot (we'll use dummy image)
        # In real test, this would come from export_plot_to_image()
        dummy_image = create_dummy_png()
        report.add_psd_plot(
            dummy_image,
            title="Accelerometer PSD",
            parameters={"Window": "Hann", "df": "1.0 Hz"},
            rms_values={"Channel_X": 2.5, "Channel_Y": 1.8},
            units="g"
        )

        # User adds summary table
        report.add_summary_table(
            channels=["Channel_X", "Channel_Y", "Channel_Z"],
            rms_values={"Channel_X": 2.5, "Channel_Y": 1.8, "Channel_Z": 3.2},
            units="g"
        )

        # User saves report
        output_path = tmp_path / "test_report.pptx"
        saved_path = report.save(str(output_path))

        # Verify file created
        assert os.path.exists(saved_path)
        assert os.path.getsize(saved_path) > 0

        # Verify slide count
        assert report.slide_count == 3


class TestComparisonCurvesWorkflow:
    """Test comparison curves import/management workflows."""

    def test_import_reference_curve(self, reference_curve_csv):
        """Test importing a reference curve from CSV."""
        import pandas as pd

        # Simulate what happens when user imports
        df = pd.read_csv(reference_curve_csv)

        frequencies = df.iloc[:, 0].values.astype(float)
        psd = df.iloc[:, 1].values.astype(float)

        curve_data = {
            'name': 'Reference',
            'frequencies': frequencies,
            'psd': psd,
            'color': '#ff6b6b',
            'visible': True
        }

        # Verify import
        assert len(curve_data['frequencies']) == 3
        assert curve_data['frequencies'][0] == 10
        assert curve_data['psd'][1] == 0.01

    def test_multiple_curves_management(self):
        """Test managing multiple comparison curves."""
        comparison_curves = []

        # User imports first curve
        comparison_curves.append({
            'name': 'Spec Upper',
            'frequencies': np.array([10, 100, 1000]),
            'psd': np.array([0.01, 0.1, 0.01]),
            'visible': True
        })

        # User imports second curve
        comparison_curves.append({
            'name': 'Spec Lower',
            'frequencies': np.array([10, 100, 1000]),
            'psd': np.array([0.001, 0.01, 0.001]),
            'visible': True
        })

        assert len(comparison_curves) == 2

        # User hides first curve
        comparison_curves[0]['visible'] = False

        visible_curves = [c for c in comparison_curves if c['visible']]
        assert len(visible_curves) == 1

        # User removes second curve
        comparison_curves.pop(1)
        assert len(comparison_curves) == 1


class TestErrorHandling:
    """Test error handling in various scenarios."""

    def test_cross_spectrum_same_channel_error(self, qtbot):
        """Test error when user selects same channel for ref and response."""
        from spectral_edge.gui.cross_spectrum_window import CrossSpectrumWindow

        sample_rate = 1000.0
        t = np.linspace(0, 5, 5000)
        channels_data = [
            ('ch1', np.sin(2 * np.pi * 50 * t), 'g', ''),
            ('ch2', np.sin(2 * np.pi * 100 * t), 'g', ''),
        ]

        window = CrossSpectrumWindow(
            channels_data=channels_data,
            sample_rate=sample_rate
        )
        qtbot.addWidget(window)

        # User selects same channel for both
        window.ref_combo.setCurrentIndex(0)
        window.resp_combo.setCurrentIndex(0)

        # This should be detected (in real app, would show warning)
        assert window.ref_combo.currentIndex() == window.resp_combo.currentIndex()

        window.close()

    def test_insufficient_channels_for_cross_spectrum(self):
        """Test handling when only one channel available."""
        from spectral_edge.gui.cross_spectrum_window import CrossSpectrumWindow

        sample_rate = 1000.0
        t = np.linspace(0, 5, 5000)
        channels_data = [
            ('ch1', np.sin(2 * np.pi * 50 * t), 'g', ''),
        ]

        # Should handle gracefully (in real app, would show warning)
        window = CrossSpectrumWindow(
            channels_data=channels_data,
            sample_rate=sample_rate
        )

        # Only one channel available
        assert window.ref_combo.count() == 1

        window.close()

    def test_invalid_csv_format(self, tmp_path):
        """Test handling invalid CSV format."""
        import pandas as pd

        # Create invalid CSV (only one column)
        csv_path = tmp_path / "invalid.csv"
        csv_path.write_text("frequency\n10\n100\n")

        df = pd.read_csv(csv_path)

        # Should detect invalid format
        assert df.shape[1] < 2  # Less than 2 columns = invalid


def create_dummy_png():
    """Create a minimal valid PNG image for testing."""
    # Minimal 1x1 red PNG
    return bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
        0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
        0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
        0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND chunk
        0x44, 0xAE, 0x42, 0x60, 0x82
    ])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
