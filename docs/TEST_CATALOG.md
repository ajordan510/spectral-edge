# SpectralEdge Test Catalog

This document catalogs all existing and proposed tests, explaining their value in ensuring **accuracy**, **robustness**, and **reliability**.

---

## Test Value Categories

| Category | Definition | Example |
|----------|------------|---------|
| **Accuracy** | Validates mathematical/algorithmic correctness | PSD peak at correct frequency |
| **Robustness** | Handles edge cases, errors, invalid inputs | Empty arrays, division by zero |
| **Reliability** | Consistent behavior across conditions | Same result on Windows/Linux |

---

## 1. Core Algorithm Tests (Unit Tests)

### 1.1 PSD Calculation Tests (`tests/test_psd.py`)

| Test | Status | Value Type | What It Ensures |
|------|--------|------------|-----------------|
| `test_psd_basic_calculation` | ✅ Exists | Accuracy | Output arrays have correct shape; frequencies are positive and increasing |
| `test_psd_peak_detection` | ✅ Exists | Accuracy | Pure 10 Hz sine wave produces peak at 10 Hz (±1 Hz tolerance) |
| `test_psd_multiple_peaks` | ✅ Exists | Accuracy | Multi-frequency signals (10 Hz + 50 Hz) show both peaks |
| `test_psd_window_types` | ✅ Exists | Reliability | All window types (hann, hamming, blackman, bartlett) produce valid results |
| `test_psd_multi_channel` | ✅ Exists | Reliability | 2D input arrays (multi-channel) handled correctly |
| `test_psd_to_db_conversion` | ✅ Exists | Accuracy | dB conversion formula (10×log10) is correct |
| `test_psd_to_db_with_zeros` | ✅ Exists | Robustness | Zero values don't produce infinity |
| `test_rms_calculation` | ✅ Exists | Accuracy | RMS from PSD matches theory (A/√2 for sine wave) within 5% |
| `test_rms_with_frequency_range` | ✅ Exists | Accuracy | RMS over specific frequency bands is correct |
| `test_window_options_function` | ✅ Exists | Reliability | API returns expected window options |
| `test_psd_input_validation` | ✅ Exists | Robustness | Empty arrays and invalid sample rates raise proper errors |

**Proposed Additions:**

| Test | Value Type | What It Would Ensure |
|------|------------|----------------------|
| `test_psd_parseval_theorem` | Accuracy | Total power in PSD equals time-domain variance |
| `test_psd_nyquist_limit` | Accuracy | PSD doesn't exceed Nyquist frequency (fs/2) |
| `test_psd_overlap_effect` | Accuracy | Different overlap values produce statistically valid results |
| `test_maximax_envelope_property` | Accuracy | Maximax PSD ≥ Welch PSD at ALL frequencies |
| `test_psd_very_short_signal` | Robustness | Graceful handling when signal < nperseg |
| `test_psd_very_long_signal` | Reliability | Memory-efficient handling of million-sample signals |
| `test_psd_nan_handling` | Robustness | NaN values in signal are detected/handled |
| `test_psd_dc_offset_removal` | Accuracy | DC component properly removed by detrending |

---

### 1.2 Cross-Spectrum Tests (`tests/test_gui_headless.py`)

| Test | Status | Value Type | What It Ensures |
|------|--------|------------|-----------------|
| `test_csd_with_correlated_signals` | ✅ Exists | Accuracy | CSD peaks at signal frequency for correlated signals |
| `test_coherence_identical_signals` | ✅ Exists | Accuracy | Coherence = 1.0 for identical signals |
| `test_coherence_uncorrelated_signals` | ✅ Exists | Accuracy | Coherence ≈ 0 for random noise |
| `test_transfer_function_unity_gain` | ✅ Exists | Accuracy | H(f) magnitude = 1.0 for identical input/output |
| `test_transfer_function_phase_shift` | ✅ Exists | Accuracy | 45° phase shift detected within 5° tolerance |

**Proposed Additions:**

| Test | Value Type | What It Would Ensure |
|------|------------|----------------------|
| `test_csd_symmetry` | Accuracy | CSD(x,y) = conj(CSD(y,x)) |
| `test_coherence_bounds` | Robustness | Coherence always in [0, 1] for any input |
| `test_transfer_function_known_system` | Accuracy | H(f) matches known filter response |
| `test_csd_different_lengths` | Robustness | Proper error when signals have different lengths |
| `test_coherence_statistical_significance` | Accuracy | Coherence threshold calculation is correct |

---

### 1.3 Octave Band Tests

| Test | Status | Value Type | What It Would Ensure |
|------|--------|------------|----------------------|
| `test_octave_band_center_frequencies` | 📋 Proposed | Accuracy | Center frequencies match ANSI S1.11 standard |
| `test_octave_band_energy_conservation` | 📋 Proposed | Accuracy | Total energy preserved (Parseval's theorem) |
| `test_octave_band_all_fractions` | 📋 Proposed | Reliability | 1/1, 1/3, 1/6, 1/12, 1/24, 1/36 all work |
| `test_octave_band_frequency_range` | 📋 Proposed | Robustness | Bands outside data range handled gracefully |

---

## 2. Data Loading Tests

### 2.1 CSV Loading (`tests/test_integration.py`)

| Test | Status | Value Type | What It Ensures |
|------|--------|------------|-----------------|
| `test_csv_parsing_two_columns` | ✅ Exists | Accuracy | Two-column CSV parsed correctly |
| `test_csv_parsing_with_header` | ✅ Exists | Reliability | Custom headers handled |

**Proposed Additions:**

| Test | Value Type | What It Would Ensure |
|------|------------|----------------------|
| `test_csv_auto_sample_rate` | Accuracy | Sample rate correctly inferred from time column |
| `test_csv_missing_values` | Robustness | Missing/empty cells handled gracefully |
| `test_csv_scientific_notation` | Reliability | Scientific notation (1.23e-5) parsed correctly |
| `test_csv_large_file` | Reliability | Files with 1M+ rows load efficiently |
| `test_csv_unicode_headers` | Robustness | Unicode in channel names doesn't break loading |

---

### 2.2 HDF5 Loading (`tests/test_integration.py`)

| Test | Status | Value Type | What It Ensures |
|------|--------|------------|-----------------|
| `test_hdf5_loader_integration` | ✅ Exists | Reliability | Can open file, find flights/channels, load data |

**Proposed Additions:**

| Test | Value Type | What It Would Ensure |
|------|------------|----------------------|
| `test_hdf5_lazy_loading` | Reliability | Data not loaded until requested (memory efficient) |
| `test_hdf5_decimation` | Accuracy | Decimation factor correctly calculated |
| `test_hdf5_metadata_extraction` | Accuracy | Flight/channel metadata correctly extracted |
| `test_hdf5_corrupted_file` | Robustness | Corrupted files produce clear error message |
| `test_hdf5_missing_attributes` | Robustness | Missing metadata handled with defaults |

---

## 3. GUI Component Tests

### 3.1 Cross-Spectrum Window (`tests/test_gui_headless.py`)

| Test | Status | Value Type | What It Ensures |
|------|--------|------------|-----------------|
| `test_window_initialization` | ✅ Exists | Reliability | Window creates with correct title and elements |
| `test_channel_selection` | ✅ Exists | Reliability | Combo boxes populated correctly |
| `test_calculation_runs` | ✅ Exists | Reliability | Calculation completes without error |
| `test_coherence_values_valid` | ✅ Exists | Accuracy | Output coherence in valid range [0,1] |

**Proposed Additions:**

| Test | Value Type | What It Would Ensure |
|------|------------|----------------------|
| `test_cross_spectrum_plot_updates` | Reliability | Plots update after recalculation |
| `test_cross_spectrum_parameter_change` | Reliability | Changing df/overlap updates results |
| `test_cross_spectrum_export` | Reliability | Results can be exported for reporting |

---

### 3.2 PSD Window

| Test | Status | Value Type | What It Would Ensure |
|------|--------|------------|----------------------|
| `test_psd_window_data_flow` | ✅ Exists | Reliability | Data flows correctly through window |
| `test_psd_window_comparison_curves` | 📋 Proposed | Reliability | Reference curves display correctly |
| `test_psd_window_octave_toggle` | 📋 Proposed | Reliability | Octave band toggle updates plot |
| `test_psd_window_spectrogram_launch` | 📋 Proposed | Reliability | Spectrogram window opens with correct data |
| `test_psd_window_maximax_toggle` | 📋 Proposed | Reliability | Switching Welch↔Maximax works |

---

### 3.3 Report Generator (`tests/test_gui_headless.py`)

| Test | Status | Value Type | What It Ensures |
|------|--------|------------|-----------------|
| `test_report_creation` | ✅ Exists | Reliability | Report object creates successfully |
| `test_summary_table` | ✅ Exists | Accuracy | Table created with correct channels/values |
| `test_save_to_bytes` | ✅ Exists | Reliability | Output is valid PPTX format |
| `test_full_report_workflow` | ✅ Exists | Reliability | Complete report workflow succeeds |

**Proposed Additions:**

| Test | Value Type | What It Would Ensure |
|------|------------|----------------------|
| `test_report_plot_image_quality` | Accuracy | Exported images have sufficient resolution |
| `test_report_parameters_formatting` | Accuracy | Parameters displayed with correct units/precision |
| `test_report_large_channel_count` | Robustness | Reports with 20+ channels work |
| `test_report_special_characters` | Robustness | Unicode in channel names renders correctly |

---

## 4. User Workflow Tests

### 4.1 Simulated Interactions (`tests/test_user_workflows.py`)

| Test | Status | Value Type | What It Ensures |
|------|--------|------------|-----------------|
| `test_open_calculate_close_workflow` | ✅ Exists | Reliability | Basic user workflow completes |
| `test_change_channels_workflow` | ✅ Exists | Reliability | Channel selection updates correctly |
| `test_import_reference_curve` | ✅ Exists | Reliability | CSV reference curve imports |
| `test_multiple_curves_management` | ✅ Exists | Reliability | Add/hide/remove curves works |

**Proposed Additions:**

| Test | Value Type | What It Would Ensure |
|------|------------|----------------------|
| `test_load_csv_calculate_export_workflow` | Reliability | Complete CSV→PSD→Report workflow |
| `test_load_hdf5_multi_channel_workflow` | Reliability | HDF5 multi-channel analysis workflow |
| `test_event_definition_workflow` | Reliability | Event manager workflow completes |
| `test_spectrogram_generation_workflow` | Reliability | Spectrogram workflow with 4 channels |

---

## 5. Error Handling Tests

### 5.1 Input Validation (`tests/test_user_workflows.py`)

| Test | Status | Value Type | What It Ensures |
|------|--------|------------|-----------------|
| `test_cross_spectrum_same_channel_error` | ✅ Exists | Robustness | Warning shown for same channel selection |
| `test_insufficient_channels_for_cross_spectrum` | ✅ Exists | Robustness | Single channel handled gracefully |
| `test_invalid_csv_format` | ✅ Exists | Robustness | Invalid CSV detected |

**Proposed Additions:**

| Test | Value Type | What It Would Ensure |
|------|------------|----------------------|
| `test_frequency_range_validation` | Robustness | freq_min < freq_max enforced |
| `test_df_vs_signal_length` | Robustness | Error when df requires more samples than available |
| `test_maximax_window_validation` | Robustness | Maximax window not larger than signal |
| `test_filter_cutoff_validation` | Robustness | Filter cutoff < Nyquist enforced |
| `test_file_not_found_error` | Robustness | Clear message for missing files |
| `test_permission_denied_error` | Robustness | Clear message for inaccessible files |

---

## 6. Data Contract Tests (`tests/test_data_contracts.py`)

| Test | Status | Value Type | What It Ensures |
|------|--------|------------|-----------------|
| `test_flight_info_contract` | ✅ Exists | Reliability | FlightInfo has required attributes |
| `test_channel_info_contract` | ✅ Exists | Reliability | ChannelInfo has required attributes |
| `test_channel_selection_tuple_contract` | ✅ Exists | Reliability | 4-tuple format is correct |
| `test_hdf5_loader_contract` | ✅ Exists | Reliability | Loader has required methods |
| `test_psd_welch_contract` | ✅ Exists | Reliability | Function signature and return types correct |
| `test_psd_maximax_contract` | ✅ Exists | Accuracy | Maximax ≥ Welch property holds |
| `test_numpy_compatibility` | ✅ Exists | Reliability | NumPy arrays work as expected |

**Proposed Additions:**

| Test | Value Type | What It Would Ensure |
|------|------------|----------------------|
| `test_csd_contract` | Reliability | CSD function signature and return types |
| `test_coherence_contract` | Reliability | Coherence function signature and return types |
| `test_report_generator_contract` | Reliability | ReportGenerator has required methods |
| `test_comparison_curve_contract` | Reliability | Comparison curve dict has required keys |

---

## 7. Multi-Rate Support Tests (`tests/test_multi_rate_channels.py`)

| Test | Status | Value Type | What It Ensures |
|------|--------|------------|-----------------|
| `test_multi_rate_psd` | ✅ Exists | Accuracy | Different sample rates achieve same df |
| `test_channel_data_class` | ✅ Exists | Reliability | ChannelData class works correctly |
| `test_backward_compatibility` | ✅ Exists | Reliability | Old 4-tuple format still works |

**Proposed Additions:**

| Test | Value Type | What It Would Ensure |
|------|------------|----------------------|
| `test_multi_rate_time_alignment` | Accuracy | Signals with different rates align correctly |
| `test_multi_rate_cross_spectrum` | Accuracy | CSD works with different sample rates |
| `test_multi_rate_spectrogram` | Reliability | Spectrograms work with mixed rates |

---

## 8. Performance Tests

| Test | Status | Value Type | What It Would Ensure |
|------|--------|------------|----------------------|
| `test_psd_1m_samples_performance` | 📋 Proposed | Reliability | 1M samples processes in <5 seconds |
| `test_hdf5_100_channels_performance` | 📋 Proposed | Reliability | 100 channels load in <10 seconds |
| `test_spectrogram_large_data_performance` | 📋 Proposed | Reliability | Large spectrograms don't freeze UI |
| `test_memory_usage_large_file` | 📋 Proposed | Reliability | Memory stays bounded for large files |

---

## Summary Statistics

| Category | Existing | Proposed | Total |
|----------|----------|----------|-------|
| **Core Algorithm (PSD)** | 11 | 8 | 19 |
| **Cross-Spectrum** | 5 | 5 | 10 |
| **Octave Bands** | 0 | 4 | 4 |
| **CSV Loading** | 2 | 5 | 7 |
| **HDF5 Loading** | 1 | 5 | 6 |
| **GUI Components** | 7 | 6 | 13 |
| **Report Generator** | 4 | 4 | 8 |
| **User Workflows** | 4 | 4 | 8 |
| **Error Handling** | 3 | 6 | 9 |
| **Data Contracts** | 7 | 4 | 11 |
| **Multi-Rate** | 3 | 3 | 6 |
| **Performance** | 0 | 4 | 4 |
| **TOTAL** | **47** | **58** | **105** |

---

## Priority Implementation Order

### Phase 1: Critical Accuracy Tests
1. `test_psd_parseval_theorem` - Mathematical correctness foundation
2. `test_maximax_envelope_property` - Core algorithm guarantee
3. `test_octave_band_energy_conservation` - Standards compliance

### Phase 2: Robustness Tests
4. `test_psd_nan_handling` - Real-world data quality
5. `test_csv_missing_values` - Input data variability
6. `test_hdf5_corrupted_file` - Error recovery

### Phase 3: Reliability Tests
7. `test_psd_1m_samples_performance` - Large data handling
8. `test_load_csv_calculate_export_workflow` - End-to-end validation
9. `test_memory_usage_large_file` - Production stability

---

## How to Run Tests

```bash
# All existing tests
QT_QPA_PLATFORM=offscreen pytest tests/ -v

# Only accuracy-critical tests
pytest tests/test_psd.py tests/test_gui_headless.py::TestCrossSpectrumFunctions -v

# Only robustness tests
pytest -k "error or invalid or validation" -v

# Performance benchmarks (when implemented)
pytest tests/test_performance.py -v --benchmark
```
