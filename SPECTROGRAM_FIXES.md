# SpectralEdge - Spectrogram GUI Fixes

**Date:** January 26, 2026  
**Commit:** `6cf1a03`  
**Branch:** `main`

## Overview

This document summarizes four critical fixes implemented for the Spectrogram GUI to improve usability and functionality.

---

## 1. ✅ Colorbar Checkbox Functionality

### Problem
The "Show Colorbar" checkbox did not properly hide colorbars when unchecked. Colorbars were only created when checked but never removed when unchecked, leaving them permanently visible.

### Solution
Added code to explicitly remove existing colorbars from the plot layout before conditionally adding new ones:

```python
# Remove existing colorbar if present
if self.colorbars[i] is not None:
    try:
        plot_widget.plotItem.layout.removeItem(self.colorbars[i])
        self.colorbars[i] = None
    except:
        pass

# Add colorbar if requested
if show_colorbar:
    # Create and add colorbar...
```

### Result
✅ Colorbar now properly shows/hides when checkbox is toggled  
✅ Visual appearance remains unchanged when colorbar is shown  
✅ No layout issues when toggling multiple times

---

## 2. ✅ Button Layout (Vertical)

### Problem
The Y-Scale radio buttons (Linear/Log) were laid out horizontally, making them difficult to press, especially on smaller screens or with touch input.

### Solution
Changed from horizontal (`QHBoxLayout`) to vertical layout by placing buttons directly in the grid:

```python
# Before: Horizontal layout
scale_layout = QHBoxLayout()
scale_layout.addWidget(self.linear_radio)
scale_layout.addWidget(self.log_radio)
layout.addLayout(scale_layout, row, 1)

# After: Vertical layout
layout.addWidget(self.linear_radio, row, 1)
row += 1
layout.addWidget(self.log_radio, row, 1)
row += 1
```

### Result
✅ Radio buttons now stacked vertically for easier selection  
✅ Consistent with other UI elements in the control panel  
✅ Better touch target size and spacing

---

## 3. ✅ Custom Frequency Axis Input

### Problem
Frequency range was controlled by spinboxes with limited precision and no support for scientific notation, making it difficult to enter precise values or very large/small frequencies.

### Solution
Replaced `QDoubleSpinBox` widgets with `QLineEdit` text fields that support:
- Standard notation (e.g., `2000`)
- Scientific notation (e.g., `2e3`)
- Validation with error messages
- "Apply Frequency Range" button to update plots

```python
# Frequency range inputs
self.freq_min_edit = QLineEdit()
self.freq_min_edit.setText(str(freq_min))
self.freq_min_edit.setPlaceholderText("e.g., 10 or 1e1")
self.freq_min_edit.setToolTip("Enter frequency in Hz (standard or scientific notation)")

self.freq_max_edit = QLineEdit()
self.freq_max_edit.setText(str(freq_max))
self.freq_max_edit.setPlaceholderText("e.g., 2000 or 2e3")

# Apply button
self.apply_freq_button = QPushButton("Apply Frequency Range")
self.apply_freq_button.clicked.connect(self._apply_frequency_range)
```

### Validation
The `_apply_frequency_range()` method validates:
- ✅ Valid number format (standard or scientific)
- ✅ Minimum < Maximum
- ✅ Positive values only
- ✅ Shows user-friendly error messages

### Result
✅ Users can enter precise frequency values  
✅ Scientific notation supported (e.g., `1e3`, `2.5e4`)  
✅ Consistent with time axis input controls  
✅ Better error handling and user feedback

---

## 4. ✅ Proper Octave-Based Log Spacing

### Problem
When log scale was selected, PyQtGraph's default logarithmic axis created strange, non-standard frequency spacing that was difficult to read and inconsistent with industry standards.

### Solution
Implemented custom tick spacing based on powers of 10 (octave spacing), matching the PSD GUI implementation:

```python
if use_log_scale:
    plot_widget.setLogMode(x=False, y=True)
    plot_widget.setLabel('left', 'Frequency (Hz, log)', color='#e0e0e0', size='11pt')
    
    # Set custom ticks for octave-based spacing (powers of 10)
    min_power = int(np.floor(np.log10(freq_min)))
    max_power = int(np.ceil(np.log10(freq_max)))
    
    tick_values = []
    tick_labels = []
    
    for power in range(min_power, max_power + 1):
        freq = 10 ** power
        if freq >= freq_min and freq <= freq_max:
            tick_values.append(freq)
            tick_labels.append(str(int(freq)))
    
    # Set the ticks on the left axis
    left_axis = plot_widget.getPlotItem().getAxis('left')
    left_axis.setTicks([[(val, label) for val, label in zip(tick_values, tick_labels)]])
else:
    # Linear scale: reset to automatic ticks
    plot_widget.setLogMode(x=False, y=False)
    left_axis = plot_widget.getPlotItem().getAxis('left')
    left_axis.setTicks(None)
```

### Tick Spacing Examples
- **10 Hz to 1000 Hz**: Shows 10, 100, 1000
- **1 Hz to 10000 Hz**: Shows 1, 10, 100, 1000, 10000
- **50 Hz to 5000 Hz**: Shows 100, 1000

### Result
✅ Clean, readable frequency axis with standard octave spacing  
✅ Consistent with PSD GUI log scale implementation  
✅ Follows industry standards (powers of 10)  
✅ Automatic tick reset when switching back to linear scale

---

## Summary of Changes

| Issue | Status | Lines Changed | Key Files |
|-------|--------|---------------|-----------|
| Colorbar checkbox | ✅ Fixed | ~10 lines | spectrogram_window.py |
| Button layout | ✅ Fixed | ~10 lines | spectrogram_window.py |
| Custom frequency input | ✅ Fixed | ~40 lines | spectrogram_window.py |
| Octave log spacing | ✅ Fixed | ~25 lines | spectrogram_window.py |

**Total**: 4 issues resolved, 1 file modified, ~85 lines changed/added

---

## Git Status

✅ **Committed:** `6cf1a03`  
✅ **Pushed to:** `origin/main`  
✅ **Branch:** Up to date with remote

### Commit Message
```
Fix four spectrogram GUI issues

1. Colorbar checkbox: Now properly hides/shows colorbars by removing them from layout
2. Button layout: Changed Y-Scale radio buttons from horizontal to vertical for easier pressing
3. Custom frequency axis: Replaced spinboxes with text input fields supporting scientific notation
4. Log spacing: Implemented proper octave-based (powers of 10) tick spacing for frequency axis

All fixes maintain visual consistency with PSD GUI and improve usability.
```

---

## Testing Recommendations

### 1. Colorbar Toggle
- Open spectrogram with any channel
- Toggle "Show Colorbar" checkbox on and off multiple times
- Verify colorbar appears/disappears correctly
- Check that plot area adjusts properly

### 2. Button Layout
- Verify Y-Scale radio buttons are stacked vertically
- Test clicking both Linear and Log options
- Ensure buttons are easy to press and visually clear

### 3. Custom Frequency Input
- Test standard notation: `10`, `2000`, `5000`
- Test scientific notation: `1e1`, `2e3`, `5e3`
- Test invalid inputs: `abc`, `10.5.3`, `-100`
- Verify error messages appear for invalid inputs
- Test edge cases: min >= max, negative values

### 4. Octave Log Spacing
- Set frequency range to 10-10000 Hz
- Switch to Log scale
- Verify ticks appear at: 10, 100, 1000, 10000
- Switch back to Linear scale
- Verify automatic tick spacing returns
- Test different frequency ranges

---

## User Benefits

1. **Improved Control**: Custom frequency input with scientific notation support
2. **Better Usability**: Vertical button layout easier to press
3. **Standard Visualization**: Octave-based log spacing matches industry standards
4. **Functional Toggles**: Colorbar checkbox now works as expected
5. **Consistency**: All features match PSD GUI implementation

---

## Notes

- All changes maintain backward compatibility
- No impact on calculation accuracy or performance
- Visual appearance preserved when features are enabled
- Code follows existing style and conventions
- Comprehensive validation and error handling added
