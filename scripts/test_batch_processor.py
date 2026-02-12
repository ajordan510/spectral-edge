"""
Test script for batch PSD processor

Runs a comprehensive test of the batch processor with:
- 20+ channels from large test HDF5 file
- All output formats enabled (Excel, CSV, PowerPoint, HDF5 writeback)
- Full duration and event-based processing
- Performance timing

Author: SpectralEdge Development Team
Date: 2026-02-04
"""

import sys
import os
import time
import logging
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from spectral_edge.batch.config import (
    BatchConfig, FilterConfig, PSDConfig, SpectrogramConfig,
    DisplayConfig, OutputConfig, EventDefinition
)
from spectral_edge.batch.processor import BatchProcessor
from spectral_edge.utils.hdf5_loader import HDF5FlightDataLoader
from spectral_edge.utils.logging_config import setup_logging


def main():
    """Run batch processor test."""
    # Setup logging
    log_file = setup_logging(log_level="DEBUG")
    print(f"Log file: {log_file}")

    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("BATCH PROCESSOR COMPREHENSIVE TEST")
    logger.info("=" * 80)

    # Test parameters
    hdf5_file = "data/large_test_flight_data.hdf5"
    output_dir = "data/batch_test_output"

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Verify HDF5 file exists
    if not os.path.exists(hdf5_file):
        print(f"ERROR: HDF5 file not found: {hdf5_file}")
        print("Run: python scripts/generate_large_test_hdf5.py first")
        return 1

    print(f"\n{'='*60}")
    print("TEST CONFIGURATION")
    print(f"{'='*60}")
    print(f"HDF5 File: {hdf5_file}")
    print(f"Output Dir: {output_dir}")

    # Load HDF5 file and select channels
    print("\nLoading HDF5 file and selecting channels...")
    loader_start = time.perf_counter()

    try:
        loader = HDF5FlightDataLoader(hdf5_file)
        print(f"  Flights available: {list(loader.flights.keys())}")
    except Exception as e:
        print(f"ERROR loading HDF5: {e}")
        return 1

    loader_time = time.perf_counter() - loader_start
    print(f"  HDF5 metadata load time: {loader_time:.2f}s")

    # Select 24 channels (from multiple flights)
    # 8 channels from flight_001, 8 from flight_002, 8 from flight_003
    selected_channels = []
    flights_to_use = ['flight_001', 'flight_002', 'flight_003']
    channels_per_flight = 8

    for flight_key in flights_to_use:
        if flight_key in loader.channels:
            channels = list(loader.channels[flight_key].keys())[:channels_per_flight]
            for ch in channels:
                selected_channels.append((flight_key, ch))

    print(f"\nSelected {len(selected_channels)} channels:")
    for flight_key, ch_key in selected_channels[:5]:
        print(f"  - {flight_key}/{ch_key}")
    print(f"  ... and {len(selected_channels) - 5} more")

    loader.close()

    # Create batch configuration
    config = BatchConfig(
        config_name="comprehensive_test",
        source_type="hdf5",
        source_files=[hdf5_file],
        selected_channels=selected_channels,
        process_full_duration=False,  # Use events for faster test
        events=[
            EventDefinition(
                name="event_1_takeoff",
                start_time=10.0,
                end_time=30.0,
                description="Takeoff phase"
            ),
            EventDefinition(
                name="event_2_cruise",
                start_time=50.0,
                end_time=100.0,
                description="Cruise phase"
            ),
            EventDefinition(
                name="event_3_landing",
                start_time=150.0,
                end_time=180.0,
                description="Landing phase"
            )
        ],
        filter_config=FilterConfig(
            enabled=True,
            filter_type="bandpass",
            cutoff_low=10.0,
            cutoff_high=5000.0
        ),
        psd_config=PSDConfig(
            method="welch",
            window="hann",
            overlap_percent=50.0,
            use_efficient_fft=True,
            desired_df=1.0,
            freq_min=10.0,
            freq_max=5000.0,
            frequency_spacing="linear"
        ),
        spectrogram_config=SpectrogramConfig(
            enabled=True,
            desired_df=2.0,
            overlap_percent=50.0,
            snr_threshold=20.0,
            colormap="viridis"
        ),
        display_config=DisplayConfig(
            psd_auto_scale=True,
            psd_show_legend=True,
            psd_show_grid=True
        ),
        output_config=OutputConfig(
            excel_enabled=True,
            csv_enabled=True,
            powerpoint_enabled=True,
            hdf5_writeback_enabled=True,
            output_directory=output_dir
        )
    )

    print(f"\n{'='*60}")
    print("BATCH CONFIGURATION")
    print(f"{'='*60}")
    print(f"  Channels: {len(selected_channels)}")
    print(f"  Events: {len(config.events)}")
    print(f"  Total PSD calculations: {len(selected_channels) * len(config.events)}")
    print(f"  Filter: {'Enabled' if config.filter_config.enabled else 'Disabled'}")
    print(f"  Spectrogram: {'Enabled' if config.spectrogram_config.enabled else 'Disabled'}")
    print(f"  Outputs: Excel={config.output_config.excel_enabled}, "
          f"CSV={config.output_config.csv_enabled}, "
          f"PPT={config.output_config.powerpoint_enabled}, "
          f"HDF5={config.output_config.hdf5_writeback_enabled}")

    # Run batch processing
    print(f"\n{'='*60}")
    print("RUNNING BATCH PROCESSING")
    print(f"{'='*60}")

    total_start = time.perf_counter()

    # Track detailed timing
    timing_log = []

    def progress_callback(progress_info):
        """Track progress with timing."""
        timing_log.append({
            'time': time.perf_counter() - total_start,
            'progress': progress_info.percent_complete,
            'message': str(progress_info)
        })
        print(f"  [{progress_info.percent_complete:3.0f}%] {progress_info}")

    try:
        processor = BatchProcessor(config, progress_callback=progress_callback)
        result = processor.process()
    except Exception as e:
        print(f"\nERROR during processing: {e}")
        import traceback
        traceback.print_exc()
        return 1

    processing_time = time.perf_counter() - total_start

    # Print results
    print(f"\n{'='*60}")
    print("PROCESSING RESULTS")
    print(f"{'='*60}")
    print(f"  Total time: {processing_time:.2f}s")
    print(f"  Channels processed: {result.channels_processed}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Warnings: {len(result.warnings)}")

    if result.errors:
        print("\n  ERRORS:")
        for err in result.errors[:10]:
            print(f"    - {err}")
        if len(result.errors) > 10:
            print(f"    ... and {len(result.errors) - 10} more")

    if result.warnings:
        print("\n  WARNINGS:")
        for warn in result.warnings[:10]:
            print(f"    - {warn}")
        if len(result.warnings) > 10:
            print(f"    ... and {len(result.warnings) - 10} more")

    # Now generate outputs
    print(f"\n{'='*60}")
    print("GENERATING OUTPUTS")
    print(f"{'='*60}")

    output_times = {}

    # Excel output
    if config.output_config.excel_enabled:
        print("\n  Generating Excel output...")
        excel_start = time.perf_counter()
        try:
            from spectral_edge.batch.excel_output import export_to_excel
            excel_path = export_to_excel(result, output_dir)
            output_times['excel'] = time.perf_counter() - excel_start
            print(f"    Excel: {excel_path} ({output_times['excel']:.2f}s)")
        except Exception as e:
            print(f"    Excel ERROR: {e}")
            import traceback
            traceback.print_exc()

    # CSV output
    if config.output_config.csv_enabled:
        print("\n  Generating CSV output...")
        csv_start = time.perf_counter()
        try:
            from spectral_edge.batch.csv_output import export_to_csv
            csv_paths = export_to_csv(result, output_dir)
            output_times['csv'] = time.perf_counter() - csv_start
            print(f"    CSV: {len(csv_paths)} files ({output_times['csv']:.2f}s)")
        except Exception as e:
            print(f"    CSV ERROR: {e}")
            import traceback
            traceback.print_exc()

    # PowerPoint output
    if config.output_config.powerpoint_enabled:
        print("\n  Generating PowerPoint output...")
        ppt_start = time.perf_counter()
        try:
            from spectral_edge.batch.powerpoint_output import generate_powerpoint_report
            ppt_path = generate_powerpoint_report(result, output_dir, config)
            output_times['powerpoint'] = time.perf_counter() - ppt_start
            print(f"    PowerPoint: {ppt_path} ({output_times['powerpoint']:.2f}s)")
        except Exception as e:
            print(f"    PowerPoint ERROR: {e}")
            import traceback
            traceback.print_exc()

    # HDF5 writeback
    if config.output_config.hdf5_writeback_enabled:
        print("\n  Writing PSDs back to HDF5...")
        hdf5_start = time.perf_counter()
        try:
            from spectral_edge.batch.hdf5_output import write_psds_to_hdf5
            write_psds_to_hdf5(result, hdf5_file)
            output_times['hdf5'] = time.perf_counter() - hdf5_start
            print(f"    HDF5 writeback: {output_times['hdf5']:.2f}s")
        except Exception as e:
            print(f"    HDF5 writeback ERROR: {e}")
            import traceback
            traceback.print_exc()

    total_time = time.perf_counter() - total_start

    # Print summary
    print(f"\n{'='*60}")
    print("PERFORMANCE SUMMARY")
    print(f"{'='*60}")
    print(f"  Processing: {processing_time:.2f}s")
    print(f"  Outputs:")
    for name, t in output_times.items():
        print(f"    - {name}: {t:.2f}s")
    print(f"  Total: {total_time:.2f}s")
    print(f"\n  Throughput: {len(selected_channels) * len(config.events) / total_time:.2f} PSD/s")

    # Check output files
    print(f"\n{'='*60}")
    print("OUTPUT FILES")
    print(f"{'='*60}")
    for f in os.listdir(output_dir):
        fpath = os.path.join(output_dir, f)
        size_kb = os.path.getsize(fpath) / 1024
        print(f"  {f}: {size_kb:.1f} KB")

    print(f"\n{'='*60}")
    print("TEST COMPLETE")
    print(f"{'='*60}")

    return 0 if len(result.errors) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
