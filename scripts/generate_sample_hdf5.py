"""
Generate sample HDF5 flight test data file.

This script creates a realistic HDF5 file structure for testing the SpectralEdge
tool with large multi-flight datasets. The structure follows aerospace flight test
data conventions with multiple flights, channels at different sample rates, and
comprehensive metadata.

Usage:
    python scripts/generate_sample_hdf5.py

Output:
    data/sample_flight_data.hdf5 (~5GB file with 2 flights)

Author: SpectralEdge Development Team
Date: 2025-01-21
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
    # Create time vector
    num_samples = int(duration * sample_rate)
    time = np.linspace(0, duration, num_samples, endpoint=False)
    
    # Initialize signal with noise
    signal = np.random.normal(0, noise_level, num_samples)
    
    # Add frequency components
    for freq, amp in zip(frequencies, amplitudes):
        signal += amp * np.sin(2 * np.pi * freq * time)
    
    # Add some transient events (simulating shocks or vibration events)
    num_events = int(duration / 30)  # One event every 30 seconds
    for _ in range(num_events):
        event_time = np.random.uniform(0, duration)
        event_idx = int(event_time * sample_rate)
        event_duration = int(0.5 * sample_rate)  # 0.5 second event
        
        if event_idx + event_duration < num_samples:
            # Add a decaying sinusoid (shock response)
            event_time_vec = np.arange(event_duration) / sample_rate
            decay = np.exp(-5 * event_time_vec)
            event_signal = 5.0 * np.sin(2 * np.pi * 200 * event_time_vec) * decay
            signal[event_idx:event_idx+event_duration] += event_signal
    
    return time, signal


def create_flight_data(h5file, flight_id, flight_num, duration, date_str):
    """
    Create data for a single flight in the HDF5 file.
    
    Parameters:
    -----------
    h5file : h5py.File
        Open HDF5 file object
    flight_id : str
        Flight identifier (e.g., "FT-001")
    flight_num : int
        Flight number (used for varying parameters)
    duration : float
        Flight duration in seconds
    date_str : str
        Flight date string
    """
    print(f"  Creating {flight_id}...")
    
    # Create flight group
    flight_group = h5file.create_group(f'flight_{flight_num:03d}')
    
    # Add flight metadata
    meta_group = flight_group.create_group('metadata')
    meta_group.attrs['flight_id'] = flight_id
    meta_group.attrs['date'] = date_str
    meta_group.attrs['duration'] = duration
    meta_group.attrs['description'] = f'Test flight {flight_num}'
    meta_group.attrs['vehicle'] = 'Test Vehicle Alpha'
    meta_group.attrs['test_type'] = 'Vibration characterization'
    
    # Create channels group
    channels_group = flight_group.create_group('channels')
    
    # Define channel configurations
    # Each flight has slightly different instrumentation to simulate real scenarios
    channel_configs = [
        # High-rate accelerometers (always present)
        {
            'name': 'accelerometer_x',
            'sample_rate': 40000.0,
            'units': 'g',
            'frequencies': [10, 60, 120, 500, 1000],
            'amplitudes': [0.5, 1.0, 0.8, 0.3, 0.2],
            'noise': 0.05,
            'description': 'X-axis acceleration',
            'sensor_id': 'ACC-X-001',
            'range_min': -50.0,
            'range_max': 50.0,
            'location': 'Forward bulkhead'
        },
        {
            'name': 'accelerometer_y',
            'sample_rate': 40000.0,
            'units': 'g',
            'frequencies': [15, 65, 125, 550, 1100],
            'amplitudes': [0.6, 0.9, 0.7, 0.4, 0.25],
            'noise': 0.05,
            'description': 'Y-axis acceleration',
            'sensor_id': 'ACC-Y-001',
            'range_min': -50.0,
            'range_max': 50.0,
            'location': 'Forward bulkhead'
        },
        {
            'name': 'accelerometer_z',
            'sample_rate': 40000.0,
            'units': 'g',
            'frequencies': [12, 62, 122, 520, 1050],
            'amplitudes': [0.7, 1.1, 0.9, 0.35, 0.22],
            'noise': 0.05,
            'description': 'Z-axis acceleration',
            'sensor_id': 'ACC-Z-001',
            'range_min': -50.0,
            'range_max': 50.0,
            'location': 'Forward bulkhead'
        },
        # Medium-rate pressure sensors
        {
            'name': 'pressure_1',
            'sample_rate': 10000.0,
            'units': 'psi',
            'frequencies': [5, 20, 100],
            'amplitudes': [50.0, 20.0, 5.0],
            'noise': 2.0,
            'description': 'Chamber pressure',
            'sensor_id': 'PRES-001',
            'range_min': 0.0,
            'range_max': 1000.0,
            'location': 'Combustion chamber'
        },
        # Low-rate temperature sensors
        {
            'name': 'temperature_1',
            'sample_rate': 100.0,
            'units': 'degC',
            'frequencies': [0.1, 0.5],
            'amplitudes': [10.0, 5.0],
            'noise': 0.5,
            'description': 'Skin temperature',
            'sensor_id': 'TEMP-001',
            'range_min': -50.0,
            'range_max': 200.0,
            'location': 'Outer skin'
        },
    ]
    
    # Add flight-specific channels
    if flight_num == 2:
        # Flight 2 has an additional accelerometer
        channel_configs.append({
            'name': 'accelerometer_aft',
            'sample_rate': 40000.0,
            'units': 'g',
            'frequencies': [11, 61, 121, 510, 1020],
            'amplitudes': [0.55, 1.05, 0.85, 0.32, 0.21],
            'noise': 0.05,
            'description': 'Aft section acceleration',
            'sensor_id': 'ACC-AFT-001',
            'range_min': -50.0,
            'range_max': 50.0,
            'location': 'Aft bulkhead'
        })
    
    # Generate data for each channel
    for config in channel_configs:
        print(f"    Generating {config['name']} ({config['sample_rate']} Hz)...")
        
        # Generate signal
        time, signal = generate_signal(
            duration,
            config['sample_rate'],
            config['frequencies'],
            config['amplitudes'],
            config['noise']
        )
        
        # Create channel group
        channel_group = channels_group.create_group(config['name'])
        
        # Determine chunk size (10 seconds of data)
        chunk_size = int(10 * config['sample_rate'])
        
        # Create datasets with chunking and compression
        # Using GZIP compression level 4 (good balance of speed and compression)
        data_dataset = channel_group.create_dataset(
            'data',
            data=signal,
            chunks=(chunk_size,),
            compression='gzip',
            compression_opts=4
        )
        
        time_dataset = channel_group.create_dataset(
            'time',
            data=time,
            chunks=(chunk_size,),
            compression='gzip',
            compression_opts=4
        )
        
        # Add channel metadata as attributes
        channel_group.attrs['units'] = config['units']
        channel_group.attrs['sample_rate'] = config['sample_rate']
        channel_group.attrs['start_time'] = 0.0
        channel_group.attrs['description'] = config['description']
        channel_group.attrs['sensor_id'] = config['sensor_id']
        channel_group.attrs['range_min'] = config['range_min']
        channel_group.attrs['range_max'] = config['range_max']
        channel_group.attrs['location'] = config['location']
        channel_group.attrs['calibration_date'] = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=5)).strftime('%Y-%m-%d')


def create_sample_hdf5_file(output_path, num_flights=2, duration_per_flight=450.0):
    """
    Create a sample HDF5 file with multiple flights.
    
    Parameters:
    -----------
    output_path : str
        Path to output HDF5 file
    num_flights : int
        Number of flights to generate
    duration_per_flight : float
        Duration of each flight in seconds
    """
    print(f"Creating sample HDF5 file: {output_path}")
    print(f"  Flights: {num_flights}")
    print(f"  Duration per flight: {duration_per_flight} seconds")
    print(f"  This will take several minutes and create a ~5GB file...\n")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Create HDF5 file
    with h5py.File(output_path, 'w') as h5file:
        # Add file-level metadata
        meta_group = h5file.create_group('metadata')
        meta_group.attrs['file_version'] = '1.0'
        meta_group.attrs['created_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        meta_group.attrs['description'] = 'Sample flight test data for SpectralEdge'
        meta_group.attrs['organization'] = 'Test Organization'
        meta_group.attrs['project'] = 'Vehicle Development Program'
        
        # Generate flights
        base_date = datetime(2025, 1, 15)
        for i in range(num_flights):
            flight_id = f"FT-{i+1:03d}"
            flight_date = (base_date + timedelta(days=i*5)).strftime('%Y-%m-%d')
            
            create_flight_data(
                h5file,
                flight_id,
                i + 1,
                duration_per_flight,
                flight_date
            )
        
        # Add common channels mapping (for cross-flight comparison)
        common_channels = {
            'accelerometer_x': ['flight_001/channels/accelerometer_x', 'flight_002/channels/accelerometer_x'],
            'accelerometer_y': ['flight_001/channels/accelerometer_y', 'flight_002/channels/accelerometer_y'],
            'accelerometer_z': ['flight_001/channels/accelerometer_z', 'flight_002/channels/accelerometer_z'],
            'pressure_1': ['flight_001/channels/pressure_1', 'flight_002/channels/pressure_1'],
            'temperature_1': ['flight_001/channels/temperature_1', 'flight_002/channels/temperature_1'],
        }
        
        # Store as JSON string in dataset
        import json
        mapping_str = json.dumps(common_channels, indent=2)
        h5file.create_dataset('common_channels_mapping', data=mapping_str)
    
    # Get file size
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"\n✓ Sample HDF5 file created successfully!")
    print(f"  File: {output_path}")
    print(f"  Size: {file_size_mb:.1f} MB")
    print(f"\nYou can now load this file in SpectralEdge to test HDF5 functionality.")


if __name__ == '__main__':
    # Output path
    output_path = 'data/sample_flight_data.hdf5'
    
    # Generate sample file
    # Note: Using shorter duration for faster generation during testing
    # Change to 450.0 for full 5GB file
    create_sample_hdf5_file(
        output_path,
        num_flights=2,
        duration_per_flight=100.0  # Use 450.0 for full-size file
    )
