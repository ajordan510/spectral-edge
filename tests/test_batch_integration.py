"""
Integration tests for batch processor.

This module provides end-to-end integration tests for the batch processor,
testing the complete workflow from data loading through output generation.

Author: SpectralEdge Development Team
"""

import os
import sys
import tempfile
import shutil
import numpy as np
import h5py
import pytest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Check for optional dependencies
try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

from spectral_edge.batch.config import (
    BatchConfig, PSDConfig, FilterConfig, SpectrogramConfig,
    DisplayConfig, OutputConfig, EventDefinition
)
from spectral_edge.batch.processor import BatchProcessor
from spectral_edge.batch.hdf5_output import write_psds_to_hdf5

# Conditionally import excel_output only if openpyxl is available
if OPENPYXL_AVAILABLE:
    from spectral_edge.batch.excel_output import export_to_excel


class TestBatchProcessorIntegration:
    """Integration tests for batch processor."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_hdf5_file(self, temp_dir):
        """Create sample HDF5 file with test data."""
        file_path = os.path.join(temp_dir, "test_flight.h5")
        
        # Create sample data
        duration = 10.0  # seconds
        sample_rate = 1000.0  # Hz
        num_samples = int(duration * sample_rate)
        time = np.linspace(0, duration, num_samples)
        
        # Create two channels with different frequencies
        freq1 = 50.0  # Hz
        freq2 = 100.0  # Hz
        signal1 = 2.0 * np.sin(2 * np.pi * freq1 * time) + 0.5 * np.random.randn(num_samples)
        signal2 = 1.5 * np.sin(2 * np.pi * freq2 * time) + 0.3 * np.random.randn(num_samples)
        
        # Create HDF5 file
        with h5py.File(file_path, 'w') as f:
            flight_group = f.create_group('flight_0001')
            channels_group = flight_group.create_group('channels')
            
            # Channel 1
            ch1_dataset = channels_group.create_dataset('accel_x', data=signal1)
            ch1_dataset.attrs['sample_rate'] = sample_rate
            ch1_dataset.attrs['units'] = 'g'
            ch1_dataset.attrs['time_offset'] = 0.0
            
            # Channel 2
            ch2_dataset = channels_group.create_dataset('accel_y', data=signal2)
            ch2_dataset.attrs['sample_rate'] = sample_rate
            ch2_dataset.attrs['units'] = 'g'
            ch2_dataset.attrs['time_offset'] = 0.0
        
        return file_path
    
    @pytest.fixture
    def sample_csv_files(self, temp_dir):
        """Create sample CSV files with test data."""
        # Create two CSV files
        csv_files = []
        
        for i in range(2):
            file_path = os.path.join(temp_dir, f"test_data_{i+1}.csv")
            
            # Create sample data
            duration = 10.0  # seconds
            sample_rate = 1000.0  # Hz
            num_samples = int(duration * sample_rate)
            time = np.linspace(0, duration, num_samples)
            
            # Create signals
            freq = 50.0 + i * 50.0  # 50 Hz and 100 Hz
            signal = 2.0 * np.sin(2 * np.pi * freq * time) + 0.5 * np.random.randn(num_samples)
            
            # Write CSV
            with open(file_path, 'w') as f:
                f.write("Time (s),Accel (g)\n")
                for t, s in zip(time, signal):
                    f.write(f"{t:.6f},{s:.6f}\n")
            
            csv_files.append(file_path)
        
        return csv_files
    
    @pytest.mark.skipif(not OPENPYXL_AVAILABLE, reason="openpyxl not installed")
    def test_hdf5_full_workflow(self, sample_hdf5_file, temp_dir):
        """Test complete workflow with HDF5 source."""
        # Create configuration
        config = BatchConfig(
            source_type="hdf5",
            source_files=[sample_hdf5_file],
            selected_channels=[("flight_0001", "accel_x"), ("flight_0001", "accel_y")],
            process_full_duration=True,
            events=[],
            psd_config=PSDConfig(
                method="welch",
                window="hann",
                overlap_percent=50,
                desired_df=1.0,
                use_efficient_fft=True,
                freq_min=20.0,
                freq_max=500.0,
                frequency_spacing="linear",
                remove_running_mean=True
            ),
            filter_config=FilterConfig(enabled=False),
            spectrogram_config=SpectrogramConfig(enabled=False),
            display_config=DisplayConfig(),
            output_config=OutputConfig(
                excel_enabled=True,
                csv_enabled=True,
                powerpoint_enabled=True,
                hdf5_writeback_enabled=True,
                output_directory=temp_dir
            )
        )
        
        # Run batch processor
        processor = BatchProcessor(config)
        result = processor.process()
        
        # Verify results
        assert len(result.errors) == 0, f"Processing errors: {result.errors}"
        assert len(result.channel_results) == 2, "Should process 2 channels"

        # Check that PSDs were calculated
        for channel_key, events in result.channel_results.items():
            assert "full_duration" in events, f"Missing full_duration for {channel_key}"
            event_result = events["full_duration"]
            assert event_result['frequencies'] is not None
            assert event_result['psd'] is not None
            assert event_result['metadata']['rms'] > 0

        # Generate outputs
        excel_path = export_to_excel(result, temp_dir)
        assert os.path.exists(excel_path), "Excel file not created"

        # Verify HDF5 write-back
        write_psds_to_hdf5(result, sample_hdf5_file)

        # Check that processed_psds group was created
        with h5py.File(sample_hdf5_file, 'r') as f:
            assert 'flight_0001/processed_psds' in f, "processed_psds group not created"
            psd_group = f['flight_0001/processed_psds/full_duration']
            assert 'accel_x' in psd_group, "accel_x PSD not saved"
            assert 'accel_y' in psd_group, "accel_y PSD not saved"
        
        print(f"✅ HDF5 full workflow test passed")
        print(f"   - Processed {len(result.channel_results)} channels")
        print(f"   - Generated Excel: {excel_path}")
        print(f"   - HDF5 write-back successful")
    
    @pytest.mark.skipif(not OPENPYXL_AVAILABLE, reason="openpyxl not installed")
    def test_hdf5_event_based_workflow(self, sample_hdf5_file, temp_dir):
        """Test event-based processing with HDF5 source."""
        # Create configuration with events
        config = BatchConfig(
            source_type="hdf5",
            source_files=[sample_hdf5_file],
            selected_channels=[("flight_0001", "accel_x")],
            process_full_duration=False,
            events=[
                EventDefinition(name="Event1", start_time=0.0, end_time=3.0, description="First 3 seconds"),
                EventDefinition(name="Event2", start_time=5.0, end_time=8.0, description="Middle 3 seconds")
            ],
            psd_config=PSDConfig(),
            filter_config=FilterConfig(enabled=False),
            spectrogram_config=SpectrogramConfig(enabled=False),
            display_config=DisplayConfig(),
            output_config=OutputConfig(
                excel_enabled=True,
                csv_enabled=False,
                powerpoint_enabled=False,
                hdf5_writeback_enabled=False,
                output_directory=temp_dir
            )
        )
        
        # Run batch processor
        processor = BatchProcessor(config)
        result = processor.process()
        
        # Verify results
        assert len(result.errors) == 0, f"Processing errors: {result.errors}"
        assert len(result.channel_results) == 1, "Should process 1 channel"
        
        # Check that both events were processed
        channel_result = result.channel_results[("flight_0001", "accel_x")]
        assert "Event1" in channel_result, "Event1 not processed"
        assert "Event2" in channel_result, "Event2 not processed"
        
        # Generate Excel output
        excel_path = export_to_excel(result, temp_dir)
        assert os.path.exists(excel_path), "Excel file not created"

        print(f"✅ HDF5 event-based workflow test passed")
        print(f"   - Processed 2 events for 1 channel")
        print(f"   - Generated Excel: {excel_path}")
    
    @pytest.mark.skipif(not OPENPYXL_AVAILABLE, reason="openpyxl not installed")
    def test_csv_workflow(self, sample_csv_files, temp_dir):
        """Test complete workflow with CSV source."""
        # Create configuration
        config = BatchConfig(
            source_type="csv",
            source_files=sample_csv_files,
            selected_channels=[],  # Not used for CSV
            process_full_duration=True,
            events=[],
            psd_config=PSDConfig(
                method="welch",
                window="hann",
                overlap_percent=50,
                desired_df=1.0,
                use_efficient_fft=True,
                freq_min=20.0,
                freq_max=500.0,
                frequency_spacing="linear",
                remove_running_mean=True
            ),
            filter_config=FilterConfig(enabled=False),
            spectrogram_config=SpectrogramConfig(enabled=False),
            display_config=DisplayConfig(),
            output_config=OutputConfig(
                excel_enabled=True,
                csv_enabled=True,
                powerpoint_enabled=False,
                hdf5_writeback_enabled=False,
                output_directory=temp_dir
            )
        )
        
        # Run batch processor
        processor = BatchProcessor(config)
        result = processor.process()
        
        # Verify results
        assert len(result.errors) == 0, f"Processing errors: {result.errors}"
        assert len(result.channel_results) == 2, "Should process 2 CSV files"
        
        # Generate outputs
        excel_path = export_to_excel(result, temp_dir)
        assert os.path.exists(excel_path), "Excel file not created"

        print(f"✅ CSV workflow test passed")
        print(f"   - Processed {len(result.channel_results)} CSV files")
        print(f"   - Generated Excel: {excel_path}")
    
    def test_filtering_workflow(self, sample_hdf5_file, temp_dir):
        """Test workflow with filtering enabled."""
        # Create configuration with filtering
        config = BatchConfig(
            source_type="hdf5",
            source_files=[sample_hdf5_file],
            selected_channels=[("flight_0001", "accel_x")],
            process_full_duration=True,
            events=[],
            psd_config=PSDConfig(),
            filter_config=FilterConfig(
                enabled=True,
                filter_type="lowpass",
                filter_design="butterworth",
                filter_order=4,
                cutoff_low=10.0,
                cutoff_high=200.0
            ),
            spectrogram_config=SpectrogramConfig(enabled=False),
            display_config=DisplayConfig(),
            output_config=OutputConfig(
                excel_enabled=True,
                csv_enabled=False,
                powerpoint_enabled=False,
                hdf5_writeback_enabled=False,
                output_directory=temp_dir
            )
        )
        
        # Run batch processor
        processor = BatchProcessor(config)
        result = processor.process()
        
        # Verify results
        assert len(result.errors) == 0, f"Processing errors: {result.errors}"
        assert len(result.channel_results) == 1, "Should process 1 channel"
        
        # Check metadata indicates filtering was applied
        channel_result = result.channel_results[("flight_0001", "accel_x")]
        event_result = channel_result["full_duration"]
        assert event_result['metadata']['filter_applied'] == True, "Filter not applied"
        
        print(f"✅ Filtering workflow test passed")
        print(f"   - Filter applied successfully")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
