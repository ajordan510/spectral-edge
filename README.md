# SpectralEdge

**SpectralEdge** is a professional-grade signal processing suite designed for engineers and scientists. It provides a graphical user interface (GUI) for interactive analysis, batch processing capabilities for large datasets, and a comprehensive library of signal processing functions.

## Features

- **Cross-Platform:** Compatible with both Linux and Windows.
- **Modular Design:** A library of core functions separate from the GUI, allowing for easy expansion and maintenance.
- **Advanced Plotting:** Interactive plots with features like zooming, panning, and data selection.
- **Report Generation:** Automatically generate reports in PowerPoint format with embedded plots.
- **Versatile Data Input:** Supports CSV, HDF5, and DEWESoft (.dxd/.dxz) file formats.
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
   - For DEWESoft files (.dxd/.dxz), first convert to CSV or MAT format (see [DEWESoft Import Guide](docs/DEWESOFT_IMPORT.md))
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

## PowerPoint Slide Catalog

The following are the canonical slide templates used across PSD GUI, Statistics GUI, and Batch PowerPoint exports. Style/layout changes should be made in shared methods in `spectral_edge/utils/report_generator.py`.

| Canonical Slide Name | Generator Method | Used By |
|---|---|---|
| Title Slide | `add_title_slide(...)` | PSD GUI, Statistics GUI, Batch |
| Processing Configuration Slide | `add_bulleted_sections_slide(...)` | PSD GUI, Statistics GUI, Batch |
| Single Plot Slide | `add_single_plot_slide(...)` | PSD GUI, Statistics GUI, Batch |
| Two-Plot Slide | `add_two_plot_slide(...)` | PSD GUI, Batch |
| Three-Plot Slide | `add_three_plot_slide(...)` | PSD GUI, Batch |
| Statistics Dashboard Slide | `add_statistics_dashboard_slide(...)` | PSD GUI, Batch |
| RMS Summary Table Slide | `add_rms_table_slide(...)` | PSD GUI, Statistics GUI, Batch |
| Text Slide | `add_text_slide(...)` | Shared fallback/notes |

Template governance: update shared slide methods in `spectral_edge/utils/report_generator.py` so style changes propagate everywhere.

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

### Automated Testing & CI/CD

SpectralEdge includes a comprehensive automated testing framework that can validate functionality without requiring a physical display. This enables continuous integration (CI) testing on cloud servers.

#### What is CI/CD?

**Continuous Integration (CI)** is the practice of automatically running tests every time code is pushed to a repository. This catches bugs early, before they reach your desktop.

**Benefits:**
- Catch bugs before they break your desktop testing
- Validate code works on multiple platforms (Windows, Linux)
- Ensure new features don't break existing functionality
- Reduce manual testing time

#### Test Layers

| Layer | What It Tests | Requires Display? | Speed |
|-------|--------------|-------------------|-------|
| **Unit Tests** | Core algorithms (PSD, CSD, coherence) | No | Fast (seconds) |
| **Headless GUI Tests** | GUI components with virtual display | No (uses Xvfb) | Medium |
| **User Workflow Tests** | Simulated button clicks/interactions | No (uses Xvfb) | Medium |
| **Integration Tests** | Full application workflows | No (uses Xvfb) | Slower |

#### Running Tests Locally

**1. Unit Tests (No GUI required):**
```bash
# Run core algorithm tests
pytest tests/test_psd.py tests/test_core_algorithms.py -v
```

**2. Headless GUI Tests:**
```bash
# Linux - with virtual framebuffer
xvfb-run pytest tests/test_gui_headless.py -v

# Any platform - with Qt offscreen mode
QT_QPA_PLATFORM=offscreen pytest tests/test_gui_headless.py -v

# Windows PowerShell
$env:QT_QPA_PLATFORM="offscreen"; pytest tests/test_gui_headless.py -v
```

**3. All Tests:**
```bash
# Use the convenience script (Linux)
./scripts/run_headless_tests.sh

# Or run all tests
QT_QPA_PLATFORM=offscreen pytest tests/ -v
```

#### GitHub Actions Workflow

The CI pipeline runs automatically on every push and pull request. It's defined in `.github/workflows/ci.yml`.

**Pipeline Jobs:**

```
┌─────────────────┐
│   Code Quality  │  ← Syntax errors, style checks
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│   Unit Tests    │     │   Unit Tests    │
│  (Ubuntu/3.11)  │     │  (Windows/3.11) │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
         ┌─────────────────┐
         │  GUI Tests      │  ← Headless with Xvfb
         │  (Ubuntu)       │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │  Integration    │
         │  Tests          │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │  Build          │  ← Import validation
         │  Validation     │
         └─────────────────┘
```

**What Each Job Does:**

| Job | Purpose |
|-----|---------|
| **lint** | Check for syntax errors and code style issues |
| **unit-tests** | Run core algorithm tests on Ubuntu and Windows |
| **gui-tests** | Test GUI components without a physical display |
| **integration-tests** | Test complete application workflows |
| **build** | Verify all modules import correctly |

#### Viewing CI Results

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. View the latest workflow run
4. Click on any job to see detailed logs

**Status Badges:**
- ✅ Green checkmark = All tests passed
- ❌ Red X = Tests failed (click to see which ones)
- 🟡 Yellow dot = Tests in progress

#### Writing New Tests

When adding new features, add corresponding tests:

**1. For core algorithms** (no GUI):
```python
# tests/test_my_feature.py
def test_my_new_function():
    from spectral_edge.core.psd import my_new_function
    result = my_new_function(input_data)
    assert result == expected_value
```

**2. For GUI components**:
```python
# tests/test_gui_headless.py
def test_my_window(qapp):
    from spectral_edge.gui.my_window import MyWindow
    window = MyWindow()
    assert window is not None
    window.close()
```

**3. For user interactions** (with pytest-qt):
```python
# tests/test_user_workflows.py
def test_button_click(qtbot):
    window = MyWindow()
    qtbot.addWidget(window)
    qtbot.mouseClick(window.my_button, Qt.MouseButton.LeftButton)
    assert window.result == expected
```

#### Key Technologies

| Tool | Purpose |
|------|---------|
| **pytest** | Test framework |
| **pytest-qt** | PyQt6 testing utilities |
| **Xvfb** | Virtual framebuffer (fake display for Linux) |
| **QT_QPA_PLATFORM=offscreen** | Qt's built-in headless mode |
| **GitHub Actions** | Cloud CI/CD runner |

#### Troubleshooting CI Failures

**"No module named 'PyQt6'"**
- PyQt6 not installed in the CI environment
- Check that `requirements.txt` includes PyQt6

**"cannot open display"**
- Xvfb not running
- Use `xvfb-run` or set `QT_QPA_PLATFORM=offscreen`

**Tests pass locally but fail in CI**
- Check for hardcoded paths
- Ensure all dependencies are in `requirements.txt`
- Check for timing-dependent tests

---

### Automated Test Suite Summary

The test suite consists of **150+ automated tests** organized into the following categories:

#### Core Algorithm Tests (`test_core_algorithms.py` - 35 tests)

| Category | Tests | What It Validates |
|----------|-------|-------------------|
| PSD Accuracy | 10 | Parseval's theorem, peak detection, Nyquist frequency, DC handling |
| Maximax Accuracy | 2 | Envelope property (maximax ≥ welch), transient capture |
| Cross-Spectrum | 7 | CSD symmetry, coherence bounds [0,1], transfer function accuracy |
| Octave Bands | 2 | Energy conservation, all fraction options |
| Robustness | 7 | Input validation, NaN handling, short signals |
| Reliability | 5 | Window types, multi-channel, deterministic results |

#### Data Loading Tests (`test_data_loading.py` - 17 tests)

| Category | Tests | What It Validates |
|----------|-------|-------------------|
| CSV Loading | 8 | Parsing, sample rate detection, unicode, missing values |
| HDF5 Loading | 6 | Metadata extraction, lazy loading, error handling |
| Comparison Curves | 3 | Import, data structure, management |

#### Error Handling Tests (`test_error_handling.py` - 25 tests)

| Category | Tests | What It Validates |
|----------|-------|-------------------|
| PSD Validation | 6 | Empty signal, invalid sample rate, nperseg limits |
| Maximax Validation | 2 | Short signal handling, window validation |
| Cross-Spectrum | 5 | Mismatched lengths, empty signals |
| Frequency Range | 2 | Min > max errors, out-of-range handling |
| Edge Cases | 6 | Single sample, constant signal, inf values |

#### GUI Comprehensive Tests (`test_gui_comprehensive.py` - 65+ tests)

| Category | Tests | What It Validates |
|----------|-------|-------------------|
| Landing Page | 4 | Window creation, tool cards, navigation |
| File Loading | 6 | CSV/HDF5 loading, channel population, button states |
| Parameters | 15 | All spin boxes, combos, checkboxes for PSD settings |
| Display Options | 8 | Crosshair, octave bands, running mean removal |
| Axis Limits | 4 | Text inputs, apply/auto-fit buttons |
| Filter Controls | 10 | Enable toggle, types, designs, cutoff controls |
| Comparison Curves | 5 | Import, toggle, remove, clear operations |
| Action Buttons | 6 | Calculate, spectrogram, events, cross-spectrum |
| Spectrogram Window | 12 | All parameters, colormap, limits, recalculate |
| Cross-Spectrum Window | 8 | Channel selection, tabs, threshold toggle |

#### Plot Verification Tests (`test_plot_verification.py` - 25+ tests)

| Category | Tests | What It Validates |
|----------|-------|-------------------|
| Data Accuracy | 5 | Frequency range, peak detection, positive values, resolution |
| Plot Elements | 7 | Grid, labels, title, curves, legend visibility |
| Styling | 3 | Background color, channel colors |
| Export | 2 | PNG export, valid format |
| Spectrogram | 5 | Image items, data shape, time/frequency range |
| Cross-Spectrum | 6 | Coherence range, peak detection, transfer function |

#### Running the Full Test Suite

```bash
# Run all tests (core + GUI if PyQt6 available)
QT_QPA_PLATFORM=offscreen pytest tests/ -v

# Run only core tests (no GUI required)
pytest tests/test_psd.py tests/test_core_algorithms.py tests/test_data_loading.py tests/test_error_handling.py -v

# Run with coverage report
pytest tests/ --cov=spectral_edge --cov-report=html
```

---

### Manual Testing Checklist

Some functionality cannot be fully verified through automated testing. Use this checklist before releases:

#### Visual Appearance (Requires Human Eye)

- [ ] **Dark theme consistency**: Colors are uniform across all windows
- [ ] **Font readability**: Text is legible at various window sizes
- [ ] **Plot aesthetics**: Lines are smooth, colors distinguishable
- [ ] **High-DPI display**: UI scales correctly on 4K monitors
- [ ] **Icon/emoji display**: Tool card icons render correctly

#### Mouse Interactions

- [ ] **Plot zoom**: Mouse wheel zooms PSD and time history plots smoothly
- [ ] **Plot pan**: Click-drag pans plots without jumping
- [ ] **Crosshair tracking**: Crosshair follows mouse accurately on PSD plot
- [ ] **Event selection**: Click-to-select time ranges works on time history
- [ ] **Legend interaction**: Legend items are clickable (if applicable)

#### File Operations

- [ ] **Native file dialog**: CSV file browser opens and filters correctly
- [ ] **HDF5 navigation**: Flight navigator shows correct file structure
- [ ] **Large file handling**: 100+ MB files load without freezing UI
- [ ] **Report export**: PowerPoint report opens in MS PowerPoint/LibreOffice

#### Performance

- [ ] **UI responsiveness**: Interface remains responsive during calculations
- [ ] **Progress indication**: Long calculations show progress (if implemented)
- [ ] **Memory usage**: No memory leaks after repeated calculations
- [ ] **Multi-window**: Multiple spectrogram windows work simultaneously

#### Cross-Platform (Test on Each Target Platform)

**Windows:**
- [ ] Application launches via `run.bat`
- [ ] File dialogs use Windows native style
- [ ] Plots render correctly

**Linux:**
- [ ] Application launches via Python command
- [ ] Works with both X11 and Wayland (if applicable)
- [ ] File permissions handled correctly

#### Edge Cases

- [ ] **Empty file**: Appropriate error message shown
- [ ] **Corrupted file**: Graceful failure with helpful message
- [ ] **Very long duration**: 1+ hour recordings handled
- [ ] **Many channels**: 10+ channels don't crash channel selector

---

### Test Coverage Summary

| Component | Automated | Manual Required |
|-----------|-----------|-----------------|
| Core PSD algorithms | ✅ 100% | - |
| Cross-spectrum (CSD, coherence) | ✅ 100% | - |
| Octave band conversion | ✅ 100% | - |
| File loading logic | ✅ 95% | Native dialogs |
| GUI button functionality | ✅ 95% | - |
| Parameter controls | ✅ 95% | - |
| Plot data accuracy | ✅ 90% | - |
| Plot visual appearance | ⚠️ 50% | ✅ Colors, aesthetics |
| Mouse interactions | ⚠️ 30% | ✅ Zoom, pan, drag |
| Performance/responsiveness | ⚠️ 20% | ✅ UI feel |
| Cross-platform behavior | ❌ 0% | ✅ Each platform |

**Legend:** ✅ Well covered | ⚠️ Partially covered | ❌ Not automatable

For detailed information on testing limitations and potential improvements, see `docs/GUI_TESTING_LIMITATIONS.md`.

Contributions welcome!

## Theory and Technical Documentation

This section provides technical details on the signal processing algorithms and methodologies used in the tool.

### Power Spectral Density (PSD) Calculation

#### Overview

SpectralEdge implements two PSD calculation methods following aerospace industry standards:

1. **Welch Method (Averaged PSD)**: Standard averaged periodogram for stationary signals
2. **Maximax Method (Envelope PSD)**: Envelope of 1-second PSDs per SMC-S-016 for transient events

Both methods use **full resolution data** (not decimated) to ensure accurate high-frequency content.

---

#### Welch Method - Averaged PSD

**Algorithm**: Welch's method (1967) divides the signal into overlapping segments, computes a periodogram for each segment, and averages them to reduce variance.

**Implementation**: `spectral_edge/core/psd.py::calculate_psd_welch()`

**Process Flow**:

1. **Segmentation**
   - Signal divided into segments of length `nperseg` samples
   - Segments overlap by `noverlap` samples (typically 50%)
   - `nperseg = sample_rate / df` (frequency resolution)

2. **Preprocessing (Automatic)**
   - **Mean removal**: Each segment is detrended using `detrend='constant'`
   - **Effect**: Removes DC offset and prevents low-frequency contamination
   - **Applied**: Segment-by-segment before FFT
   - **Result**: DC component ≈ 0 in final PSD

3. **Windowing**
   - Window function applied to each segment (default: Hann)
   - **Purpose**: Reduces spectral leakage
   - **Options**: Hann, Hamming, Blackman, Flattop, Bartlett
   - **Energy correction**: Automatic via `scaling='density'`

4. **FFT Computation**
   - Fast Fourier Transform computed on windowed, detrended segment
   - Produces complex frequency spectrum

5. **Power Calculation**
   - Power spectral density = |FFT|² / (sample_rate × window_energy)
   - Units: signal²/Hz (e.g., g²/Hz for acceleration)

6. **Averaging**
   - PSDs from all segments averaged
   - Reduces variance (noise) in estimate

**Key Parameters**:
- `df` (Δf): Frequency resolution in Hz (e.g., 1.0 Hz)
- `overlap`: Overlap percentage (default: 50%)
- `window`: Window function type (default: Hann)
- `use_efficient_fft`: Round nperseg to power of 2 for speed

**Frequency Resolution**:
```
df = sample_rate / nperseg
nperseg = sample_rate / df

Example: sample_rate = 1000 Hz, df = 1.0 Hz
  → nperseg = 1000 samples = 1.0 second segments
```

**Trade-offs**:
- **Smaller df** (larger nperseg): Better frequency resolution, fewer segments, higher variance
- **Larger df** (smaller nperseg): Worse frequency resolution, more segments, lower variance
- **Typical values**: df = 0.5 to 2.0 Hz for vibration analysis

---

#### Maximax Method - Envelope PSD

**Standard**: SMC-S-016 (Test Requirements for Launch, Upper-Stage, and Space Vehicles)

**Definition**: "The spectra for each of a series of 1-second times, overlapped by 50%, are enveloped to produce the so-called maxi-max flight spectrum."

**Implementation**: `spectral_edge/core/psd.py::calculate_psd_maximax()`

**Process Flow**:

1. **Window Segmentation**
   - Signal divided into 1-second windows (default)
   - Windows overlap by 50% (default)
   - Example: 10-second signal → 19 windows (1s each, 50% overlap)

2. **PSD Calculation per Window**
   - Welch's method applied to EACH window independently
   - Same preprocessing (detrending, windowing) as averaged PSD
   - Produces one PSD per window

3. **Envelope (Maximum)**
   - At each frequency, take MAXIMUM across all window PSDs
   - `PSD_maximax(f) = max(PSD_window1(f), PSD_window2(f), ...)`
   - Captures worst-case transient events

4. **Result**
   - Envelope PSD that bounds all window PSDs
   - Always ≥ averaged PSD at every frequency
   - Preserves transient peaks that would be averaged out

**Key Parameters**:
- `maximax_window`: Window duration in seconds (default: 1.0 s per SMC-S-016)
- `overlap_percent`: Window overlap percentage (default: 50%)
- `df`: Frequency resolution within each window
- `window`: Window function type (default: Hann)

**When to Use**:
- **Averaged PSD**: Stationary vibration, steady-state analysis
- **Maximax PSD**: Transient events, launch vibration, worst-case envelope

**Comparison**:
```
Averaged PSD:  Mean of all segment PSDs
Maximax PSD:   Maximum of all window PSDs (envelope)

Result: Maximax ≥ Averaged at all frequencies
```

---

#### Data Preprocessing Details

**Automatic Preprocessing** (applied by `scipy.signal.welch`):

1. **Mean Removal (Detrending)**
   - **Parameter**: `detrend='constant'` (default)
   - **Action**: Removes mean from each segment before FFT
   - **Formula**: `segment_detrended = segment - np.mean(segment)`
   - **Applied**: Independently to each segment

2. **What Gets Removed**:
   - ✅ **DC offset** (nonzero mean)
   - ✅ **Constant bias** in each segment
   - ✅ **Slowly varying mean** (removed segment-by-segment)
   - ⚠️ **Linear trends**: Partially removed (only within each segment)
   - ⚠️ **Very low frequencies** (< df): Attenuated but may appear

3. **Effect on PSD**:
   - **DC component** (0 Hz): ≈ 0 (removed)
   - **Low frequencies** (< df): Partially attenuated
   - **Higher frequencies** (> df): Unaffected, accurately represented

4. **Why This Matters**:
   - Prevents DC offset from dominating low frequencies
   - Standard practice for vibration analysis
   - Follows aerospace testing conventions (SMC-S-016)
   - Ensures PSD represents AC (vibration) content, not DC bias

**Example - Accelerometer with Gravity**:
```
Original signal:  1.0 g (gravity) + 0.1 g vibration at 50 Hz
                           ↓
After detrending:  0.1 g vibration at 50 Hz (gravity removed)
                           ↓
PSD shows:         Peak at 50 Hz, no DC spike ✓
```

**Optional Preprocessing** (not currently implemented):
- **Linear detrending**: `detrend='linear'` removes linear trends
- **High-pass filtering**: Removes all content below cutoff frequency
- See `docs/PSD_PREPROCESSING_REPORT.md` for details

---

#### RMS Calculation from PSD

**Method**: Parseval's theorem - total power equals integral of PSD

**Formula**:
```
RMS = sqrt(∫ PSD(f) df)
    = sqrt(sum(PSD × df))  [numerical integration]
```

**Implementation**: `spectral_edge/core/psd.py::calculate_rms_from_psd()`

**Verification**:
- RMS from PSD should match time-domain RMS within ~1%
- Discrepancy indicates frequency range doesn't capture all signal energy
- Use wider frequency range if RMS values don't match

---

#### Octave Band Conversion

**Purpose**: Convert narrowband PSD to standard octave bands for smoothed visualization

**Implementation**: `spectral_edge/core/psd.py::convert_psd_to_octave_bands()`

**Standard**: ANSI/IEC center frequencies (f_ref = 1000 Hz)

**Process**:
1. Define octave band center frequencies (e.g., 1/3 octave: 10, 12.5, 16, 20, ...)
2. For each band, calculate bandwidth: `BW = f_center × (2^(1/(2×fraction)) - 2^(-1/(2×fraction)))`
3. Integrate narrowband PSD over bandwidth: `PSD_octave = ∫ PSD(f) df / BW`
4. Result: Smoothed PSD with fewer points

**Options**:
- 1/3 octave: ~30 bands (20-2000 Hz)
- 1/6 octave: ~60 bands
- 1/12 octave: ~120 bands
- 1/24 octave: ~240 bands
- 1/36 octave: ~360 bands

**Energy Conservation**: Total RMS preserved (Parseval's theorem maintained)

---

#### References

1. **Welch, P. (1967)**: "The use of fast Fourier transform for the estimation of power spectra: A method based on time averaging over short, modified periodograms", IEEE Transactions on Audio and Electroacoustics

2. **SMC-S-016**: Test Requirements for Launch, Upper-Stage, and Space Vehicles, NASA

3. **Bendat & Piersol**: "Random Data: Analysis and Measurement Procedures", 4th Edition, Wiley (2010)

4. **scipy.signal.welch**: https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html

5. **ANSI S1.11**: Specification for Octave-Band and Fractional-Octave-Band Analog and Digital Filters

---

## Scripts and Utilities

The `scripts/` directory contains standalone utilities for data conversion, testing, and development.

### Data Conversion

#### dxd_converter.py

Convert DEWESoft `.dxd`/`.dxz` files to CSV or HDF5 format.

**Usage:**
```bash
# Convert to CSV
python scripts/dxd_converter.py input.dxd output.csv

# Convert to HDF5 (SpectralEdge-compatible)
python scripts/dxd_converter.py input.dxd output.h5 --format hdf5

# Convert specific channels only
python scripts/dxd_converter.py input.dxd output.csv --channels "Accel_X,Accel_Y,Accel_Z"

# Limit samples for preview
python scripts/dxd_converter.py input.dxd preview.csv --max-samples 10000
```

**Features:**
- Supports CSV and HDF5 output formats
- Memory-efficient chunked reading for large files
- Selective channel export
- Real-time progress tracking
- Cross-platform (Windows, Linux, macOS)

**Requirements:** DEWESoft Data Reader Library (included in `scripts/dewesoft/`)

### Test Data Generation

#### generate_sample_hdf5.py

Generate synthetic HDF5 test data with realistic vibration signals.

**Usage:**
```bash
python scripts/generate_sample_hdf5.py
```

**Output:** `data/sample_flight_data.h5` with 3 channels (Accel_X, Accel_Y, Accel_Z)

#### generate_large_test_hdf5.py

Generate large HDF5 files for performance testing.

**Usage:**
```bash
python scripts/generate_large_test_hdf5.py
```

**Output:** Multi-GB HDF5 file with configurable duration and sample rate

#### generate_sample_data.py

Generate simple CSV test data.

**Usage:**
```bash
python scripts/generate_sample_data.py
```

### Development Tools

#### plot_layout_tuner.py

Interactive tool for tuning plot layouts and styling.

**Usage:**
```bash
python scripts/plot_layout_tuner.py
```

#### test_batch_processor.py

Standalone test for batch processing functionality.

**Usage:**
```bash
python scripts/test_batch_processor.py
```

### Testing

#### run_headless_tests.sh

Run all tests in headless mode (Linux).

**Usage:**
```bash
./scripts/run_headless_tests.sh
```

**What it does:**
- Sets up virtual framebuffer (Xvfb)
- Runs pytest with coverage
- Generates test reports

---

## DEWESoft Data Import

SpectralEdge supports importing data from **DEWESoft** data acquisition files (`.dxd` and `.dxz` formats) using the official DEWESoft Data Reader Library.

### Quick Start

**Python Script (DXD Converter):**
```bash
# Convert to CSV
python scripts/dxd_converter.py input.dxd output.csv

# Convert to HDF5 (SpectralEdge-compatible)
python scripts/dxd_converter.py input.dxd output.h5 --format hdf5
```

**MATLAB Script (DXD to MAT):**
```matlab
dxd_to_mat('input.dxd', 'output.mat');
```

### Features

- ✓ Convert DEWESoft `.dxd` and `.dxz` files to CSV, HDF5, or MATLAB `.mat` format
- ✓ Cross-platform support (Windows and Linux)
- ✓ Selective channel export or full file export
- ✓ Support for synchronous, asynchronous, and array channels
- ✓ Large file handling with sample limiting
- ✓ Comprehensive error handling and validation

### Documentation

For detailed usage instructions, examples, and troubleshooting, see:

**[DEWESoft Import Guide](docs/DEWESOFT_IMPORT.md)**

The guide includes:
- Installation and setup
- Python script usage (`dxd_converter.py`)
- MATLAB script usage (`dxd_to_mat.m`)
- Output format specifications
- Integration with SpectralEdge workflow
- Troubleshooting common issues
- Platform-specific notes
- Advanced usage and batch conversion

### Example Workflow

1. **Convert DEWESoft file to HDF5 (recommended):**
   ```bash
   python scripts/dxd_converter.py data/flight_test.dxd data/flight_test.h5 --format hdf5
   ```

   Or convert to CSV:
   ```bash
   python scripts/dxd_converter.py data/flight_test.dxd data/flight_test.csv
   ```

2. **Load data in SpectralEdge:**
   - Open SpectralEdge
   - Click "Load HDF5 Data" (for .h5 files) or "Load CSV Data" (for .csv files)
   - Select the converted file
   - Select channels and perform PSD analysis

### Library Files

The DEWESoft Data Reader Library files are included in:
- `scripts/dewesoft/` - Python wrapper and libraries
- `matlab/dewesoft/` - MATLAB wrapper and libraries

No additional downloads required!

---

### Future Documentation

- Shock Response Spectrum (SRS)
- Sound Pressure Level (SPL)
- Fatigue Damage Spectrum (FDS)
- Vibration Response Spectrum (VRS)

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
