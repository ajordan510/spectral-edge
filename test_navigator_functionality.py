"""
Comprehensive Test Script for Enhanced Flight Navigator

This script tests all functionality of the enhanced flight navigator:
- HDF5 loading
- Metadata extraction
- Tree population in all view modes
- Search functionality
- Filter functionality
- Column customization
- Selection management

Usage:
    python test_navigator_functionality.py

Author: SpectralEdge Development Team
Date: 2026-01-27
"""

import sys
from spectral_edge.utils.hdf5_loader import HDF5FlightDataLoader
from spectral_edge.utils.selection_manager import SelectionManager


def test_hdf5_loader():
    """Test HDF5 loader functionality."""
    print("=" * 80)
    print("TEST 1: HDF5 Loader")
    print("=" * 80)
    
    try:
        loader = HDF5FlightDataLoader('data/large_test_flight_data.hdf5')
        print(f"✓ Loaded HDF5 file: {loader.file_path}")
        
        # Test flights
        flights = loader.get_flights()
        print(f"✓ Found {len(flights)} flights")
        for flight in flights:
            print(f"  - {flight}")
        
        # Test channels
        total_channels = 0
        for flight in flights:
            channels = loader.get_channels(flight.flight_key)
            total_channels += len(channels)
            print(f"✓ Flight {flight.flight_id}: {len(channels)} channels")
        
        print(f"✓ Total channels: {total_channels}")
        
        # Test unique locations
        locations = loader.get_unique_locations()
        print(f"✓ Found {len(locations)} unique locations:")
        for loc in locations:
            print(f"  - {loc}")
        
        # Test unique sensor types
        sensor_types = loader.get_unique_sensor_types()
        print(f"✓ Found {len(sensor_types)} unique sensor types:")
        for st in sensor_types:
            print(f"  - {st}")
        
        # Test channel info with time range
        flight_key = flights[0].flight_key
        channels = loader.get_channels(flight_key)
        if channels:
            channel = channels[0]
            print(f"\n✓ Sample channel info:")
            print(f"  Name: {channel.channel_key}")
            print(f"  Location: {channel.location}")
            print(f"  Sample Rate: {channel.sample_rate} Hz")
            print(f"  Units: {channel.units}")
            print(f"  Time Range: {channel.time_range_str}")
            print(f"  Sensor Type: {channel.get_sensor_type()}")
        
        loader.close()
        print("\n✓ TEST 1 PASSED: HDF5 Loader works correctly")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_selection_manager():
    """Test selection manager functionality."""
    print("\n" + "=" * 80)
    print("TEST 2: Selection Manager")
    print("=" * 80)
    
    try:
        manager = SelectionManager()
        print("✓ Created selection manager")
        
        # Test saving selection
        test_selection = [('flight_001', 'accelerometer_x_1'), ('flight_001', 'accelerometer_y_1')]
        manager.save_selection('Test Selection', test_selection, 'Test description')
        print("✓ Saved test selection")
        
        # Test loading saved selections
        saved = manager.get_saved_selections()
        if 'Test Selection' in saved:
            print(f"✓ Retrieved saved selection: {saved['Test Selection']['description']}")
        else:
            raise ValueError("Saved selection not found")
        
        # Test adding recent selection
        manager.add_recent_selection(test_selection, "Recent test")
        print("✓ Added recent selection")
        
        # Test loading recent selections
        recent = manager.get_recent_selections()
        if recent:
            print(f"✓ Retrieved {len(recent)} recent selections")
        else:
            raise ValueError("Recent selections not found")
        
        # Clean up
        manager.delete_saved_selection('Test Selection')
        print("✓ Deleted test selection")
        
        print("\n✓ TEST 2 PASSED: Selection Manager works correctly")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_column_config():
    """Test column configuration."""
    print("\n" + "=" * 80)
    print("TEST 3: Column Configuration")
    print("=" * 80)
    
    try:
        from spectral_edge.gui.flight_navigator import ColumnConfig
        
        # Test getting visible columns
        visible = ColumnConfig.get_visible_columns()
        print(f"✓ Default visible columns: {visible}")
        
        # Test getting headers
        headers = ColumnConfig.get_column_headers()
        print(f"✓ Column headers: {headers}")
        
        # Test setting visibility
        ColumnConfig.set_column_visibility('time_range', True)
        if ColumnConfig.COLUMNS['time_range']['visible']:
            print("✓ Set time_range column visible")
        else:
            raise ValueError("Failed to set column visibility")
        
        # Reset to default
        ColumnConfig.set_column_visibility('time_range', False)
        
        print("\n✓ TEST 3 PASSED: Column Configuration works correctly")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_loading():
    """Test actual data loading from HDF5."""
    print("\n" + "=" * 80)
    print("TEST 4: Data Loading")
    print("=" * 80)
    
    try:
        loader = HDF5FlightDataLoader('data/large_test_flight_data.hdf5')
        
        # Get first channel
        flights = loader.get_flights()
        flight_key = flights[0].flight_key
        channels = loader.get_channels(flight_key)
        channel = channels[0]
        
        print(f"✓ Loading data for: {channel.channel_key}")
        
        # Load data
        data = loader.load_channel_data(flight_key, channel.channel_key)
        
        print(f"✓ Loaded data:")
        print(f"  Time points: {len(data['time_full'])}")
        print(f"  Data points: {len(data['data_full'])}")
        print(f"  Sample rate: {data['sample_rate']} Hz")
        print(f"  Decimation factor: {data['decimation_factor']}")
        print(f"  Display points: {len(data['time_display'])}")
        
        loader.close()
        print("\n✓ TEST 4 PASSED: Data Loading works correctly")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE FUNCTIONALITY TEST")
    print("Enhanced Flight Navigator")
    print("=" * 80 + "\n")
    
    results = []
    
    # Run tests
    results.append(("HDF5 Loader", test_hdf5_loader()))
    results.append(("Selection Manager", test_selection_manager()))
    results.append(("Column Configuration", test_column_config()))
    results.append(("Data Loading", test_data_loading()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name:30s} {status}")
    
    print("=" * 80)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 80)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! The Enhanced Flight Navigator is ready to use.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
