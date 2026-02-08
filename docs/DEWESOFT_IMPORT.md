# DEWESoft Data Import Guide

## Overview

SpectralEdge now includes support for importing data from **DEWESoft** data acquisition files (`.dxd` and `.dxz` formats) using the official **DEWESoft Data Reader Library**. This guide explains how to use the provided conversion scripts to convert DEWESoft files to CSV or MATLAB `.mat` format for analysis in SpectralEdge.

## What is DEWESoft?

DEWESoft is a professional data acquisition and analysis software platform widely used in aerospace, automotive, and industrial testing. DEWESoft systems record high-speed sensor data in proprietary `.dxd` (DEWESoft Data) and `.dxz` (compressed) formats.

## Supported Features

The conversion scripts support:

- ✓ Reading `.dxd` and `.dxz` files
- ✓ Extracting file metadata (sample rate, duration, timestamps)
- ✓ Listing all available channels with properties
- ✓ Selective channel export or full file export
- ✓ Synchronous and asynchronous channel types
- ✓ Array channels (multi-dimensional data)
- ✓ Cross-platform support (Windows and Linux)
- ✓ Large file handling with sample limiting
- ✓ Comprehensive error handling and validation

## Installation

### Prerequisites

**Python Script:**
- Python 3.8 or later
- Standard library modules (ctypes, csv, argparse)
- DEWESoft Data Reader Library (included)

**MATLAB Script:**
- MATLAB R2018b or later
- DEWESoft Data Reader Library (included)

### Library Files

The DEWESoft Data Reader Library files are included in the following directories:

```
spectral-edge/
├── scripts/dewesoft/          # Python library files
│   ├── DWDataReaderHeader.py  # Python wrapper
│   ├── DWDataReaderLib64.dll  # Windows 64-bit
│   ├── DWDataReaderLib64.so   # Linux 64-bit
│   └── DWDataReaderLib.dll    # Windows 32-bit
└── matlab/dewesoft/           # MATLAB library files
    ├── DWDataReader.m         # MATLAB wrapper class
    ├── DWDataReaderLibFuncs.h # C header file
    ├── DWDataReaderLib64.dll  # Windows 64-bit
    ├── DWDataReaderLib64.so   # Linux 64-bit
    └── DWDataReaderLib.dll    # Windows 32-bit
```

**No additional installation is required** - the scripts automatically load the appropriate library based on your platform and architecture.

## Python Script: dxd_to_csv.py

### Description

Converts DEWESoft `.dxd` files to CSV format for use in SpectralEdge or other analysis tools.

### Basic Usage

```bash
# Convert entire file to CSV
python scripts/dxd_to_csv.py input.dxd output.csv

# Convert specific channels only
python scripts/dxd_to_csv.py input.dxd output.csv --channels "Accel_X,Accel_Y,Accel_Z"

# Limit to first 10000 samples per channel
python scripts/dxd_to_csv.py input.dxd output.csv --max-samples 10000
```

### Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `input_file` | Path to input `.dxd` or `.dxz` file | `data/flight_test.dxd` |
| `output_file` | Path to output `.csv` file | `output/flight_test.csv` |
| `--channels` | Comma-separated list of channel names | `--channels "CH1,CH2,CH3"` |
| `--max-samples` | Maximum samples per channel | `--max-samples 10000` |
| `--all-channels` | Export all channels (default) | `--all-channels` |

### Output Format

The CSV file contains:

1. **Metadata rows** (commented with `#`):
   - Sample rate
   - Duration
   - Number of channels

2. **Header rows**:
   - Row 1: Channel names
   - Row 2: Engineering units

3. **Data rows**:
   - Column 1: Time (seconds)
   - Columns 2+: Channel values

Example CSV structure:
```csv
# DEWESoft Data Export
# Sample Rate: 5000.00 Hz
# Duration: 120.50 s
# Channels: 3

Time (s),Accel_X,Accel_Y,Accel_Z
s,g,g,g
0.000000,0.012345,0.023456,0.034567
0.000200,0.013456,0.024567,0.035678
...
```

### Examples

**Example 1: Convert flight test data**
```bash
python scripts/dxd_to_csv.py \
    data/flight_test_2024_03_15.dxd \
    output/flight_test.csv
```

**Example 2: Extract vibration channels only**
```bash
python scripts/dxd_to_csv.py \
    data/vibration_test.dxd \
    output/vibration.csv \
    --channels "Accel_X,Accel_Y,Accel_Z,Gyro_X,Gyro_Y,Gyro_Z"
```

**Example 3: Preview large file (first 10000 samples)**
```bash
python scripts/dxd_to_csv.py \
    data/long_duration_test.dxd \
    output/preview.csv \
    --max-samples 10000
```

## MATLAB Script: dxd_to_mat.m

### Description

Converts DEWESoft `.dxd` files to MATLAB `.mat` format for analysis in MATLAB or SpectralEdge.

### Basic Usage

```matlab
% Convert entire file to MAT
dxd_to_mat('input.dxd', 'output.mat');

% Convert specific channels only
channels = {'Accel_X', 'Accel_Y', 'Accel_Z'};
dxd_to_mat('input.dxd', 'output.mat', 'channels', channels);

% Limit to first 10000 samples per channel
dxd_to_mat('input.dxd', 'output.mat', 'max_samples', 10000);

% Use HDF5-based format for large files (> 2 GB)
dxd_to_mat('input.dxd', 'output.mat', 'format', '-v7.3');
```

### Function Signature

```matlab
function dxd_to_mat(input_file, output_file, varargin)
```

### Optional Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `'channels'` | Cell array | Channel names to export | All channels |
| `'max_samples'` | Numeric | Maximum samples per channel | All samples |
| `'format'` | String | MAT file format (`'-v7'` or `'-v7.3'`) | `'-v7'` |

### Output Structure

The MAT file contains a structure named `dewesoft_data` with two fields:

**1. metadata** (structure):
- `sample_rate` - Sample rate in Hz
- `start_measure_time` - Start measurement time (seconds)
- `start_store_time` - Start storage time (seconds)
- `duration` - Total duration (seconds)
- `input_file` - Original input file path
- `conversion_date` - Date/time of conversion

**2. channels** (structure array):
Each element contains:
- `name` - Channel name (string)
- `unit` - Engineering unit (string)
- `description` - Channel description (string)
- `data_type` - Data type name (string)
- `timestamps` - Time vector (double array)
- `values` - Data values (double array)

### Loading and Using the Data

```matlab
% Load the MAT file
data = load('output.mat');

% Access metadata
metadata = data.dewesoft_data.metadata;
fprintf('Sample rate: %.2f Hz\n', metadata.sample_rate);
fprintf('Duration: %.2f s\n', metadata.duration);

% Access channels
channels = data.dewesoft_data.channels;
num_channels = length(channels);
fprintf('Number of channels: %d\n', num_channels);

% Plot first channel
ch1 = channels(1);
figure;
plot(ch1.timestamps, ch1.values);
xlabel('Time (s)');
ylabel(sprintf('%s (%s)', ch1.name, ch1.unit));
title(ch1.name);
grid on;

% Find a specific channel by name
for i = 1:length(channels)
    if strcmp(channels(i).name, 'Accel_X')
        accel_x = channels(i);
        break;
    end
end
```

### Examples

**Example 1: Convert flight test data**
```matlab
dxd_to_mat('data/flight_test_2024_03_15.dxd', 'output/flight_test.mat');
```

**Example 2: Extract specific channels**
```matlab
channels = {'Accel_X', 'Accel_Y', 'Accel_Z', 'Gyro_X', 'Gyro_Y', 'Gyro_Z'};
dxd_to_mat('data/vibration_test.dxd', 'output/vibration.mat', ...
           'channels', channels);
```

**Example 3: Large file with HDF5 format**
```matlab
dxd_to_mat('data/long_duration_test.dxd', 'output/long_test.mat', ...
           'format', '-v7.3');
```

## Integration with SpectralEdge

### Workflow

1. **Convert DEWESoft file to CSV or MAT**
   ```bash
   python scripts/dxd_to_csv.py data/test.dxd data/test.csv
   ```

2. **Load CSV in SpectralEdge Batch Processor**
   - Open SpectralEdge Batch Processor
   - Go to "File Selection" tab
   - Click "Add Files" and select the converted CSV file
   - Proceed with channel selection and PSD analysis

3. **Alternative: Load MAT file directly**
   - If using MATLAB conversion, the MAT file can be loaded in SpectralEdge
   - The batch processor supports both CSV and MAT formats

### Recommended Workflow for Large Files

For very large DEWESoft files (> 1 GB), use this workflow:

1. **Preview the file** (limit samples):
   ```bash
   python scripts/dxd_to_csv.py large_file.dxd preview.csv --max-samples 10000
   ```

2. **Identify channels of interest** by examining the preview

3. **Extract only needed channels**:
   ```bash
   python scripts/dxd_to_csv.py large_file.dxd output.csv \
       --channels "Channel1,Channel2,Channel3"
   ```

4. **Load in SpectralEdge** for PSD analysis

## Troubleshooting

### Common Issues

**Issue 1: "Library not found" error**

**Symptoms:**
```
ERROR: Failed to load DEWESoft Data Reader Library
OSError: [WinError 126] The specified module could not be found
```

**Solution:**
- Ensure the library files are in the `scripts/dewesoft/` or `matlab/dewesoft/` directory
- On Windows, you may need to install Visual C++ Redistributable
- On Linux, ensure you have execute permissions: `chmod +x scripts/dewesoft/*.so`

---

**Issue 2: "File cannot be opened" error**

**Symptoms:**
```
ERROR: Failed to open file: input.dxd
DWSTAT_ERROR_FILE_CANNOT_OPEN
```

**Solution:**
- Verify the file path is correct
- Check that the file is not open in DEWESoft X software
- Ensure you have read permissions for the file
- Try copying the file to a local directory (not network drive)

---

**Issue 3: "Channel not found" error**

**Symptoms:**
```
WARNING: Channel 'Accel_X' not found in file
```

**Solution:**
- Run the script without `--channels` option to see all available channels
- Check for exact spelling and case sensitivity
- Some channels may have spaces or special characters in names

---

**Issue 4: Memory error with large files**

**Symptoms:**
```
MemoryError: Unable to allocate array
```

**Solution:**
- Use the `--max-samples` option to limit the number of samples
- Export only specific channels with `--channels` option
- Close other applications to free up memory
- For MATLAB, use `-v7.3` format which supports out-of-core access

---

**Issue 5: MATLAB library loading error**

**Symptoms:**
```
Error using loadlibrary
The specified module could not be found
```

**Solution:**
- Ensure all `.h` header files are in `matlab/dewesoft/` directory
- Check that the DLL/SO file matches your MATLAB architecture (32-bit vs 64-bit)
- Try running MATLAB as administrator (Windows)
- On Linux, ensure library dependencies are installed: `ldd DWDataReaderLib64.so`

## Platform-Specific Notes

### Windows

- The scripts automatically select 64-bit or 32-bit DLL based on Python/MATLAB architecture
- If you encounter DLL loading errors, install [Visual C++ Redistributable](https://support.microsoft.com/en-us/help/2977003/the-latest-supported-visual-c-downloads)
- Antivirus software may block DLL loading - add an exception if needed

### Linux

- The scripts use `.so` (shared object) files instead of DLLs
- Ensure execute permissions: `chmod +x scripts/dewesoft/*.so matlab/dewesoft/*.so`
- Install required dependencies: `sudo apt-get install libstdc++6`
- If you get "cannot open shared object file" errors, check `ldd` output for missing dependencies

## Advanced Usage

### Batch Conversion

**Python (Bash script):**
```bash
#!/bin/bash
# Convert all DXD files in a directory to CSV

for file in data/*.dxd; do
    basename=$(basename "$file" .dxd)
    python scripts/dxd_to_csv.py "$file" "output/${basename}.csv"
done
```

**MATLAB:**
```matlab
% Convert all DXD files in a directory to MAT

dxd_files = dir('data/*.dxd');
for i = 1:length(dxd_files)
    input_file = fullfile(dxd_files(i).folder, dxd_files(i).name);
    [~, basename, ~] = fileparts(dxd_files(i).name);
    output_file = fullfile('output', [basename '.mat']);
    
    fprintf('Converting %s...\n', dxd_files(i).name);
    dxd_to_mat(input_file, output_file);
end
```

### Custom Channel Selection

Create a text file with channel names (one per line):

**channels.txt:**
```
Accel_X
Accel_Y
Accel_Z
Gyro_X
Gyro_Y
Gyro_Z
```

**Python script to read channel list:**
```python
with open('channels.txt', 'r') as f:
    channels = ','.join([line.strip() for line in f if line.strip()])

os.system(f'python scripts/dxd_to_csv.py input.dxd output.csv --channels "{channels}"')
```

## Performance Tips

1. **Use selective channel export** - Only export channels you need for analysis
2. **Limit samples for preview** - Use `--max-samples` for quick file inspection
3. **Use local storage** - Copy files from network drives to local disk before conversion
4. **Close other applications** - Free up memory for large file processing
5. **Use HDF5 format for large MATLAB files** - `-v7.3` format supports files > 2 GB

## File Format Comparison

| Format | Pros | Cons | Best For |
|--------|------|------|----------|
| **CSV** | Universal compatibility, human-readable, works with Excel | Large file size, slower to load | Small to medium datasets, data sharing |
| **MAT** | Fast loading in MATLAB, compact, preserves metadata | MATLAB-specific, requires MATLAB to view | MATLAB analysis, large datasets |
| **HDF5** | Very large file support, efficient storage, cross-platform | Requires HDF5 tools to view | Very large datasets (> 2 GB) |

## Support and Resources

### DEWESoft Resources

- [DEWESoft Official Website](https://dewesoft.com)
- [DEWESoft Data Reader Library Download](https://dewesoft.com/download/developer-downloads)
- [DEWESoft X Software](https://dewesoft.com/products/software)

### SpectralEdge Resources

- [SpectralEdge GitHub Repository](https://github.com/ajordan510/spectral-edge)
- [SpectralEdge Documentation](../README.md)
- [Batch Processor Guide](BATCH_PROCESSOR.md)

### Getting Help

If you encounter issues not covered in this guide:

1. Check the [GitHub Issues](https://github.com/ajordan510/spectral-edge/issues) page
2. Review the DEWESoft Data Reader Library documentation (included in `docs/` folder)
3. Create a new issue with:
   - Your operating system and Python/MATLAB version
   - Complete error message
   - Sample file (if possible) or file characteristics

## License

The DEWESoft Data Reader Library is proprietary software provided by Dewesoft d.o.o. under their license terms. The Python and MATLAB wrapper scripts provided with SpectralEdge are released under the MIT License.

## Changelog

### Version 1.0.0 (2026-02-08)
- Initial release
- Python script: `dxd_to_csv.py`
- MATLAB script: `dxd_to_mat.m`
- Support for .dxd and .dxz files
- Cross-platform support (Windows, Linux)
- Comprehensive error handling and validation
- Selective channel export
- Sample limiting for large files

---

**Last Updated:** February 8, 2026  
**Author:** SpectralEdge Development Team  
**Version:** 1.0.0
