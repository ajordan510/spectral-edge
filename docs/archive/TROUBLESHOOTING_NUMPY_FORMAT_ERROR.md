# Troubleshooting: "unsupported format string passed to numpy.ndarray"

## 🔴 Error Message

```
Failed to load HDF5 file: unsupported format string passed to numpy.ndarray.__format__
```

---

## 🎯 What This Means

This error occurs when your HDF5 file contains **non-numeric data types** that NumPy cannot process for spectral analysis. The data must be numeric (integers or floats) to calculate PSD, spectrograms, and other analyses.

---

## 🔍 Common Causes

### **1. Object/Mixed Data Types**
Your data was saved as Python objects or mixed types instead of pure numbers.

**Example** (wrong):
```python
data = [1.0, 2.0, "3.0", 4.0]  # Mixed: numbers and strings
channel.create_dataset('test', data=data)
# dtype = object (WRONG!)
```

**Fix**:
```python
data = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
channel.create_dataset('test', data=data)
# dtype = float64 (CORRECT!)
```

---

### **2. String/Text Data**
Your channel contains text data instead of numbers.

**Example** (wrong):
```python
data = ['1.0', '2.0', '3.0']  # Strings, not numbers
# dtype = <U3 or |S3 (WRONG!)
```

**Fix**:
```python
data = np.array([1.0, 2.0, 3.0], dtype=np.float64)
# dtype = float64 (CORRECT!)
```

---

### **3. Structured/Compound Data Types**
Your data has multiple fields (like a struct or table).

**Example** (wrong):
```python
# Structured array with named fields
dtype = np.dtype([('time', 'f8'), ('value', 'f8')])
data = np.array([(0.0, 1.0), (0.001, 2.0)], dtype=dtype)
# dtype = [('time', '<f8'), ('value', '<f8')] (WRONG!)
```

**Fix**: Create separate channels for each field:
```python
times = np.array([0.0, 0.001], dtype=np.float64)
values = np.array([1.0, 2.0], dtype=np.float64)

channels.create_dataset('time', data=times)
channels.create_dataset('value', data=values)
```

---

### **4. Datetime/Timestamp Data**
Your data contains datetime objects instead of numeric timestamps.

**Example** (wrong):
```python
data = np.array(['2025-01-23', '2025-01-24'], dtype='datetime64')
# dtype = datetime64 (WRONG!)
```

**Fix**: Convert to numeric (seconds since epoch):
```python
timestamps = np.array([1706000000.0, 1706086400.0], dtype=np.float64)
# dtype = float64 (CORRECT!)
```

---

### **5. MATLAB Cell Arrays or Structs**
MATLAB cell arrays or structs don't convert directly to numeric arrays.

**Example** (wrong in MATLAB):
```matlab
data = {1.0, 2.0, 3.0};  % Cell array (WRONG!)
```

**Fix in MATLAB**:
```matlab
data = [1.0, 2.0, 3.0];  % Numeric array (CORRECT!)
% Or explicitly convert:
data = double([1.0, 2.0, 3.0]);
```

---

## 🛠️ How to Diagnose Your File

### **Step 1: Run the Diagnostic Script**
```bash
cd SpectralEdge
python diagnose_hdf5.py your_file.h5
```

### **Step 2: Look for Data Type Errors**
The script will show you the exact data type of each channel:

**Good** (will work):
```
✓ Data type: float64 (numeric)
✓ Data type: int32 (numeric)
```

**Bad** (will cause error):
```
✗ Data type: object (PROBLEMATIC!)
  Issue: Object dtype (likely strings or mixed types)
  This will cause: 'unsupported format string passed to numpy.ndarray'

✗ Data type: <U10 (PROBLEMATIC!)
  Issue: String/bytes dtype
  This will cause: 'unsupported format string passed to numpy.ndarray'

✗ Data type: [('time', '<f8'), ('value', '<f8')] (PROBLEMATIC!)
  Issue: Structured dtype with fields: ('time', 'value')
  This will cause: 'unsupported format string passed to numpy.ndarray'
```

### **Step 3: Follow the Fix Suggestions**
The diagnostic script provides specific fixes for each issue.

---

## ✅ How to Fix in MATLAB

### **Method 1: Use the Conversion Script** (Recommended)
The `convert_to_hdf5.m` script automatically handles data types:

```matlab
% Your data (can be any numeric type)
flight.channels.accel_x.data = your_signal;  % Auto-converts to double
flight.channels.accel_x.sample_rate = 1000;
flight.channels.accel_x.units = 'g';
flight.channels.accel_x.start_time = 0.0;

% Convert (handles everything)
convert_to_hdf5('output.h5', flight);
```

### **Method 2: Explicit Conversion**
If you're writing HDF5 directly in MATLAB:

```matlab
% Ensure data is numeric (double precision)
data = double(your_data);  % Convert to float64

% Verify it's numeric
if ~isnumeric(data)
    error('Data must be numeric!');
end

% Write to HDF5
h5create('output.h5', '/flight_001/channels/accel_x', size(data));
h5write('output.h5', '/flight_001/channels/accel_x', data);

% Add attributes
h5writeatt('output.h5', '/flight_001/channels/accel_x', 'units', 'g');
h5writeatt('output.h5', '/flight_001/channels/accel_x', 'sample_rate', 1000.0);
h5writeatt('output.h5', '/flight_001/channels/accel_x', 'start_time', 0.0);
```

### **Method 3: Check and Convert**
```matlab
% Check data type
if iscell(your_data)
    error('Data is a cell array! Convert to numeric array.');
end

if isstruct(your_data)
    error('Data is a struct! Extract numeric fields.');
end

if ischar(your_data) || isstring(your_data)
    error('Data is text! Convert to numeric.');
end

% Convert to double (float64)
data = double(your_data);

% Verify shape (must be 1D)
if ~isvector(data)
    error('Data must be 1D vector! Reshape or separate into channels.');
end

% Ensure column vector
data = data(:);
```

---

## ✅ How to Fix in Python

### **Method 1: Explicit Numeric Conversion**
```python
import h5py
import numpy as np

# Ensure data is numeric
data = np.array(your_data, dtype=np.float64)  # Force float64

# Verify
assert np.issubdtype(data.dtype, np.number), "Data must be numeric!"
assert data.ndim == 1, "Data must be 1D!"

# Write to HDF5
with h5py.File('output.h5', 'w') as f:
    flight = f.create_group('flight_001')
    channels = flight.create_group('channels')
    
    channel = channels.create_dataset('accel_x', data=data)
    channel.attrs['units'] = 'g'
    channel.attrs['sample_rate'] = 1000.0
    channel.attrs['start_time'] = 0.0
```

### **Method 2: Convert Existing File**
If you already have an HDF5 file with wrong data types:

```python
import h5py
import numpy as np

# Open existing file
with h5py.File('input.h5', 'r') as f_in:
    with h5py.File('output_fixed.h5', 'w') as f_out:
        
        # Copy structure
        for flight_key in f_in.keys():
            if not flight_key.startswith('flight_'):
                continue
            
            flight_in = f_in[flight_key]
            flight_out = f_out.create_group(flight_key)
            
            # Copy metadata if exists
            if 'metadata' in flight_in:
                meta_out = flight_out.create_group('metadata')
                for attr_name, attr_value in flight_in['metadata'].attrs.items():
                    meta_out.attrs[attr_name] = attr_value
            
            # Convert channels
            if 'channels' in flight_in:
                channels_in = flight_in['channels']
                channels_out = flight_out.create_group('channels')
                
                for ch_name in channels_in.keys():
                    ch_in = channels_in[ch_name]
                    
                    # Convert data to float64
                    try:
                        data = np.array(ch_in[...], dtype=np.float64)
                        print(f"✓ Converted {ch_name}: {ch_in.dtype} → float64")
                    except Exception as e:
                        print(f"✗ Failed to convert {ch_name}: {e}")
                        continue
                    
                    # Create new channel with numeric data
                    ch_out = channels_out.create_dataset(ch_name, data=data)
                    
                    # Copy attributes
                    for attr_name, attr_value in ch_in.attrs.items():
                        ch_out.attrs[attr_name] = attr_value

print("Fixed file saved as: output_fixed.h5")
```

---

## 🔍 Validation After Fix

### **Step 1: Run Diagnostic**
```bash
python diagnose_hdf5.py output_fixed.h5
```

### **Step 2: Check for Numeric Data Types**
Look for:
```
✓ Data type: float64 (numeric)
✓ Sample values: [0.1 0.2 0.15 0.18 0.22]
```

### **Step 3: Load in SpectralEdge**
If diagnostic shows all numeric types, the file should load successfully.

---

## 📋 Quick Checklist

Use this to verify your data before saving:

### **In MATLAB**:
```
☐ Data is numeric (not cell array, struct, or string)
☐ Used double() to ensure float64
☐ Data is 1D vector
☐ No NaN or Inf values (or handle appropriately)
☐ Used convert_to_hdf5.m script (recommended)
```

### **In Python**:
```
☐ Used dtype=np.float64 or dtype=np.int32
☐ Verified with np.issubdtype(data.dtype, np.number)
☐ Data is 1D: data.ndim == 1
☐ No object, string, or structured dtypes
☐ No datetime or timedelta types
```

---

## 🎯 Valid Data Types

### **✅ VALID (will work)**:
- `float64` (double precision float)
- `float32` (single precision float)
- `int64` (64-bit integer)
- `int32` (32-bit integer)
- `int16` (16-bit integer)
- `uint64`, `uint32`, `uint16` (unsigned integers)

### **❌ INVALID (will cause error)**:
- `object` (Python objects, mixed types)
- `<U10`, `|S10` (strings)
- `[('field1', 'f8'), ...]` (structured arrays)
- `datetime64`, `timedelta64` (datetime types)
- `void` (raw binary data)

---

## 💡 Pro Tips

### **1. Always Use Explicit Type Conversion**
```python
# Don't rely on automatic conversion
data = np.array(your_data, dtype=np.float64)  # Explicit!
```

### **2. Validate Before Saving**
```python
assert np.issubdtype(data.dtype, np.number), "Must be numeric!"
assert data.ndim == 1, "Must be 1D!"
assert len(data) > 0, "Must have data!"
```

### **3. Use the Provided Scripts**
- MATLAB: `convert_to_hdf5.m` (handles everything)
- Python: `diagnose_hdf5.py` (validates before loading)

### **4. Check Sample Values**
The diagnostic script shows sample values to help identify issues:
```
✓ Sample values: [0.1 0.2 0.15 0.18 0.22]  ← Good
✗ Sample values: ['1.0' '2.0' '3.0']       ← Strings! Convert to numeric
```

---

## 📞 Still Having Issues?

If you've converted to numeric types but still see the error:

1. **Run diagnostic script** - it will show the exact data type
2. **Check for hidden non-numeric data** - sometimes only some channels have issues
3. **Verify with h5dump** - check the actual HDF5 structure:
   ```bash
   h5dump -d /flight_001/channels/your_channel your_file.h5 | head -20
   ```
4. **Try the Python conversion script** above to force numeric types

---

## 📚 Related Documentation

- **HDF5_QUICK_REFERENCE.md** - Quick reference for HDF5 format
- **HDF5_MANDATORY_FIELDS_CHECKLIST.md** - Complete requirements
- **matlab/README_MATLAB_CONVERSION.md** - MATLAB conversion guide
- **matlab/QUICK_START.md** - Quick start examples

---

## 🎯 Summary

**The Problem**: Non-numeric data types in HDF5 file

**The Solution**: Convert all channel data to numeric types (float64 or int32)

**The Tools**:
1. `diagnose_hdf5.py` - Identifies the exact issue
2. `convert_to_hdf5.m` - MATLAB script that handles conversion
3. Python conversion script (above) - Fixes existing files

**The Fix**:
```matlab
% MATLAB
data = double(your_data);  % Convert to float64
```

```python
# Python
data = np.array(your_data, dtype=np.float64)
```

Run the diagnostic script on your file to see exactly what needs to be fixed! 🚀
