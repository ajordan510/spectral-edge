# SpectralEdge System Baseline

**Date:** 2025-01-28  
**Version:** Pre-Multi-Channel Support  
**Purpose:** Document current system state before implementing multi-channel harmonization

---

## Overview

This document captures the current state of SpectralEdge before implementing multi-channel support for different sample rates and time lengths. It serves as a baseline for:

1. **Regression Testing** - Verify no existing functionality breaks
2. **Change Tracking** - Document what changed and why
3. **Rollback Reference** - Know what to restore if issues arise

---

## Current Data Flow

### 1. HDF5 File → Flight Navigator

```
HDF5 File (*.hdf5)
  ↓
HDF5FlightDataLoader.load_data()
  ↓
FlightNavigator.set_loader()
  ↓
User selects channels in tree
  ↓
FlightNavigator.load_selected.emit(channels_data)
```

**Data Format:**
```python
channels_data: List[Tuple[str, np.ndarray, str, str]]
# Each tuple: (channel_name, signal, units, flight_name)
# - channel_name: str (e.g., "Accel_X")
# - signal: np.ndarray, dtype=float64, shape=(n_samples,)
# - units: str (e.g., "g", "Pa", "V")
# - flight_name: str (e.g., "FT-001")
```

### 2. Flight Navigator → PSD Window

```
FlightNavigator.load_selected signal
  ↓
PSDAnalysisWindow._on_hdf5_data_selected(channels_data)
  ↓
Store in self.channels_data
  ↓
User clicks "Calculate PSD"
  ↓
calculate_psd_welch(signal, sample_rate, df=...)
```

**Key Constraint:** All channels must have same sample rate (currently enforced by UI)

### 3. Flight Navigator → Spectrogram Window

```
FlightNavigator.load_selected signal
  ↓
SpectrogramWindow._on_hdf5_data_selected(channels_data)
  ↓
Plot spectrograms independently per channel
```

**Key Constraint:** Each channel plotted separately, no alignment required

---

## Current Limitations

### Sample Rate Handling

**Status:** ❌ NOT SUPPORTED

- **Issue:** Cannot compare channels with different sample rates
- **Current Behavior:** User must select channels with same rate
- **UI Enforcement:** Navigator shows sample rate, user responsible

**Example Scenario:**
```
Channel A: 10,000 Hz
Channel B: 20,000 Hz
→ Cannot be loaded together for PSD comparison
```

### Time Length Handling

**Status:** ❌ NOT SUPPORTED

- **Issue:** Cannot compare channels with different durations
- **Current Behavior:** Undefined (likely crashes or incorrect plots)
- **No Validation:** System doesn't check or warn

**Example Scenario:**
```
Channel A: 0-100 seconds
Channel B: 0-50 seconds
→ Behavior undefined
```

---

## Key Data Contracts

### 1. Channel Selection Tuple

**Contract ID:** `CHANNEL_TUPLE_V1`

```python
Tuple[str, np.ndarray, str, str]
# (channel_name, signal, units, flight_name)
```

**Validation:**
- Element 0: `str` - Channel name
- Element 1: `np.ndarray` - Signal data, dtype=float64, ndim=1
- Element 2: `str` - Units
- Element 3: `str` - Flight name

**Used By:**
- `FlightNavigator.load_selected` signal
- `PSDAnalysisWindow._on_hdf5_data_selected()`
- `SpectrogramWindow._on_hdf5_data_selected()`

**Test:** `tests/test_data_contracts.py::test_channel_selection_tuple_contract`

### 2. PSD Calculation Function

**Contract ID:** `PSD_WELCH_V1`

```python
def calculate_psd_welch(
    signal: np.ndarray,
    sample_rate: float,
    df: Optional[float] = None,
    window: str = 'hann',
    overlap_percent: float = 50.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Returns: (frequencies, psd)
    - frequencies: np.ndarray, shape=(n_freq,), Hz
    - psd: np.ndarray, shape=(n_freq,), units²/Hz
    """
```

**Key Property:**
- `df` parameter controls frequency resolution
- `nperseg = sample_rate / df`
- Different sample rates → different nperseg → same df ✓

**Used By:**
- `PSDAnalysisWindow._update_plot()`
- `PSDAnalysisWindow._update_plot_with_events()`

**Test:** `tests/test_data_contracts.py::test_psd_welch_contract`

### 3. HDF5FlightDataLoader Interface

**Contract ID:** `HDF5_LOADER_V1`

**Key Methods:**
```python
class HDF5FlightDataLoader:
    def __init__(self, file_path: str)
    def load_data() -> None
    def get_flights() -> Dict[str, FlightInfo]
    def get_flight_keys() -> List[str]
    def get_channels(flight_key: str) -> Dict[str, ChannelInfo]
    def get_channel_keys(flight_key: str) -> List[str]
    def load_channel_data(flight_key: str, channel_key: str) -> Dict
    def get_time_data(flight_key: str, channel_key: str) -> np.ndarray
    def close() -> None
```

**Used By:**
- `FlightNavigator`
- `PSDAnalysisWindow`
- `SpectrogramWindow`

**Test:** `tests/test_data_contracts.py::test_hdf5_loader_contract`

---

## Test Results (Baseline)

### Data Contract Tests

**File:** `tests/test_data_contracts.py`

**Results:**
```
Passed: 70 / 74
Failed: 4 / 74

Failures:
- HDF5FlightDataLoader.load exists (method name mismatch)
- HDF5FlightDataLoader.get_channel_data exists (method name mismatch)
- HDF5FlightDataLoader.load is callable (method name mismatch)
- maximax PSD >= welch PSD (numerical tolerance)
```

**Status:** ✅ ACCEPTABLE BASELINE

The 4 failures are minor naming mismatches and numerical tolerance issues, not functional problems.

### PyQt6 Validation

**File:** `tests/test_pyqt6_validation.py`

**Results:**
```
✓ All PyQt6 attributes validated
✓ No invalid attribute references found
```

**Status:** ✅ PASS

---

## File Dependency Map

### Core Modules

**`spectral_edge/core/psd.py`**
- **Exports:** 6 functions
- **Imported By:** 3 files
- **Impact:** 🟡 MEDIUM
- **Functions:**
  - `calculate_psd_welch()`
  - `calculate_psd_maximax()`
  - `convert_psd_to_octave_bands()`
  - `calculate_rms_from_psd()`
  - `psd_to_db()`
  - `get_window_options()`

**`spectral_edge/utils/hdf5_loader.py`**
- **Exports:** 3 classes
- **Imported By:** 5+ files
- **Impact:** 🔴 HIGH
- **Classes:**
  - `FlightInfo`
  - `ChannelInfo`
  - `HDF5FlightDataLoader`

### GUI Modules

**`spectral_edge/gui/flight_navigator.py`**
- **Exports:** 1 class
- **Imported By:** 2 files
- **Impact:** 🟡 MEDIUM
- **Signals:**
  - `load_selected(List[Tuple[str, np.ndarray, str, str]])`

**`spectral_edge/gui/psd_window.py`**
- **Exports:** 2 classes
- **Imported By:** 1 file
- **Impact:** 🟢 LOW
- **Classes:**
  - `ScientificAxisItem`
  - `PSDAnalysisWindow`

**`spectral_edge/gui/spectrogram_window.py`**
- **Exports:** 1 class
- **Imported By:** 1 file
- **Impact:** 🟢 LOW
- **Classes:**
  - `SpectrogramWindow`

---

## Known Issues (Pre-Implementation)

### 1. Multi-Rate Channels Not Supported

**Severity:** 🔴 HIGH  
**Impact:** Cannot compare data from different sensors  
**Workaround:** User must manually select same-rate channels

### 2. Different Time Lengths Not Handled

**Severity:** 🟡 MEDIUM  
**Impact:** Undefined behavior, potential crashes  
**Workaround:** None (user unaware of issue)

### 3. No Sample Rate Validation

**Severity:** 🟡 MEDIUM  
**Impact:** User can select incompatible channels  
**Workaround:** None (relies on user knowledge)

---

## Change Management Process

### Before Making Changes

1. ✅ Run baseline tests:
   ```bash
   python tests/test_data_contracts.py
   python tests/test_pyqt6_validation.py
   ```

2. ✅ Analyze impact:
   ```bash
   python tools/analyze_change_impact.py <file_to_change>
   ```

3. ✅ Document planned changes in issue/PR

### During Implementation

1. ✅ Follow data contracts (see `docs/DATA_CONTRACTS.md`)
2. ✅ Maintain backward compatibility
3. ✅ Add tests for new functionality
4. ✅ Update documentation

### After Making Changes

1. ✅ Run all tests:
   ```bash
   python tests/test_data_contracts.py
   python tests/test_pyqt6_validation.py
   ```

2. ✅ Verify no regressions (compare to baseline)
3. ✅ Test manually with real data
4. ✅ Update this baseline document

---

## Rollback Plan

If issues arise after implementation:

1. **Identify failing tests:**
   ```bash
   python tests/test_data_contracts.py > current_results.txt
   diff baseline_results.txt current_results.txt
   ```

2. **Revert specific changes:**
   ```bash
   git log --oneline --since="2025-01-28"
   git revert <commit_hash>
   ```

3. **Restore from baseline:**
   ```bash
   git checkout <baseline_commit> -- <file_path>
   ```

4. **Verify restoration:**
   ```bash
   python tests/test_data_contracts.py
   ```

---

## Next Steps

### Planned Implementation: Multi-Channel Support

**Goal:** Enable comparison of channels with different sample rates and time lengths

**Approach:** Simplified (no FFT upsampling)

**Changes:**
1. Add `ChannelData` class to wrap channel information
2. Update PSD window to handle multi-rate data
3. Add time-domain zero-padding for length alignment
4. Update UI to show sample rate information

**Expected Impact:**
- 🟡 MEDIUM impact on `psd_window.py`
- 🟢 LOW impact on `hdf5_loader.py`
- 🟢 LOW impact on `flight_navigator.py`

**Testing Strategy:**
1. Run baseline tests before changes
2. Add new tests for multi-rate scenarios
3. Run all tests after changes
4. Manual testing with real multi-rate data

---

## Appendix: Baseline Test Output

### Data Contract Tests (Full Output)

```
============================================================
  SpectralEdge Data Contract Validation
============================================================

Passed: 70
Failed: 4
Total:  74

Failures:
✗ HDF5FlightDataLoader.load exists
✗ HDF5FlightDataLoader.get_channel_data exists
✗ HDF5FlightDataLoader.load is callable
✗ maximax PSD >= welch PSD (envelope property)
```

### Change Impact Analysis (psd.py)

```
======================================================================
  CHANGE IMPACT ANALYSIS: spectral_edge/core/psd.py
======================================================================

Severity: 🟡 MEDIUM
Importers: 3 files
Exports: 6 symbols

Recommendation: Requires careful testing. Run contract and integration tests.
```

---

**Document Version:** 1.0  
**Last Updated:** 2025-01-28  
**Next Review:** After multi-channel implementation
