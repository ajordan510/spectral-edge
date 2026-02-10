# PSD Window GUI Update Instructions

**File**: `spectral_edge/gui/psd_window.py`  
**Status**: Partial - Core functions fixed, GUI needs systematic update  
**Priority**: HIGH - Required before tool can be used with HDF5 data

---

## Overview

The PSD window GUI needs to be updated to separate **display data** (decimated for fast plotting) from **calculation data** (full resolution for accuracy). This document provides step-by-step instructions for completing the update.

---

## Architecture Change

### OLD (Single Data Storage):
```python
self.time_data = ...      # Used for both plotting AND calculations
self.signal_data = ...    # Used for both plotting AND calculations
```

**Problem**: When HDF5 data is decimated for display, calculations use decimated data → loss of accuracy.

### NEW (Dual Data Storage):
```python
# Display data (decimated, ~10k points, fast plotting)
self.time_data_display = ...
self.signal_data_display = ...

# Calculation data (full resolution, accurate PSD)
self.time_data_full = ...
self.signal_data_full = ...
```

**Benefit**: Plots remain responsive, calculations remain accurate.

---

## Step-by-Step Update Guide

### Step 1: Update Instance Variable Initialization

**Location**: `__init__()` method

**Find**:
```python
self.time_data = None
self.signal_data = None
self.sample_rate = None
```

**Replace with**:
```python
# Display data (decimated for plotting)
self.time_data_display = None
self.signal_data_display = None

# Calculation data (full resolution)
self.time_data_full = None
self.signal_data_full = None

# Metadata
self.sample_rate = None
self.decimation_factor = 1  # Track decimation for display
```

---

### Step 2: Update CSV Loading

**Location**: `_on_csv_loaded()` method

**Current Implementation**:
```python
def _on_csv_loaded(self, data_dict):
    """Handle CSV data loaded from file."""
    self.time_data = data_dict['time']
    self.signal_data = data_dict['data']
    self.sample_rate = data_dict['sample_rate']
    # ... rest of method
```

**Updated Implementation**:
```python
def _on_csv_loaded(self, data_dict):
    """Handle CSV data loaded from file."""
    # For CSV, no decimation needed (typically smaller files)
    # Store same data for both full and display
    self.time_data_full = data_dict['time']
    self.signal_data_full = data_dict['data']
    self.time_data_display = data_dict['time']
    self.signal_data_display = data_dict['data']
    self.sample_rate = data_dict['sample_rate']
    self.decimation_factor = 1  # No decimation for CSV
    
    # Update status
    num_channels = self.signal_data_full.shape[1] if self.signal_data_full.ndim > 1 else 1
    num_samples = len(self.time_data_full)
    duration = self.time_data_full[-1] - self.time_data_full[0]
    
    self.status_label.setText(
        f"Loaded CSV: {num_channels} channel(s), "
        f"{num_samples} samples, {duration:.2f} seconds, "
        f"{self.sample_rate:.1f} Hz (Full resolution)"
    )
    
    # ... rest of method (update plotting to use _display data)
```

---

### Step 3: Update HDF5 Loading

**Location**: `_on_hdf5_data_selected()` method

**Current Implementation** (partially updated):
```python
def _on_hdf5_data_selected(self, result_dict):
    """Handle HDF5 data selected from Flight Navigator."""
    # Extract data from result dictionary
    time_full = result_dict['time_full']
    data_full = result_dict['data_full']
    # ... etc
```

**Verify/Complete Implementation**:
```python
def _on_hdf5_data_selected(self, result_dict):
    """Handle HDF5 data selected from Flight Navigator."""
    # Extract full resolution data (for calculations)
    self.time_data_full = result_dict['time_full']
    self.signal_data_full = result_dict['data_full']
    
    # Extract display data (decimated for plotting)
    self.time_data_display = result_dict['time_display']
    self.signal_data_display = result_dict['data_display']
    
    # Extract metadata
    self.sample_rate = result_dict['sample_rate']
    self.decimation_factor = result_dict.get('decimation_factor', 1)
    
    # Calculate actual duration from full resolution time vector
    duration = self.time_data_full[-1] - self.time_data_full[0]
    num_samples_full = len(self.time_data_full)
    num_samples_display = len(self.time_data_display)
    num_channels = self.signal_data_full.shape[1] if self.signal_data_full.ndim > 1 else 1
    
    # Update status with decimation info
    if self.decimation_factor > 1:
        self.status_label.setText(
            f"Loaded HDF5: {num_channels} channel(s), "
            f"{num_samples_full} samples ({num_samples_display} for display), "
            f"{duration:.2f} seconds, {self.sample_rate:.1f} Hz "
            f"(Decimated {self.decimation_factor}x for display)"
        )
    else:
        self.status_label.setText(
            f"Loaded HDF5: {num_channels} channel(s), "
            f"{num_samples_full} samples, {duration:.2f} seconds, "
            f"{self.sample_rate:.1f} Hz (Full resolution)"
        )
    
    # ... rest of method (update plotting to use _display data)
```

---

### Step 4: Update Time History Plotting

**Location**: `_plot_time_history()` method

**Find all instances of**:
```python
self.time_data
self.signal_data
```

**Replace with**:
```python
self.time_data_display  # For plotting
self.signal_data_display  # For plotting
```

**Example**:
```python
def _plot_time_history(self):
    """Plot time history of loaded signal."""
    if self.time_data_display is None or self.signal_data_display is None:
        return
    
    self.time_plot_widget.clear()
    
    # Plot using DISPLAY data (decimated for performance)
    if self.signal_data_display.ndim == 1:
        # Single channel
        self.time_plot_widget.plot(
            self.time_data_display, 
            self.signal_data_display,
            pen='c'
        )
    else:
        # Multi-channel
        for i in range(self.signal_data_display.shape[1]):
            self.time_plot_widget.plot(
                self.time_data_display,
                self.signal_data_display[:, i],
                pen=(i, self.signal_data_display.shape[1])
            )
    
    self.time_plot_widget.setLabel('left', 'Amplitude')
    self.time_plot_widget.setLabel('bottom', 'Time', units='s')
    self.time_plot_widget.setTitle('Time History (Display Data)')
```

---

### Step 5: Update PSD Calculation

**Location**: `_calculate_psd()` method

**Find all instances of**:
```python
self.time_data
self.signal_data
```

**Replace with**:
```python
self.time_data_full  # For calculations
self.signal_data_full  # For calculations
```

**Example**:
```python
def _calculate_psd(self):
    """Calculate PSD using current parameters."""
    if self.signal_data_full is None:
        QMessageBox.warning(self, "No Data", "Please load data first.")
        return
    
    # Show calculation message
    self.status_label.setText("Calculating PSD with full resolution data...")
    QApplication.processEvents()
    
    try:
        # Get parameters
        df = self.df_input.value()
        overlap_percent = self.overlap_input.value()
        window_type = self.window_combo.currentText().lower()
        
        # Use FULL RESOLUTION data for calculation
        if self.psd_type_combo.currentText() == "Averaged (Welch)":
            freq, psd = calculate_psd_welch(
                self.signal_data_full,
                self.sample_rate,
                df=df,
                overlap_percent=overlap_percent,
                window=window_type
            )
        else:  # Maximax
            maximax_window = self.maximax_window_input.value()
            freq, psd = calculate_psd_maximax(
                self.signal_data_full,
                self.sample_rate,
                df=df,
                maximax_window=maximax_window,
                overlap_percent=overlap_percent,
                window=window_type
            )
        
        # Store results
        self.freq_data = freq
        self.psd_data = psd
        
        # Plot results
        self._plot_psd()
        
        # Update status
        self.status_label.setText("PSD calculation complete (full resolution)")
        
    except Exception as e:
        QMessageBox.critical(self, "Calculation Error", f"Error calculating PSD:\n{str(e)}")
        self.status_label.setText("PSD calculation failed")
```

---

### Step 6: Update Event Management

**Location**: Event-related methods

**Find all instances where events are defined or used**:
```python
self.time_data
self.signal_data
```

**Replace with**:
```python
self.time_data_full  # For event calculations
self.signal_data_full  # For event calculations
```

**Example** (in event extraction):
```python
def _extract_event_data(self, start_time, stop_time):
    """Extract data for a specific event."""
    # Use FULL RESOLUTION data for event extraction
    mask = (self.time_data_full >= start_time) & (self.time_data_full <= stop_time)
    event_time = self.time_data_full[mask]
    event_signal = self.signal_data_full[mask]
    return event_time, event_signal
```

---

### Step 7: Update Channel Selection

**Location**: Channel selection methods

**Update to work with both data types**:
```python
def _on_channel_selected(self, channel_index):
    """Handle channel selection for multi-channel data."""
    if self.signal_data_full is None:
        return
    
    # Extract selected channel from BOTH datasets
    if self.signal_data_full.ndim > 1:
        self.current_channel_data_full = self.signal_data_full[:, channel_index]
        self.current_channel_data_display = self.signal_data_display[:, channel_index]
    else:
        self.current_channel_data_full = self.signal_data_full
        self.current_channel_data_display = self.signal_data_display
    
    # Update plots using display data
    self._plot_time_history()
```

---

### Step 8: Update Data Validation

**Location**: All methods that check if data is loaded

**Find**:
```python
if self.signal_data is None:
```

**Replace with**:
```python
if self.signal_data_full is None:
```

**Rationale**: Full resolution data is the source of truth. If it's loaded, display data should also be loaded.

---

### Step 9: Update Export Functions

**Location**: Export/save methods

**Use FULL RESOLUTION data for exports**:
```python
def _export_results(self):
    """Export PSD results to file."""
    # Use full resolution data for exports
    # (User wants accurate data, not decimated)
    data_to_export = {
        'time': self.time_data_full,
        'signal': self.signal_data_full,
        'frequency': self.freq_data,
        'psd': self.psd_data,
        'sample_rate': self.sample_rate
    }
    # ... save to file
```

---

### Step 10: Add Status Messages

**Add informative status messages throughout**:

```python
# When loading HDF5 with decimation
self.status_label.setText("Loading HDF5 data (full resolution for calculations)...")

# When calculating PSD
self.status_label.setText("Calculating PSD with full resolution data...")

# When plotting
self.status_label.setText("Plotting time history (decimated for display)...")

# When complete
self.status_label.setText(f"Ready - {num_channels} channels, {duration:.2f}s, {self.sample_rate:.1f} Hz")
```

---

## Testing Checklist

After making all updates, test the following:

### CSV Data:
- [ ] Load single-channel CSV
- [ ] Verify time history plots correctly
- [ ] Calculate averaged PSD
- [ ] Calculate maximax PSD
- [ ] Verify status shows "Full resolution"

### HDF5 Data:
- [ ] Load single-channel HDF5
- [ ] Verify status shows decimation factor
- [ ] Verify time history plots smoothly (decimated)
- [ ] Calculate averaged PSD (should use full resolution)
- [ ] Calculate maximax PSD (should use full resolution)
- [ ] Verify PSD captures high frequencies (not limited by decimated Nyquist)

### Multi-Channel:
- [ ] Load multi-channel CSV
- [ ] Load multi-channel HDF5
- [ ] Switch between channels
- [ ] Calculate PSD for each channel
- [ ] Verify all use full resolution

### Events:
- [ ] Define event on time history
- [ ] Calculate PSD for event
- [ ] Verify event uses full resolution data

### Edge Cases:
- [ ] Very large HDF5 file (>100k samples)
- [ ] Very high sample rate (>40 kHz)
- [ ] Maximax with small window (verify validation)
- [ ] Multi-channel with different lengths (if supported)

---

## Common Pitfalls

1. **Forgetting to update a plot call**: Search for ALL instances of `self.time_data` and `self.signal_data`
2. **Using display data for calculations**: Always use `_full` for calculations
3. **Using full data for plots**: Always use `_display` for plots (performance)
4. **Not updating validation checks**: Check for `signal_data_full` not `signal_data`
5. **Inconsistent status messages**: Always indicate which data is being used

---

## Performance Considerations

### Memory Usage:
- Full resolution: ~4 bytes/sample × samples × channels
- Display resolution: ~4 bytes/sample × 10,000 × channels
- For 100 channels, 100s, 40kHz: ~160 MB full + ~4 MB display = ~164 MB total
- Acceptable for modern systems

### Calculation Time:
- PSD on full resolution takes longer but is accurate
- User sees "Calculating..." message
- Typical: 1-5 seconds for 100s of data
- Worth the wait for correct results

### Plotting Performance:
- Decimated data keeps plots responsive
- ~10k points per channel is optimal for pyqtgraph
- No lag when panning/zooming

---

## Verification

Before committing, verify:

1. **Search for old variables**:
   ```bash
   grep -n "self\.time_data[^_]" psd_window.py
   grep -n "self\.signal_data[^_]" psd_window.py
   ```
   Should return NO results (all should be `_full` or `_display`)

2. **Run the tool**:
   - Load HDF5 data
   - Calculate PSD
   - Verify no errors

3. **Check PSD results**:
   - Compare with previous version
   - Should capture higher frequencies now
   - Maximax should be >= averaged

4. **Run tests**:
   ```bash
   pytest tests/test_psd.py -v
   ```

---

## Next Steps After GUI Update

1. Update CSV loader to return dict (for consistency)
2. Create comprehensive unit tests
3. Update spectrogram window (if needed)
4. Update documentation
5. Performance profiling (if needed)

---

**End of Instructions**
