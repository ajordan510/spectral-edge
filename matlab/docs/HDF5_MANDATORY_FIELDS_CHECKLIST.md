# HDF5 Mandatory Fields Checklist

This document provides a complete checklist of all mandatory and optional fields required for SpectralEdge HDF5 files.

---

## 📋 Quick Checklist

Use this to verify your HDF5 file structure:

```
☐ File has at least one group starting with 'flight_'
☐ Each flight group has a 'channels' subgroup
☐ Each channel is a 1D dataset (not a group, not 2D/3D)
☐ Each channel has 'units' attribute (string)
☐ Each channel has 'sample_rate' attribute (float > 0)
☐ Each channel has 'start_time' attribute (float)
☐ Channel data is numeric (int or float)
☐ Channel data has at least 1 sample
```

---

## 🏗️ File Structure

### **Level 1: Root**
```
your_file.h5/
```

**Requirements**:
- ✅ **MANDATORY**: Must contain at least one group with name starting with `flight_`
- ⚠️ **IMPORTANT**: Group names MUST start with `flight_` (case-sensitive)
  - ✓ Valid: `flight_001`, `flight_002`, `flight_test_1`
  - ✗ Invalid: `Flight_001`, `FLIGHT_001`, `data`, `test`

---

### **Level 2: Flight Groups**
```
your_file.h5/
├── flight_001/          ← MANDATORY: Name must start with 'flight_'
├── flight_002/          ← Can have multiple flights
└── flight_003/
```

**Requirements**:
- ✅ **MANDATORY**: Group name must start with `flight_`
- ✅ **MANDATORY**: Must contain a `channels` subgroup
- ⭕ **OPTIONAL**: Can contain a `metadata` subgroup

---

### **Level 3a: Flight Metadata (OPTIONAL)**
```
flight_001/
└── metadata/            ← OPTIONAL but recommended
    └── attributes:
        - flight_id      ← OPTIONAL
        - date           ← OPTIONAL
        - duration       ← OPTIONAL
        - description    ← OPTIONAL
```

**Attributes** (all optional):

| Attribute | Type | Example | Description |
|-----------|------|---------|-------------|
| `flight_id` | string | `"Test_Flight_001"` | Flight identifier |
| `date` | string | `"2025-01-23"` | Flight date |
| `duration` | float | `120.5` | Flight duration in seconds |
| `description` | string | `"Vibration test"` | Flight description |

**Notes**:
- All flight metadata is **OPTIONAL**
- Recommended for better organization
- Does not affect data loading

---

### **Level 3b: Channels Group (MANDATORY)**
```
flight_001/
└── channels/            ← MANDATORY: Must exist and contain datasets
    ├── channel_1        ← MANDATORY: At least one channel
    ├── channel_2        ← Can have multiple channels
    └── channel_3
```

**Requirements**:
- ✅ **MANDATORY**: Group must be named exactly `channels` (lowercase)
- ✅ **MANDATORY**: Must contain at least one dataset
- ⚠️ **IMPORTANT**: Channels are DATASETS, not groups

---

### **Level 4: Channel Datasets (MANDATORY)**
```
channels/
└── accel_x              ← MANDATORY: Dataset (not a group!)
    ├── data: [1D array] ← MANDATORY: 1D numeric array
    └── attributes:      ← MANDATORY: All three required
        - units          ← MANDATORY: string
        - sample_rate    ← MANDATORY: float > 0
        - start_time     ← MANDATORY: float
        - description    ← OPTIONAL
        - sensor_id      ← OPTIONAL
        - location       ← OPTIONAL
        - range_min      ← OPTIONAL
        - range_max      ← OPTIONAL
```

**Data Requirements**:
- ✅ **MANDATORY**: Must be a dataset (not a group)
- ✅ **MANDATORY**: Must be 1D array with shape `(N,)` where N ≥ 1
- ✅ **MANDATORY**: Must be numeric type (int or float)
- ✗ **INVALID**: 2D arrays like `(N, 3)` - create separate channels instead
- ✗ **INVALID**: 0D scalars or empty arrays

**Mandatory Attributes**:

| Attribute | Type | Valid Values | Example | Description |
|-----------|------|--------------|---------|-------------|
| `units` | string | Any string | `"g"`, `"m/s^2"`, `"V"` | Physical units |
| `sample_rate` | float | Must be > 0 | `1000.0`, `40000.0` | Sampling rate in Hz |
| `start_time` | float | Any float | `0.0`, `10.5` | Start time in seconds |

**Optional Attributes**:

| Attribute | Type | Example | Description |
|-----------|------|---------|-------------|
| `description` | string | `"X-axis accelerometer"` | Channel description |
| `sensor_id` | string | `"ACCEL_001"` | Sensor identifier |
| `location` | string | `"Wing tip"` | Sensor location |
| `range_min` | float | `-10.0` | Minimum expected value |
| `range_max` | float | `10.0` | Maximum expected value |

---

## ✅ Complete Valid Example

### **Minimal Valid File** (only mandatory fields):
```
my_data.h5/
└── flight_001/
    └── channels/
        └── test_signal
            ├── data: [1.0, 2.0, 3.0, ...]  (1D array, N samples)
            └── attributes:
                - units: "g"
                - sample_rate: 1000.0
                - start_time: 0.0
```

### **Complete Valid File** (with optional fields):
```
my_data.h5/
├── flight_001/
│   ├── metadata/
│   │   └── attributes:
│   │       - flight_id: "Test_Flight_001"
│   │       - date: "2025-01-23"
│   │       - duration: 10.0
│   │       - description: "Vibration test"
│   │
│   └── channels/
│       ├── accel_x
│       │   ├── data: [0.1, 0.2, 0.15, ...]  (10000 samples)
│       │   └── attributes:
│       │       - units: "g"
│       │       - sample_rate: 1000.0
│       │       - start_time: 0.0
│       │       - description: "X-axis accelerometer"
│       │       - sensor_id: "ACCEL_001"
│       │       - location: "Wing tip"
│       │
│       ├── accel_y
│       │   ├── data: [0.05, 0.08, 0.06, ...]  (10000 samples)
│       │   └── attributes:
│       │       - units: "g"
│       │       - sample_rate: 1000.0
│       │       - start_time: 0.0
│       │       - description: "Y-axis accelerometer"
│       │
│       └── accel_z
│           ├── data: [1.0, 1.02, 0.98, ...]  (10000 samples)
│           └── attributes:
│               - units: "g"
│               - sample_rate: 1000.0
│               - start_time: 0.0
│               - description: "Z-axis accelerometer"
│
└── flight_002/
    ├── metadata/
    │   └── attributes:
    │       - flight_id: "Test_Flight_002"
    │       - date: "2025-01-23"
    │       - duration: 15.0
    │
    └── channels/
        └── pressure
            ├── data: [101.3, 101.4, 101.2, ...]  (15000 samples)
            └── attributes:
                - units: "kPa"
                - sample_rate: 1000.0
                - start_time: 0.0
```

---

## ❌ Common Mistakes

### **Mistake 1: Wrong Flight Group Name**
```
❌ WRONG:
my_data.h5/
└── Flight_001/          ← Capital 'F' - won't be recognized
└── data/                ← Doesn't start with 'flight_'
└── test/                ← Doesn't start with 'flight_'

✓ CORRECT:
my_data.h5/
└── flight_001/          ← Lowercase 'flight_'
└── flight_test_1/       ← Starts with 'flight_'
```

### **Mistake 2: Missing Channels Group**
```
❌ WRONG:
flight_001/
└── accel_x              ← Channel directly in flight group

✓ CORRECT:
flight_001/
└── channels/            ← Channels subgroup required
    └── accel_x
```

### **Mistake 3: Channels as Groups Instead of Datasets**
```
❌ WRONG:
channels/
└── accel_x/             ← Group (has subgroups/datasets)
    └── data             ← Data as sub-dataset

✓ CORRECT:
channels/
└── accel_x              ← Dataset (contains array directly)
    └── data: [array]
```

### **Mistake 4: 2D Data**
```
❌ WRONG:
accel.data = [[x1, y1, z1],
              [x2, y2, z2],
              [x3, y3, z3]]  ← Shape: (N, 3) - 2D array

✓ CORRECT:
accel_x.data = [x1, x2, x3, ...]  ← Shape: (N,) - 1D array
accel_y.data = [y1, y2, y3, ...]  ← Shape: (N,) - 1D array
accel_z.data = [z1, z2, z3, ...]  ← Shape: (N,) - 1D array
```

### **Mistake 5: Missing Required Attributes**
```
❌ WRONG:
channel.attrs['units'] = 'g'
# Missing sample_rate and start_time!

✓ CORRECT:
channel.attrs['units'] = 'g'
channel.attrs['sample_rate'] = 1000.0
channel.attrs['start_time'] = 0.0
```

### **Mistake 6: Wrong Attribute Types**
```
❌ WRONG:
channel.attrs['sample_rate'] = '1000'      ← String, not float
channel.attrs['sample_rate'] = 1000        ← Int, should be float
channel.attrs['units'] = 1.0               ← Float, should be string

✓ CORRECT:
channel.attrs['sample_rate'] = 1000.0      ← Float
channel.attrs['units'] = 'g'               ← String
channel.attrs['start_time'] = 0.0          ← Float
```

### **Mistake 7: Invalid Sample Rate**
```
❌ WRONG:
channel.attrs['sample_rate'] = 0.0         ← Zero
channel.attrs['sample_rate'] = -1000.0     ← Negative

✓ CORRECT:
channel.attrs['sample_rate'] = 1000.0      ← Positive
```

---

## 🔍 Field-by-Field Requirements

### **Flight Group Name**
- **Required**: YES
- **Type**: HDF5 Group
- **Naming**: Must start with `flight_` (lowercase)
- **Examples**: `flight_001`, `flight_002`, `flight_test_1`
- **Invalid**: `Flight_001`, `FLIGHT_001`, `data`, `test`

### **Channels Subgroup**
- **Required**: YES
- **Type**: HDF5 Group
- **Naming**: Must be exactly `channels` (lowercase)
- **Parent**: Flight group
- **Content**: Must contain at least one channel dataset

### **Channel Dataset**
- **Required**: YES (at least one per flight)
- **Type**: HDF5 Dataset
- **Shape**: Must be 1D array `(N,)` where N ≥ 1
- **Data Type**: Numeric (int or float)
- **Naming**: Any valid name (e.g., `accel_x`, `pressure`, `temperature`)

### **Channel Attribute: units**
- **Required**: YES
- **Type**: String
- **Valid Values**: Any string
- **Examples**: `"g"`, `"m/s^2"`, `"V"`, `"kPa"`, `"degC"`
- **Purpose**: Physical units of measurement

### **Channel Attribute: sample_rate**
- **Required**: YES
- **Type**: Float
- **Valid Values**: Must be > 0
- **Examples**: `1000.0`, `40000.0`, `100.0`
- **Purpose**: Sampling rate in Hz
- **Common Error**: Using int instead of float, or negative/zero values

### **Channel Attribute: start_time**
- **Required**: YES
- **Type**: Float
- **Valid Values**: Any float (typically 0.0)
- **Examples**: `0.0`, `10.5`, `100.0`
- **Purpose**: Start time of recording in seconds

### **Flight Metadata Group**
- **Required**: NO (optional but recommended)
- **Type**: HDF5 Group
- **Naming**: Must be exactly `metadata`
- **Parent**: Flight group
- **Content**: Attributes only (no datasets)

### **Flight Attribute: flight_id**
- **Required**: NO (optional)
- **Type**: String
- **Examples**: `"Test_Flight_001"`, `"Vibration_Test_20250123"`

### **Flight Attribute: date**
- **Required**: NO (optional)
- **Type**: String
- **Examples**: `"2025-01-23"`, `"2025-01-23 14:30:00"`

### **Flight Attribute: duration**
- **Required**: NO (optional)
- **Type**: Float
- **Examples**: `120.5`, `3600.0`
- **Purpose**: Flight duration in seconds

### **Flight Attribute: description**
- **Required**: NO (optional)
- **Type**: String
- **Examples**: `"Vibration test"`, `"Modal analysis"`

---

## 📝 Validation Checklist

Use this checklist to verify your file before loading:

### **Structure Checks**
```
☐ 1. File has at least one group starting with 'flight_'
☐ 2. Flight group name uses lowercase 'flight_' prefix
☐ 3. Each flight has a 'channels' subgroup (lowercase)
☐ 4. Channels group contains at least one dataset
☐ 5. Each channel is a dataset, not a group
```

### **Data Checks**
```
☐ 6. Each channel data is 1D array (shape: (N,))
☐ 7. Each channel has at least 1 sample (N ≥ 1)
☐ 8. Channel data is numeric (int or float, not string)
☐ 9. No 2D or 3D arrays (separate into individual channels)
```

### **Attribute Checks**
```
☐ 10. Each channel has 'units' attribute (string)
☐ 11. Each channel has 'sample_rate' attribute (float)
☐ 12. Each channel has 'start_time' attribute (float)
☐ 13. sample_rate is positive (> 0)
☐ 14. Attribute types are correct (not all strings)
```

---

## 🛠️ How to Check Your File

### **Method 1: Use Diagnostic Script**
```bash
cd SpectralEdge
python diagnose_hdf5.py your_file.h5
```

This will show you exactly what's in your file and what's missing.

### **Method 2: Use h5dump**
```bash
h5dump -n your_file.h5      # Show structure
h5dump -A your_file.h5      # Show attributes
```

### **Method 3: Python Inspection**
```python
import h5py

with h5py.File('your_file.h5', 'r') as f:
    # Check top-level groups
    print("Top-level groups:", list(f.keys()))
    
    # Check flight structure
    if 'flight_001' in f:
        flight = f['flight_001']
        print("Flight subgroups:", list(flight.keys()))
        
        # Check channels
        if 'channels' in flight:
            channels = flight['channels']
            print("Channels:", list(channels.keys()))
            
            # Check first channel
            if len(channels.keys()) > 0:
                channel_name = list(channels.keys())[0]
                channel = channels[channel_name]
                print(f"\n{channel_name}:")
                print(f"  Type: {type(channel)}")
                print(f"  Shape: {channel.shape}")
                print(f"  Attributes: {dict(channel.attrs)}")
```

---

## 💡 Quick Reference

### **Absolute Minimum Required**:
```
your_file.h5/
└── flight_001/                    ← Group starting with 'flight_'
    └── channels/                  ← Subgroup named 'channels'
        └── channel_name           ← Dataset (1D array)
            └── attributes:
                - units: string    ← Required
                - sample_rate: float > 0  ← Required
                - start_time: float       ← Required
```

### **Recommended Structure**:
```
your_file.h5/
└── flight_001/
    ├── metadata/                  ← Optional but helpful
    │   └── attributes:
    │       - flight_id
    │       - date
    │       - duration
    │       - description
    └── channels/
        └── channel_name
            ├── data: 1D array
            └── attributes:
                - units            ← Required
                - sample_rate      ← Required
                - start_time       ← Required
                - description      ← Optional
                - sensor_id        ← Optional
                - location         ← Optional
```

---

## 🎯 Summary

**MANDATORY (will fail without these)**:
1. At least one group starting with `flight_`
2. Each flight has `channels` subgroup
3. Each channel is a 1D dataset
4. Each channel has `units` attribute (string)
5. Each channel has `sample_rate` attribute (float > 0)
6. Each channel has `start_time` attribute (float)

**OPTIONAL (recommended but not required)**:
- Flight `metadata` group
- Flight attributes: `flight_id`, `date`, `duration`, `description`
- Channel attributes: `description`, `sensor_id`, `location`, `range_min`, `range_max`

**Use the diagnostic script** (`diagnose_hdf5.py`) to check your file!
