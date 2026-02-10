# HDF5 Format Validation and Debugging

SpectralEdge now includes comprehensive HDF5 format validation with detailed diagnostic messages to help you debug loading issues.

---

## 🎯 Overview

When you load an HDF5 file, SpectralEdge automatically validates the file structure and provides detailed error messages if any issues are found. This helps you quickly identify and fix format problems.

---

## ✅ What Gets Validated

### **1. File Structure**
- ✓ File must have groups named `flight_001`, `flight_002`, etc.
- ✓ Each flight must have a `channels` subgroup
- ✓ Each channel must be a dataset (not a group)

### **2. Data Format**
- ✓ Channel data must be 1D arrays (not 2D or 3D)
- ✓ Data must be numeric

### **3. Required Attributes**
Each channel dataset must have these attributes:
- ✓ `units` - string (e.g., 'g', 'm/s^2', 'V')
- ✓ `sample_rate` - float (Hz, must be > 0)
- ✓ `start_time` - float (seconds)

### **4. Optional Attributes**
Recommended but not required:
- Flight metadata: `flight_id`, `date`, `duration`, `description`
- Channel metadata: `description`, `sensor_id`, `location`, `range_min`, `range_max`

---

## 🔍 Validation Messages

### **Success Message**
When a file loads successfully, you'll see:

```
HDF5 Loaded Successfully

File: your_data.h5
Flights: 2
Total channels: 6

Select flights and channels from the navigator.
```

### **Error Messages**
When validation fails, you'll see detailed diagnostic information showing:
- What was expected
- What was found
- How to fix the issue

---

## 🐛 Common Issues and Solutions

### **Issue 1: No Flight Groups Found**

**Error Message**:
```
❌ ERROR: No flight groups found!
Expected: Groups named 'flight_001', 'flight_002', etc.
Found: ['data', 'signals']
```

**Cause**: Top-level groups don't start with 'flight_'

**Solution**: Rename groups to start with 'flight_':
```matlab
% Wrong
f.create_group('data')

% Correct
f.create_group('flight_001')
```

---

### **Issue 2: No Channels Group**

**Error Message**:
```
❌ ERROR: No 'channels' group in flight_001!
Expected: flight_001/channels/
Found: ['metadata', 'data']
```

**Cause**: Flight group doesn't contain a 'channels' subgroup

**Solution**: Create channels subgroup:
```matlab
% Wrong
flight.create_dataset('accel_x', data=signal)

% Correct
channels = flight.create_group('channels')
channels.create_dataset('accel_x', data=signal)
```

---

### **Issue 3: 2D Data**

**Error Message**:
```
❌ ERROR: accel data is not 1D!
Expected: 1D array (shape: (N,))
Found: 2D array (shape: (1000, 3))

Each channel must be a 1D array of signal values.
If you have multi-axis data, create separate channels:
  - accel_x, accel_y, accel_z (not accel with shape (N, 3))
```

**Cause**: Channel dataset is 2D or 3D array

**Solution**: Create separate 1D channels:
```matlab
% Wrong
channels.create_dataset('accel', data=[x, y, z])  % 2D

% Correct
channels.create_dataset('accel_x', data=x)  % 1D
channels.create_dataset('accel_y', data=y)  % 1D
channels.create_dataset('accel_z', data=z)  % 1D
```

---

### **Issue 4: Missing Attributes**

**Error Message**:
```
❌ ERROR: test_signal missing required attributes!
Required: ['units', 'sample_rate', 'start_time']
Found: ['units']
Missing: ['sample_rate', 'start_time']

Each channel must have these attributes:
  - units: string (e.g., 'g', 'm/s^2', 'V')
  - sample_rate: float (Hz, must be > 0)
  - start_time: float (seconds, typically 0.0)
```

**Cause**: Channel dataset missing required attributes

**Solution**: Add all required attributes:
```matlab
channel = channels.create_dataset('test_signal', data=signal)
channel.attrs['units'] = 'g'
channel.attrs['sample_rate'] = 1000.0
channel.attrs['start_time'] = 0.0
```

---

### **Issue 5: Invalid Sample Rate**

**Error Message**:
```
❌ ERROR: test_signal has invalid sample_rate!
Expected: Positive number (> 0)
Found: -1000.0

Sample rate must be a positive number in Hz.
```

**Cause**: Sample rate is zero, negative, or invalid

**Solution**: Use positive sample rate:
```matlab
% Wrong
channel.attrs['sample_rate'] = -1000.0  % Negative
channel.attrs['sample_rate'] = 0.0      % Zero

% Correct
channel.attrs['sample_rate'] = 1000.0   % Positive
```

---

## 🧪 Testing Your HDF5 Files

### **Method 1: Load in SpectralEdge**
1. Run SpectralEdge
2. Click "Load HDF5"
3. Select your file
4. Read validation messages

### **Method 2: Python Validation Script**
Use the included validation script:

```bash
cd SpectralEdge/matlab
python test_hdf5_structure.py your_file.h5
```

This provides detailed validation without opening the GUI.

### **Method 3: Test Script**
Run the comprehensive test script:

```bash
cd SpectralEdge
python test_hdf5_validation.py
```

This creates various test files and demonstrates validation.

---

## 📋 Required HDF5 Structure

```
your_file.h5
├── flight_001/                    ← Must start with 'flight_'
│   ├── metadata/                  ← Optional but recommended
│   │   └── attributes:
│   │       - flight_id: string
│   │       - date: string
│   │       - duration: float
│   │       - description: string
│   │
│   └── channels/                  ← REQUIRED
│       ├── channel_name           ← Dataset (1D array)
│       │   └── attributes:        ← REQUIRED
│       │       - units: string
│       │       - sample_rate: float (> 0)
│       │       - start_time: float
│       │       - description: string (optional)
│       │       - sensor_id: string (optional)
│       │       - location: string (optional)
│       │
│       └── another_channel
│           └── ...
│
├── flight_002/
│   └── ...
│
└── flight_003/
    └── ...
```

---

## 💡 Best Practices

### **1. Use MATLAB Conversion Script**
The provided `convert_to_hdf5.m` script handles all formatting automatically:

```matlab
flight.flight_id = 'Test_001';
flight.channels.accel_x.data = signal;
flight.channels.accel_x.sample_rate = 1000;
flight.channels.accel_x.units = 'g';
flight.channels.accel_x.start_time = 0.0;

convert_to_hdf5('output.h5', flight);
```

### **2. Validate Before Loading**
Use the Python validation script to check files before loading in SpectralEdge:

```bash
python matlab/test_hdf5_structure.py your_file.h5
```

### **3. Check Sample Rates**
Ensure sample rates are positive and realistic:
- Typical: 100 Hz to 100 kHz
- Must be > 0

### **4. Use Descriptive Names**
- Flight IDs: `Flight_001`, `Vibration_Test_20250123`
- Channel names: `accel_x`, `pressure_sensor_01`, `strain_gauge_wing_tip`

### **5. Include Metadata**
While optional, metadata makes files easier to work with:
- Flight: `flight_id`, `date`, `description`
- Channel: `description`, `location`, `sensor_id`

---

## 🔧 Debugging Tips

### **1. Check File Structure**
Use `h5dump` to inspect file structure:

```bash
h5dump -n your_file.h5  # Show structure
h5dump -A your_file.h5  # Show attributes
```

### **2. Verify Data Shapes**
In Python:

```python
import h5py
with h5py.File('your_file.h5', 'r') as f:
    channel = f['flight_001/channels/accel_x']
    print(f"Shape: {channel.shape}")        # Should be (N,)
    print(f"Attributes: {dict(channel.attrs)}")
```

### **3. Check Attribute Types**
Ensure attributes are correct types:
- `units`: string
- `sample_rate`: float (not int, not string)
- `start_time`: float

### **4. Enable Verbose Mode**
In Python code:

```python
loader = HDF5FlightDataLoader(file_path, verbose=True)
```

This prints detailed validation messages to console.

---

## 📚 Related Documentation

- **MATLAB Conversion**: See `matlab/README_MATLAB_CONVERSION.md`
- **Quick Start**: See `matlab/QUICK_START.md`
- **Examples**: Run `matlab/example_conversion.m`
- **Validation Script**: Use `matlab/test_hdf5_structure.py`

---

## 🎯 Summary

**SpectralEdge validates**:
1. ✓ Flight groups (must start with 'flight_')
2. ✓ Channels subgroup (required)
3. ✓ 1D data arrays (not 2D/3D)
4. ✓ Required attributes (units, sample_rate, start_time)
5. ✓ Valid sample rates (> 0)

**When validation fails**:
- Detailed error messages show what's wrong
- Suggestions for how to fix it
- References to documentation

**Best practice**:
- Use provided MATLAB conversion script
- Validate files before loading
- Include optional metadata for better organization

---

## 💬 Need Help?

If you're still having issues:

1. Check the error message carefully - it tells you exactly what's wrong
2. Review `matlab/README_MATLAB_CONVERSION.md` for examples
3. Run `test_hdf5_validation.py` to see working examples
4. Use `test_hdf5_structure.py` to validate your files
5. Check that you're using the MATLAB conversion script correctly

The validation system is designed to help you quickly identify and fix format issues!
