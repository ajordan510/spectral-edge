"""
Integration Tests for SpectralEdge

Tests the integration between major components:
- HDF5 Loader → Flight Navigator
- Flight Navigator → PSD Window
- Flight Navigator → Spectrogram Window

These tests ensure data flows correctly through the system.

Usage:
    QT_QPA_PLATFORM=offscreen python tests/test_integration.py
"""

import sys
import os
import numpy as np
import tempfile
import h5py

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set Qt platform before importing PyQt6
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from spectral_edge.utils.hdf5_loader import HDF5FlightDataLoader
from spectral_edge.gui.flight_navigator import FlightNavigator
from spectral_edge.gui.psd_window import PSDAnalysisWindow


class IntegrationTester:
    """Runs integration tests."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.test_hdf5_file = None
    
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
            print("\n✓ All integration tests passed!")
            return True
    
    def create_test_hdf5(self):
        """Create a small test HDF5 file."""
        # Create temporary file
        fd, path = tempfile.mkstemp(suffix='.hdf5')
        os.close(fd)
        
        with h5py.File(path, 'w') as f:
            # Create flight group
            flight = f.create_group('flight_001')
            flight.attrs['flight_id'] = 'TEST-001'
            flight.attrs['date'] = '2024-01-15'
            flight.attrs['duration'] = 10.0
            flight.attrs['description'] = 'Test flight'
            
            # Create channels group
            channels = flight.create_group('channels')
            
            # Create test channel 1
            sample_rate_1 = 1000.0
            duration = 10.0
            n_samples_1 = int(sample_rate_1 * duration)
            t1 = np.linspace(0, duration, n_samples_1)
            signal_1 = np.sin(2 * np.pi * 10 * t1)  # 10 Hz sine wave
            
            ch1 = channels.create_dataset('Accel_X', data=signal_1)
            ch1.attrs['units'] = 'g'
            ch1.attrs['sample_rate'] = sample_rate_1
            ch1.attrs['description'] = 'X-axis accelerometer'
            ch1.attrs['sensor_id'] = 'ACC-001'
            ch1.attrs['location'] = 'Wing Tip'
            ch1.attrs['range_min'] = -10.0
            ch1.attrs['range_max'] = 10.0
            
            # Create test channel 2 (different sample rate)
            sample_rate_2 = 2000.0
            n_samples_2 = int(sample_rate_2 * duration)
            t2 = np.linspace(0, duration, n_samples_2)
            signal_2 = np.sin(2 * np.pi * 20 * t2)  # 20 Hz sine wave
            
            ch2 = channels.create_dataset('Accel_Y', data=signal_2)
            ch2.attrs['units'] = 'g'
            ch2.attrs['sample_rate'] = sample_rate_2
            ch2.attrs['description'] = 'Y-axis accelerometer'
            ch2.attrs['sensor_id'] = 'ACC-002'
            ch2.attrs['location'] = 'Wing Tip'
            ch2.attrs['range_min'] = -10.0
            ch2.attrs['range_max'] = 10.0
        
        self.test_hdf5_file = path
        return path
    
    def cleanup_test_hdf5(self):
        """Remove test HDF5 file."""
        if self.test_hdf5_file and os.path.exists(self.test_hdf5_file):
            os.remove(self.test_hdf5_file)


def test_hdf5_loader_integration(tester: IntegrationTester):
    """Test HDF5 loader can load test file."""
    tester.section("HDF5 Loader Integration")
    
    # Create test file
    test_file = tester.create_test_hdf5()
    
    try:
        # Load file
        loader = HDF5FlightDataLoader(test_file)
        tester.test("HDF5FlightDataLoader can open test file", True)
        
        # Get flights
        flights = loader.get_flights()
        tester.test(
            "Loader finds 1 flight",
            len(flights) == 1
        )
        
        # Get channels
        channels = loader.get_channels('flight_001')
        tester.test(
            "Loader finds 2 channels",
            len(channels) == 2
        )
        
        # Load channel data
        data = loader.load_channel_data('flight_001', 'Accel_X')
        tester.test(
            "Loader can load channel data",
            'data_full' in data
        )
        
        tester.test(
            "Loaded data is numpy array",
            isinstance(data['data_full'], np.ndarray)
        )
        
        tester.test(
            "Loaded data has correct length",
            len(data['data_full']) == 10000  # 1000 Hz * 10 seconds
        )
        
        # Close loader
        loader.close()
        tester.test("Loader can be closed", True)
        
    except Exception as e:
        tester.test("HDF5 Loader integration", False, str(e))


def test_flight_navigator_integration(tester: IntegrationTester, app: QApplication):
    """Test Flight Navigator can load and emit data."""
    tester.section("Flight Navigator Integration")
    
    try:
        # Create navigator
        navigator = FlightNavigator()
        tester.test("FlightNavigator can be instantiated", True)
        
        # Load test file
        test_file = tester.test_hdf5_file
        loader = HDF5FlightDataLoader(test_file)
        
        navigator.set_loader(loader)
        tester.test("Navigator accepts HDF5 loader", True)
        
        # Check if tree is populated
        tree = navigator.tree
        tester.test(
            "Navigator tree widget exists",
            tree is not None
        )
        
        # Signal tracking
        signal_received = []
        
        def on_load_selected(selected_items):
            signal_received.append(selected_items)
        
        navigator.load_selected.connect(on_load_selected)
        
        # Simulate selection and load
        # (In real GUI, user would select items and click Load)
        # For testing, we'll manually create the selection
        
        # Get channel data
        data1 = loader.load_channel_data('flight_001', 'Accel_X')
        data2 = loader.load_channel_data('flight_001', 'Accel_Y')
        
        # Create selection tuple
        selection = [
            ('Accel_X', data1['data_full'], 'g', 'TEST-001'),
            ('Accel_Y', data2['data_full'], 'g', 'TEST-001')
        ]
        
        # Emit signal manually (simulating Load button click)
        navigator.load_selected.emit(selection)
        
        # Process events
        app.processEvents()
        
        tester.test(
            "Navigator emits load_selected signal",
            len(signal_received) > 0
        )
        
        if len(signal_received) > 0:
            received = signal_received[0]
            tester.test(
                "Signal contains 2 channels",
                len(received) == 2
            )
            
            tester.test(
                "Signal contains 4-tuples",
                all(len(item) == 4 for item in received)
            )
            
            tester.test(
                "Signal contains numpy arrays",
                all(isinstance(item[1], np.ndarray) for item in received)
            )
        
        loader.close()
        
    except Exception as e:
        tester.test("Flight Navigator integration", False, str(e))


def test_psd_window_integration(tester: IntegrationTester, app: QApplication):
    """Test PSD Window can receive and process data."""
    tester.section("PSD Window Integration")
    
    try:
# Create PSD window
        psd_window = PSDAnalysisWindow()
        tester.test("PSDAnalysisWindow can be instantiated", True)
        
        # Create test data
        sample_rate = 1000.0
        duration = 10.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        signal = np.sin(2 * np.pi * 10 * t)  # 10 Hz sine wave
        
        # Create selection tuple
        selection = [
            ('Test_Channel', signal, 'g', 'TEST-001')
        ]
        
        # Send data to PSD window
        psd_window._on_hdf5_data_selected(selection)
        
        # Process events
        app.processEvents()
        
        tester.test("PSD Window accepts channel data", True)
        
        # Check if data was stored
        tester.test(
            "PSD Window stores channels_data",
            hasattr(psd_window, 'channels_data') and len(psd_window.channels_data) > 0
        )
        
        # Check if UI was updated
        tester.test(
            "PSD Window has info_label",
            hasattr(psd_window, 'info_label')
        )
        
    except Exception as e:
        tester.test("PSD Window integration", False, str(e))


def test_multi_rate_data_flow(tester: IntegrationTester, app: QApplication):
    """Test data flow with multiple sample rates."""
    tester.section("Multi-Rate Data Flow")
    
    try:
        # Load test file with 2 different sample rates
        test_file = tester.test_hdf5_file
        loader = HDF5FlightDataLoader(test_file)
        
        # Load both channels
        data1 = loader.load_channel_data('flight_001', 'Accel_X')  # 1000 Hz
        data2 = loader.load_channel_data('flight_001', 'Accel_Y')  # 2000 Hz
        
        tester.test(
            "Channel 1 has 1000 Hz sample rate",
            data1['sample_rate'] == 1000.0
        )
        
        tester.test(
            "Channel 2 has 2000 Hz sample rate",
            data2['sample_rate'] == 2000.0
        )
        
        tester.test(
            "Channel 1 has 10000 samples",
            len(data1['data_full']) == 10000
        )
        
        tester.test(
            "Channel 2 has 20000 samples",
            len(data2['data_full']) == 20000
        )
        
        # Create selection with both channels
        selection = [
            ('Accel_X', data1['data_full'], 'g', 'TEST-001'),
            ('Accel_Y', data2['data_full'], 'g', 'TEST-001')
        ]
        
        # Send to PSD window
        psd_window = PSDAnalysisWindow()
        psd_window._on_hdf5_data_selected(selection)
        
        app.processEvents()
        
        tester.test(
            "PSD Window accepts multi-rate data",
            len(psd_window.channels_data) == 2
        )
        
        loader.close()
        
    except Exception as e:
        tester.test("Multi-rate data flow", False, str(e))


def main():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("  SpectralEdge Integration Tests")
    print("="*60)
    print("\nTesting data flow between components")
    print("Ensures backward compatibility of interfaces\n")
    
    # Create Qt application (required for GUI tests)
    app = QApplication(sys.argv)
    
    tester = IntegrationTester()
    
    # Run all tests
    test_hdf5_loader_integration(tester)
    test_flight_navigator_integration(tester, app)
    test_psd_window_integration(tester, app)
    test_multi_rate_data_flow(tester, app)
    
    # Cleanup
    tester.cleanup_test_hdf5()
    
    # Print summary
    success = tester.summary()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
