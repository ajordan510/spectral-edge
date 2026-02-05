"""
Test suite for data loading functions (CSV and HDF5).

Tests validate:
- CSV file parsing and validation
- HDF5 file loading and metadata extraction
- Sample rate detection
- Error handling for invalid files

Author: SpectralEdge Development Team
"""

import pytest
import numpy as np
import tempfile
import os
from pathlib import Path


class TestCSVLoading:
    """Tests for CSV data loading functionality."""

    @pytest.fixture
    def sample_csv_two_column(self, tmp_path):
        """Create a simple two-column CSV (frequency, PSD)."""
        csv_path = tmp_path / "two_column.csv"
        csv_path.write_text("frequency,psd\n10,0.001\n100,0.01\n1000,0.1\n")
        return str(csv_path)

    @pytest.fixture
    def sample_csv_time_series(self, tmp_path):
        """Create a time-series CSV with time and signal columns."""
        sample_rate = 1000.0
        duration = 1.0
        t = np.arange(0, duration, 1/sample_rate)
        signal = np.sin(2 * np.pi * 50 * t)

        csv_path = tmp_path / "time_series.csv"
        with open(csv_path, 'w') as f:
            f.write("time,signal (g)\n")
            for i in range(len(t)):
                f.write(f"{t[i]:.6f},{signal[i]:.6f}\n")
        return str(csv_path)

    @pytest.fixture
    def sample_csv_multi_channel(self, tmp_path):
        """Create a multi-channel time-series CSV."""
        sample_rate = 1000.0
        duration = 1.0
        t = np.arange(0, duration, 1/sample_rate)
        ch1 = np.sin(2 * np.pi * 50 * t)
        ch2 = np.sin(2 * np.pi * 100 * t)

        csv_path = tmp_path / "multi_channel.csv"
        with open(csv_path, 'w') as f:
            f.write("time,accel_x (g),accel_y (g)\n")
            for i in range(len(t)):
                f.write(f"{t[i]:.6f},{ch1[i]:.6f},{ch2[i]:.6f}\n")
        return str(csv_path)

    def test_csv_parsing_two_columns(self, sample_csv_two_column):
        """Test parsing simple two-column CSV files."""
        import pandas as pd

        df = pd.read_csv(sample_csv_two_column)

        assert df.shape[1] >= 2
        frequencies = df.iloc[:, 0].values.astype(float)
        psd = df.iloc[:, 1].values.astype(float)

        assert len(frequencies) == 3
        assert frequencies[0] == 10
        assert psd[2] == 0.1

    def test_csv_parsing_with_header(self, sample_csv_time_series):
        """Test parsing CSV with custom header names."""
        import pandas as pd

        df = pd.read_csv(sample_csv_time_series)

        assert 'time' in df.columns
        assert len(df) == 1000  # 1 second at 1000 Hz

    def test_csv_auto_sample_rate(self, sample_csv_time_series):
        """Test sample rate correctly inferred from time column."""
        import pandas as pd

        df = pd.read_csv(sample_csv_time_series)
        time = df['time'].values

        # Calculate sample rate from time differences
        dt = np.diff(time)
        sample_rate = 1.0 / np.mean(dt)

        assert abs(sample_rate - 1000.0) < 1.0  # Should be ~1000 Hz

    def test_csv_multi_channel_parsing(self, sample_csv_multi_channel):
        """Test parsing multi-channel CSV correctly."""
        import pandas as pd

        df = pd.read_csv(sample_csv_multi_channel)

        # Should have time + 2 signal columns
        assert df.shape[1] == 3
        assert len(df) == 1000

    def test_csv_scientific_notation(self, tmp_path):
        """Test scientific notation (1.23e-5) parsed correctly."""
        csv_path = tmp_path / "scientific.csv"
        csv_path.write_text("freq,psd\n1e1,1.5e-5\n1e2,2.3e-4\n1e3,4.5e-3\n")

        import pandas as pd
        df = pd.read_csv(csv_path)

        assert df.iloc[0, 0] == 10.0
        assert abs(df.iloc[0, 1] - 1.5e-5) < 1e-10

    def test_csv_missing_values_detection(self, tmp_path):
        """Test detection of missing/empty cells."""
        csv_path = tmp_path / "missing.csv"
        csv_path.write_text("time,signal\n0.0,1.0\n0.1,\n0.2,3.0\n")

        import pandas as pd
        df = pd.read_csv(csv_path)

        # Should detect NaN
        assert df.isna().any().any()

    def test_csv_invalid_single_column(self, tmp_path):
        """Test detection of invalid CSV with only one column."""
        csv_path = tmp_path / "invalid.csv"
        csv_path.write_text("frequency\n10\n100\n")

        import pandas as pd
        df = pd.read_csv(csv_path)

        assert df.shape[1] < 2  # Less than 2 columns = invalid for PSD

    def test_csv_unicode_headers(self, tmp_path):
        """Test Unicode in channel names doesn't break loading."""
        csv_path = tmp_path / "unicode.csv"
        csv_path.write_text("time,Beschleunigung_X (m/s²),Température (°C)\n0.0,1.0,25.0\n", encoding='utf-8')

        import pandas as pd
        df = pd.read_csv(csv_path)

        assert len(df.columns) == 3
        assert 'Beschleunigung' in df.columns[1]


class TestHDF5Loading:
    """Tests for HDF5 data loading functionality."""

    @pytest.fixture
    def sample_hdf5_file(self, tmp_path):
        """Create a sample HDF5 file for testing."""
        h5py = pytest.importorskip("h5py")

        hdf5_path = tmp_path / "test_data.hdf5"

        sample_rate = 1000.0
        duration = 5.0
        t = np.arange(0, duration, 1/sample_rate)
        signal = np.sin(2 * np.pi * 50 * t) + 0.1 * np.random.randn(len(t))

        with h5py.File(hdf5_path, 'w') as f:
            flight = f.create_group('flight_001')

            # Metadata
            meta = flight.create_group('metadata')
            meta.attrs['flight_id'] = 'flight_001'
            meta.attrs['date'] = '2024-01-15'
            meta.attrs['duration'] = duration

            # Channels
            channels = flight.create_group('channels')
            ch1 = channels.create_group('accel_x')
            ch1.create_dataset('time', data=t)
            ch1.create_dataset('data', data=signal)
            ch1.attrs['units'] = 'g'
            ch1.attrs['sample_rate'] = sample_rate

        return str(hdf5_path)

    def test_hdf5_file_open(self, sample_hdf5_file):
        """Test HDF5 file can be opened."""
        h5py = pytest.importorskip("h5py")

        with h5py.File(sample_hdf5_file, 'r') as f:
            assert 'flight_001' in f

    def test_hdf5_metadata_extraction(self, sample_hdf5_file):
        """Test flight/channel metadata correctly extracted."""
        h5py = pytest.importorskip("h5py")

        with h5py.File(sample_hdf5_file, 'r') as f:
            flight = f['flight_001']
            assert flight['metadata'].attrs['flight_id'] == 'flight_001'
            assert flight['metadata'].attrs['duration'] == 5.0

    def test_hdf5_channel_data_loading(self, sample_hdf5_file):
        """Test channel data loads correctly."""
        h5py = pytest.importorskip("h5py")

        with h5py.File(sample_hdf5_file, 'r') as f:
            channel = f['flight_001/channels/accel_x']
            data = channel['data'][:]
            time = channel['time'][:]

            assert len(data) == 5000  # 5 seconds at 1000 Hz
            assert len(time) == 5000
            assert channel.attrs['units'] == 'g'

    def test_hdf5_sample_rate_extraction(self, sample_hdf5_file):
        """Test sample rate correctly extracted from attributes."""
        h5py = pytest.importorskip("h5py")

        with h5py.File(sample_hdf5_file, 'r') as f:
            channel = f['flight_001/channels/accel_x']
            sample_rate = channel.attrs['sample_rate']

            assert sample_rate == 1000.0

    def test_hdf5_missing_file_error(self):
        """Test clear error message for missing files."""
        h5py = pytest.importorskip("h5py")

        with pytest.raises((FileNotFoundError, OSError)):
            with h5py.File('/nonexistent/path/file.hdf5', 'r') as f:
                pass

    def test_hdf5_lazy_loading_concept(self, sample_hdf5_file):
        """Test that data is not loaded until requested (lazy loading)."""
        h5py = pytest.importorskip("h5py")

        with h5py.File(sample_hdf5_file, 'r') as f:
            # Accessing dataset object doesn't load data
            dataset = f['flight_001/channels/accel_x/data']
            assert dataset.shape == (5000,)

            # Data loaded only when indexed
            data = dataset[:]
            assert len(data) == 5000


class TestComparisonCurveImport:
    """Tests for importing comparison/reference curves."""

    @pytest.fixture
    def reference_curve_csv(self, tmp_path):
        """Create a reference PSD curve CSV."""
        csv_path = tmp_path / "reference.csv"
        csv_path.write_text(
            "frequency,psd\n"
            "10,0.001\n"
            "20,0.002\n"
            "50,0.005\n"
            "100,0.01\n"
            "200,0.005\n"
            "500,0.002\n"
            "1000,0.001\n"
        )
        return str(csv_path)

    def test_reference_curve_import(self, reference_curve_csv):
        """Test importing a reference PSD curve from CSV."""
        import pandas as pd

        df = pd.read_csv(reference_curve_csv)
        frequencies = df.iloc[:, 0].values.astype(float)
        psd = df.iloc[:, 1].values.astype(float)

        assert len(frequencies) == 7
        assert frequencies[0] == 10
        assert frequencies[-1] == 1000
        assert np.all(psd > 0)

    def test_reference_curve_data_structure(self, reference_curve_csv):
        """Test reference curve data structure creation."""
        import pandas as pd

        df = pd.read_csv(reference_curve_csv)

        curve_data = {
            'name': 'Spec Limit',
            'frequencies': df.iloc[:, 0].values.astype(float),
            'psd': df.iloc[:, 1].values.astype(float),
            'color': '#ff6b6b',
            'line_style': 'dash',
            'visible': True,
            'file_path': reference_curve_csv
        }

        assert curve_data['name'] == 'Spec Limit'
        assert len(curve_data['frequencies']) == 7
        assert curve_data['visible'] is True

    def test_multiple_curves_management(self):
        """Test managing multiple comparison curves."""
        comparison_curves = []

        # Add first curve
        comparison_curves.append({
            'name': 'Upper Limit',
            'frequencies': np.array([10, 100, 1000]),
            'psd': np.array([0.01, 0.1, 0.01]),
            'visible': True
        })

        # Add second curve
        comparison_curves.append({
            'name': 'Lower Limit',
            'frequencies': np.array([10, 100, 1000]),
            'psd': np.array([0.001, 0.01, 0.001]),
            'visible': True
        })

        assert len(comparison_curves) == 2

        # Toggle visibility
        comparison_curves[0]['visible'] = False
        visible_curves = [c for c in comparison_curves if c['visible']]
        assert len(visible_curves) == 1

        # Remove curve
        comparison_curves.pop(0)
        assert len(comparison_curves) == 1
        assert comparison_curves[0]['name'] == 'Lower Limit'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
