# Multi-Channel Harmonization Proposal
## Handling Different Sample Rates and Time Lengths

**Document Version:** 1.0  
**Date:** January 27, 2026  
**Author:** SpectralEdge Development Team

---

## Executive Summary

This document proposes a comprehensive approach for handling channels with different sample rates and time lengths in SpectralEdge, enabling seamless multi-channel comparison without impacting PSD calculation integrity.

**Key Requirements:**
1. Handle different sample rates via FFT zero-padding (upsampling)
2. Harmonize to next power-of-2 sample rate
3. Handle different time lengths gracefully
4. Maintain PSD calculation accuracy
5. Enable seamless visual comparison

---

## Current State Analysis

### What Works Now
- ✅ Multiple channels from same flight (same sample rate, same length)
- ✅ Warning when sample rates differ (line 1825 in psd_window.py)
- ✅ Uses first channel's time vector as reference
- ✅ Stacks signals with `np.column_stack()` assuming equal lengths

### Current Limitations
- ❌ Different sample rates cause warning but no harmonization
- ❌ Different lengths cause `np.column_stack()` to fail with shape mismatch
- ❌ No resampling or interpolation implemented
- ❌ Time alignment not handled

---

## Proposed Solution Architecture

### Three-Layer Approach

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Data Loading & Validation                          │
│  - Detect sample rate and length differences                │
│  - Store original metadata for each channel                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Harmonization (NEW)                                │
│  - Sample rate harmonization via FFT zero-padding           │
│  - Time length alignment via zero-padding or truncation     │
│  - Maintain original data for individual PSD calculations   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Analysis & Visualization                           │
│  - PSD calculated on ORIGINAL data (per channel)            │
│  - Harmonized data used ONLY for time plots & spectrograms  │
│  - Frequency axes aligned for comparison                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Part 1: Sample Rate Harmonization

### Strategy: FFT-Based Upsampling with Zero-Padding

**Your Requirement:** "Upsample by zero-padding the FFT at the center of the spectrum"

This is the **correct** approach for spectral analysis because:
- ✅ Preserves original frequency content exactly
- ✅ No interpolation artifacts
- ✅ Maintains phase relationships
- ✅ Computationally efficient
- ✅ Reversible process

### Algorithm

```python
def upsample_via_fft_zeropad(signal, original_fs, target_fs):
    """
    Upsample signal using FFT zero-padding (frequency domain interpolation).
    
    This method:
    1. Takes FFT of original signal
    2. Zero-pads in the CENTER of the spectrum
    3. Takes IFFT to get upsampled time series
    
    Parameters:
    -----------
    signal : np.ndarray
        Original time series
    original_fs : float
        Original sample rate (Hz)
    target_fs : float
        Target sample rate (Hz), must be >= original_fs
        
    Returns:
    --------
    upsampled_signal : np.ndarray
        Upsampled time series at target_fs
    new_time : np.ndarray
        New time vector
    """
    if target_fs < original_fs:
        raise ValueError("target_fs must be >= original_fs for upsampling")
    
    if target_fs == original_fs:
        return signal, np.arange(len(signal)) / original_fs
    
    # Calculate upsampling ratio
    ratio = target_fs / original_fs
    
    # FFT of original signal
    fft_signal = np.fft.fft(signal)
    n_original = len(signal)
    
    # Calculate new length (must maintain ratio)
    n_new = int(np.round(n_original * ratio))
    
    # Zero-pad in frequency domain (INSERT zeros in middle)
    n_half = n_original // 2
    
    if n_original % 2 == 0:  # Even length
        # Split at Nyquist, insert zeros in middle
        fft_padded = np.concatenate([
            fft_signal[:n_half],           # Positive frequencies
            np.zeros(n_new - n_original),  # Zero-padding
            fft_signal[n_half:]            # Negative frequencies
        ])
    else:  # Odd length
        # Split after positive frequencies
        fft_padded = np.concatenate([
            fft_signal[:n_half+1],
            np.zeros(n_new - n_original),
            fft_signal[n_half+1:]
        ])
    
    # Scale by ratio to preserve amplitude
    fft_padded *= ratio
    
    # IFFT to get upsampled signal
    upsampled = np.fft.ifft(fft_padded).real
    
    # New time vector
    new_time = np.arange(len(upsampled)) / target_fs
    
    return upsampled, new_time
```

### Target Sample Rate Selection

**Your Requirement:** "Go to the next power of two sample rate"

```python
def get_target_sample_rate(sample_rates):
    """
    Determine target sample rate as next power of 2 above maximum.
    
    Parameters:
    -----------
    sample_rates : list of float
        Sample rates of all channels
        
    Returns:
    --------
    target_fs : float
        Next power-of-2 sample rate
    """
    max_fs = max(sample_rates)
    
    # Find next power of 2
    power = np.ceil(np.log2(max_fs))
    target_fs = 2 ** power
    
    return target_fs
```

**Example:**
- Channel 1: 10,000 Hz
- Channel 2: 15,000 Hz
- Channel 3: 20,000 Hz
- **Target:** 2^15 = 32,768 Hz (next power of 2 above 20,000)

### Why This Works for PSD

**Critical Insight:** We will **NOT** calculate PSD on upsampled data!

```python
# CORRECT APPROACH (Proposed)
for channel in channels:
    # Calculate PSD on ORIGINAL data at ORIGINAL sample rate
    freq_original, psd_original = calculate_psd_welch(
        channel.data_original,      # ← Original data
        channel.sample_rate_original  # ← Original sample rate
    )
    
    # Interpolate PSD to common frequency axis for plotting
    freq_common = np.linspace(0, target_fs/2, num_points)
    psd_interp = np.interp(freq_common, freq_original, psd_original)
    
    # Plot on common axis
    plot(freq_common, psd_interp)
```

**Why this preserves accuracy:**
1. PSD calculated on original data → No resampling artifacts
2. Only the **frequency axis** is harmonized for visualization
3. Interpolation in frequency domain is safe (smooth function)
4. Each channel's PSD is independent and accurate

---

## Part 2: Time Length Alignment

### The Challenge

**Scenario 1:** Different durations
- Channel 1: 0 to 100 seconds
- Channel 2: 0 to 150 seconds

**Scenario 2:** Different start times (if metadata available)
- Channel 1: 10s to 110s
- Channel 2: 0s to 100s

**Scenario 3:** Different lengths after upsampling
- Channel 1: 100,000 samples @ 10 kHz → 327,680 samples @ 32,768 Hz
- Channel 2: 200,000 samples @ 10 kHz → 655,360 samples @ 32,768 Hz

### Proposed Strategies

#### Strategy A: Zero-Padding (Recommended)

**Use Case:** Time history plots, spectrograms, visual comparison

```python
def align_time_lengths(signals, time_vectors, method='zero_pad'):
    """
    Align signals of different lengths to common time axis.
    
    Parameters:
    -----------
    signals : list of np.ndarray
        List of time series (possibly different lengths)
    time_vectors : list of np.ndarray
        Corresponding time vectors
    method : str
        'zero_pad' or 'truncate'
        
    Returns:
    --------
    aligned_signals : np.ndarray
        2D array (samples x channels) with aligned lengths
    common_time : np.ndarray
        Common time vector
    """
    # Find maximum length and time span
    max_length = max(len(s) for s in signals)
    max_time = max(t[-1] for t in time_vectors)
    min_time = min(t[0] for t in time_vectors)
    
    if method == 'zero_pad':
        # Pad shorter signals with zeros at the end
        aligned = []
        for signal in signals:
            if len(signal) < max_length:
                padded = np.pad(signal, (0, max_length - len(signal)), 
                               mode='constant', constant_values=0)
                aligned.append(padded)
            else:
                aligned.append(signal)
        
        # Use time vector from longest signal
        longest_idx = np.argmax([len(s) for s in signals])
        common_time = time_vectors[longest_idx]
        
        return np.column_stack(aligned), common_time
    
    elif method == 'truncate':
        # Truncate all signals to minimum length
        min_length = min(len(s) for s in signals)
        truncated = [s[:min_length] for s in signals]
        
        # Use time vector from first signal (truncated)
        common_time = time_vectors[0][:min_length]
        
        return np.column_stack(truncated), common_time
```

**Pros of Zero-Padding:**
- ✅ Preserves all data
- ✅ Clear visual indication (zeros) where data doesn't exist
- ✅ Allows full-duration analysis of each channel
- ✅ No information loss

**Cons:**
- ⚠️ Zeros visible in plots (can be masked)
- ⚠️ Need to track valid data regions

#### Strategy B: Truncation

**Use Case:** When you only want overlapping time region

**Pros:**
- ✅ All channels have valid data at all times
- ✅ Simpler logic

**Cons:**
- ❌ Loses data from longer channels
- ❌ May discard valuable information

#### Strategy C: Time-Based Alignment (Advanced)

If HDF5 files have absolute timestamps:

```python
def align_by_timestamp(channels_data):
    """
    Align channels based on absolute timestamps.
    
    Handles:
    - Different start times
    - Different end times
    - Gaps in data
    """
    # Find common time window
    start_time = max(ch.start_timestamp for ch in channels_data)
    end_time = min(ch.end_timestamp for ch in channels_data)
    
    # Resample each channel to common time grid
    common_time = np.arange(start_time, end_time, 1/target_fs)
    
    aligned_signals = []
    for ch in channels_data:
        # Interpolate to common time grid
        signal_aligned = np.interp(
            common_time, 
            ch.time_absolute, 
            ch.signal,
            left=0, right=0  # Fill with zeros outside range
        )
        aligned_signals.append(signal_aligned)
    
    return np.column_stack(aligned_signals), common_time
```

### Recommended Approach

**For SpectralEdge:**

1. **Default:** Zero-padding (Strategy A)
2. **User Option:** Truncate to common region
3. **Future:** Time-based alignment if timestamps available

---

## Part 3: Impact on PSD Calculations

### Critical Principle: Calculate PSD on Original Data

**The Golden Rule:**
> **PSD calculations MUST be performed on the original, unmodified data at the original sample rate.**

### Implementation Strategy

```python
class ChannelData:
    """
    Enhanced channel data structure to support harmonization.
    """
    def __init__(self, signal, sample_rate, time_vector, name, units):
        # Original data (NEVER modified)
        self.signal_original = signal
        self.sample_rate_original = sample_rate
        self.time_original = time_vector
        
        # Harmonized data (for visualization only)
        self.signal_harmonized = None
        self.sample_rate_harmonized = None
        self.time_harmonized = None
        
        # Metadata
        self.name = name
        self.units = units
        
        # PSD results (calculated from original data)
        self.psd_freq = None
        self.psd_values = None
    
    def calculate_psd(self, method='welch', **kwargs):
        """
        Calculate PSD using ORIGINAL data.
        """
        if method == 'welch':
            self.psd_freq, self.psd_values = calculate_psd_welch(
                self.signal_original,      # ← Original!
                self.sample_rate_original,  # ← Original!
                **kwargs
            )
        elif method == 'maximax':
            self.psd_freq, self.psd_values = calculate_psd_maximax(
                self.signal_original,
                self.sample_rate_original,
                **kwargs
            )
        
        return self.psd_freq, self.psd_values
    
    def harmonize(self, target_sample_rate, target_length):
        """
        Create harmonized version for visualization.
        Does NOT affect PSD calculation.
        """
        # Upsample via FFT zero-padding
        self.signal_harmonized, self.time_harmonized = upsample_via_fft_zeropad(
            self.signal_original,
            self.sample_rate_original,
            target_sample_rate
        )
        self.sample_rate_harmonized = target_sample_rate
        
        # Align length
        if len(self.signal_harmonized) < target_length:
            # Zero-pad
            pad_length = target_length - len(self.signal_harmonized)
            self.signal_harmonized = np.pad(
                self.signal_harmonized, 
                (0, pad_length), 
                mode='constant'
            )
            # Extend time vector
            dt = 1 / target_sample_rate
            time_extension = np.arange(
                self.time_harmonized[-1] + dt,
                self.time_harmonized[-1] + dt * (pad_length + 1),
                dt
            )[:pad_length]
            self.time_harmonized = np.concatenate([
                self.time_harmonized, 
                time_extension
            ])
        elif len(self.signal_harmonized) > target_length:
            # Truncate
            self.signal_harmonized = self.signal_harmonized[:target_length]
            self.time_harmonized = self.time_harmonized[:target_length]
```

### Modified Workflow in PSD Window

```python
def _on_hdf5_data_selected(self, selected_items):
    """
    Enhanced version with harmonization support.
    """
    # Step 1: Load all channels with original data
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
            units=channel_info.units
        )
        
        channels.append(channel)
        sample_rates.append(result['sample_rate'])
    
    # Step 2: Check if harmonization needed
    if len(set(sample_rates)) > 1:
        # Different sample rates detected
        print("Multiple sample rates detected - harmonization required")
        
        # Determine target sample rate (next power of 2)
        target_fs = get_target_sample_rate(sample_rates)
        print(f"Target sample rate: {target_fs} Hz")
        
        # Determine target length
        max_length_at_target = max(
            int(len(ch.signal_original) * target_fs / ch.sample_rate_original)
            for ch in channels
        )
        
        # Harmonize all channels
        for ch in channels:
            ch.harmonize(target_fs, max_length_at_target)
        
        # Use harmonized data for display
        self.signal_data_display = np.column_stack([
            ch.signal_harmonized for ch in channels
        ])
        self.time_data_display = channels[0].time_harmonized
        self.sample_rate = target_fs
        
        # Show harmonization info
        self.info_label.setText(
            f"Harmonized to {target_fs:.0f} Hz | "
            f"Duration: {self.time_data_display[-1]:.2f} s | "
            f"Channels: {len(channels)} (mixed rates)"
        )
    else:
        # Same sample rate - check lengths
        lengths = [len(ch.signal_original) for ch in channels]
        
        if len(set(lengths)) > 1:
            # Different lengths - align
            print("Different lengths detected - alignment required")
            
            target_length = max(lengths)
            for ch in channels:
                ch.harmonize(ch.sample_rate_original, target_length)
            
            self.signal_data_display = np.column_stack([
                ch.signal_harmonized for ch in channels
            ])
        else:
            # Same rate, same length - no harmonization needed
            self.signal_data_display = np.column_stack([
                ch.signal_original for ch in channels
            ])
        
        self.time_data_display = channels[0].time_original
        self.sample_rate = channels[0].sample_rate_original
    
    # Step 3: Store channels for PSD calculation
    self.channels = channels  # ← Store ChannelData objects
    
    # Step 4: Calculate PSDs on ORIGINAL data
    for ch in self.channels:
        ch.calculate_psd(method='welch', **self.get_psd_params())
```

### PSD Calculation Function (Modified)

```python
def _calculate_psd(self):
    """
    Calculate PSD for all channels using ORIGINAL data.
    """
    self.psd_results = {}
    self.rms_values = {}
    
    for i, channel in enumerate(self.channels):
        # PSD already calculated on original data
        freq = channel.psd_freq
        psd = channel.psd_values
        
        # Calculate RMS
        rms = calculate_rms_from_psd(freq, psd)
        
        # Store results
        self.psd_results[channel.name] = {
            'frequency': freq,
            'psd': psd,
            'sample_rate': channel.sample_rate_original  # ← Original!
        }
        self.rms_values[channel.name] = rms
    
    # For plotting, interpolate all PSDs to common frequency axis
    self._harmonize_psd_frequency_axes()
```

### PSD Frequency Axis Harmonization

```python
def _harmonize_psd_frequency_axes(self):
    """
    Interpolate all PSD curves to common frequency axis for plotting.
    This is safe because PSD is a smooth function.
    """
    # Find common frequency range
    max_freq = min(
        ch.psd_freq[-1] for ch in self.channels
    )  # Limited by lowest Nyquist
    
    # Create common frequency axis (logarithmic spacing for better resolution)
    self.freq_common = np.logspace(
        np.log10(self.channels[0].psd_freq[1]),  # Skip DC
        np.log10(max_freq),
        num=1000
    )
    
    # Interpolate each PSD to common axis
    self.psd_common = {}
    for ch in self.channels:
        psd_interp = np.interp(
            self.freq_common,
            ch.psd_freq,
            ch.psd_values,
            left=np.nan,
            right=np.nan
        )
        self.psd_common[ch.name] = psd_interp
```

---

## Part 4: Implementation Plan

### Phase 1: Core Harmonization Functions (New Module)

**File:** `spectral_edge/core/harmonization.py`

**Functions to implement:**
1. `upsample_via_fft_zeropad()` - FFT-based upsampling
2. `get_target_sample_rate()` - Next power-of-2 calculation
3. `align_time_lengths()` - Zero-padding or truncation
4. `harmonize_channel_data()` - Main orchestration function

**Estimated effort:** 4-6 hours

### Phase 2: Enhanced Data Structure

**File:** `spectral_edge/utils/channel_data.py`

**New class:**
- `ChannelData` - Stores original + harmonized data

**Estimated effort:** 2-3 hours

### Phase 3: Modify PSD Window

**File:** `spectral_edge/gui/psd_window.py`

**Changes:**
1. Modify `_on_hdf5_data_selected()` to use `ChannelData`
2. Add harmonization logic
3. Ensure PSD calculated on original data
4. Add harmonization info to UI
5. Implement `_harmonize_psd_frequency_axes()`

**Estimated effort:** 6-8 hours

### Phase 4: Modify Spectrogram Window

**File:** `spectral_edge/gui/spectrogram_window.py`

**Changes:**
1. Accept harmonized data for display
2. Update to handle `ChannelData` objects

**Estimated effort:** 2-3 hours

### Phase 5: Testing & Validation

**Test cases:**
1. Same rate, same length (no harmonization)
2. Different rates, same length
3. Same rate, different lengths
4. Different rates, different lengths
5. Verify PSD accuracy (compare to single-channel)
6. Verify visual alignment in time plots

**Estimated effort:** 4-5 hours

### Phase 6: Documentation

**Updates needed:**
1. User guide section on multi-rate channels
2. Technical documentation on harmonization
3. Code comments and docstrings

**Estimated effort:** 2-3 hours

---

## Part 5: User Interface Considerations

### Information Display

Add to info label when harmonization occurs:

```
Harmonized to 32,768 Hz | Duration: 120.5 s | Channels: 3 (mixed: 10k, 20k, 25k Hz)
```

### Visual Indicators

**Time History Plot:**
- Dashed vertical lines at boundaries where channels have different valid regions
- Tooltip showing which channels have valid data at cursor position

**PSD Plot:**
- Legend shows original sample rate for each channel
- Example: "Channel_1 (10 kHz)" vs "Channel_2 (20 kHz)"

### User Options (Future)

**Settings dialog:**
- [ ] Enable/disable harmonization
- [ ] Choose alignment method (zero-pad vs truncate)
- [ ] Set target sample rate manually (override power-of-2)

---

## Part 6: Validation & Testing Strategy

### Validation Tests

**Test 1: Verify FFT Zero-Padding Preserves Spectrum**
```python
def test_fft_upsample_preserves_spectrum():
    # Create test signal with known frequencies
    fs_original = 1000  # Hz
    t = np.arange(0, 1, 1/fs_original)
    signal = np.sin(2*np.pi*50*t) + 0.5*np.sin(2*np.pi*120*t)
    
    # Upsample to 2048 Hz
    signal_up, t_up = upsample_via_fft_zeropad(signal, fs_original, 2048)
    
    # Calculate PSDs
    f1, psd1 = calculate_psd_welch(signal, fs_original)
    f2, psd2 = calculate_psd_welch(signal_up, 2048)
    
    # Interpolate psd2 to f1 for comparison
    psd2_interp = np.interp(f1, f2, psd2)
    
    # Check that PSDs match within tolerance
    np.testing.assert_allclose(psd1, psd2_interp, rtol=0.01)
```

**Test 2: Verify PSD Independence**
```python
def test_psd_independent_of_harmonization():
    # Load same channel twice
    ch1 = load_channel("flight_001", "accel_01")
    ch2 = load_channel("flight_001", "accel_01")
    
    # Harmonize ch2 to different rate
    ch2_harmonized = upsample_via_fft_zeropad(
        ch2.signal, ch2.sample_rate, 32768
    )
    
    # Calculate PSDs
    f1, psd1 = calculate_psd_welch(ch1.signal, ch1.sample_rate)
    f2, psd2 = calculate_psd_welch(ch2_harmonized, 32768)
    
    # Interpolate and compare
    psd2_interp = np.interp(f1, f2, psd2)
    np.testing.assert_allclose(psd1, psd2_interp, rtol=0.01)
```

**Test 3: Verify Time Alignment**
```python
def test_time_alignment_zero_padding():
    # Create signals of different lengths
    signal1 = np.random.randn(1000)
    signal2 = np.random.randn(1500)
    
    # Align
    aligned, time = align_time_lengths(
        [signal1, signal2],
        [np.arange(1000)/1000, np.arange(1500)/1000],
        method='zero_pad'
    )
    
    # Check shape
    assert aligned.shape == (1500, 2)
    
    # Check that signal1 has zeros at end
    assert np.all(aligned[1000:, 0] == 0)
    
    # Check that signal2 is unchanged
    np.testing.assert_array_equal(aligned[:, 1], signal2)
```

---

## Part 7: Potential Issues & Mitigations

### Issue 1: Memory Usage

**Problem:** Upsampling increases data size

**Example:**
- Original: 100,000 samples @ 10 kHz = 0.8 MB
- Upsampled: 327,680 samples @ 32,768 Hz = 2.6 MB
- 3 channels: 7.8 MB vs 2.4 MB (3.25x increase)

**Mitigation:**
1. Only harmonize for display (decimated version)
2. Keep original data for PSD calculation
3. Add memory usage warning for large datasets
4. Implement lazy harmonization (on-demand)

### Issue 2: Computation Time

**Problem:** FFT upsampling takes time

**Mitigation:**
1. Show progress bar for large datasets
2. Cache harmonized results
3. Parallelize harmonization across channels
4. Use efficient FFT (power-of-2 lengths)

### Issue 3: User Confusion

**Problem:** Users may not understand why data looks different

**Mitigation:**
1. Clear UI indicators when harmonization is active
2. Tooltip explanations
3. Documentation with examples
4. Option to view original data

### Issue 4: Edge Cases

**Problem:** Very different sample rates (e.g., 100 Hz vs 100 kHz)

**Mitigation:**
1. Warn user if upsampling ratio > 10x
2. Suggest analyzing channels separately
3. Implement maximum target sample rate limit

---

## Part 8: Alternative Approaches (Not Recommended)

### Alternative 1: Decimation (Downsampling)

**Approach:** Downsample higher-rate channels to match lowest rate

**Pros:**
- Reduces data size
- Simpler than upsampling

**Cons:**
- ❌ Loses high-frequency information
- ❌ Irreversible
- ❌ Violates your requirement
- ❌ Degrades PSD accuracy for high-rate channels

**Verdict:** ❌ Not recommended

### Alternative 2: Interpolation in Time Domain

**Approach:** Use scipy.interpolate to resample

**Pros:**
- Conceptually simple
- Well-established methods

**Cons:**
- ⚠️ Introduces interpolation artifacts
- ⚠️ Not as clean as FFT zero-padding
- ⚠️ Slower for large datasets

**Verdict:** ⚠️ Acceptable but FFT zero-padding is better

### Alternative 3: Analyze Separately, Plot Together

**Approach:** Don't harmonize; just plot PSDs on common axis

**Pros:**
- ✅ No resampling needed
- ✅ Maximum accuracy

**Cons:**
- ❌ Can't create time history plots with multiple channels
- ❌ Can't create spectrograms with multiple channels
- ❌ Limited comparison capability

**Verdict:** ⚠️ Good for PSD-only analysis, but limits functionality

---

## Recommendation

### Recommended Implementation

**Hybrid Approach:**

1. **For PSD Analysis:**
   - Calculate on original data (no harmonization)
   - Interpolate frequency axes for plotting only

2. **For Time History & Spectrograms:**
   - Harmonize via FFT zero-padding
   - Align lengths via zero-padding
   - Clear UI indicators

3. **User Control:**
   - Default: Automatic harmonization
   - Option: Analyze channels separately
   - Warning: If harmonization ratio > 10x

### Implementation Priority

**High Priority (Implement First):**
1. FFT zero-padding upsampling
2. Next power-of-2 target rate
3. Zero-padding for length alignment
4. PSD calculation on original data

**Medium Priority (Implement Second):**
5. PSD frequency axis harmonization
6. UI indicators for harmonization
7. Validation tests

**Low Priority (Future Enhancement):**
8. Time-based alignment (if timestamps available)
9. User options for alignment method
10. Advanced memory optimization

---

## Summary

### Key Takeaways

1. **Sample Rate Harmonization:** FFT zero-padding to next power-of-2 ✅
2. **Length Alignment:** Zero-padding (default) or truncation ✅
3. **PSD Integrity:** Always calculate on original data ✅
4. **Visualization:** Use harmonized data for time plots only ✅
5. **Implementation:** Phased approach with validation ✅

### No Impact on PSD Calculations

**Guaranteed by:**
- Separate storage of original vs harmonized data
- PSD functions only access original data
- Harmonization used exclusively for visualization
- Frequency axis interpolation is safe (smooth function)

### Estimated Total Effort

- **Core implementation:** 20-25 hours
- **Testing & validation:** 5-6 hours
- **Documentation:** 2-3 hours
- **Total:** 27-34 hours (~4-5 days)

---

## Questions for User

Before implementation, please confirm:

1. ✅ **FFT zero-padding approach** - Is this the method you want?
2. ✅ **Next power-of-2 target rate** - Confirmed?
3. ❓ **Length alignment** - Prefer zero-padding or truncation as default?
4. ❓ **UI indicators** - What level of detail do you want shown?
5. ❓ **Maximum upsampling ratio** - Should we warn/limit if ratio > X?
6. ❓ **Timestamps** - Do your HDF5 files have absolute timestamps we can use?

---

**End of Proposal**
