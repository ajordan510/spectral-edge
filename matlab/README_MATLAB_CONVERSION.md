# MATLAB to HDF5 Conversion for SpectralEdge

This directory contains MATLAB scripts to convert your flight test data into the HDF5 format required by SpectralEdge.

---

## 📋 Requirements

### Software Requirements
- **MATLAB** R2011a or later (for HDF5 support)
- No additional toolboxes required (uses built-in HDF5 functions)

### MATLAB HDF5 Functions Used
- `h5create` - Create HDF5 datasets
- `h5write` - Write data to HDF5 files
- `h5writeatt` - Write attributes to HDF5 datasets/groups
- `h5info` - Read HDF5 file structure (for verification)

---

## 📁 Files

### `convert_to_hdf5.m`
Main conversion function that handles the entire conversion process.

**Key Features**:
- Converts single or multiple flights
- Validates input data structure
- Writes proper metadata and attributes
- Handles optional fields gracefully
- Provides detailed error messages

### `example_conversion.m`
Comprehensive examples demonstrating various use cases.

**Includes**:
1. Simple single channel test data
2. Multi-axis accelerometer data
3. Multiple flights in one file
4. High sample rate data (40 kHz)
5. Template for converting your existing data

---

## 🚀 Quick Start

### Step 1: Add Scripts to MATLAB Path

```matlab
% Navigate to the matlab directory
cd('/path/to/SpectralEdge/matlab')

% Or add to path
addpath('/path/to/SpectralEdge/matlab')
```

### Step 2: Prepare Your Data

Your data must be organized into a MATLAB structure with this format:

```matlab
flight.flight_id = 'Your_Flight_ID';           % Required: string
flight.date = '2025-01-22';                    % Optional: string
flight.description = 'Test description';       % Optional: string

% Each channel must have:
flight.channels.channel_name.data = signal_vector;     % Required: 1D array
flight.channels.channel_name.sample_rate = 1000;       % Required: Hz
flight.channels.channel_name.units = 'g';              % Required: string
flight.channels.channel_name.start_time = 0.0;         % Optional: seconds
flight.channels.channel_name.description = 'desc';     % Optional: string
flight.channels.channel_name.sensor_id = 'ACC_001';    % Optional: string
flight.channels.channel_name.location = 'Wing tip';    % Optional: string
```

### Step 3: Convert to HDF5

```matlab
% Single flight
convert_to_hdf5('output.h5', flight);

% Multiple flights
convert_to_hdf5('output.h5', {flight1, flight2, flight3});
```

### Step 4: Load in SpectralEdge

1. Launch SpectralEdge: `run.bat` (Windows) or `./run.sh` (Linux)
2. Click "Load HDF5"
3. Select your `.h5` file
4. Choose flight and channels from the navigator

---

## 📊 Data Structure Requirements

### Required Fields

#### Flight Level
- `flight_id` - String identifier for the flight
- `channels` - Struct containing channel data

#### Channel Level
- `data` - 1D numeric vector of signal data
- `sample_rate` - Positive scalar (Hz)
- `units` - String (e.g., 'g', 'm/s^2', 'V', 'Pa')

### Optional Fields

#### Flight Level
- `date` - String (YYYY-MM-DD format recommended)
- `description` - String describing the flight/test

#### Channel Level
- `start_time` - Scalar, start time in seconds (default: 0.0)
- `description` - String describing the channel
- `sensor_id` - String identifier for the sensor
- `location` - String describing sensor location
- `range_min` - Scalar, minimum sensor range
- `range_max` - Scalar, maximum sensor range

---

## 💡 Usage Examples

### Example 1: Simple Test Signal

```matlab
% Generate test signal
fs = 1000;  % 1 kHz
t = (0:1/fs:10-1/fs)';
signal = sin(2*pi*50*t) + 0.1*randn(size(t));

% Package data
flight.flight_id = 'Test_001';
flight.date = '2025-01-22';
flight.channels.test_signal.data = signal;
flight.channels.test_signal.sample_rate = fs;
flight.channels.test_signal.units = 'g';
flight.channels.test_signal.start_time = 0.0;

% Convert
convert_to_hdf5('test.h5', flight);
```

### Example 2: Triaxial Accelerometer

```matlab
% Load your data
load('vibration_test.mat');  % Contains accel_x, accel_y, accel_z, fs

% Package data
flight.flight_id = 'Vibration_Test_001';
flight.date = '2025-01-22';
flight.description = 'Wing tip vibration test';

% X-axis
flight.channels.accel_x.data = accel_x;
flight.channels.accel_x.sample_rate = fs;
flight.channels.accel_x.units = 'g';
flight.channels.accel_x.start_time = 0.0;
flight.channels.accel_x.location = 'Wing tip';

% Y-axis
flight.channels.accel_y.data = accel_y;
flight.channels.accel_y.sample_rate = fs;
flight.channels.accel_y.units = 'g';
flight.channels.accel_y.start_time = 0.0;
flight.channels.accel_y.location = 'Wing tip';

% Z-axis
flight.channels.accel_z.data = accel_z;
flight.channels.accel_z.sample_rate = fs;
flight.channels.accel_z.units = 'g';
flight.channels.accel_z.start_time = 0.0;
flight.channels.accel_z.location = 'Wing tip';

% Convert
convert_to_hdf5('vibration_test.h5', flight);
```

### Example 3: Multiple Flights

```matlab
% Flight 1
flights{1}.flight_id = 'Flight_001';
flights{1}.date = '2025-01-22';
flights{1}.channels.accel_z.data = signal1;
flights{1}.channels.accel_z.sample_rate = 1000;
flights{1}.channels.accel_z.units = 'g';
flights{1}.channels.accel_z.start_time = 0.0;

% Flight 2
flights{2}.flight_id = 'Flight_002';
flights{2}.date = '2025-01-23';
flights{2}.channels.accel_z.data = signal2;
flights{2}.channels.accel_z.sample_rate = 1000;
flights{2}.channels.accel_z.units = 'g';
flights{2}.channels.accel_z.start_time = 0.0;

% Convert
convert_to_hdf5('multiple_flights.h5', flights);
```

---

## 🔍 HDF5 File Structure

The conversion script creates HDF5 files with this structure:

```
output.h5
├── flight_001/
│   ├── metadata/
│   │   └── attributes: flight_id, date, duration, description
│   └── channels/
│       ├── accel_x (dataset)
│       │   └── attributes: units, sample_rate, start_time, description, etc.
│       ├── accel_y (dataset)
│       └── accel_z (dataset)
├── flight_002/
│   └── ...
└── flight_003/
    └── ...
```

### Group Naming
- Flights are named `flight_001`, `flight_002`, etc. (automatically numbered)
- Channels use your provided names (e.g., `accel_x`, `pressure_sensor`)

### Attributes
- **Flight metadata**: Stored as attributes on `/flight_XXX/metadata` group
- **Channel metadata**: Stored as attributes on each channel dataset

---

## ⚠️ Common Issues and Solutions

### Issue 1: "Data must be a numeric vector"
**Cause**: Data is 2D array or matrix  
**Solution**: Extract each column separately
```matlab
% Wrong
flight.channels.accel.data = [x_data, y_data, z_data];  % 2D array

% Correct
flight.channels.accel_x.data = x_data;  % 1D vector
flight.channels.accel_y.data = y_data;  % 1D vector
flight.channels.accel_z.data = z_data;  % 1D vector
```

### Issue 2: "Sample rate must be positive"
**Cause**: Sample rate is 0, negative, or missing  
**Solution**: Provide valid sample rate
```matlab
flight.channels.accel_x.sample_rate = 1000;  % Hz
```

### Issue 3: "Missing required field: units"
**Cause**: Units field not specified  
**Solution**: Always provide units string
```matlab
flight.channels.accel_x.units = 'g';  % or 'm/s^2', 'V', etc.
```

### Issue 4: File already exists
**Cause**: Output file already exists  
**Solution**: Script automatically deletes existing file, or delete manually
```matlab
delete('output.h5');
convert_to_hdf5('output.h5', flight);
```

---

## 🧪 Testing Your Conversion

### Verify in MATLAB

```matlab
% Check file structure
info = h5info('output.h5');
disp(info);

% Read back data to verify
data = h5read('output.h5', '/flight_001/channels/accel_x');
attrs = h5readatt('output.h5', '/flight_001/channels/accel_x', 'sample_rate');
```

### Verify in SpectralEdge

1. Load the HDF5 file
2. Check that:
   - Flight names appear correctly
   - Channel names and units are correct
   - Sample rates are correct
   - Data plots correctly in time history
   - PSD calculations work without errors

---

## 📏 Performance Considerations

### File Size
- HDF5 files are typically **smaller** than MATLAB `.mat` files
- Compression is automatic for large datasets
- Example: 100s @ 40 kHz = 4M samples ≈ 30 MB

### Memory Usage
- Conversion is memory-efficient
- Data is written directly to disk
- Can handle datasets larger than available RAM

### Conversion Speed
- Typical: 1-5 seconds for 10M samples
- Depends on: data size, disk speed, number of channels

---

## 🔧 Advanced Usage

### Custom Channel Names

Use any valid MATLAB field name for channels:

```matlab
flight.channels.accelerometer_x_wing_tip.data = ...
flight.channels.pressure_sensor_01.data = ...
flight.channels.strain_gauge_fuselage.data = ...
```

### Multiple Sensor Types

Mix different sensor types in one flight:

```matlab
% Accelerometer
flight.channels.accel_z.data = accel_data;
flight.channels.accel_z.units = 'g';
flight.channels.accel_z.sample_rate = 5000;

% Pressure sensor
flight.channels.pressure.data = pressure_data;
flight.channels.pressure.units = 'Pa';
flight.channels.pressure.sample_rate = 100;

% Strain gauge
flight.channels.strain.data = strain_data;
flight.channels.strain.units = 'με';
flight.channels.strain.sample_rate = 1000;
```

### Different Sample Rates

Each channel can have its own sample rate:

```matlab
flight.channels.high_freq.sample_rate = 40000;  % 40 kHz
flight.channels.low_freq.sample_rate = 100;     % 100 Hz
```

---

## 📚 Additional Resources

### MATLAB HDF5 Documentation
- [h5create](https://www.mathworks.com/help/matlab/ref/h5create.html)
- [h5write](https://www.mathworks.com/help/matlab/ref/h5write.html)
- [h5writeatt](https://www.mathworks.com/help/matlab/ref/h5writeatt.html)

### SpectralEdge Documentation
- See `docs/` directory for PSD analysis documentation
- See `README.md` for testing instructions

---

## 💬 Support

If you encounter issues:

1. Check that your MATLAB version supports HDF5 (R2011a+)
2. Verify your data structure matches the required format
3. Run `example_conversion.m` to test the scripts
4. Check the error message for specific field/validation issues

---

## 📝 Summary

**To convert your data**:

1. Organize into flight structure with required fields
2. Run `convert_to_hdf5('output.h5', flight)`
3. Load in SpectralEdge and verify

**Required fields**:
- `flight.flight_id` (string)
- `flight.channels.name.data` (1D vector)
- `flight.channels.name.sample_rate` (Hz)
- `flight.channels.name.units` (string)

**That's it!** The script handles all HDF5 formatting automatically.
