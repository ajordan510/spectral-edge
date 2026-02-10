# Epic 2: PSD Analysis Tool - Summary

## Overview

Epic 2 successfully delivers a fully functional Power Spectral Density (PSD) analysis tool for SpectralEdge. This epic focused on building the core signal processing capabilities, data loading infrastructure, and a professional GUI for interactive analysis.

## Deliverables

### Core Signal Processing Library

**File**: `spectral_edge/core/psd.py`

This module provides the mathematical foundation for PSD analysis with the following functions:

- **`calculate_psd_welch()`**: Implements Welch's method for PSD calculation with configurable parameters including window type, segment length, overlap, and FFT length. Supports both single-channel and multi-channel data.

- **`psd_to_db()`**: Converts PSD values from linear scale to decibel (dB) scale for better visualization of data spanning multiple orders of magnitude.

- **`calculate_rms_from_psd()`**: Calculates the Root Mean Square (RMS) value from PSD data, with optional frequency range filtering.

- **`get_window_options()`**: Provides descriptions of available window functions (Hann, Hamming, Blackman, Bartlett, Boxcar).

All functions include comprehensive docstrings explaining the theory, parameters, and usage examples.

### Data Loading Utilities

**File**: `spectral_edge/utils/data_loader.py`

This module handles CSV file loading and validation with the following capabilities:

- **`load_csv_data()`**: Loads time-series data from CSV files with automatic sample rate detection. Validates data integrity and handles various CSV formats.

- **`load_csv_data_simple()`**: Simplified loader for CSV files without time columns when the sample rate is known.

- **`get_file_info()`**: Quickly previews CSV file structure without loading all data.

- **`validate_data_for_analysis()`**: Ensures data meets minimum requirements for signal processing.

- **`DataLoadError`**: Custom exception class for data loading errors.

### PSD Analysis GUI

**File**: `spectral_edge/gui/psd_window.py`

A professional, aerospace-styled GUI window providing:

- **File Loading**: Browse and load CSV files with automatic validation and info display
- **Parameter Configuration**: 
  - Window type selection (Hann, Hamming, Blackman, Bartlett, Boxcar)
  - Segment length adjustment (64-8192 samples)
  - Overlap percentage control (0-90%)
  - dB scale toggle
- **Interactive Plotting**: PyQtGraph-based plot with zoom, pan, and logarithmic frequency axis
- **Results Display**: Shows channel name, RMS value, and frequency range
- **Real-time Calculation**: Instant PSD computation and visualization

### Landing Page Integration

**File**: `spectral_edge/gui/landing_page.py` (updated)

The landing page now launches the PSD Analysis tool when the corresponding card is clicked. The window management system ensures only one instance of each tool runs at a time.

### Comprehensive Test Suite

**File**: `tests/test_psd.py`

A thorough test suite with 11 test cases covering:

- Basic PSD calculation functionality
- Peak frequency detection accuracy
- Multi-frequency component identification
- Different window type validation
- Multi-channel data processing
- dB conversion accuracy
- RMS calculation from PSD
- Frequency range filtering
- Input validation and error handling

**Test Results**: All 11 tests passed successfully, validating the accuracy and reliability of the PSD calculation functions.

### Sample Data

**File**: `data/sample_vibration_data.csv`

A synthetic vibration signal for testing and demonstration purposes containing:
- Sample rate: 5000 Hz
- Duration: 10 seconds
- 2 channels (Accelerometer_X, Accelerometer_Y)
- Frequency components at 10, 60, 120, and 500 Hz
- Realistic noise

### Updated Dependencies

**File**: `requirements.txt` (updated)

Added `pandas` for CSV data handling.

## Technical Highlights

### Welch's Method Implementation

The PSD calculation uses Welch's method, which is the industry standard for spectral estimation. This method divides the signal into overlapping segments, applies a window function to each segment, computes the FFT, and averages the results. This approach significantly reduces variance (noise) in the PSD estimate compared to computing the FFT of the entire signal.

### Multi-Channel Support

The data loader and PSD calculation functions are designed to handle both single-channel and multi-channel data efficiently. The current GUI implementation processes one channel at a time, but the underlying functions support simultaneous processing of hundreds of channels.

### Robust Data Validation

The data loader includes extensive validation to ensure data quality:
- Checks for non-finite values (NaN, Inf)
- Validates time column monotonicity
- Detects and warns about non-uniform sampling
- Verifies minimum data duration requirements

### Professional GUI Design

The GUI follows the aerospace-inspired design theme established in Epic 1 with dark blues and grays, providing a professional appearance suitable for engineering applications.

## Usage Example

To use the PSD Analysis tool:

1. Launch SpectralEdge by running `run.bat` (Windows) or `run.sh` (Linux/macOS)
2. Click on the "PSD Analysis" card on the landing page
3. Click "Load CSV File" and select a data file (e.g., `data/sample_vibration_data.csv`)
4. Adjust parameters as needed (window type, segment length, overlap)
5. Click "Calculate PSD" to compute and display the power spectral density
6. Use mouse to zoom and pan the plot for detailed examination
7. Toggle "Display in dB" to switch between linear and logarithmic scales

## Code Quality

All code in Epic 2 follows best practices:

- **Comprehensive Documentation**: Every function includes detailed docstrings explaining purpose, parameters, returns, and usage
- **Type Hints**: Functions use type hints for better code clarity and IDE support
- **Error Handling**: Robust error handling with informative error messages
- **Modular Design**: Clear separation between calculation logic, data handling, and GUI
- **Extensive Comments**: Code includes inline comments explaining complex operations for novice Python users

## Future Enhancements (Epic 3+)

The foundation established in Epic 2 enables future enhancements:

- Multi-channel simultaneous display
- Report generation (PowerPoint with embedded plots)
- Batch processing of multiple files
- Advanced filtering options
- Save/export PSD results to HDF5
- HDF5 input file support
- Frequency band RMS calculations
- Peak detection and annotation

## Conclusion

Epic 2 successfully delivers a production-ready PSD analysis tool with professional-grade signal processing capabilities, an intuitive GUI, and comprehensive testing. The modular architecture ensures easy expansion and maintenance as the tool suite grows.
