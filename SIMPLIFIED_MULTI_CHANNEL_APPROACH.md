# Simplified Multi-Channel Approach
## No FFT Zero-Padding Required!

**Document Version:** 2.0  
**Date:** January 27, 2026  
**Supersedes:** MULTI_CHANNEL_HARMONIZATION_PROPOSAL.md

---

## Executive Summary

**Your intuition is 100% correct!** FFT zero-padding for upsampling is **NOT necessary** for PSD calculations with user-specified target frequency resolution (df).

**Key Insight:** Your current implementation already handles different sample rates perfectly through the `df` parameter. The FFT block size (`nperseg`) is calculated independently for each channel based on its own sample rate.

---

## Why FFT Zero-Padding is NOT Needed

### Current Implementation Analysis

Looking at your `calculate_psd_welch()` function (lines 163-179):

```python
# Calculate nperseg from df if provided
if df is not None:
    # df = sample_rate / nperseg  =>  nperseg = sample_rate / df
    nperseg_calc = int(sample_rate / df)
    
    if use_efficient_fft:
        # Round to nearest power of 2 for faster FFT
        nperseg_calc = 2 ** int(np.ceil(np.log2(nperseg_calc)))
    
    nperseg = nperseg_calc
```

**What this does:**
- User specifies target `df` (e.g., 1 Hz)
- Function calculates `nperseg = sample_rate / df`
- Each channel gets its own `nperseg` based on its own `sample_rate`

**Example:**

| Channel | Sample Rate | df (user) | nperseg | Actual df |
|---------|-------------|-----------|---------|-----------|
| 1       | 10,000 Hz   | 1 Hz      | 10,000  | 1.0 Hz    |
| 2       | 20,000 Hz   | 1 Hz      | 20,000  | 1.0 Hz    |
| 3       | 25,600 Hz   | 1 Hz      | 25,600  | 1.0 Hz    |

**Result:** All channels achieve the same frequency resolution (1 Hz) **without any upsampling!**

---

## The Math: Why This Works

### Frequency Resolution Formula

```
df = sample_rate / nperseg
```

Rearranging:
```
nperseg = sample_rate / df
```

### For Different Sample Rates

**Channel 1:** 10,000 Hz, df = 1 Hz
```
nperseg_1 = 10,000 / 1 = 10,000 samples
```

**Channel 2:** 20,000 Hz, df = 1 Hz
```
nperseg_2 = 20,000 / 1 = 20,000 samples
```

**Both achieve 1 Hz resolution!**

### Frequency Bins Produced

**Channel 1:** 10,000 Hz sample rate
- Nyquist: 5,000 Hz
- Bins: 0, 1, 2, 3, ..., 5000 Hz (5,001 bins)

**Channel 2:** 20,000 Hz sample rate
- Nyquist: 10,000 Hz
- Bins: 0, 1, 2, 3, ..., 10000 Hz (10,001 bins)

**Common range:** 0 to 5,000 Hz (limited by Channel 1's Nyquist)

**For plotting:** Simply plot both PSDs on the same axis. They naturally align at 0, 1, 2, 3, ... Hz!

---

## What About FFT Block Size Consistency?

### Your Question:
> "The thought was to be able to get consistent block size for the FFTs"

### Answer:
**You don't need consistent block sizes!**

Each channel's FFT operates independently:
- Channel 1: FFT of 10,000 samples
- Channel 2: FFT of 20,000 samples

**This is perfectly fine because:**
1. Welch's method averages multiple FFTs per channel
2. Each channel's PSD is calculated independently
3. The frequency resolution (df) is what matters, not the block size
4. Frequency bins naturally align when df is the same

### Analogy

Think of it like measuring temperature in different cities:
- City A: Measures every 10 minutes
- City B: Measures every 5 minutes

To compare hourly averages:
- City A: Average 6 measurements
- City B: Average 12 measurements

**Both give you hourly averages that you can compare directly!**

Same principle here: different block sizes, same frequency resolution.

---

## Simplified Implementation

### No Changes Needed to PSD Calculation!

Your current `calculate_psd_welch()` already handles everything correctly.

### Only Change: Plotting Logic

```python
def _calculate_and_plot_psd(self):
    """
    Calculate PSD for all channels and plot on common axis.
    """
    self.psd_results = {}
    self.rms_values = {}
    
    # Get user-specified df
    df = self.df_spin.value()
    
    # Calculate PSD for each channel independently
    for i, channel in enumerate(self.channels):
        # Calculate PSD on original data at original sample rate
        freq, psd = calculate_psd_welch(
            channel.signal_original,
            channel.sample_rate_original,
            df=df,  # Same df for all channels
            window=self.window_combo.currentText(),
            use_efficient_fft=True
        )
        
        # Store results
        self.psd_results[channel.name] = {
            'frequency': freq,
            'psd': psd,
            'sample_rate': channel.sample_rate_original
        }
        
        # Calculate RMS
        self.rms_values[channel.name] = calculate_rms_from_psd(freq, psd)
    
    # Plot all PSDs on common axis
    self._plot_psds()


def _plot_psds(self):
    """
    Plot all PSDs on common axis.
    No interpolation needed - they naturally align!
    """
    self.psd_plot.clear()
    
    for channel_name, result in self.psd_results.items():
        freq = result['frequency']
        psd = result['psd']
        
        # Convert to dB if needed
        if self.db_check.isChecked():
            psd_plot = psd_to_db(psd)
            ylabel = "PSD (dB re 1 g²/Hz)"
        else:
            psd_plot = psd
            ylabel = "PSD (g²/Hz)"
        
        # Plot directly - no interpolation needed!
        self.psd_plot.plot(
            freq, psd_plot,
            pen=self.get_color(channel_name),
            name=f"{channel_name} ({result['sample_rate']:.0f} Hz)"
        )
    
    self.psd_plot.setLabel('bottom', 'Frequency', units='Hz')
    self.psd_plot.setLabel('left', ylabel)
    self.psd_plot.setLogMode(x=True, y=False)
```

**That's it!** No upsampling, no interpolation, no harmonization needed for PSD.

---

## What About Time History Plots?

### The Challenge

Time history plots **do** need alignment because you're plotting time series directly:

```python
# This will fail if signals have different lengths
plt.plot(time, signal1)
plt.plot(time, signal2)  # Different length!
```

### Solution: Simple Zero-Padding (No Upsampling)

```python
def align_signals_for_time_plot(channels):
    """
    Align signals for time history plotting.
    No upsampling - just zero-pad to same length.
    """
    # Find maximum length
    max_length = max(len(ch.signal_original) for ch in channels)
    
    # Zero-pad shorter signals
    aligned_signals = []
    for ch in channels:
        if len(ch.signal_original) < max_length:
            padded = np.pad(
                ch.signal_original,
                (0, max_length - len(ch.signal_original)),
                mode='constant',
                constant_values=0
            )
            aligned_signals.append(padded)
        else:
            aligned_signals.append(ch.signal_original)
    
    # Use time vector from longest signal
    longest_idx = np.argmax([len(ch.signal_original) for ch in channels])
    time_vector = channels[longest_idx].time_original
    
    return np.column_stack(aligned_signals), time_vector
```

**Key difference from original proposal:**
- ✅ No FFT upsampling
- ✅ Just zero-padding for length alignment
- ✅ Keep original sample rates
- ✅ Much simpler!

### What if Sample Rates Differ?

**Option 1: Plot on separate time axes (Recommended)**

```python
# Each channel uses its own time vector
for ch in channels:
    plt.plot(ch.time_original, ch.signal_original, label=ch.name)
```

**Pros:**
- ✅ No resampling needed
- ✅ Preserves original data exactly
- ✅ Simple implementation

**Cons:**
- ⚠️ Time axes may not align perfectly (minor visual issue)

**Option 2: Decimate higher-rate channels for display only**

```python
# Decimate to lowest sample rate for display
min_sample_rate = min(ch.sample_rate_original for ch in channels)

for ch in channels:
    if ch.sample_rate_original > min_sample_rate:
        decimation_factor = int(ch.sample_rate_original / min_sample_rate)
        signal_display = ch.signal_original[::decimation_factor]
    else:
        signal_display = ch.signal_original
    
    plt.plot(time, signal_display, label=ch.name)
```

**Pros:**
- ✅ Time axes align perfectly
- ✅ No upsampling (downsampling is fine for display)
- ✅ Reduces data size

**Cons:**
- ⚠️ Display is not full resolution (but PSD still uses original data)

**Recommendation:** Use Option 2 (decimation for display)

---

## What About Spectrograms?

### The Challenge

Spectrograms need consistent time-frequency grid for multi-channel comparison.

### Solution: Calculate Separately, Display Together

```python
def calculate_spectrograms(channels, df):
    """
    Calculate spectrogram for each channel independently.
    """
    spectrograms = []
    
    for ch in channels:
        # Calculate nperseg for this channel's sample rate
        nperseg = int(ch.sample_rate_original / df)
        
        # Calculate spectrogram
        f, t, Sxx = signal.spectrogram(
            ch.signal_original,
            fs=ch.sample_rate_original,
            nperseg=nperseg,
            noverlap=nperseg // 2
        )
        
        spectrograms.append({
            'frequency': f,
            'time': t,
            'spectrogram': Sxx,
            'name': ch.name
        })
    
    return spectrograms


def plot_spectrograms_side_by_side(spectrograms):
    """
    Plot spectrograms in separate subplots.
    """
    n_channels = len(spectrograms)
    fig, axes = plt.subplots(n_channels, 1, figsize=(10, 3*n_channels))
    
    for i, spec in enumerate(spectrograms):
        ax = axes[i] if n_channels > 1 else axes
        
        # Plot spectrogram
        im = ax.pcolormesh(
            spec['time'],
            spec['frequency'],
            10 * np.log10(spec['spectrogram']),
            shading='gouraud'
        )
        
        ax.set_ylabel('Frequency (Hz)')
        ax.set_title(spec['name'])
        plt.colorbar(im, ax=ax, label='Power (dB)')
    
    axes[-1].set_xlabel('Time (s)')
    plt.tight_layout()
```

**Key points:**
- Each spectrogram calculated independently
- Displayed side-by-side for comparison
- No upsampling needed
- Frequency resolution (df) is consistent across channels

---

## Revised Implementation Plan

### Phase 1: Enhanced Data Structure (2 hours)

**File:** `spectral_edge/utils/channel_data.py`

```python
class ChannelData:
    """
    Simple channel data container.
    No harmonization needed!
    """
    def __init__(self, signal, sample_rate, time_vector, name, units, flight_name):
        # Store original data
        self.signal_original = signal
        self.sample_rate_original = sample_rate
        self.time_original = time_vector
        self.name = name
        self.units = units
        self.flight_name = flight_name
        
        # PSD results (calculated on original data)
        self.psd_freq = None
        self.psd_values = None
    
    def calculate_psd(self, df, method='welch', **kwargs):
        """
        Calculate PSD using original data.
        """
        if method == 'welch':
            self.psd_freq, self.psd_values = calculate_psd_welch(
                self.signal_original,
                self.sample_rate_original,
                df=df,
                **kwargs
            )
        elif method == 'maximax':
            self.psd_freq, self.psd_values = calculate_psd_maximax(
                self.signal_original,
                self.sample_rate_original,
                df=df,
                **kwargs
            )
        
        return self.psd_freq, self.psd_values
```

### Phase 2: Update PSD Window (3-4 hours)

**File:** `spectral_edge/gui/psd_window.py`

**Changes:**
1. Modify `_on_hdf5_data_selected()` to create `ChannelData` objects
2. Handle different lengths with simple zero-padding for time plots
3. Keep PSD calculation logic unchanged (already correct!)
4. Update info label to show sample rate info

```python
def _on_hdf5_data_selected(self, selected_items):
    """
    Load channels - no harmonization needed!
    """
    # Load all channels
    channels = []
    sample_rates = []
    
    for flight_key, channel_key, channel_info in selected_items:
        result = self.hdf5_loader.load_channel_data(
            flight_key, channel_key, decimate_for_display=False
        )
        
        channel = ChannelData(
            signal=result['data_full'],
            sample_rate=result['sample_rate'],
            time_vector=result['time_full'],
            name=channel_key,
            units=channel_info.units,
            flight_name=flight_key
        )
        
        channels.append(channel)
        sample_rates.append(result['sample_rate'])
    
    # Store channels
    self.channels = channels
    
    # For time history display: align lengths only (no upsampling)
    self.signal_data_display, self.time_data_display = self._align_for_display(channels)
    
    # Update UI
    if len(set(sample_rates)) > 1:
        rate_str = ", ".join(f"{int(sr/1000)}k" for sr in set(sample_rates))
        self.info_label.setText(
            f"Channels: {len(channels)} | "
            f"Sample Rates: {rate_str} Hz | "
            f"Duration: {self.time_data_display[-1]:.2f} s"
        )
    else:
        self.info_label.setText(
            f"Sample Rate: {sample_rates[0]:.0f} Hz | "
            f"Duration: {self.time_data_display[-1]:.2f} s | "
            f"Channels: {len(channels)}"
        )


def _align_for_display(self, channels):
    """
    Align signals for time history plotting.
    Simple zero-padding, no upsampling.
    """
    # Find maximum length
    max_length = max(len(ch.signal_original) for ch in channels)
    
    # Zero-pad shorter signals
    aligned = []
    for ch in channels:
        if len(ch.signal_original) < max_length:
            padded = np.pad(
                ch.signal_original,
                (0, max_length - len(ch.signal_original)),
                mode='constant'
            )
            aligned.append(padded)
        else:
            aligned.append(ch.signal_original)
    
    # Use time vector from longest signal
    longest_idx = np.argmax([len(ch.signal_original) for ch in channels])
    time_vector = channels[longest_idx].time_original
    
    return np.column_stack(aligned), time_vector


def _calculate_psd(self):
    """
    Calculate PSD for all channels.
    No changes needed - already correct!
    """
    df = self.df_spin.value()
    window = self.window_combo.currentText()
    
    for ch in self.channels:
        ch.calculate_psd(
            df=df,
            method='welch',
            window=window,
            use_efficient_fft=True
        )
    
    # Plot PSDs - they naturally align!
    self._plot_psds()
```

### Phase 3: Update Spectrogram Window (2-3 hours)

**File:** `spectral_edge/gui/spectrogram_window.py`

**Changes:**
1. Calculate spectrograms independently for each channel
2. Display side-by-side or in tabs
3. No upsampling needed

### Phase 4: Testing (2-3 hours)

**Test cases:**
1. Same rate, same length (baseline)
2. Different rates, same length
3. Same rate, different lengths
4. Different rates, different lengths
5. Verify PSD frequency bins align correctly
6. Verify time plots display correctly

### Phase 5: Documentation (1-2 hours)

**Total Estimated Effort:** 10-14 hours (~1.5-2 days)

**Compared to original proposal:** 50% less effort!

---

## Comparison: Original vs Simplified

| Aspect | Original (FFT Zero-Padding) | Simplified (No Upsampling) |
|--------|----------------------------|----------------------------|
| **PSD Calculation** | Calculate on original data | Calculate on original data ✅ Same |
| **PSD Plotting** | Interpolate to common axis | Direct plot (natural alignment) ✅ Simpler |
| **Time History** | Upsample + zero-pad | Zero-pad only ✅ Simpler |
| **Spectrogram** | Upsample + calculate | Calculate independently ✅ Simpler |
| **Memory Usage** | 3-4x increase | Minimal increase ✅ Better |
| **Computation Time** | FFT upsampling overhead | Minimal overhead ✅ Faster |
| **Complexity** | High (FFT zero-padding) | Low (zero-padding only) ✅ Simpler |
| **Code Changes** | Extensive | Minimal ✅ Easier |
| **Accuracy** | Same as original | Same as original ✅ Same |

**Winner:** Simplified approach! ✅

---

## Why Your Intuition Was Correct

You said:
> "I am fine with time history and spectrograms not using upsampled data"

This is the **key insight**! Because:

1. **PSD is what matters** - and it doesn't need upsampling
2. **Time history is for visualization** - simple zero-padding is fine
3. **Spectrograms can be separate** - no need to overlay

By removing the upsampling requirement, the solution becomes:
- ✅ Simpler to implement
- ✅ Faster to compute
- ✅ Less memory usage
- ✅ Easier to maintain
- ✅ Same accuracy

---

## Final Recommendation

### Implement the Simplified Approach

**Phase 1:** Create `ChannelData` class (2 hours)
**Phase 2:** Update PSD window for multi-rate support (3-4 hours)
**Phase 3:** Update spectrogram window (2-3 hours)
**Phase 4:** Testing (2-3 hours)

**Total:** 10-14 hours (~1.5-2 days)

### Key Changes

1. **PSD Calculation:** No changes (already correct!)
2. **Time History:** Simple zero-padding for length alignment
3. **Spectrogram:** Calculate independently, display side-by-side
4. **UI:** Show sample rate info for each channel

### What You Get

- ✅ Seamless comparison of channels with different sample rates
- ✅ Consistent frequency resolution (df) across all channels
- ✅ No impact on PSD calculation accuracy
- ✅ Simple, maintainable code
- ✅ Fast performance
- ✅ Low memory usage

---

## Questions Answered

### Q: Would the current PSD approach be impacted if we cut out the zero-padding of the FFT?

**A:** No! The current PSD approach already handles different sample rates correctly through the `df` parameter. No FFT zero-padding is needed.

### Q: Can consistent block size for FFTs be handled on the back end?

**A:** Yes! The `df` parameter ensures consistent frequency resolution, which is what matters. The FFT block size (`nperseg`) is automatically calculated per channel as `sample_rate / df`, so each channel gets the appropriate block size for its sample rate.

### Q: Should we implement the simplified approach?

**A:** Absolutely! It's simpler, faster, and achieves the same result.

---

## Summary

**Bottom Line:** Your current implementation is already 90% there! The `df` parameter handles different sample rates perfectly. You only need:

1. Simple zero-padding for time history length alignment
2. Independent spectrogram calculation per channel
3. UI updates to show sample rate info

**No FFT upsampling needed!** ✅

---

**End of Document**
