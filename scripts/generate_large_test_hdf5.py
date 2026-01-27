"""
Generate Large Test HDF5 File for Navigator Testing

This script creates a realistic large HDF5 file with:
- 7 flights
- ~150 channels total (20-25 channels per flight)
- Multiple sensor types: Accelerometers, Microphones, Strain Gages, Pressure, Temperature
- Various locations: Forward bulkhead, Wing root, Tail section, Fuselage stations, etc.
- Different sample rates: 10 Hz to 51.2 kHz
- Comprehensive metadata including location information
- Variable time ranges per channel

Usage:
    python scripts/generate_large_test_hdf5.py

Output:
    data/large_test_flight_data.hdf5 (~500MB file with 7 flights, 150 channels)

Author: SpectralEdge Development Team
Date: 2026-01-27
"""

import h5py
import numpy as np
import os
from datetime import datetime, timedelta


def generate_signal(duration, sample_rate, frequencies, amplitudes, noise_level=0.1):
    """
    Generate a synthetic signal with multiple frequency components and noise.
    
    Parameters:
    -----------
    duration : float
        Signal duration in seconds
    sample_rate : float
        Sample rate in Hz
    frequencies : list of float
        List of frequency components to include (Hz)
    amplitudes : list of float
        List of amplitudes for each frequency component
    noise_level : float
        Standard deviation of Gaussian noise to add
    
    Returns:
    --------
    time : ndarray
        Time vector
    signal : ndarray
        Generated signal
    """
    num_samples = int(duration * sample_rate)
    time = np.linspace(0, duration, num_samples, endpoint=False)
    
    # Initialize signal with noise
    signal = np.random.normal(0, noise_level, num_samples)
    
    # Add frequency components
    for freq, amp in zip(frequencies, amplitudes):
        signal += amp * np.sin(2 * np.pi * freq * time)
    
    return time, signal


def create_flight_data(h5file, flight_id, flight_num, duration, date_str, channel_configs):
    """
    Create data for a single flight in the HDF5 file.
    
    Parameters:
    -----------
    h5file : h5py.File
        Open HDF5 file object
    flight_id : str
        Flight identifier (e.g., "FT-001")
    flight_num : int
        Flight number
    duration : float
        Flight duration in seconds
    date_str : str
        Flight date string
    channel_configs : list of dict
        List of channel configurations
    """
    print(f"  Creating {flight_id} with {len(channel_configs)} channels...")
    
    # Create flight group
    flight_group = h5file.create_group(f'flight_{flight_num:03d}')
    
    # Add flight metadata
    meta_group = flight_group.create_group('metadata')
    meta_group.attrs['flight_id'] = flight_id
    meta_group.attrs['date'] = date_str
    meta_group.attrs['duration'] = duration
    meta_group.attrs['description'] = f'Test flight {flight_num} - Vibration and acoustic characterization'
    meta_group.attrs['vehicle'] = 'Test Vehicle Alpha'
    meta_group.attrs['test_type'] = 'Vibration and acoustic characterization'
    
    # Create channels group
    channels_group = flight_group.create_group('channels')
    
    # Create each channel
    for config in channel_configs:
        # Generate signal data
        time, data = generate_signal(
            config['duration'],
            config['sample_rate'],
            config['frequencies'],
            config['amplitudes'],
            config['noise']
        )
        
        # Create channel group
        channel_group = channels_group.create_group(config['name'])
        
        # Store time and data
        channel_group.create_dataset('time', data=time, compression='gzip', compression_opts=4)
        channel_group.create_dataset('data', data=data, compression='gzip', compression_opts=4)
        
        # Add channel metadata
        channel_group.attrs['units'] = config['units']
        channel_group.attrs['sample_rate'] = config['sample_rate']
        channel_group.attrs['start_time'] = config['start_time']
        channel_group.attrs['description'] = config['description']
        channel_group.attrs['sensor_id'] = config['sensor_id']
        channel_group.attrs['range_min'] = config['range_min']
        channel_group.attrs['range_max'] = config['range_max']
        channel_group.attrs['location'] = config['location']


def main():
    """Generate large test HDF5 file."""
    print("=" * 80)
    print("Generating Large Test HDF5 File")
    print("=" * 80)
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    output_file = 'data/large_test_flight_data.hdf5'
    
    # Define locations
    locations = [
        'Forward bulkhead',
        'Wing root left',
        'Wing root right',
        'Tail section',
        'Fuselage station 10',
        'Fuselage station 20',
        'Fuselage station 30',
        'Engine mount left',
        'Engine mount right',
        'Landing gear bay',
        'Cockpit',
        'Cargo bay'
    ]
    
    # Define sensor configurations for each flight
    # Each flight has slightly different channels to simulate real scenarios
    base_date = datetime(2025, 1, 15)
    
    with h5py.File(output_file, 'w') as h5file:
        # Add file-level metadata
        meta_group = h5file.create_group('metadata')
        meta_group.attrs['created'] = datetime.now().isoformat()
        meta_group.attrs['version'] = '1.0'
        meta_group.attrs['description'] = 'Large test dataset for SpectralEdge navigator testing'
        
        # Create 7 flights
        for flight_num in range(1, 8):
            flight_id = f'FT-{flight_num:03d}'
            date_str = (base_date + timedelta(days=flight_num*3)).strftime('%Y-%m-%d')
            duration = 200.0 + flight_num * 20  # Varying durations
            
            # Define channels for this flight
            channel_configs = []
            
            # High-rate accelerometers (3 per location, 3 locations)
            accel_locations = ['Forward bulkhead', 'Wing root left', 'Tail section']
            for loc_idx, location in enumerate(accel_locations):
                for axis in range(3):
                    axis_name = ['x', 'y', 'z'][axis]
                    freq_offset = axis * 5
                    channel_configs.append({
                        'name': f'accelerometer_{axis_name}_{loc_idx+1}',
                        'duration': duration - flight_num * 2,  # Variable end times
                        'start_time': flight_num * 0.5,  # Variable start times
                        'sample_rate': 40000.0,
                        'units': 'g',
                        'frequencies': [10+freq_offset, 60+freq_offset, 120+freq_offset, 500+freq_offset],
                        'amplitudes': [0.5, 1.0, 0.8, 0.3],
                        'noise': 0.05,
                        'description': f'{axis_name.upper()}-axis acceleration',
                        'sensor_id': f'ACC-{axis_name.upper()}-{loc_idx+1:03d}',
                        'range_min': -50.0,
                        'range_max': 50.0,
                        'location': location
                    })
            
            # Microphones (2 per location, 2 locations)
            mic_locations = ['Cockpit', 'Engine mount left']
            for loc_idx, location in enumerate(mic_locations):
                for mic_num in range(1, 3):
                    channel_configs.append({
                        'name': f'microphone_{loc_idx*2+mic_num}',
                        'duration': duration - flight_num,
                        'start_time': flight_num * 0.3,
                        'sample_rate': 51200.0,
                        'units': 'Pa',
                        'frequencies': [100, 500, 1000, 2000, 5000],
                        'amplitudes': [10.0, 20.0, 15.0, 8.0, 5.0],
                        'noise': 1.0,
                        'description': f'Acoustic pressure microphone {loc_idx*2+mic_num}',
                        'sensor_id': f'MIC-{loc_idx*2+mic_num:03d}',
                        'range_min': -1000.0,
                        'range_max': 1000.0,
                        'location': location
                    })
            
            # Strain gages (1 per location, 4 locations)
            strain_locations = ['Wing root left', 'Wing root right', 'Fuselage station 10', 'Landing gear bay']
            for loc_idx, location in enumerate(strain_locations):
                channel_configs.append({
                    'name': f'strain_gage_{loc_idx+1}',
                    'duration': duration,
                    'start_time': 0.0,
                    'sample_rate': 1000.0,
                    'units': 'με',
                    'frequencies': [5, 10, 20],
                    'amplitudes': [100.0, 50.0, 30.0],
                    'noise': 5.0,
                    'description': f'Strain gage {loc_idx+1}',
                    'sensor_id': f'STR-{loc_idx+1:03d}',
                    'range_min': -5000.0,
                    'range_max': 5000.0,
                    'location': location
                })
            
            # Pressure sensors (1 per location, 3 locations)
            pressure_locations = ['Engine mount left', 'Engine mount right', 'Cargo bay']
            for loc_idx, location in enumerate(pressure_locations):
                channel_configs.append({
                    'name': f'pressure_{loc_idx+1}',
                    'duration': duration - 5,
                    'start_time': 2.0,
                    'sample_rate': 100.0,
                    'units': 'psi',
                    'frequencies': [1, 5],
                    'amplitudes': [5.0, 2.0],
                    'noise': 0.5,
                    'description': f'Pressure sensor {loc_idx+1}',
                    'sensor_id': f'PRS-{loc_idx+1:03d}',
                    'range_min': 0.0,
                    'range_max': 100.0,
                    'location': location
                })
            
            # Temperature sensors (1 per location, 2 locations)
            temp_locations = ['Engine mount left', 'Cargo bay']
            for loc_idx, location in enumerate(temp_locations):
                channel_configs.append({
                    'name': f'temperature_{loc_idx+1}',
                    'duration': duration,
                    'start_time': 0.0,
                    'sample_rate': 10.0,
                    'units': '°C',
                    'frequencies': [0.1],
                    'amplitudes': [5.0],
                    'noise': 0.2,
                    'description': f'Temperature sensor {loc_idx+1}',
                    'sensor_id': f'TMP-{loc_idx+1:03d}',
                    'range_min': -40.0,
                    'range_max': 150.0,
                    'location': location
                })
            
            # Create the flight with all channels
            create_flight_data(h5file, flight_id, flight_num, duration, date_str, channel_configs)
            print(f"    ✓ Created {len(channel_configs)} channels")
    
    # Get file size
    file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
    
    print("=" * 80)
    print(f"✓ Successfully created: {output_file}")
    print(f"  File size: {file_size_mb:.1f} MB")
    print(f"  Flights: 7")
    print(f"  Channels per flight: ~{len(channel_configs)}")
    print(f"  Total channels: ~{7 * len(channel_configs)}")
    print("=" * 80)


if __name__ == '__main__':
    main()
