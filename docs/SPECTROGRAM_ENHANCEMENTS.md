# Spectrogram GUI Enhancements

**Date**: January 22, 2026  
**Version**: Enhanced spectrogram window  
**Status**: Complete

---

## Overview

The spectrogram window has been significantly enhanced with professional features for better visualization control and analysis capabilities.

---

## New Features

### 1. **SNR-Based Color Scale**

**What it does**: Controls the dynamic range of the color scale using Signal-to-Noise Ratio (SNR) in dB.

**How to use**:
- Adjust "SNR (dB)" spinbox in Display Options (default: 60 dB)
- Higher SNR = larger dynamic range (more detail in weak signals)
- Lower SNR = smaller dynamic range (focus on strong signals)

**Technical details**:
- Color scale max = maximum power in spectrogram
- Color scale min = max - SNR (dB)
- Example: If max = -20 dB and SNR = 60 dB, then min = -80 dB

**Use cases**:
- SNR = 40 dB: Focus on dominant features
- SNR = 60 dB: Balanced view (default)
- SNR = 80 dB: Show weak signals and noise floor

---

### 2. **Actual Δf Display**

**What it does**: Shows the actual frequency resolution achieved after efficient FFT rounding.

**Display location**: Parameters panel, below "Desired Δf (Hz)"

**Example**:
```
Desired Δf (Hz): 1.0
Actual Δf (Hz):  0.977    ← Shown in blue
```

**Why it matters**:
- When "Efficient FFT" is enabled, nperseg is rounded to power of 2
- Actual df = sample_rate / nperseg (rounded)
- Helps understand true frequency resolution

**Calculation**:
```python
nperseg_desired = int(sample_rate / df_desired)
nperseg_actual = 2^ceil(log2(nperseg_desired))  # If efficient FFT
actual_df = sample_rate / nperseg_actual
```

---

### 3. **Parameter and Display Panel Separation**

**Layout**: 
- Left side (80%): Spectrogram plots
- Right side (20%): Scrollable control panel

**Control panel sections**:
1. **Parameters**: Window, Δf, overlap, efficient FFT
2. **Display Options**: Frequency range, scale, colormap, SNR, colorbar
3. **Axis Limits**: Auto/manual toggle, time limits
4. **Recalculate Button**: Apply parameter changes

**Benefits**:
- Clear separation of calculation vs visualization controls
- Scrollable panel for small screens
- More space for spectrograms
- Professional layout matching PSD tool

---

### 4. **Custom Axis Limits**

**What it does**: Allows manual control of time axis limits.

**How to use**:
1. **Auto mode** (default):
   - "Auto Limits" checkbox checked
   - Time limits automatically set to data range
   - Manual controls disabled

2. **Manual mode**:
   - Uncheck "Auto Limits"
   - Set "Time Min" and "Time Max" manually
   - Click "Apply Limits"
   - All spectrograms zoom to specified range

**Use cases**:
- Focus on specific time segment
- Compare specific events across channels
- Zoom into transient features

---

### 5. **Colorbar Visibility Toggle**

**What it does**: Show or hide the colorbar legend on spectrograms.

**How to use**:
- Check "Show Colorbar" to display colorbar
- Uncheck to hide colorbar (more plot space)

**Colorbar shows**:
- Power range in dB
- Min value (bottom) = max - SNR
- Max value (top) = maximum power

**When to hide**:
- Multi-channel view (less clutter)
- Exporting for presentations
- When SNR is shown in title

---

### 6. **Improved Window Size**

**New minimum size**: 1400 x 900 pixels (was 1200 x 800)

**Reason**: Accommodate new control panel and larger spectrograms

---

## Feature Comparison

### Before
```
┌─────────────────────────────────────┐
│  Spectrogram                        │
│  ┌─────────────────────────────┐   │
│  │                             │   │
│  │    Spectrogram Plot         │   │
│  │                             │   │
│  └─────────────────────────────┘   │
│                                     │
│  Controls (mixed):                  │
│  - Window, Δf, Overlap              │
│  - Freq range, Scale, Colormap      │
│  - Recalculate button               │
└─────────────────────────────────────┘
```

### After
```
┌───────────────────────────────────────────────────────┐
│  Spectrogram                                          │
│  ┌────────────────────┐  ┌──────────────────────┐    │
│  │                    │  │ PARAMETERS           │    │
│  │   Spectrogram      │  │ - Window             │    │
│  │   Plot(s)          │  │ - Desired Δf         │    │
│  │                    │  │ - Actual Δf ← NEW    │    │
│  │   (80% width)      │  │ - Overlap            │    │
│  │                    │  │ - Efficient FFT      │    │
│  └────────────────────┘  │                      │    │
│                          │ DISPLAY OPTIONS      │    │
│                          │ - Freq range         │    │
│                          │ - Y-Scale            │    │
│                          │ - Colormap           │    │
│                          │ - SNR (dB) ← NEW     │    │
│                          │ - Show Colorbar ← NEW│    │
│                          │                      │    │
│                          │ AXIS LIMITS ← NEW    │    │
│                          │ - Auto/Manual        │    │
│                          │ - Time min/max       │    │
│                          │ - Apply button       │    │
│                          │                      │    │
│                          │ [Recalculate]        │    │
│                          └──────────────────────┘    │
│                          (20% width, scrollable)     │
└───────────────────────────────────────────────────────┘
```

---

## Technical Implementation

### SNR Color Scale

```python
# Calculate color scale based on SNR
max_power = np.max(Sxx_db)
min_power = max_power - snr_db

# Set image levels
img.setImage(Sxx_plot, autoLevels=False, levels=(min_power, max_power))
```

### Actual Δf Calculation

```python
# Calculate nperseg from desired df
nperseg = int(sample_rate / df_desired)

# Use efficient FFT size if requested
if efficient_fft:
    nperseg = 2 ** int(np.ceil(np.log2(nperseg)))

# Calculate actual df
actual_df = sample_rate / nperseg

# Display
self.actual_df_label.setText(f"{actual_df:.3f}")
```

### Custom Axis Limits

```python
def _apply_custom_limits(self):
    """Apply custom axis limits to all plots."""
    time_min = self.time_min_spin.value()
    time_max = self.time_max_spin.value()
    
    # Validate
    if time_min >= time_max:
        show_warning(self, "Invalid Limits", 
                     "Time minimum must be less than maximum.")
        return
    
    # Apply to all plots
    for plot_widget in self.plot_widgets:
        plot_widget.setXRange(time_min, time_max, padding=0)
```

---

## Usage Examples

### Example 1: Focus on Strong Signals

**Goal**: Highlight dominant frequency components

**Settings**:
- SNR (dB): 40
- Show Colorbar: Checked
- Auto Limits: Checked

**Result**: Color scale focuses on 40 dB range around peak, weak signals appear dark

---

### Example 2: Analyze Noise Floor

**Goal**: See weak signals and noise characteristics

**Settings**:
- SNR (dB): 80
- Show Colorbar: Checked
- Auto Limits: Checked

**Result**: Color scale spans 80 dB, reveals noise floor and weak components

---

### Example 3: Zoom to Event

**Goal**: Focus on specific time segment (e.g., 10-20 seconds)

**Settings**:
- Auto Limits: Unchecked
- Time Min: 10.0
- Time Max: 20.0
- Click "Apply Limits"

**Result**: All spectrograms zoom to 10-20 second range

---

### Example 4: Clean Export View

**Goal**: Prepare spectrograms for presentation

**Settings**:
- SNR (dB): 50 (balanced)
- Show Colorbar: Unchecked (less clutter)
- Colormap: viridis (professional)

**Result**: Clean spectrograms without colorbar, SNR shown in title

---

## Troubleshooting

### Issue: Actual Δf very different from desired

**Cause**: Efficient FFT rounds nperseg to power of 2

**Solution**: 
- Disable "Efficient FFT" for exact df
- Or adjust desired df to get closer actual df
- Example: Desired 1.0 Hz → Actual 0.977 Hz (acceptable)

### Issue: Colorbar not visible

**Cause**: "Show Colorbar" unchecked

**Solution**: Check "Show Colorbar" in Display Options

### Issue: Can't change time limits

**Cause**: "Auto Limits" is checked

**Solution**: Uncheck "Auto Limits" to enable manual controls

### Issue: Spectrogram too dark/bright

**Cause**: SNR setting not appropriate for data

**Solution**: 
- Too dark → Decrease SNR (e.g., 40 dB)
- Too bright/washed out → Increase SNR (e.g., 80 dB)

---

## Performance Notes

- SNR calculation is instant (no recalculation needed)
- Colorbar toggle is instant
- Custom axis limits are instant (zoom only)
- Parameter changes require "Recalculate" (full recomputation)

---

## Future Enhancements

Potential additions:
1. Vertical carousel buttons (up/down) for multi-channel navigation
2. Export individual spectrograms to image files
3. Cursor readout showing time, frequency, power
4. Synchronized zoom across all channels
5. Colorbar position control (left/right/top/bottom)

---

**End of Document**
