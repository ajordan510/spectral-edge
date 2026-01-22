# Quick Start: MATLAB to HDF5 Conversion

Convert your MATLAB flight test data to SpectralEdge HDF5 format in 3 steps.

---

## Step 1: Prepare Data Structure

```matlab
% Required fields
flight.flight_id = 'Your_Flight_ID';
flight.channels.channel_name.data = your_signal_vector;
flight.channels.channel_name.sample_rate = 1000;  % Hz
flight.channels.channel_name.units = 'g';

% Optional but recommended
flight.date = '2025-01-22';
flight.channels.channel_name.start_time = 0.0;
flight.channels.channel_name.description = 'Channel description';
```

---

## Step 2: Convert to HDF5

```matlab
convert_to_hdf5('output.h5', flight);
```

---

## Step 3: Load in SpectralEdge

1. Run SpectralEdge: `run.bat`
2. Click "Load HDF5"
3. Select your `.h5` file
4. Choose flight and channels

---

## Complete Example

```matlab
% Load your data
load('my_test_data.mat');  % Contains: time, accel_x, accel_y, accel_z, fs

% Package into flight structure
flight.flight_id = 'Vibration_Test_001';
flight.date = '2025-01-22';
flight.description = 'Wing vibration test';

% X-axis
flight.channels.accel_x.data = accel_x;
flight.channels.accel_x.sample_rate = fs;
flight.channels.accel_x.units = 'g';
flight.channels.accel_x.start_time = 0.0;

% Y-axis
flight.channels.accel_y.data = accel_y;
flight.channels.accel_y.sample_rate = fs;
flight.channels.accel_y.units = 'g';
flight.channels.accel_y.start_time = 0.0;

% Z-axis
flight.channels.accel_z.data = accel_z;
flight.channels.accel_z.sample_rate = fs;
flight.channels.accel_z.units = 'g';
flight.channels.accel_z.start_time = 0.0;

% Convert
convert_to_hdf5('vibration_test.h5', flight);
```

---

## Multiple Flights

```matlab
% Flight 1
flights{1}.flight_id = 'Flight_001';
flights{1}.channels.accel_z.data = signal1;
flights{1}.channels.accel_z.sample_rate = 1000;
flights{1}.channels.accel_z.units = 'g';
flights{1}.channels.accel_z.start_time = 0.0;

% Flight 2
flights{2}.flight_id = 'Flight_002';
flights{2}.channels.accel_z.data = signal2;
flights{2}.channels.accel_z.sample_rate = 1000;
flights{2}.channels.accel_z.units = 'g';
flights{2}.channels.accel_z.start_time = 0.0;

% Convert
convert_to_hdf5('multiple_flights.h5', flights);
```

---

## Required Fields Summary

| Level | Field | Type | Example |
|-------|-------|------|---------|
| Flight | `flight_id` | string | `'Flight_001'` |
| Flight | `channels` | struct | `struct()` |
| Channel | `data` | 1D vector | `[1.2; 0.8; ...]` |
| Channel | `sample_rate` | scalar | `1000` |
| Channel | `units` | string | `'g'` |

---

## Common Units

- Acceleration: `'g'`, `'m/s^2'`
- Pressure: `'Pa'`, `'psi'`, `'bar'`
- Strain: `'με'`, `'mm/m'`
- Voltage: `'V'`, `'mV'`
- Force: `'N'`, `'lbf'`
- Temperature: `'°C'`, `'K'`

---

## Troubleshooting

**Error: "Data must be a numeric vector"**  
→ Ensure data is 1D: `data = data(:);`

**Error: "Sample rate must be positive"**  
→ Check: `sample_rate > 0`

**Error: "Missing required field: units"**  
→ Add: `flight.channels.name.units = 'g';`

---

## Need More Help?

- See `README_MATLAB_CONVERSION.md` for detailed documentation
- Run `example_conversion.m` for working examples
- Check `docs/` for SpectralEdge documentation
