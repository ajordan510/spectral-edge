# Epic 3: HDF5 Support & Maximax PSD

## Overview

Epic 3 adds comprehensive support for large-scale aerospace flight test data with two major features:

1. **HDF5 Data Management** - Memory-efficient loading and navigation of multi-flight datasets
2. **Maximax PSD** - MPE-style envelope PSD calculation for conservative test specifications

## Features Implemented

### 1. HDF5 Data Structure

SpectralEdge uses a hierarchical HDF5 structure optimized for aerospace flight test data:

```
root/
├── metadata/
│   ├── file_version: "1.0"
│   ├── created_date
│   └── description
│
├── flight_001/
│   ├── metadata/
│   │   ├── flight_id
│   │   ├── date
│   │   ├── duration
│   │   └── description
│   │
│   ├── channels/
│   │   ├── accelerometer_x/
│   │   │   ├── data [chunked, compressed]
│   │   │   ├── time [chunked, compressed]
│   │   │   └── attributes:
│   │   │       ├── units
│   │   │       ├── sample_rate
│   │   │       ├── description
│   │   │       ├── sensor_id
│   │   │       └── range_min/max
│   │   └── ...
│   └── ...
└── flight_002/
    └── ...
```

**Key Features:**
- Supports multiple flights in one file
- Each channel has independent sample rate and time vector
- Flexible metadata storage
- Chunked and compressed datasets for efficiency
- Designed to handle 5GB+ files

### 2. HDF5FlightDataLoader

Memory-efficient data loader that never loads entire datasets into memory.

**Key Methods:**
- `get_flights()` - List all flights in file
- `get_channels(flight_key)` - List channels for a flight
- `load_channel_data(flight_key, channel_key)` - Load data with optional decimation
- `load_channel_segment(flight_key, channel_key, start_time, end_time)` - Load time segment

**Decimation Strategy:**
- Automatically decimates large datasets for display (~10k points)
- Full resolution used for PSD calculations
- Configurable decimation factor

### 3. Flight & Channel Navigator

Interactive GUI for browsing and selecting data from HDF5 files.

**Features:**
- Tree view of flights and channels
- Hierarchical selection (select entire flight or individual channels)
- Metadata display (sample rate, units, duration)
- Multi-channel selection
- Non-modal window (stays open while working)

**Usage:**
1. Click "Load HDF5 File" in PSD window
2. Flight Navigator opens automatically
3. Check channels you want to analyze
4. Click "Load Selected"
5. Data loads into PSD tool

### 4. Maximax PSD Calculation

Implements Maximum Predicted Environment (MPE) style PSD calculation.

**Algorithm:**
```
1. Divide signal into overlapping windows (e.g., 1 second each)
2. Calculate PSD for each window using Welch's method
3. At each frequency bin, take MAXIMUM across all windows
4. Result: Conservative envelope PSD
```

**Why Maximax?**
- Standard approach for aerospace test specifications
- Captures worst-case spectral content
- More conservative than averaged PSD
- Typical for MPE (Maximum Predicted Environment) definitions

**Parameters:**
- **Maximax Window**: Duration of each window (default 1.0 seconds)
- **Maximax Overlap**: Overlap between windows (default 50%)
- **Window Type**: Same as traditional PSD (Hann, Hamming, etc.)
- **Δf**: Frequency resolution (same as traditional PSD)

**Comparison:**

| Method | Approach | Use Case |
|--------|----------|----------|
| **Traditional PSD** | Average PSDs across time | General analysis, random vibration |
| **Maximax PSD** | Maximum PSDs across time | Test specifications, MPE, conservative design |

### 5. GUI Integration

**New Controls in PSD Window:**
- "Load HDF5 File" button
- "Use Maximax PSD" checkbox (default ON)
- "Maximax Window (s)" spinbox
- "Maximax Overlap (%)" spinbox

**Workflow:**
1. Load HDF5 file → Flight Navigator opens
2. Select channels → Data loads
3. Set PSD parameters (df, window type, etc.)
4. Choose Maximax or Traditional mode
5. Calculate PSD
6. Results show envelope (maximax) or average (traditional)

## Sample Data Generation

Use the provided script to generate test HDF5 files:

```bash
python scripts/generate_sample_hdf5.py
```

**Generated File:**
- 3 flights (FT-001, FT-002, FT-003)
- 6 channels per flight:
  - 3 accelerometers (X, Y, Z) at 10 kHz
  - 2 pressure sensors at 1 kHz
  - 1 temperature sensor at 100 Hz
- ~100 seconds duration per flight
- Realistic signal content (sine waves + noise)
- Proper metadata and units
- Compressed and chunked for efficiency

**File Size:** ~50-100 MB (representative of structure, not full 5GB scale)

## Technical Details

### Memory Efficiency

**Problem:** 40 kHz × 500 seconds × 100 channels = 2 billion samples = 16 GB RAM

**Solution:**
1. **Chunked Reading** - Load only needed segments
2. **Decimation** - Reduce display data to ~10k points
3. **Lazy Loading** - Load on-demand, not all at once
4. **HDF5 Compression** - Gzip compression reduces file size

### PSD Calculation Strategy

**For Maximax:**
```python
# Pseudo-code
for each 1-second window:
    psd_window = calculate_welch(window_data)
    psd_maximax = max(psd_maximax, psd_window)  # Element-wise max
```

**Computational Cost:**
- Traditional: O(N) where N = signal length
- Maximax: O(N × W) where W = number of windows
- Typical: 30s signal, 1s windows, 50% overlap → 59 windows
- Still very fast with modern CPUs

### Window Energy Correction

Both traditional and maximax PSDs use `scipy.signal.welch` with `scaling='density'`, which automatically applies proper window energy correction. This ensures:
- Total power equals signal variance
- Correct units (g²/Hz)
- Independent of window function choice

## Usage Examples

### Example 1: Load HDF5 and Calculate Maximax PSD

```python
# In GUI:
1. Click "Load HDF5 File"
2. Select "flight_test_data.hdf5"
3. In Flight Navigator, select "flight_001/accelerometer_x"
4. Click "Load Selected"
5. Ensure "Use Maximax PSD" is checked
6. Set "Maximax Window" to 1.0 seconds
7. Click "Calculate PSD"
8. Result: Conservative envelope PSD
```

### Example 2: Compare Maximax vs Traditional

```python
# Calculate both and compare:
1. Load data
2. Check "Use Maximax PSD", calculate → Save plot
3. Uncheck "Use Maximax PSD", calculate → Compare
4. Maximax will show higher peaks (conservative)
```

### Example 3: Event-Based Maximax

```python
# Analyze specific flight phases:
1. Load HDF5 data
2. Click "Manage Events"
3. Define events (Liftoff, Max-Q, etc.)
4. Use Maximax PSD for each event
5. Compare envelope PSDs across flight phases
```

## Future Enhancements (Epic 4+)

- **Batch Processing** - Process multiple flights automatically
- **Cross-Flight Comparison** - Statistical analysis across flights
- **Multi-Channel HDF5 Loading** - Load multiple channels simultaneously
- **Custom HDF5 Import** - Support user-defined HDF5 structures
- **Report Generation** - Automated reports with maximax PSDs

## Best Practices

### For HDF5 Files:
1. Use chunked datasets (chunk size ~10k samples)
2. Enable gzip compression (level 4-6)
3. Store metadata as attributes
4. Use consistent naming conventions
5. Include units in channel names or attributes

### For Maximax PSD:
1. Use 1-second windows for typical aerospace data
2. Use 50% overlap for good statistical coverage
3. Ensure signal duration >> maximax window (at least 10x)
4. Compare with traditional PSD to understand conservatism
5. Document maximax parameters in reports

### For Large Datasets:
1. Use HDF5, not CSV
2. Decimate for display, full resolution for analysis
3. Process in segments if memory constrained
4. Use events to focus on regions of interest
5. Close HDF5 files when done (automatic in SpectralEdge)

## Troubleshooting

**Issue:** "Failed to load HDF5 file"
- **Solution:** Ensure file follows SpectralEdge HDF5 structure
- **Solution:** Check file permissions
- **Solution:** Verify h5py is installed

**Issue:** "Maximax window is larger than signal duration"
- **Solution:** Reduce maximax window duration
- **Solution:** Use longer signal segments

**Issue:** Memory error with large files
- **Solution:** Use decimation for display
- **Solution:** Load smaller time segments
- **Solution:** Use events to analyze specific regions

**Issue:** Maximax PSD looks same as traditional
- **Solution:** Signal may be very stationary
- **Solution:** Try shorter maximax window
- **Solution:** Check that maximax mode is enabled

## References

- NASA-HDBK-7005: Dynamic Environmental Criteria
- MIL-STD-810: Environmental Engineering Considerations
- Aerospace recommended practices for MPE development
- HDF5 documentation: https://www.hdfgroup.org/

## Summary

Epic 3 transforms SpectralEdge into a production-ready tool for aerospace flight test data analysis with:
- ✅ Efficient handling of 5GB+ datasets
- ✅ Multi-flight data management
- ✅ Industry-standard maximax PSD calculation
- ✅ Intuitive data navigation
- ✅ Memory-efficient implementation
- ✅ Comprehensive documentation

Ready for real-world aerospace applications! 🚀
