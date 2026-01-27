# SpectralEdge - Quick Start Guide

## Overview

SpectralEdge is a professional signal processing suite for aerospace and vibration testing. It provides tools for Power Spectral Density (PSD) analysis, spectrogram generation, and event-based analysis.

## Installation

### Requirements
- Python 3.11 or higher
- Windows, Linux, or macOS

### Quick Install

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ajordan510/spectral-edge.git
   cd spectral-edge
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Windows
Double-click `run_spectral_edge.bat` or run from command prompt:
```cmd
run_spectral_edge.bat
```

### Linux/Mac
Run from terminal:
```bash
./run_spectral_edge.sh
```

### Alternative (All Platforms)
```bash
python -m spectral_edge.main
```

## First Time Setup

The application will automatically:
1. Check for required dependencies
2. Install missing packages (if needed)
3. Launch the SpectralEdge landing page

## Using the Application

### 1. Launch PSD Analysis Tool
- Click on "PSD Analysis" card on the landing page
- The PSD Analysis window will open

### 2. Load Data

#### Option A: Load HDF5 File (Recommended)
1. Click "Load HDF5 File" button
2. Select your HDF5 flight test data file
3. The Flight & Channel Navigator will open
4. Select flights and channels you want to analyze
5. Click "Load Selected"

#### Option B: Load CSV File
1. Click "Load CSV File" button
2. Select your CSV data file
3. Data will be loaded and displayed

### 3. Configure PSD Parameters
- **Method**: Choose between Welch's Method or Maxi-Max
- **Window**: Select window function (Hann, Hamming, etc.)
- **NFFT**: Set FFT size (power of 2)
- **Overlap**: Set overlap percentage
- **Detrend**: Enable/disable detrending

### 4. Calculate PSD
- Click "Calculate PSD" button
- Results will be displayed in the plot
- View in different formats:
  - Linear frequency
  - Octave bands (1/1, 1/3, 1/6, 1/12, 1/24)
  - Narrowband
  - Time history

### 5. Additional Features
- **Event Manager**: Define and analyze specific time segments
- **Spectrogram**: Generate time-frequency spectrograms
- **Export**: Save results and plots

## HDF5 File Format

SpectralEdge expects HDF5 files with the following structure:

```
file.hdf5
├── flight_001/
│   ├── metadata/
│   │   ├── @flight_id
│   │   ├── @date
│   │   └── @duration
│   └── channels/
│       ├── channel_name/
│       │   ├── time (dataset)
│       │   ├── data (dataset)
│       │   ├── @units
│       │   ├── @sample_rate
│       │   └── @location
```

### Required Metadata
- **Flight level**: flight_id, date, duration
- **Channel level**: units, sample_rate, location

## Troubleshooting

### "Module not found" error
```bash
pip install -r requirements.txt
```

### Application won't start
1. Check Python version: `python --version` (must be 3.11+)
2. Verify all dependencies installed: `pip list`
3. Try running directly: `python -m spectral_edge.main`

### HDF5 file won't load
1. Verify file structure matches expected format
2. Check that required metadata attributes exist
3. Review error messages in console

### Display issues on Linux
If you encounter Qt/display issues on Linux:
```bash
export QT_QPA_PLATFORM=xcb
python -m spectral_edge.main
```

## Sample Data

To test the application, you can generate sample HDF5 data:
```bash
python scripts/generate_large_test_hdf5.py
```

This creates a test file with:
- 7 flights
- 154 channels (22 per flight)
- Multiple sensor types
- 10 unique locations

## Features

### PSD Analysis
- Welch's method and Maxi-Max calculation
- Multiple window functions
- Octave band analysis (1/1 to 1/24)
- Event-based analysis
- Multi-channel comparison

### Spectrogram
- Time-frequency analysis
- Customizable frequency axis
- Colorbar with proper scaling
- Log/linear frequency scale

### Flight Navigator
- Browse flights and channels
- Search and filter capabilities
- Location-based navigation
- Saved selections

## Documentation

- **Enhanced Navigator**: See `ENHANCED_NAVIGATOR_README.md`
- **PSD Fixes**: See `FIXES_SUMMARY.md`
- **Spectrogram**: See `SPECTROGRAM_FIXES.md`

## Support

For issues or questions:
1. Check documentation in the `docs/` directory
2. Review troubleshooting section above
3. Check GitHub issues

## Version

Current Version: 2.0.0  
Last Updated: January 27, 2026

## License

[Your License Here]

---

**Ready to start? Run the application and explore the tools!**
