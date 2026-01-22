"""
Test script to verify HDF5 files created by MATLAB conversion script
match the structure expected by SpectralEdge.

This script can be used to validate HDF5 files before loading them
into SpectralEdge.

Usage:
    python test_hdf5_structure.py <hdf5_file>
"""

import h5py
import sys
import numpy as np


def validate_hdf5_file(filename):
    """Validate HDF5 file structure for SpectralEdge compatibility."""
    
    print(f"\n{'='*60}")
    print(f"Validating: {filename}")
    print(f"{'='*60}\n")
    
    try:
        with h5py.File(filename, 'r') as f:
            # Find all flight groups
            flights = [key for key in f.keys() if key.startswith('flight_')]
            
            if not flights:
                print("❌ ERROR: No flight groups found (must start with 'flight_')")
                return False
            
            print(f"✓ Found {len(flights)} flight(s)")
            
            all_valid = True
            
            for flight_key in flights:
                print(f"\n--- {flight_key} ---")
                flight_group = f[flight_key]
                
                # Check metadata
                if 'metadata' in flight_group:
                    meta = flight_group['metadata']
                    print(f"  Metadata:")
                    for attr_name in meta.attrs:
                        print(f"    {attr_name}: {meta.attrs[attr_name]}")
                else:
                    print(f"  ⚠ Warning: No metadata group")
                
                # Check channels
                if 'channels' not in flight_group:
                    print(f"  ❌ ERROR: No 'channels' group found")
                    all_valid = False
                    continue
                
                channels_group = flight_group['channels']
                channel_names = list(channels_group.keys())
                
                if not channel_names:
                    print(f"  ❌ ERROR: No channels found")
                    all_valid = False
                    continue
                
                print(f"  ✓ Found {len(channel_names)} channel(s)")
                
                for channel_name in channel_names:
                    channel = channels_group[channel_name]
                    
                    # Check it's a dataset
                    if not isinstance(channel, h5py.Dataset):
                        print(f"    ❌ {channel_name}: Not a dataset")
                        all_valid = False
                        continue
                    
                    # Check data shape
                    if len(channel.shape) != 1:
                        print(f"    ❌ {channel_name}: Data must be 1D (shape: {channel.shape})")
                        all_valid = False
                        continue
                    
                    # Check required attributes
                    required_attrs = ['units', 'sample_rate', 'start_time']
                    missing_attrs = []
                    
                    for attr in required_attrs:
                        if attr not in channel.attrs:
                            missing_attrs.append(attr)
                    
                    if missing_attrs:
                        print(f"    ❌ {channel_name}: Missing attributes: {missing_attrs}")
                        all_valid = False
                        continue
                    
                    # Get attributes
                    units = channel.attrs['units']
                    sample_rate = channel.attrs['sample_rate']
                    start_time = channel.attrs['start_time']
                    
                    # Validate sample rate
                    if sample_rate <= 0:
                        print(f"    ❌ {channel_name}: Sample rate must be positive ({sample_rate})")
                        all_valid = False
                        continue
                    
                    # Calculate duration
                    n_samples = channel.shape[0]
                    duration = n_samples / sample_rate
                    
                    print(f"    ✓ {channel_name}:")
                    print(f"        Samples: {n_samples:,}")
                    print(f"        Sample rate: {sample_rate:.0f} Hz")
                    print(f"        Duration: {duration:.2f} s")
                    print(f"        Units: {units}")
                    print(f"        Start time: {start_time:.2f} s")
                    
                    # Optional attributes
                    optional_attrs = ['description', 'sensor_id', 'location']
                    for attr in optional_attrs:
                        if attr in channel.attrs:
                            print(f"        {attr.capitalize()}: {channel.attrs[attr]}")
            
            print(f"\n{'='*60}")
            if all_valid:
                print("✓ File structure is VALID for SpectralEdge")
            else:
                print("❌ File structure has ERRORS")
            print(f"{'='*60}\n")
            
            return all_valid
            
    except Exception as e:
        print(f"\n❌ ERROR reading file: {e}\n")
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_hdf5_structure.py <hdf5_file>")
        sys.exit(1)
    
    filename = sys.argv[1]
    valid = validate_hdf5_file(filename)
    
    sys.exit(0 if valid else 1)
