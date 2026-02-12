"""
Unit Tests for Batch Processing Module

Tests the core batch processing engine, configuration system, and CSV loader.

Author: SpectralEdge Development Team
Date: 2026-02-02
"""

import pytest
import numpy as np
import tempfile
import json
from pathlib import Path

from spectral_edge.batch.config import (
    BatchConfig, PSDConfig, FilterConfig, SpectrogramConfig,
    OutputConfig, EventDefinition, PowerPointConfig, ReferenceCurveConfig
)
from spectral_edge.batch.csv_loader import (
    load_csv_files, detect_csv_format, _extract_units_from_name,
    _clean_channel_name, _interpolate_nans
)


class TestConfigClasses:
    """Test configuration dataclasses."""
    
    def test_filter_config_validation(self):
        """Test FilterConfig validation."""
        # Valid config
        config = FilterConfig(
            enabled=True,
            filter_type="lowpass",
            filter_design="butterworth",
            filter_order=4,
            cutoff_high=1000.0
        )
        config.validate()  # Should not raise
        
        # Invalid filter type
        config.filter_type = "invalid"
        with pytest.raises(ValueError):
            config.validate()

    def test_filter_config_accepts_user_override_fields(self):
        """User cutoff overrides should be accepted without hard-stop range checks."""
        config = FilterConfig(
            enabled=True,
            filter_type="bandpass",
            filter_design="butterworth",
            filter_order=4,
            user_highpass_hz=0.3,
            user_lowpass_hz=50000.0,
        )
        config.validate()  # Clamping happens later during processing, not config validation.
    
    def test_psd_config_validation(self):
        """Test PSDConfig validation."""
        # Valid config
        config = PSDConfig(
            method="welch",
            window="hann",
            overlap_percent=50.0,
            desired_df=1.0,
            freq_min=20.0,
            freq_max=2000.0
        )
        config.validate()  # Should not raise
        
        # Invalid frequency range
        config.freq_min = 3000.0
        with pytest.raises(ValueError):
            config.validate()
    
    def test_event_definition_validation(self):
        """Test EventDefinition validation."""
        # Valid event
        event = EventDefinition(
            name="liftoff",
            start_time=10.0,
            end_time=15.0
        )
        event.validate()  # Should not raise
        
        # Invalid time range
        event.start_time = 20.0
        with pytest.raises(ValueError):
            event.validate()
    
    def test_batch_config_save_load(self):
        """Test saving and loading batch configuration."""
        # Create config
        config = BatchConfig(
            source_type="csv",
            source_files=["test.csv"],
            config_name="test_config"
        )
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            config.save(temp_path)
            
            # Load and verify
            loaded_config = BatchConfig.load(temp_path)
            assert loaded_config.source_type == "csv"
            assert loaded_config.config_name == "test_config"
            assert len(loaded_config.source_files) == 1
        finally:
            Path(temp_path).unlink()

    def test_batch_config_reference_curves_roundtrip(self):
        """Test reference curve persistence in batch config save/load."""
        config = BatchConfig(
            source_type="csv",
            source_files=["test.csv"],
            powerpoint_config=PowerPointConfig(
                reference_curves=[
                    ReferenceCurveConfig(
                        name="Minimum Screening",
                        frequencies=[20.0, 80.0, 800.0, 2000.0],
                        psd=[0.01, 0.04, 0.04, 0.01],
                        enabled=True,
                        source="builtin",
                        builtin_id="minimum_screening",
                        color="#ff6b6b",
                        line_style="dashed",
                    ),
                    ReferenceCurveConfig(
                        name="Imported Curve",
                        frequencies=[30.0, 120.0, 900.0, 1800.0],
                        psd=[0.02, 0.05, 0.05, 0.02],
                        enabled=False,
                        source="imported",
                        file_path="curve.csv",
                        color="#4d96ff",
                        line_style="dashed",
                    ),
                ]
            ),
        )

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            config.save(temp_path)
            loaded_config = BatchConfig.load(temp_path)
            curves = loaded_config.powerpoint_config.reference_curves
            assert len(curves) == 2
            assert curves[0].builtin_id == "minimum_screening"
            assert curves[1].source == "imported"
            assert curves[1].enabled is False
        finally:
            Path(temp_path).unlink()


class TestCSVLoader:
    """Test CSV data loading functionality."""
    
    def test_extract_units_from_name(self):
        """Test unit extraction from column names."""
        assert _extract_units_from_name("accel_x (g)") == "g"
        assert _extract_units_from_name("pressure [psi]") == "psi"
        assert _extract_units_from_name("temperature") == ""
    
    def test_clean_channel_name(self):
        """Test channel name cleaning."""
        assert _clean_channel_name("accel_x (g)") == "accel_x"
        assert _clean_channel_name("pressure [psi]") == "pressure"
        assert _clean_channel_name("  temp  ") == "temp"
    
    def test_interpolate_nans(self):
        """Test NaN interpolation."""
        signal = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
        interpolated = _interpolate_nans(signal)
        
        assert not np.any(np.isnan(interpolated))
        assert np.isclose(interpolated[2], 3.0)
    
    def test_load_csv_with_header(self):
        """Test loading CSV file with header."""
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write("time,accel_x (g),accel_y (g)\n")
            for i in range(100):
                t = i * 0.001  # 1000 Hz
                f.write(f"{t},{np.sin(2*np.pi*10*t)},{np.cos(2*np.pi*10*t)}\n")
            temp_path = f.name
        
        try:
            # Load CSV
            data = load_csv_files([temp_path])
            
            assert temp_path in data
            channels = data[temp_path]
            
            assert "accel_x" in channels
            assert "accel_y" in channels
            
            time, signal, fs, units = channels["accel_x"]
            assert len(time) == 100
            assert len(signal) == 100
            assert np.isclose(fs, 1000.0, rtol=0.1)
            assert units == "g"
        finally:
            Path(temp_path).unlink()
    
    def test_detect_csv_format(self):
        """Test CSV format detection."""
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            f.write("time,channel_1,channel_2\n")
            for i in range(1000):
                t = i * 0.01  # 100 Hz
                f.write(f"{t},{i},{i*2}\n")
            temp_path = f.name
        
        try:
            # Detect format
            info = detect_csv_format(temp_path)
            
            assert info['has_header'] == True
            assert info['num_columns'] == 3
            assert info['num_rows'] == 1000
            assert np.isclose(info['estimated_sample_rate'], 100.0, rtol=0.1)
            assert np.isclose(info['estimated_duration'], 9.99, rtol=0.1)
        finally:
            Path(temp_path).unlink()


class TestBatchProcessor:
    """Test batch processing engine."""
    
    @pytest.fixture
    def sample_config(self):
        """Create a sample batch configuration."""
        return BatchConfig(
            source_type="csv",
            source_files=[],
            process_full_duration=True,
            psd_config=PSDConfig(
                method="welch",
                desired_df=1.0,
                freq_min=20.0,
                freq_max=2000.0
            )
        )
    
    def test_config_validation(self, sample_config):
        """Test that valid configuration passes validation."""
        # This should raise because no source files
        with pytest.raises(ValueError):
            sample_config.validate()
        
        # Add a dummy file path (validation will fail on file existence)
        sample_config.source_files = ["/nonexistent/file.csv"]
        with pytest.raises(ValueError):
            sample_config.validate()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
