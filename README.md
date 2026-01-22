# SpectralEdge

**SpectralEdge** is a professional-grade signal processing suite designed for engineers and scientists. It provides a graphical user interface (GUI) for interactive analysis, batch processing capabilities for large datasets, and a comprehensive library of signal processing functions.

## Features

- **Cross-Platform:** Compatible with both Linux and Windows.
- **Modular Design:** A library of core functions separate from the GUI, allowing for easy expansion and maintenance.
- **Advanced Plotting:** Interactive plots with features like zooming, panning, and data selection.
- **Report Generation:** Automatically generate reports in PowerPoint format with embedded plots.
- **Versatile Data Input:** Supports both CSV and HDF5 file formats.
- **High-Performance:** Optimized for handling high-rate data (5000+ samples per second) and large channel counts.
- **User-Friendly Distribution:** Packaged as a portable application that does not require admin privileges for installation.

## Epics

- **Epic 1: Foundation & Framework:** Establish the project structure, core libraries, testing framework, and initial GUI landing page.
- **Future Epics:** Focus on the development of individual signal processing tools and modules.

## Setup and Installation

### Windows

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ajordan510/spectral-edge.git
   cd spectral-edge
   ```

2. **Run the application:**
   ```bash
   run.bat
   ```
   
   The batch file will automatically:
   - Check for Python 3.11+ installation
   - Create a virtual environment if needed
   - Install all required dependencies
   - Launch the SpectralEdge GUI

### Linux

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ajordan510/spectral-edge.git
   cd spectral-edge
   ```

2. **Create virtual environment and install dependencies:**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python -m spectral_edge.main
   ```

## Usage

### Basic Workflow

1. **Load Data:**
   - Click "Load CSV Data" for CSV files
   - Click "Load HDF5 Data" for HDF5 files
   - Select channels to analyze

2. **Calculate PSD:**
   - Set frequency range (Min/Max Hz)
   - Configure PSD parameters (Δf, window type, overlap)
   - Choose Welch (averaged) or Maximax (envelope) method
   - Click "Calculate PSD"

3. **Visualize Results:**
   - View time history and PSD plots
   - Enable "Octave Band Display" for smoothed visualization
   - Generate spectrograms for time-frequency analysis
   - Use interactive crosshair for precise measurements

4. **Advanced Features:**
   - Define events for segment analysis
   - Compare multiple channels
   - Export results

## Testing

### Quick Functionality Test

**Purpose:** Verify basic functionality after installation or updates.

1. **Launch Application:**
   ```bash
   run.bat  # Windows
   ```

2. **Load Sample Data:**
   - Use any CSV file with time and signal columns
   - Or load HDF5 flight data

3. **Calculate PSD:**
   - Set Δf = 1.0 Hz
   - Click "Calculate PSD"
   - Verify plot appears without errors

4. **Test Octave Bands:**
   - Check "Octave Band Display"
   - Select "1/3 Octave"
   - Verify plot updates to scatter points with dashed lines

5. **Test Spectrogram:**
   - Select 1-4 channels
   - Click "Generate Spectrogram"
   - Verify spectrogram window opens with correct layout

---

### Comprehensive Test Suite

**Purpose:** Validate all features after major refactoring or before release.

#### Test 1: CSV Data Loading

**Objective:** Verify CSV loading and single-channel analysis.

1. Load single-channel CSV file
2. Verify time history plot displays correctly
3. Calculate averaged PSD (Δf = 1.0 Hz)
4. Verify PSD plot and RMS value
5. Calculate maximax PSD (window = 1.0 s)
6. Verify maximax PSD ≥ averaged PSD

**Expected Results:**
- Time history: Smooth plot with correct units
- Averaged PSD: Continuous line
- Maximax PSD: Higher or equal to averaged at all frequencies
- RMS: Reasonable value for signal amplitude

---

#### Test 2: HDF5 Data Loading

**Objective:** Verify HDF5 loading with decimation handling.

1. Load HDF5 file with high sample rate data (e.g., 40 kHz)
2. Select single channel
3. Verify status bar shows:
   - Sample rate (e.g., "40000.0 Hz")
   - Duration (e.g., "100.0 s")
   - Decimation info (e.g., "Decimated 25x for display")
4. Verify time history plots smoothly (not laggy)
5. Calculate PSD
6. Verify PSD captures high frequencies (not limited by decimated Nyquist)

**Expected Results:**
- Status shows full resolution sample rate
- Status shows decimation factor
- Time history responsive (~10k points)
- PSD includes frequencies up to Nyquist of full resolution
- No "PSD calculated on decimated data" issues

---

#### Test 3: Multi-Channel Analysis

**Objective:** Verify multi-channel support.

1. Load multi-channel HDF5 file
2. Select 2-4 channels
3. Calculate PSD for all channels
4. Verify all PSDs plotted with different colors
5. Verify legend shows all channels with RMS values
6. Switch between channels in time history

**Expected Results:**
- All selected channels plotted
- Different colors for each channel
- Legend readable and correct
- Time history switches correctly

---

#### Test 4: Maximax PSD Validation

**Objective:** Verify maximax algorithm follows SMC-S-016.

1. Load data with known transient events
2. Calculate averaged PSD (Δf = 1.0 Hz)
3. Calculate maximax PSD with different windows:
   - 0.5 s
   - 1.0 s
   - 2.0 s
4. Verify maximax ≥ averaged at all frequencies
5. Verify larger windows → smoother maximax

**Expected Results:**
- Maximax always ≥ averaged
- Maximax captures transient peaks
- Window size affects smoothness
- No parameter validation errors

---

#### Test 5: Octave Band Display

**Objective:** Verify octave band conversion and visualization.

1. Calculate narrowband PSD (Δf = 1.0 Hz, 10-2000 Hz)
2. Note number of frequency points (e.g., ~2000)
3. Enable "Octave Band Display"
4. Select "1/3 Octave"
5. Verify:
   - Plot updates to scatter points + dashed lines
   - Fewer points displayed (~30 bands)
   - Legend shows "(1/3 Octave)"
   - RMS value unchanged
6. Test other fractions:
   - 1/6 Octave (~60 bands)
   - 1/12 Octave (~120 bands)
   - 1/36 Octave (~360 bands)
7. Disable octave display
8. Verify returns to narrowband (solid line)

**Expected Results:**
- Octave bands show smoothed spectrum
- Scatter points at standard center frequencies
- More bands with smaller octave fractions
- Toggle works correctly
- No conversion errors

---

#### Test 6: Multi-Channel Spectrogram

**Objective:** Verify multi-channel spectrogram with adaptive layout.

1. Load multi-channel HDF5 data
2. Select 1 channel → Generate Spectrogram
   - Verify: Single full-size plot
3. Select 2 channels → Generate Spectrogram
   - Verify: Vertical stack (2 rows)
4. Select 3 channels → Generate Spectrogram
   - Verify: 2x2 grid with 3 plots
5. Select 4 channels → Generate Spectrogram
   - Verify: 2x2 grid (all quadrants)
6. Select 5+ channels → Generate Spectrogram
   - Verify: Warning message
   - Verify: Only first 4 displayed
7. Adjust parameters (Δf, window, overlap)
8. Click "Recalculate"
9. Verify all spectrograms update

**Expected Results:**
- Correct layout for each channel count
- Each spectrogram labeled with channel name
- All spectrograms use same parameters
- Warning for >4 channels
- Recalculate updates all plots

---

#### Test 7: Event-Based Analysis

**Objective:** Verify event definition and PSD calculation.

1. Load data
2. Click "Event Manager"
3. Define event:
   - Click start time on time history
   - Click end time
   - Name event (e.g., "Launch")
4. Calculate PSD
5. Verify event PSD plotted
6. Define multiple events
7. Calculate PSDs for all events
8. Verify all event PSDs plotted with different colors

**Expected Results:**
- Event selection works on time history
- Event PSD calculated from full resolution data
- Multiple events supported
- Legend shows event names

---

#### Test 8: Parameter Validation

**Objective:** Verify error handling for invalid parameters.

1. Set Δf = 10 Hz, Maximax window = 0.1 s
2. Calculate maximax PSD
3. Verify error message: "nperseg > window_samples"
4. Adjust to valid parameters
5. Verify calculation succeeds

**Expected Results:**
- Clear error messages for invalid parameters
- No crashes
- Helpful guidance for fixing issues

---

#### Test 9: Performance Test

**Objective:** Verify performance with large datasets.

1. Load HDF5 file with:
   - High sample rate (40 kHz)
   - Long duration (100+ seconds)
   - Multiple channels (4+)
2. Verify time history plots quickly (<1 second)
3. Calculate PSD
4. Verify calculation completes in reasonable time (2-5 seconds)
5. Generate spectrogram
6. Verify spectrogram calculates in reasonable time (5-10 seconds)

**Expected Results:**
- Time history responsive (decimated display data)
- PSD calculation acceptable (full resolution data)
- No memory errors
- No UI freezing

---

#### Test 10: Data Integrity

**Objective:** Verify calculations use correct data.

1. Load HDF5 data (decimated for display)
2. Calculate PSD
3. Verify PSD includes high frequencies:
   - If sample rate = 40 kHz, Nyquist = 20 kHz
   - PSD should go up to ~20 kHz
   - NOT limited to decimated Nyquist (~800 Hz for 25x decimation)
4. Verify RMS calculation:
   - Calculate RMS from PSD
   - Compare with time-domain RMS
   - Should match within ~1%

**Expected Results:**
- PSD uses full resolution data (not decimated)
- High frequencies present in PSD
- RMS values accurate
- Parseval's theorem satisfied

---

### Test Results Checklist

Use this checklist to track testing progress:

- [ ] Test 1: CSV Data Loading
- [ ] Test 2: HDF5 Data Loading
- [ ] Test 3: Multi-Channel Analysis
- [ ] Test 4: Maximax PSD Validation
- [ ] Test 5: Octave Band Display
- [ ] Test 6: Multi-Channel Spectrogram
- [ ] Test 7: Event-Based Analysis
- [ ] Test 8: Parameter Validation
- [ ] Test 9: Performance Test
- [ ] Test 10: Data Integrity

---

### Reporting Issues

If you encounter any issues during testing:

1. **Note the test number and step**
2. **Capture error messages** (copy from console or screenshot)
3. **Note your environment:**
   - OS (Windows 10/11, Linux distro)
   - Python version (`python --version`)
   - SpectralEdge version (git commit hash)
4. **Describe expected vs actual behavior**
5. **Report via GitHub Issues** or contact development team

---

### Automated Testing (Future)

Planned automated test suite:
- Unit tests for core PSD functions
- Integration tests for data loading
- GUI tests for user interactions
- Performance benchmarks

Contributions welcome!

## Theory and Technical Documentation

This section will provide technical details on the signal processing algorithms and methodologies used in the tool, including:

- Power Spectral Density (PSD)
- Shock Response Spectrum (SRS)
- Sound Pressure Level (SPL)
- Fatigue Damage Spectrum (FDS)
- Vibration Response Spectrum (VRS)

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
