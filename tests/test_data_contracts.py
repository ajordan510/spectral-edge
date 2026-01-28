"""
Data Contract Validation Tests

This test suite validates all data contracts defined in docs/DATA_CONTRACTS.md.
Run before and after any code changes to ensure backward compatibility.

Usage:
    python tests/test_data_contracts.py
    
Exit code 0 = all tests passed
Exit code 1 = one or more tests failed
"""

import sys
import os
import numpy as np
from typing import List, Tuple, Dict, Any
# from dataclasses import is_dataclass, fields  # Not using dataclasses currently

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modules to test
from spectral_edge.utils.hdf5_loader import HDF5FlightDataLoader, FlightInfo, ChannelInfo
from spectral_edge.core.psd import calculate_psd_welch, calculate_psd_maximax


class ContractValidator:
    """Validates data contracts and reports violations."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def test(self, name: str, condition: bool, error_msg: str = ""):
        """Test a condition and record result."""
        if condition:
            self.passed += 1
            print(f"✓ {name}")
        else:
            self.failed += 1
            full_msg = f"✗ {name}"
            if error_msg:
                full_msg += f": {error_msg}"
            print(full_msg)
            self.errors.append(full_msg)
    
    def section(self, title: str):
        """Print section header."""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print('='*60)
    
    def summary(self):
        """Print test summary."""
        print(f"\n{'='*60}")
        print(f"  TEST SUMMARY")
        print('='*60)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Total:  {self.passed + self.failed}")
        
        if self.failed > 0:
            print(f"\n{'='*60}")
            print(f"  FAILURES")
            print('='*60)
            for error in self.errors:
                print(error)
            return False
        else:
            print("\n✓ All tests passed!")
            return True


def test_flight_info_contract(validator: ContractValidator):
    """Test FlightInfo class contract."""
    validator.section("FlightInfo Contract")
    
    # Test class exists
    validator.test(
        "FlightInfo class exists",
        FlightInfo is not None
    )
    
    # Test instantiation with metadata dict
    try:
        metadata = {
            'flight_id': 'TEST-001',
            'date': '2024-01-15',
            'duration': 120.5,
            'description': 'Test flight'
        }
        flight = FlightInfo('flight_001', metadata)
        validator.test("FlightInfo can be instantiated", True)
        
        # Test required attributes
        validator.test(
            "FlightInfo has flight_id attribute",
            hasattr(flight, 'flight_id')
        )
        
        validator.test(
            "FlightInfo has date attribute",
            hasattr(flight, 'date')
        )
        
        validator.test(
            "FlightInfo has duration attribute",
            hasattr(flight, 'duration')
        )
        
        validator.test(
            "FlightInfo has description attribute",
            hasattr(flight, 'description')
        )
        
        # Test attribute values
        validator.test(
            "FlightInfo.flight_id accessible",
            flight.flight_id == "TEST-001"
        )
        
        validator.test(
            "FlightInfo.duration accessible",
            flight.duration == 120.5
        )
        
        validator.test(
            "FlightInfo.date accessible",
            flight.date == "2024-01-15"
        )
        
        # Test __str__ method
        validator.test(
            "FlightInfo has __str__ method",
            hasattr(flight, '__str__') and callable(flight.__str__)
        )
        
    except Exception as e:
        validator.test("FlightInfo can be instantiated", False, str(e))


def test_channel_info_contract(validator: ContractValidator):
    """Test ChannelInfo class contract."""
    validator.section("ChannelInfo Contract")
    
    # Test class exists
    validator.test(
        "ChannelInfo class exists",
        ChannelInfo is not None
    )
    
    # Test instantiation with attributes dict
    try:
        attributes = {
            'units': 'g',
            'sample_rate': 10000.0,
            'description': 'X-axis accelerometer',
            'sensor_id': 'ACC-001',
            'location': 'Wing Tip',
            'range_min': -50.0,
            'range_max': 50.0
        }
        channel = ChannelInfo('Accel_X', 'flight_001', attributes)
        validator.test("ChannelInfo can be instantiated", True)
        
        # Test required attributes
        validator.test(
            "ChannelInfo has channel_key attribute",
            hasattr(channel, 'channel_key')
        )
        
        validator.test(
            "ChannelInfo has sample_rate attribute",
            hasattr(channel, 'sample_rate')
        )
        
        validator.test(
            "ChannelInfo has units attribute",
            hasattr(channel, 'units')
        )
        
        validator.test(
            "ChannelInfo has location attribute",
            hasattr(channel, 'location')
        )
        
        validator.test(
            "ChannelInfo has sensor_id attribute",
            hasattr(channel, 'sensor_id')
        )
        
        validator.test(
            "ChannelInfo has range_min attribute",
            hasattr(channel, 'range_min')
        )
        
        validator.test(
            "ChannelInfo has range_max attribute",
            hasattr(channel, 'range_max')
        )
        
        # Test attribute values
        validator.test(
            "ChannelInfo.sample_rate accessible",
            channel.sample_rate == 10000.0
        )
        
        validator.test(
            "ChannelInfo.location accessible",
            channel.location == "Wing Tip"
        )
        
        validator.test(
            "ChannelInfo.units accessible",
            channel.units == "g"
        )
        
        # Test methods
        validator.test(
            "ChannelInfo has __str__ method",
            hasattr(channel, '__str__') and callable(channel.__str__)
        )
        
        validator.test(
            "ChannelInfo has get_display_name method",
            hasattr(channel, 'get_display_name') and callable(channel.get_display_name)
        )
        
    except Exception as e:
        validator.test("ChannelInfo can be instantiated", False, str(e))


def test_channel_selection_tuple_contract(validator: ContractValidator):
    """Test channel selection 4-tuple contract."""
    validator.section("Channel Selection Tuple Contract")
    
    # Create test tuple
    test_signal = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    test_tuple = ("TestChannel", test_signal, "g", "TestFlight")
    
    validator.test(
        "Tuple has 4 elements",
        len(test_tuple) == 4
    )
    
    validator.test(
        "Element 0 (channel_name) is str",
        isinstance(test_tuple[0], str)
    )
    
    validator.test(
        "Element 1 (signal) is np.ndarray",
        isinstance(test_tuple[1], np.ndarray)
    )
    
    validator.test(
        "Element 1 (signal) is float64",
        test_tuple[1].dtype == np.float64
    )
    
    validator.test(
        "Element 1 (signal) is 1D",
        test_tuple[1].ndim == 1
    )
    
    validator.test(
        "Element 2 (units) is str",
        isinstance(test_tuple[2], str)
    )
    
    validator.test(
        "Element 3 (flight_name) is str",
        isinstance(test_tuple[3], str)
    )
    
    # Test unpacking
    try:
        channel_name, signal, units, flight_name = test_tuple
        validator.test("Tuple can be unpacked to 4 variables", True)
        
        validator.test(
            "Unpacked channel_name matches",
            channel_name == "TestChannel"
        )
        
        validator.test(
            "Unpacked signal matches",
            np.array_equal(signal, test_signal)
        )
    except Exception as e:
        validator.test("Tuple can be unpacked to 4 variables", False, str(e))


def test_hdf5_loader_contract(validator: ContractValidator):
    """Test HDF5FlightDataLoader interface contract."""
    validator.section("HDF5FlightDataLoader Contract")
    
    # Test class exists
    validator.test(
        "HDF5FlightDataLoader class exists",
        HDF5FlightDataLoader is not None
    )
    
    # Test required methods exist
    required_methods = [
        '__init__', 'load', 'get_flights', 'get_flight_keys', 'get_flight_info',
        'get_channels', 'get_channel_keys', 'get_channel_data', 'get_time_data', 'close'
    ]
    
    for method_name in required_methods:
        validator.test(
            f"HDF5FlightDataLoader.{method_name} exists",
            hasattr(HDF5FlightDataLoader, method_name)
        )
    
    # Test method signatures (check if callable)
    loader_class = HDF5FlightDataLoader
    
    validator.test(
        "HDF5FlightDataLoader.__init__ is callable",
        callable(getattr(loader_class, '__init__', None))
    )
    
    validator.test(
        "HDF5FlightDataLoader.load is callable",
        callable(getattr(loader_class, 'load', None))
    )
    
    validator.test(
        "HDF5FlightDataLoader.get_flights is callable",
        callable(getattr(loader_class, 'get_flights', None))
    )


def test_psd_welch_contract(validator: ContractValidator):
    """Test calculate_psd_welch function contract."""
    validator.section("calculate_psd_welch Contract")
    
    # Test function exists
    validator.test(
        "calculate_psd_welch function exists",
        callable(calculate_psd_welch)
    )
    
    # Create test signal
    sample_rate = 1000.0
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    test_signal = np.sin(2 * np.pi * 10 * t) + 0.5 * np.sin(2 * np.pi * 60 * t)
    
    # Test basic call
    try:
        frequencies, psd = calculate_psd_welch(test_signal, sample_rate)
        validator.test("calculate_psd_welch can be called", True)
        
        # Test output contract
        validator.test(
            "Returns tuple of 2 elements",
            isinstance((frequencies, psd), tuple) and len((frequencies, psd)) == 2
        )
        
        validator.test(
            "frequencies is np.ndarray",
            isinstance(frequencies, np.ndarray)
        )
        
        validator.test(
            "psd is np.ndarray",
            isinstance(psd, np.ndarray)
        )
        
        validator.test(
            "frequencies is 1D",
            frequencies.ndim == 1
        )
        
        validator.test(
            "psd is 1D",
            psd.ndim == 1
        )
        
        validator.test(
            "frequencies and psd have same length",
            len(frequencies) == len(psd)
        )
        
        validator.test(
            "frequencies starts at 0",
            frequencies[0] == 0.0
        )
        
        validator.test(
            "frequencies is monotonically increasing",
            np.all(np.diff(frequencies) > 0)
        )
        
        validator.test(
            "psd values are non-negative",
            np.all(psd >= 0)
        )
        
        validator.test(
            "Max frequency ≈ Nyquist",
            abs(frequencies[-1] - sample_rate/2) < 1.0
        )
        
    except Exception as e:
        validator.test("calculate_psd_welch can be called", False, str(e))
    
    # Test with df parameter
    try:
        df = 1.0
        frequencies, psd = calculate_psd_welch(test_signal, sample_rate, df=df)
        validator.test("calculate_psd_welch accepts df parameter", True)
        
        # Check frequency resolution
        actual_df = frequencies[1] - frequencies[0]
        validator.test(
            f"Frequency resolution ≈ {df} Hz",
            abs(actual_df - df) < 0.1,
            f"Expected ~{df} Hz, got {actual_df:.3f} Hz"
        )
        
    except Exception as e:
        validator.test("calculate_psd_welch accepts df parameter", False, str(e))


def test_psd_maximax_contract(validator: ContractValidator):
    """Test calculate_psd_maximax function contract."""
    validator.section("calculate_psd_maximax Contract")
    
    # Test function exists
    validator.test(
        "calculate_psd_maximax function exists",
        callable(calculate_psd_maximax)
    )
    
    # Create test signal (longer for maximax)
    sample_rate = 1000.0
    duration = 5.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    test_signal = np.sin(2 * np.pi * 10 * t) + 0.5 * np.sin(2 * np.pi * 60 * t)
    
    # Test basic call
    try:
        frequencies, psd_maximax = calculate_psd_maximax(test_signal, sample_rate)
        validator.test("calculate_psd_maximax can be called", True)
        
        # Test output contract
        validator.test(
            "Returns tuple of 2 elements",
            isinstance((frequencies, psd_maximax), tuple) and len((frequencies, psd_maximax)) == 2
        )
        
        validator.test(
            "frequencies is np.ndarray",
            isinstance(frequencies, np.ndarray)
        )
        
        validator.test(
            "psd_maximax is np.ndarray",
            isinstance(psd_maximax, np.ndarray)
        )
        
        validator.test(
            "psd_maximax values are non-negative",
            np.all(psd_maximax >= 0)
        )
        
        # Test that maximax >= welch (envelope property)
        freq_welch, psd_welch = calculate_psd_welch(test_signal, sample_rate)
        
        # Interpolate to same frequency grid for comparison
        psd_welch_interp = np.interp(frequencies, freq_welch, psd_welch)
        
        validator.test(
            "maximax PSD >= welch PSD (envelope property)",
            np.all(psd_maximax >= psd_welch_interp * 0.9),  # Allow 10% tolerance
            "Maximax should envelope Welch PSD"
        )
        
    except Exception as e:
        validator.test("calculate_psd_maximax can be called", False, str(e))


def test_numpy_compatibility(validator: ContractValidator):
    """Test numpy array compatibility across contracts."""
    validator.section("NumPy Compatibility")
    
    # Test float64 arrays
    test_array = np.array([1.0, 2.0, 3.0], dtype=np.float64)
    
    validator.test(
        "float64 arrays can be created",
        test_array.dtype == np.float64
    )
    
    # Test that float32 can be converted to float64
    test_array_f32 = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    test_array_f64 = test_array_f32.astype(np.float64)
    
    validator.test(
        "float32 arrays can be converted to float64",
        test_array_f64.dtype == np.float64
    )
    
    # Test 1D array operations
    validator.test(
        "1D arrays have ndim=1",
        test_array.ndim == 1
    )
    
    validator.test(
        "1D arrays can be indexed",
        test_array[0] == 1.0
    )
    
    validator.test(
        "1D arrays can be sliced",
        np.array_equal(test_array[1:], np.array([2.0, 3.0]))
    )


def main():
    """Run all contract validation tests."""
    print("\n" + "="*60)
    print("  SpectralEdge Data Contract Validation")
    print("="*60)
    print("\nValidating all data contracts from docs/DATA_CONTRACTS.md")
    print("This ensures backward compatibility across code changes.\n")
    
    validator = ContractValidator()
    
    # Run all tests
    test_flight_info_contract(validator)
    test_channel_info_contract(validator)
    test_channel_selection_tuple_contract(validator)
    test_hdf5_loader_contract(validator)
    test_psd_welch_contract(validator)
    test_psd_maximax_contract(validator)
    test_numpy_compatibility(validator)
    
    # Print summary
    success = validator.summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
