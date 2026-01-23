"""
Test script to demonstrate HDF5 validation capabilities.

This script creates various HDF5 files with different format issues
to demonstrate the validation and diagnostic messages.
"""

import h5py
import numpy as np
from spectral_edge.utils.hdf5_loader import HDF5FlightDataLoader, HDF5ValidationError


def create_valid_hdf5(filename):
    """Create a valid HDF5 file."""
    print(f"\n{'='*60}")
    print(f"Creating VALID HDF5 file: {filename}")
    print(f"{'='*60}")
    
    with h5py.File(filename, 'w') as f:
        # Create flight group
        flight = f.create_group('flight_001')
        
        # Add metadata
        meta = flight.create_group('metadata')
        meta.attrs['flight_id'] = 'Test_Flight_001'
        meta.attrs['date'] = '2025-01-23'
        meta.attrs['duration'] = 10.0
        meta.attrs['description'] = 'Test flight'
        
        # Create channels group
        channels = flight.create_group('channels')
        
        # Add channel
        fs = 1000
        duration = 10
        signal = np.sin(2*np.pi*50*np.arange(0, duration, 1/fs))
        
        channel = channels.create_dataset('test_signal', data=signal)
        channel.attrs['units'] = 'g'
        channel.attrs['sample_rate'] = fs
        channel.attrs['start_time'] = 0.0
        channel.attrs['description'] = 'Test signal'
    
    print(f"✓ Created valid HDF5 file")


def create_invalid_no_flight_groups(filename):
    """Create HDF5 with no flight groups."""
    print(f"\n{'='*60}")
    print(f"Creating INVALID HDF5 (no flight groups): {filename}")
    print(f"{'='*60}")
    
    with h5py.File(filename, 'w') as f:
        # Create wrong group name
        data_group = f.create_group('data')
        signal = np.random.randn(1000)
        data_group.create_dataset('signal', data=signal)
    
    print(f"✓ Created invalid file (no flight_ groups)")


def create_invalid_no_channels(filename):
    """Create HDF5 with flight but no channels group."""
    print(f"\n{'='*60}")
    print(f"Creating INVALID HDF5 (no channels group): {filename}")
    print(f"{'='*60}")
    
    with h5py.File(filename, 'w') as f:
        # Create flight but no channels
        flight = f.create_group('flight_001')
        meta = flight.create_group('metadata')
        meta.attrs['flight_id'] = 'Test'
    
    print(f"✓ Created invalid file (no channels group)")


def create_invalid_2d_data(filename):
    """Create HDF5 with 2D channel data."""
    print(f"\n{'='*60}")
    print(f"Creating INVALID HDF5 (2D data): {filename}")
    print(f"{'='*60}")
    
    with h5py.File(filename, 'w') as f:
        flight = f.create_group('flight_001')
        meta = flight.create_group('metadata')
        meta.attrs['flight_id'] = 'Test'
        
        channels = flight.create_group('channels')
        
        # Create 2D data (wrong!)
        signal_2d = np.random.randn(1000, 3)
        channel = channels.create_dataset('accel', data=signal_2d)
        channel.attrs['units'] = 'g'
        channel.attrs['sample_rate'] = 1000.0
        channel.attrs['start_time'] = 0.0
    
    print(f"✓ Created invalid file (2D data)")


def create_invalid_missing_attrs(filename):
    """Create HDF5 with missing required attributes."""
    print(f"\n{'='*60}")
    print(f"Creating INVALID HDF5 (missing attributes): {filename}")
    print(f"{'='*60}")
    
    with h5py.File(filename, 'w') as f:
        flight = f.create_group('flight_001')
        meta = flight.create_group('metadata')
        meta.attrs['flight_id'] = 'Test'
        
        channels = flight.create_group('channels')
        
        signal = np.random.randn(1000)
        channel = channels.create_dataset('test_signal', data=signal)
        # Missing units, sample_rate, start_time!
    
    print(f"✓ Created invalid file (missing attributes)")


def create_invalid_bad_sample_rate(filename):
    """Create HDF5 with invalid sample rate."""
    print(f"\n{'='*60}")
    print(f"Creating INVALID HDF5 (bad sample rate): {filename}")
    print(f"{'='*60}")
    
    with h5py.File(filename, 'w') as f:
        flight = f.create_group('flight_001')
        meta = flight.create_group('metadata')
        meta.attrs['flight_id'] = 'Test'
        
        channels = flight.create_group('channels')
        
        signal = np.random.randn(1000)
        channel = channels.create_dataset('test_signal', data=signal)
        channel.attrs['units'] = 'g'
        channel.attrs['sample_rate'] = -1000.0  # Negative!
        channel.attrs['start_time'] = 0.0
    
    print(f"✓ Created invalid file (negative sample rate)")


def test_validation(filename, should_pass=True):
    """Test validation on a file."""
    print(f"\n{'='*60}")
    print(f"TESTING: {filename}")
    print(f"Expected: {'PASS' if should_pass else 'FAIL'}")
    print(f"{'='*60}")
    
    try:
        loader = HDF5FlightDataLoader(filename, verbose=True)
        print(f"\n✓ File loaded successfully")
        
        # Print summary
        flights = loader.get_flights()
        print(f"\nSummary:")
        print(f"  Flights: {len(flights)}")
        for flight in flights:
            channels = loader.get_channels(flight.flight_key)
            print(f"    {flight.flight_key}: {len(channels)} channels")
        
        loader.close()
        
        if not should_pass:
            print(f"\n⚠ WARNING: Expected this to fail but it passed!")
        
    except HDF5ValidationError as e:
        print(f"\n❌ Validation failed (as expected):")
        print(f"{str(e)}")
        
        if should_pass:
            print(f"\n⚠ WARNING: Expected this to pass but it failed!")
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


if __name__ == '__main__':
    import os
    import tempfile
    
    # Create temp directory for test files
    test_dir = tempfile.mkdtemp(prefix='hdf5_validation_test_')
    print(f"\nTest files will be created in: {test_dir}")
    
    # Create test files
    valid_file = os.path.join(test_dir, 'valid.h5')
    no_flights_file = os.path.join(test_dir, 'no_flights.h5')
    no_channels_file = os.path.join(test_dir, 'no_channels.h5')
    data_2d_file = os.path.join(test_dir, 'data_2d.h5')
    missing_attrs_file = os.path.join(test_dir, 'missing_attrs.h5')
    bad_sample_rate_file = os.path.join(test_dir, 'bad_sample_rate.h5')
    
    # Create files
    create_valid_hdf5(valid_file)
    create_invalid_no_flight_groups(no_flights_file)
    create_invalid_no_channels(no_channels_file)
    create_invalid_2d_data(data_2d_file)
    create_invalid_missing_attrs(missing_attrs_file)
    create_invalid_bad_sample_rate(bad_sample_rate_file)
    
    # Test validation
    print(f"\n\n{'#'*60}")
    print(f"# VALIDATION TESTS")
    print(f"{'#'*60}")
    
    test_validation(valid_file, should_pass=True)
    test_validation(no_flights_file, should_pass=False)
    test_validation(no_channels_file, should_pass=False)
    test_validation(data_2d_file, should_pass=False)
    test_validation(missing_attrs_file, should_pass=False)
    test_validation(bad_sample_rate_file, should_pass=False)
    
    print(f"\n\n{'='*60}")
    print(f"VALIDATION TESTS COMPLETE")
    print(f"{'='*60}")
    print(f"\nTest files location: {test_dir}")
    print(f"You can inspect these files with: h5dump <filename>")
    print(f"\nTo clean up: rm -rf {test_dir}")
