# SpectralEdge Utilities

This document describes the utility tools available in SpectralEdge for data conversion and visualization tasks.

## Overview

SpectralEdge includes several utility tools designed to help with common data processing workflows. These utilities are accessible from the main landing page and provide specialized functionality that complements the main analysis tools.

---

## File Format Conversion Tool

**Purpose:** Convert between different file formats used in vibration testing and signal processing.

### Supported Conversions

1. **DXD to CSV/HDF5**
   - Convert DEWESoft .dxd files to CSV or HDF5 format
   - Supports time slicing to extract specific portions
   - Supports channel selection
   - Memory-efficient chunked processing for large files

2. **HDF5 Splitting**
   - Split large HDF5 files into multiple smaller files
   - Split by equal count or custom time slices
   - Maintains SpectralEdge-compatible structure

3. **HDF5 (SpectralEdge) to MATLAB (MARVIN)**
   - Export one `.mat` file per flight/channel pair
   - Each output contains one MARVIN-compatible structure variable
   - Preserves channel timing and units metadata

4. **MATLAB to HDF5** *(Coming Soon)*
   - Convert MATLAB .mat files to SpectralEdge HDF5 format

### Features

#### DXD Conversion

**Basic Conversion:**
1. Select input .dxd file
2. Choose output format (CSV or HDF5)
3. Select output location
4. Click "Convert"

**Advanced Options:**

- **Time Slicing:** Extract specific time ranges from the recording
  - Example: Extract 10.0s to 30.0s from a 60s recording

- **Channel Selection:** Choose which channels to include
  - Reduces file size and processing time
  - Useful when only specific channels are needed

- **File Splitting:** Split large files into multiple smaller files
  - **Split by count:** Divide into N equal segments
  - **Split by time slices:** Custom time ranges for each output file

**Memory Efficiency:**
- Automatic chunked reading for files >500 MB
- Real-time progress tracking
- File size estimation before conversion

**Output Formats:**

**CSV:**
- Human-readable text format
- Compatible with Excel, MATLAB, Python
- Larger file size (~10 bytes per value)
- Structure:
  ```
  Time (s), Channel1 (unit), Channel2 (unit), ...
  0.000, 1.234, 5.678, ...
  0.001, 1.235, 5.679, ...
  ```

**HDF5:**
- Binary format, 5-10x smaller than CSV
- Much faster read/write
- SpectralEdge-compatible structure
- Includes metadata (sample rate, units, etc.)
- Structure:
  ```
  /flight_001/
      /metadata/
          flight_id, duration, sample_rate, ...
      /channels/
          /Channel1/
              data (dataset)
              time (dataset)
              sample_rate, units (attributes)
          /Channel2/
              ...
  ```

#### HDF5 Splitting

**Use Cases:**
- Break up very large recordings for easier handling
- Create separate files for different test phases
- Distribute data to team members

**Splitting Modes:**

1. **Split by Count:**
   - Specify number of segments (e.g., 10)
   - Creates equal-duration segments
   - Example: 300s file → 10 files of 30s each

2. **Split by Time Slices:**
   - Define custom time ranges
   - Can overlap or have gaps
   - Example: Create files for specific events
     - Slice 1: 0-15s (pre-test)
     - Slice 2: 15-45s (test phase 1)
     - Slice 3: 45-75s (test phase 2)
     - Slice 4: 75-90s (post-test)

### Usage Examples

**Example 1: Convert entire DXD file to HDF5**
```
1. Click "File Converter" on landing page
2. Select "DXD to CSV/HDF5" mode
3. Browse and select input.dxd
4. Set format to "HDF5"
5. Browse and select output location (output.h5)
6. Click "Convert"
```

**Example 2: Extract 30-second time slice as CSV**
```
1. Open File Converter
2. Select input.dxd
3. Set format to "CSV"
4. Under "Splitting Options", select "Single file"
5. (Note: Time slicing without splitting requires manual time range input)
6. Select output.csv
7. Click "Convert"
```

**Example 3: Split large file into 20 segments**
```
1. Open File Converter
2. Select large_file.dxd
3. Set format to "HDF5"
4. Select "Split by count"
5. Set "20 segments"
6. Browse and select output directory
7. Click "Convert"
8. Result: 20 files created (large_file_segment_001.h5 through large_file_segment_020.h5)
```

**Example 4: Split HDF5 file by custom time ranges**
```
1. Open File Converter
2. Select "HDF5 Splitting" mode
3. Browse and select input.h5
4. Select "Split by time slices"
5. Click "Add Slice" and enter time ranges:
   - Slice 1: 0.0s to 60.0s
   - Slice 2: 60.0s to 120.0s
   - Slice 3: 120.0s to 180.0s
6. Browse and select output directory
7. Click "Convert"
8. Result: 3 files created (input_slice_001.h5, input_slice_002.h5, input_slice_003.h5)
```

### Tips

- **Use HDF5 for large files:** 5-10x smaller and much faster than CSV
- **Check size estimate:** Review estimated output size before converting
- **Split very large files:** Easier to work with multiple smaller files
- **Use time slicing:** Extract only the data you need to save disk space
- **Select specific channels:** Reduces file size when only certain channels are needed

---

## Segmented Spectrogram Viewer

**Purpose:** View spectrograms of very long-duration, high sample rate recordings by splitting them into navigable segments.

### The Problem

Traditional spectrogram tools struggle with long recordings:
- **Memory issues:** 1-hour recording at 51.2 kHz = 184 million samples
- **Slow rendering:** Generating one massive spectrogram takes minutes
- **Poor resolution:** Either too much detail (slow) or too little (useless)

### The Solution

**Segmented Spectrogram Viewer** splits long recordings into manageable segments:
- View one segment at a time
- Navigate between segments with controls
- On-demand generation with caching
- Adjustable segment duration and overlap

### Features

#### Segmentation

**Segment Duration:**
- Choose duration for each segment (1-3600 seconds)
- Default: 60 seconds
- Shorter = more segments, better time resolution
- Longer = fewer segments, better frequency resolution

**Segment Overlap:**
- Overlap between consecutive segments (0-90%)
- Default: 50%
- Prevents missing events at segment boundaries
- Example: 60s segments with 50% overlap
  - Segment 1: 0-60s
  - Segment 2: 30-90s
  - Segment 3: 60-120s

#### Navigation

**Controls:**
- **First/Prev/Next/Last buttons:** Jump between segments
- **Slider:** Quickly navigate to any segment
- **Keyboard shortcuts:**
  - Left Arrow: Previous segment
  - Right Arrow: Next segment
  - Home: First segment
  - End: Last segment

**Segment Info:**
- Current segment number
- Time range for segment
- Duration

#### Spectrogram Parameters

**NFFT:**
- FFT size for spectrogram (128-65536)
- Default: 2048
- Larger = better frequency resolution, worse time resolution
- Smaller = better time resolution, worse frequency resolution

**Overlap:**
- Overlap between FFT windows (0-99%)
- Default: 75%
- Higher = smoother spectrogram, slower generation

**Window Function:**
- Hann (default)
- Hamming
- Blackman
- Bartlett

**Frequency Range:**
- Set min/max frequency to display
- Default: 0 Hz to Nyquist frequency
- Zoom in on frequency bands of interest

#### Caching

**LRU Cache:**
- Stores recently viewed spectrograms
- Default: 10 segments
- Instant display when revisiting segments
- Automatically removes oldest when full

**Cache Management:**
- **Update Current Segment:** Regenerate current segment with new parameters
- **Update All Segments:** Clear cache, regenerate as you navigate

#### Export

**Export Current Segment:**
- Save current spectrogram as PNG image
- High-resolution export suitable for reports

**Export All Segments:**
- Batch export all segments to directory
- Progress dialog with cancel option
- Automatically generates missing spectrograms
- Files named: `spectrogram_segment_001.png`, `spectrogram_segment_002.png`, etc.

### Usage Examples

**Example 1: View 1-hour recording in 60-second segments**
```
1. Click "Spectrogram Viewer" on landing page
2. Browse and select HDF5 file
3. Select flight and channel
4. Set "Segment Duration" to 60 seconds
5. Set "Overlap" to 50%
6. Click "Generate Spectrograms"
7. Result: 60 segments created (with 50% overlap)
8. Use navigation controls to browse through segments
```

**Example 2: Focus on specific frequency range**
```
1. Open Spectrogram Viewer and load data
2. Generate spectrograms
3. Under "Spectrogram Parameters":
   - Set "Freq Range" to 1000-5000 Hz
4. Click "Update Current Segment"
5. Navigate through segments to examine 1-5 kHz band
```

**Example 3: Export all segments for presentation**
```
1. Open Spectrogram Viewer and load data
2. Generate spectrograms with desired parameters
3. Navigate through a few segments to verify appearance
4. Click "Export All"
5. Select output directory
6. Wait for batch export to complete
7. Result: PNG images for all segments in output directory
```

**Example 4: Adjust parameters for better resolution**
```
1. Open Spectrogram Viewer and load data
2. Generate spectrograms with default parameters
3. If frequency resolution is poor:
   - Increase NFFT to 4096 or 8192
   - Click "Update All Segments"
4. If time resolution is poor:
   - Decrease NFFT to 1024 or 512
   - Click "Update All Segments"
5. Navigate through segments to verify improvement
```

### Tips

- **Start with defaults:** 60s segments, 2048 NFFT, 75% overlap
- **Adjust segment duration:** Shorter for detailed analysis, longer for overview
- **Use keyboard shortcuts:** Faster navigation with arrow keys
- **Cache is your friend:** Revisit segments instantly
- **Export before changing parameters:** Save current view before updating
- **Frequency range:** Zoom in on bands of interest for better detail

### Performance

**Memory Usage:**
- Only current segment in memory
- Cache holds ~10 segments
- Total memory: ~100-500 MB (vs. 10+ GB for full spectrogram)

**Generation Speed:**
- 60s segment: ~2-5 seconds
- Cached segment: Instant
- Batch export: ~5-10 seconds per segment

**Recommended Limits:**
- Segment duration: 10-300 seconds
- NFFT: 1024-8192 for most applications
- Total segments: <1000 (for practical navigation)

---

## Integration with SpectralEdge

Both utilities integrate seamlessly with the main SpectralEdge workflow:

### File Converter → PSD Analysis

```
1. Convert DXD to HDF5 using File Converter
2. Open PSD Analysis tool
3. Load converted HDF5 file
4. Perform PSD analysis on converted data
```

### Spectrogram Viewer → Export → Reports

```
1. Generate spectrograms in Segmented Spectrogram Viewer
2. Export selected segments as PNG
3. Insert images into test reports or presentations
```

### Batch Workflow

```
1. Use File Converter to split large DXD into multiple HDF5 files
2. Use Batch Processor to run PSD analysis on all segments
3. Use Spectrogram Viewer to visually inspect each segment
4. Export spectrograms for documentation
```

---

## Troubleshooting

### File Converter Issues

**Problem: "Memory Error" during conversion**
- **Solution:** File is too large for available RAM
- **Fix:** Use splitting mode to create smaller output files

**Problem: "Invalid Reader Handle" error**
- **Solution:** DEWESoft library initialization failed
- **Fix:** Ensure .dxd file is not corrupted, try different file

**Problem: Conversion is very slow**
- **Solution:** Large file with many channels
- **Fix:** Select only needed channels, or use HDF5 format (faster than CSV)

**Problem: Output file size estimate is wrong**
- **Solution:** Estimate is approximate
- **Fix:** Actual size may vary ±20%, ensure sufficient disk space

### Spectrogram Viewer Issues

**Problem: "Out of memory" when generating spectrograms**
- **Solution:** Segment duration too long or NFFT too large
- **Fix:** Reduce segment duration or NFFT size

**Problem: Spectrogram generation is slow**
- **Solution:** High NFFT or overlap percentage
- **Fix:** Reduce NFFT or overlap, or use caching

**Problem: Spectrogram looks blocky**
- **Solution:** NFFT too small
- **Fix:** Increase NFFT to 4096 or 8192

**Problem: Can't see time details in spectrogram**
- **Solution:** NFFT too large
- **Fix:** Decrease NFFT to 1024 or 512

---

## Future Enhancements

### File Converter
- MATLAB to HDF5 conversion
- CSV to HDF5 conversion
- Support for TDMS, UFF, WAV formats
- Batch conversion mode
- Data resampling during conversion

### Spectrogram Viewer
- Colormap selection
- Amplitude scaling options
- Cursor measurements
- Zoom and pan controls
- Annotation tools
- Video export (animated spectrograms)

---

## Technical Details

### File Converter Backend

**Location:** `spectral_edge/utils/file_converter.py`

**Key Functions:**
- `get_dxd_file_info()`: Extract metadata without loading data
- `convert_dxd_to_format()`: Convert DXD to CSV/HDF5
- `convert_dxd_with_splitting()`: Convert with splitting
- `split_hdf5_by_count()`: Split HDF5 into N segments
- `split_hdf5_by_time_slices()`: Split HDF5 by time ranges

**Dependencies:**
- DEWESoft Data Reader Library (v5.0.4)
- h5py (for HDF5 operations)
- NumPy (for data handling)

### Spectrogram Viewer Backend

**Location:** `spectral_edge/gui/segmented_spectrogram_viewer.py`

**Key Components:**
- `SpectrogramCache`: LRU cache for spectrograms
- `SpectrogramGenerator`: Background thread for generation
- `SegmentedSpectrogramViewer`: Main GUI window

**Dependencies:**
- PyQt6 (GUI framework)
- pyqtgraph (plotting)
- scipy (spectrogram generation)
- NumPy (data handling)

---

## Support

For issues, questions, or feature requests related to utilities, please visit:
https://help.manus.im

---

**Last Updated:** 2026-02-08  
**Version:** 1.0.0
