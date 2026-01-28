# SpectralEdge Data Contracts
## Version 1.0 - Baseline Documentation

**Purpose:** This document defines all data structures, types, and interfaces used throughout SpectralEdge. Any changes to these contracts MUST be validated against all dependent code before deployment.

**Last Updated:** January 28, 2026  
**Baseline Commit:** TBD

---

## Table of Contents

1. [Core Data Structures](#core-data-structures)
2. [HDF5 Data Loader Contracts](#hdf5-data-loader-contracts)
3. [GUI Interface Contracts](#gui-interface-contracts)
4. [PSD Calculation Contracts](#psd-calculation-contracts)
5. [Event System Contracts](#event-system-contracts)
6. [Change Log](#change-log)

---

## Core Data Structures

### 1. FlightInfo

**Module:** `spectral_edge.utils.hdf5_loader`

**Definition:**
```python
@dataclass
class FlightInfo:
    flight_id: str          # Unique flight identifier (e.g., "FT-001")
    date: str               # ISO format date string (e.g., "2024-01-15")
    duration: float         # Flight duration in seconds
    description: str        # Human-readable description
    vehicle: str            # Vehicle identifier
    test_type: str          # Test type (e.g., "Vibration", "Acoustic")
```

**Used By:**
- `HDF5FlightDataLoader.get_flights()` → Returns `Dict[str, FlightInfo]`
- `HDF5FlightDataLoader.get_flight_info(flight_key)` → Returns `FlightInfo`
- `FlightNavigator._load_all_channels()` → Reads flight metadata

**Validation Rules:**
- `flight_id`: Non-empty string, unique within HDF5 file
- `date`: Valid ISO date string or empty
- `duration`: Positive float
- `description`, `vehicle`, `test_type`: Any string (can be empty)

**Breaking Change Impact:** HIGH
- Changes affect: Flight Navigator, PSD Window, Spectrogram Window
- Migration required if fields added/removed/renamed

---

### 2. ChannelInfo

**Module:** `spectral_edge.utils.hdf5_loader`

**Definition:**
```python
@dataclass
class ChannelInfo:
    name: str               # Channel name (e.g., "Accel_X_Wing_Tip")
    sample_rate: float      # Sample rate in Hz
    units: str              # Physical units (e.g., "g", "Pa", "με")
    description: str        # Human-readable description
    sensor_id: str          # Sensor identifier
    location: str           # Physical location (e.g., "Wing Tip", "Fuselage Station 10")
    range_min: float        # Sensor range minimum
    range_max: float        # Sensor range maximum
```

**Used By:**
- `HDF5FlightDataLoader.get_channels(flight_key)` → Returns `Dict[str, ChannelInfo]`
- `HDF5FlightDataLoader.get_channel_info(flight_key, channel_key)` → Returns `ChannelInfo`
- `FlightNavigator._load_all_channels()` → Reads channel metadata
- `PSDWindow._on_hdf5_data_selected()` → Reads channel info for display

**Validation Rules:**
- `name`: Non-empty string, unique within flight
- `sample_rate`: Positive float
- `units`: Non-empty string
- `description`, `sensor_id`, `location`: Any string (can be empty)
- `range_min`, `range_max`: Floats, range_max >= range_min

**Breaking Change Impact:** HIGH
- Changes affect: Flight Navigator, PSD Window, Spectrogram Window, Event Manager
- Migration required if fields added/removed/renamed

---

### 3. Channel Selection Tuple (Legacy)

**Module:** Multiple (PSD Window, Spectrogram Window)

**Definition:**
```python
# 4-tuple format (current)
(channel_name: str, signal: np.ndarray, units: str, flight_name: str)

# Historical formats:
# 3-tuple (deprecated): (channel_name, signal, units)
```

**Used By:**
- `PSDWindow._on_hdf5_data_selected(selected_items)` → Receives list of 4-tuples
- `SpectrogramWindow._on_hdf5_data_selected(selected_items)` → Receives list of 4-tuples
- `FlightNavigator.load_selected.emit(selected_items)` → Emits list of 4-tuples

**Validation Rules:**
- Element 0 (channel_name): Non-empty string
- Element 1 (signal): numpy.ndarray, dtype float64, 1D
- Element 2 (units): Non-empty string
- Element 3 (flight_name): Non-empty string

**Breaking Change Impact:** CRITICAL
- This is the primary interface between Flight Navigator and analysis windows
- Changes require coordinated updates across all GUI modules
- **MUST maintain backward compatibility or provide migration path**

**Migration Strategy:**
- If adding elements: Append to end, make optional with defaults
- If removing elements: Deprecate first, then remove in next major version
- If changing order: Create new interface, maintain old for 1 version

---

## HDF5 Data Loader Contracts

### HDF5FlightDataLoader Class

**Module:** `spectral_edge.utils.hdf5_loader`

**Public Methods:**

#### `__init__(file_path: str)`
- **Input:** `file_path` (str) - Path to HDF5 file
- **Output:** None
- **Side Effects:** Opens HDF5 file handle
- **Exceptions:** `FileNotFoundError`, `OSError`

#### `load() -> None`
- **Input:** None
- **Output:** None
- **Side Effects:** Loads flight and channel metadata into memory
- **Exceptions:** `ValueError` if HDF5 structure invalid

#### `get_flights() -> Dict[str, FlightInfo]`
- **Input:** None
- **Output:** Dictionary mapping flight keys to FlightInfo objects
- **Side Effects:** None
- **Exceptions:** None
- **Contract:** Returns empty dict if no flights, never returns None

#### `get_flight_keys() -> List[str]`
- **Input:** None
- **Output:** List of flight key strings
- **Side Effects:** None
- **Exceptions:** None
- **Contract:** Returns empty list if no flights, never returns None

#### `get_flight_info(flight_key: str) -> Optional[FlightInfo]`
- **Input:** `flight_key` (str) - Flight identifier
- **Output:** FlightInfo object or None if not found
- **Side Effects:** None
- **Exceptions:** None

#### `get_channels(flight_key: str) -> Dict[str, ChannelInfo]`
- **Input:** `flight_key` (str) - Flight identifier
- **Output:** Dictionary mapping channel keys to ChannelInfo objects
- **Side Effects:** None
- **Exceptions:** `KeyError` if flight_key invalid
- **Contract:** Returns empty dict if no channels, never returns None

#### `get_channel_keys(flight_key: str) -> List[str]`
- **Input:** `flight_key` (str) - Flight identifier
- **Output:** List of channel key strings
- **Side Effects:** None
- **Exceptions:** `KeyError` if flight_key invalid
- **Contract:** Returns empty list if no channels, never returns None

#### `get_channel_data(flight_key: str, channel_key: str, start_idx: int = 0, end_idx: Optional[int] = None) -> np.ndarray`
- **Input:** 
  - `flight_key` (str) - Flight identifier
  - `channel_key` (str) - Channel identifier
  - `start_idx` (int) - Start index (default 0)
  - `end_idx` (Optional[int]) - End index (default None = all data)
- **Output:** numpy.ndarray, dtype float64, 1D
- **Side Effects:** Reads from HDF5 file
- **Exceptions:** `KeyError` if flight_key or channel_key invalid
- **Contract:** Never returns None, always returns array (may be empty)

#### `get_time_data(flight_key: str, channel_key: str) -> np.ndarray`
- **Input:**
  - `flight_key` (str) - Flight identifier
  - `channel_key` (str) - Channel identifier
- **Output:** numpy.ndarray, dtype float64, 1D, time vector in seconds
- **Side Effects:** Reads from HDF5 file or calculates from sample rate
- **Exceptions:** `KeyError` if flight_key or channel_key invalid
- **Contract:** Never returns None, always returns array

#### `close() -> None`
- **Input:** None
- **Output:** None
- **Side Effects:** Closes HDF5 file handle
- **Exceptions:** None

**Breaking Change Impact:** CRITICAL
- All GUI modules depend on this interface
- Changes require updates to: Flight Navigator, PSD Window, Spectrogram Window, Event Manager

---

## GUI Interface Contracts

### FlightNavigator Signals

**Module:** `spectral_edge.gui.flight_navigator`

#### `load_selected` Signal

**Signature:**
```python
load_selected = pyqtSignal(list)  # List[Tuple[str, np.ndarray, str, str]]
```

**Emitted When:** User clicks "Load Selected" button

**Payload:**
```python
[
    (channel_name, signal_data, units, flight_name),  # Channel 1
    (channel_name, signal_data, units, flight_name),  # Channel 2
    ...
]
```

**Payload Contract:**
- Type: `List[Tuple[str, np.ndarray, str, str]]`
- Minimum length: 1 (at least one channel selected)
- Maximum length: 4 (up to 4 channels)
- Each tuple:
  - Element 0: Channel name (str, non-empty)
  - Element 1: Signal data (np.ndarray, float64, 1D, length > 0)
  - Element 2: Units (str, non-empty)
  - Element 3: Flight name (str, non-empty)

**Connected To:**
- `PSDWindow._on_hdf5_data_selected(selected_items)`
- `SpectrogramWindow._on_hdf5_data_selected(selected_items)`

**Breaking Change Impact:** CRITICAL
- This is the primary data flow from navigator to analysis windows
- Changes require coordinated updates across all receiving windows

---

### PSDWindow Interface

**Module:** `spectral_edge.gui.psd_window`

#### `_on_hdf5_data_selected(selected_items: List[Tuple])`

**Input Contract:**
```python
selected_items: List[Tuple[str, np.ndarray, str, str]]
# Each tuple: (channel_name, signal, units, flight_name)
```

**Expected Behavior:**
1. Validates input (checks types, lengths)
2. Stores channel data internally
3. Updates UI with channel info
4. Enables PSD calculation controls
5. Clears previous results

**Side Effects:**
- Updates `self.channels_data`
- Updates `self.channel_flight_names`
- Modifies UI elements
- Clears plots

**Exceptions:**
- Should handle gracefully with error dialogs
- Should not crash on invalid input

---

### SpectrogramWindow Interface

**Module:** `spectral_edge.gui.spectrogram_window`

#### `_on_hdf5_data_selected(selected_items: List[Tuple])`

**Input Contract:**
```python
selected_items: List[Tuple[str, np.ndarray, str, str]]
# Each tuple: (channel_name, signal, units, flight_name)
```

**Expected Behavior:**
1. Validates input (checks types, lengths)
2. Stores channel data internally
3. Updates UI with channel info
4. Calculates and displays spectrograms
5. Updates title with flight name

**Side Effects:**
- Updates `self.channels_data`
- Updates `self.channel_flight_names`
- Modifies UI elements
- Redraws spectrograms

**Exceptions:**
- Should handle gracefully with error dialogs
- Should not crash on invalid input

---

## PSD Calculation Contracts

### calculate_psd_welch Function

**Module:** `spectral_edge.core.psd`

**Signature:**
```python
def calculate_psd_welch(
    time_data: np.ndarray,
    sample_rate: float,
    df: Optional[float] = None,
    nperseg: Optional[int] = None,
    noverlap: Optional[int] = None,
    window: str = 'hann',
    use_efficient_fft: bool = True
) -> Tuple[np.ndarray, np.ndarray]:
```

**Input Contracts:**
- `time_data`: numpy.ndarray, dtype float64, 1D, length > 0
- `sample_rate`: float, > 0
- `df`: Optional[float], > 0, < sample_rate/2 (if provided)
- `nperseg`: Optional[int], > 0, <= len(time_data) (if provided)
- `noverlap`: Optional[int], >= 0, < nperseg (if provided)
- `window`: str, valid scipy window name
- `use_efficient_fft`: bool

**Output Contract:**
```python
(frequencies, psd)
# frequencies: np.ndarray, dtype float64, 1D, monotonically increasing, starts at 0
# psd: np.ndarray, dtype float64, 1D, same length as frequencies, all values >= 0
```

**Calculation Contract:**
- If `df` provided: `nperseg = sample_rate / df` (rounded to power of 2 if use_efficient_fft=True)
- If `noverlap` not provided: `noverlap = nperseg // 2` (50% overlap)
- Frequency resolution: `actual_df = sample_rate / nperseg`
- Nyquist frequency: `max(frequencies) ≈ sample_rate / 2`

**Invariants:**
- `len(frequencies) == len(psd)`
- `frequencies[0] == 0.0`
- `frequencies[-1] ≈ sample_rate / 2`
- `np.all(psd >= 0)`

**Breaking Change Impact:** HIGH
- Changes affect all PSD calculations in PSD Window
- Must maintain backward compatibility for existing analysis workflows

---

### calculate_psd_maximax Function

**Module:** `spectral_edge.core.psd`

**Signature:**
```python
def calculate_psd_maximax(
    time_data: np.ndarray,
    sample_rate: float,
    df: Optional[float] = None,
    segment_duration: float = 1.0,
    overlap_percent: float = 50.0,
    window: str = 'hann',
    use_efficient_fft: bool = True
) -> Tuple[np.ndarray, np.ndarray]:
```

**Input Contracts:**
- `time_data`: numpy.ndarray, dtype float64, 1D, length > 0
- `sample_rate`: float, > 0
- `df`: Optional[float], > 0, < sample_rate/2 (if provided)
- `segment_duration`: float, > 0, <= len(time_data)/sample_rate
- `overlap_percent`: float, >= 0, < 100
- `window`: str, valid scipy window name
- `use_efficient_fft`: bool

**Output Contract:**
```python
(frequencies, psd_maximax)
# frequencies: np.ndarray, dtype float64, 1D, monotonically increasing, starts at 0
# psd_maximax: np.ndarray, dtype float64, 1D, same length as frequencies, all values >= 0
```

**Calculation Contract:**
- Per SMC-S-016: "Spectra for each of a series of 1-second times, overlapped by 50%, are enveloped"
- Default segment_duration = 1.0 second
- Default overlap_percent = 50%
- Envelope method: Maximum across all segments at each frequency

**Invariants:**
- `len(frequencies) == len(psd_maximax)`
- `frequencies[0] == 0.0`
- `psd_maximax >= psd_welch` (envelope is always >= individual spectra)
- `np.all(psd_maximax >= 0)`

**Breaking Change Impact:** HIGH
- Changes affect maximax PSD calculations in PSD Window
- Must maintain SMC-S-016 compliance

---

## Event System Contracts

### Event Data Structure

**Module:** `spectral_edge.gui.event_manager`

**Definition:**
```python
{
    'name': str,           # Event name (e.g., "Takeoff", "Landing")
    'start_time': float,   # Start time in seconds
    'end_time': float,     # End time in seconds
    'color': str          # Qt color name (e.g., "red", "#FF0000")
}
```

**Used By:**
- `EventManagerWindow.get_events()` → Returns `List[Dict]`
- `PSDWindow._update_plot_with_events()` → Reads event list
- `PSDWindow._add_event_regions()` → Displays events on time plot

**Validation Rules:**
- `name`: Non-empty string
- `start_time`: float, >= 0
- `end_time`: float, > start_time
- `color`: Valid Qt color string

**Breaking Change Impact:** MEDIUM
- Changes affect PSD Window event display
- Changes affect Event Manager window

---

## Change Log

### Version 1.0 (Baseline) - January 28, 2026

**Initial documentation of existing contracts:**
- FlightInfo dataclass
- ChannelInfo dataclass
- Channel selection 4-tuple format
- HDF5FlightDataLoader interface
- FlightNavigator signals
- PSD calculation functions
- Event system data structure

**Known Issues:**
- Channel selection tuple format is not type-safe
- No formal validation of HDF5 file structure
- No versioning of data formats

**Planned Improvements:**
- Create ChannelData class to replace tuple format
- Add data validation layer
- Implement version checking for HDF5 files

---

## Appendix A: Dependency Graph

```
HDF5 File
    ↓
HDF5FlightDataLoader
    ↓
FlightNavigator
    ↓ (load_selected signal)
    ├→ PSDWindow
    │   ↓
    │   calculate_psd_welch / calculate_psd_maximax
    │   ↓
    │   EventManager (optional)
    │
    └→ SpectrogramWindow
```

**Critical Dependencies:**
1. FlightNavigator → PSDWindow: 4-tuple format
2. FlightNavigator → SpectrogramWindow: 4-tuple format
3. PSDWindow → PSD calculations: numpy array + sample_rate
4. All GUIs → HDF5FlightDataLoader: FlightInfo, ChannelInfo

**Change Impact Matrix:**

| Change To | Impacts |
|-----------|---------|
| FlightInfo | FlightNavigator, PSDWindow, SpectrogramWindow |
| ChannelInfo | FlightNavigator, PSDWindow, SpectrogramWindow |
| 4-tuple format | FlightNavigator, PSDWindow, SpectrogramWindow (CRITICAL) |
| HDF5FlightDataLoader methods | All GUIs |
| calculate_psd_welch signature | PSDWindow |
| Event data structure | PSDWindow, EventManager |

---

## Appendix B: Testing Requirements

**For Any Change to Data Contracts:**

1. **Unit Tests:**
   - Test new data structure creation
   - Test validation rules
   - Test edge cases

2. **Integration Tests:**
   - Test FlightNavigator → PSDWindow data flow
   - Test FlightNavigator → SpectrogramWindow data flow
   - Test HDF5FlightDataLoader → FlightNavigator data flow

3. **Regression Tests:**
   - Load existing HDF5 files
   - Verify all GUIs still work
   - Verify PSD calculations unchanged

4. **Manual Tests:**
   - Open application
   - Load HDF5 file
   - Select channels
   - Calculate PSD
   - View spectrogram
   - Manage events

**Test Data:**
- Small HDF5 file (1 flight, 5 channels)
- Large HDF5 file (10 flights, 150 channels)
- Edge cases: Empty flight, single sample, very long duration

---

**End of Data Contracts Document**
