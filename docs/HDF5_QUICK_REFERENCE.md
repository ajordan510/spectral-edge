# HDF5 Quick Reference for SpectralEdge

## 🚀 Quick Diagnostic

If your HDF5 file isn't loading, run this command:

```bash
cd SpectralEdge
python diagnose_hdf5.py your_file.h5
```

This will tell you exactly what's wrong and how to fix it.

---

## ✅ Minimum Required Structure

```
your_file.h5/
└── flight_001/                    ← Group starting with 'flight_'
    └── channels/                  ← Subgroup named 'channels'
        └── channel_name           ← Dataset (1D numeric array)
            └── attributes:
                - units: "g"       ← String
                - sample_rate: 1000.0  ← Float > 0
                - start_time: 0.0      ← Float
```

---

## 📋 Mandatory Requirements Checklist

### **File Structure**
- [ ] At least one group starting with `flight_` (lowercase)
- [ ] Each flight has `channels` subgroup (lowercase)
- [ ] Channels group contains at least one dataset

### **Channel Data**
- [ ] Each channel is a dataset (not a group)
- [ ] Data is 1D array: shape `(N,)` not `(N, 3)`
- [ ] Data is numeric (int or float)
- [ ] At least 1 sample (N ≥ 1)

### **Channel Attributes (all required)**
- [ ] `units` - string (e.g., `"g"`, `"m/s^2"`)
- [ ] `sample_rate` - float > 0 (e.g., `1000.0`)
- [ ] `start_time` - float (e.g., `0.0`)

---

## ❌ Common Mistakes

| Mistake | Wrong | Correct |
|---------|-------|---------|
| **Flight name** | `Flight_001`, `data` | `flight_001`, `flight_test_1` |
| **Channels location** | `flight_001/accel_x` | `flight_001/channels/accel_x` |
| **Channel type** | Group with sub-datasets | Dataset with data array |
| **Data shape** | 2D: `(N, 3)` | 1D: `(N,)` for each axis |
| **Attribute types** | `sample_rate = "1000"` | `sample_rate = 1000.0` |
| **Sample rate** | `0.0` or negative | Positive float |

---

## 🛠️ MATLAB Quick Fix

Use the provided conversion script:

```matlab
% Your data
flight.flight_id = 'Test_001';
flight.channels.accel_x.data = signal;
flight.channels.accel_x.sample_rate = 1000;
flight.channels.accel_x.units = 'g';
flight.channels.accel_x.start_time = 0.0;

% Convert (handles everything automatically)
convert_to_hdf5('output.h5', flight);
```

See `matlab/QUICK_START.md` for more examples.

---

## 🔍 Debugging Steps

1. **Run diagnostic**:
   ```bash
   python diagnose_hdf5.py your_file.h5
   ```

2. **Read error messages** - they tell you exactly what's wrong

3. **Fix issues** - follow the suggestions in the output

4. **Re-run diagnostic** to verify fixes

5. **Load in SpectralEdge**

---

## 📚 More Help

- **Detailed checklist**: `docs/HDF5_MANDATORY_FIELDS_CHECKLIST.md`
- **MATLAB conversion**: `matlab/README_MATLAB_CONVERSION.md`
- **MATLAB quick start**: `matlab/QUICK_START.md`
- **Validation guide**: `docs/HDF5_VALIDATION.md`

---

## 💡 Pro Tips

1. **Use the MATLAB script** - it handles formatting automatically
2. **Validate before loading** - run `diagnose_hdf5.py` first
3. **Check attribute types** - `1000.0` (float) not `"1000"` (string)
4. **Separate multi-axis data** - create `accel_x`, `accel_y`, `accel_z` not `accel[N,3]`
5. **Use lowercase** - `flight_001` and `channels` must be lowercase

---

## 🎯 If Nothing Shows Up

If you load an HDF5 file and nothing appears:

1. **Check terminal/console** - look for error messages
2. **Run diagnostic script** - it will find the issue
3. **Verify group names** - must start with `flight_` (lowercase)
4. **Check for `channels` subgroup** - must exist in each flight
5. **Verify attributes** - all three required (units, sample_rate, start_time)

The diagnostic script will tell you exactly what's missing!
