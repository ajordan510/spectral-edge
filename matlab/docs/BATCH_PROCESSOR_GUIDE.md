# Batch PSD Processor User Guide

## Overview

The Batch PSD Processor is a powerful tool for processing multiple channels and events in an automated workflow. It allows you to configure processing parameters once, save the configuration, and run batch analyses that generate comprehensive reports and data files.

## Key Features

- **Multi-Source Support**: Process data from HDF5 files or CSV files
- **Event-Based Analysis**: Define multiple time-based events for segmented analysis
- **Flexible Channel Selection**: Use the Enhanced Flight Navigator to select specific channels from HDF5 files
- **Comprehensive Parameter Control**: Configure PSD calculation, filtering, spectrograms, and display settings
- **Multiple Output Formats**: Generate Excel, CSV, PowerPoint reports, and write back to HDF5
- **Configuration Management**: Save and load processing configurations for repeatability
- **Background Processing**: Non-blocking execution with progress tracking

## Getting Started

### 1. Launch the Batch Processor

From the main SpectralEdge application menu, select:
```
Tools → Batch PSD Processor
```

### 2. Select Data Source

**For HDF5 Files:**
1. Click "Select HDF5 Files" in the Data Source tab
2. Choose one or more HDF5 files
3. Click "Open Enhanced Flight Navigator" to select specific channels
4. Use the navigator to filter and select channels across flights

**For CSV Files:**
1. Click "Select CSV Files" in the Data Source tab
2. Choose one or more CSV files
   - Each file can contain multiple channels (columns)
   - First column should be time
   - Subsequent columns are treated as separate channels

### 3. Define Events (Optional)

If you want to process specific time segments:

1. Go to the "Events" tab
2. Uncheck "Process Full Duration"
3. Click "Add Event" for each event you want to define
4. Fill in:
   - **Event Name**: Descriptive name (e.g., "liftoff", "max_q")
   - **Start Time**: Start time in seconds
   - **End Time**: End time in seconds
   - **Description**: Optional notes

**Note:** If "Process Full Duration" is checked, the entire time history will be processed as a single event.

### 4. Configure PSD Parameters

In the "PSD Parameters" tab, set:

- **Method**: Choose between "welch" (standard) or "maximax" (aerospace-specific)
- **Window**: Select window function (hann, hamming, blackman, bartlett)
- **Overlap**: Set overlap percentage (typically 50%)
- **Desired Δf**: Target frequency resolution in Hz
- **Use efficient FFT size**: Enable for power-of-2 FFT lengths
- **Frequency Range**: Set min/max frequencies for display (20-2000 Hz default)
- **Frequency Spacing**: Choose "linear" or "octave"
- **Remove Running Mean**: Enable to remove 1-second running mean from PSD calculation

### 5. Configure Filtering (Optional)

In the "Filter" tab:

1. Check "Enable Signal Filtering" if you want to filter the data
2. Select:
   - **Filter Type**: lowpass, highpass, or bandpass
   - **Filter Design**: butterworth, chebyshev, or bessel
   - **Filter Order**: 1-10 (4 is typical)
   - **Cutoff Frequencies**: Set appropriate cutoff(s) based on filter type

**Note:** Filtering is applied to the time history before PSD calculation.

### 6. Configure Spectrograms (Optional)

In the "Spectrogram" tab:

1. Check "Generate Spectrograms" if you want spectrogram outputs
2. Configure:
   - **Desired Δf**: Frequency resolution for spectrogram
   - **Overlap**: Overlap percentage
   - **SNR Threshold**: Signal-to-noise ratio threshold in dB
   - **Colormap**: Choose color scheme (viridis, plasma, etc.)

### 7. Set Display Options

In the "Display" tab, configure how plots will appear in reports:

- **Auto-scale axes**: Check to automatically scale plot axes
- **X-axis (Frequency)**: Set min/max frequency for PSD plots
- **Y-axis (PSD)**: Set min/max PSD values
- **Show Legend**: Include legend in plots
- **Show Grid**: Display grid lines

### 8. Select Output Formats

In the "Output" tab:

1. Click "Browse" to select an output directory
2. Check desired output formats:
   - **Excel (.xlsx)**: One sheet per event with all channel PSDs
   - **CSV**: One CSV file per event
   - **PowerPoint (.pptx)**: Professional report with plots and summaries
   - **HDF5 Write-back**: Append processed PSDs to source HDF5 file (HDF5 only)

### 9. Save Configuration (Optional)

To save your configuration for future use:

1. Click "Save Configuration"
2. Choose a location and filename (JSON format)
3. Click "Save"

**To load a saved configuration:**
1. Click "Load Configuration"
2. Select your saved JSON file
3. All parameters will be populated automatically

### 10. Run Batch Processing

1. Review all settings
2. Click "Run Batch Processing" (green button)
3. Monitor progress via the progress bar and status messages
4. Wait for completion message

## Output Files

### Excel Output

**File naming:** `batch_results.xlsx`

**Structure:**
- **Summary Sheet**: Overview of all events and channels processed
- **Event Sheets**: One sheet per event containing:
  - Frequency column
  - PSD columns for each channel
  - Proper units in headers

### CSV Output

**File naming:** `{event_name}_psd.csv`

**Format:**
- First column: Frequency (Hz)
- Subsequent columns: PSD values for each channel
- One file per event

### PowerPoint Output

**File naming:** `batch_report.pptx`

**Contents:**
- Title slide with generation timestamp
- Configuration summary slide
- One slide per event with PSD plot
- Professional formatting with legends and labels

### HDF5 Write-back

**Structure:**
```
/flight_001/
  ├── channels/          (existing - untouched)
  └── processed_psds/    (new)
      ├── liftoff/
      │   ├── accel_x/
      │   │   ├── frequencies
      │   │   ├── psd
      │   │   └── metadata (attributes)
      │   └── accel_y/
      │       └── ...
      └── ascent/
          └── ...
```

**Metadata includes:**
- PSD method
- Window function
- Overlap percentage
- Frequency spacing
- Filter settings (if applied)

## Best Practices

### Frequency Resolution

- **High resolution (small Δf)**: Better frequency detail, longer processing time
- **Low resolution (large Δf)**: Faster processing, less detail
- **Typical values**: 0.5-2.0 Hz for most applications

### Event Definition

- Define events based on flight phases or test conditions
- Ensure events don't overlap
- Use descriptive names for easy identification
- Add descriptions to document event significance

### Filtering

- Only enable filtering if necessary (adds processing time)
- Choose appropriate cutoff frequencies based on your data
- Use butterworth for general-purpose filtering
- Test filter settings on single channels first

### Output Selection

- Excel: Best for data analysis and further processing
- CSV: Best for importing into other tools
- PowerPoint: Best for presentations and reports
- HDF5: Best for maintaining data co-location and traceability

## Troubleshooting

### "No channels selected" error
**Solution:** Make sure you've selected channels using the Enhanced Flight Navigator (for HDF5) or selected valid CSV files.

### "Invalid time range" warning
**Solution:** Check that event start/end times are within the available data range. The processor will skip invalid events and log warnings.

### "Filter unstable" error
**Solution:** Reduce filter order or adjust cutoff frequencies. Very high orders (>8) or cutoffs near Nyquist can cause instability.

### Processing is slow
**Possible causes:**
- Large number of channels
- High frequency resolution (small Δf)
- Spectrograms enabled
- Multiple output formats

**Solutions:**
- Increase Δf for faster processing
- Disable spectrograms if not needed
- Process fewer channels at once
- Use efficient FFT size option

## Configuration File Format

Configuration files are saved in JSON format and contain all processing parameters. They can be edited manually if needed, but be careful to maintain valid JSON syntax.

**Example structure:**
```json
{
  "source_type": "hdf5",
  "source_files": ["/path/to/data.h5"],
  "selected_channels": [["flight_0001", "accel_x"]],
  "process_full_duration": false,
  "events": [
    {
      "name": "liftoff",
      "start_time": 0.0,
      "end_time": 10.0,
      "description": "Vehicle liftoff"
    }
  ],
  "psd_config": {
    "method": "welch",
    "window": "hann",
    "overlap_percent": 50.0,
    ...
  },
  ...
}
```

## Advanced Usage

### Scripting

The batch processor can be used programmatically:

```python
from spectral_edge.batch.config import BatchConfig
from spectral_edge.batch.processor import BatchProcessor

# Create configuration
config = BatchConfig()
config.source_type = "hdf5"
config.source_files = ["/path/to/data.h5"]
# ... configure other parameters

# Run batch processing
processor = BatchProcessor(config)
results = processor.run()
```

### Custom Event Definitions

Events can be defined programmatically for complex scenarios:

```python
from spectral_edge.batch.config import EventDefinition

events = [
    EventDefinition("phase1", 0.0, 60.0, "First minute"),
    EventDefinition("phase2", 60.0, 120.0, "Second minute"),
    # ... more events
]

config.events = events
```

## Support

For issues, questions, or feature requests, please contact the SpectralEdge development team or submit an issue on the GitHub repository.

## Version History

- **v1.0** (2026-02-02): Initial release
  - Multi-source support (HDF5, CSV)
  - Event-based processing
  - Multiple output formats
  - Configuration management
  - Background processing with progress tracking
