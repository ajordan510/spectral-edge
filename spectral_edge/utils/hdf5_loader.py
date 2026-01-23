"""
HDF5 Data Loader Utility with Comprehensive Validation

This module provides memory-efficient loading and management of large HDF5 flight test data files
with detailed format validation and diagnostic messages to help debug loading issues.

Key Features:
- Lazy loading: Only metadata is read initially
- Chunked reading: Data loaded in segments as needed
- Decimation: Automatic downsampling for display
- Cross-flight support: Identify common channels across flights
- Comprehensive validation: Detailed error messages for format issues
- Diagnostic output: Shows what was found vs. what was expected

Author: SpectralEdge Development Team
Date: 2025-01-23
"""

import h5py
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class HDF5ValidationError(Exception):
    """Custom exception for HDF5 format validation errors."""
    pass


class FlightInfo:
    """Container for flight metadata."""
    
    def __init__(self, flight_key: str, metadata: Dict):
        """
        Initialize flight information.
        
        Parameters
        ----------
        flight_key : str
            HDF5 group key (e.g., 'flight_001')
        metadata : dict
            Dictionary of flight metadata attributes
        """
        self.flight_key = flight_key
        self.flight_id = metadata.get('flight_id', flight_key)
        self.date = metadata.get('date', 'Unknown')
        self.duration = metadata.get('duration', 0.0)
        self.description = metadata.get('description', '')
        self.metadata = metadata
    
    def __str__(self):
        return f"{self.flight_id} ({self.date}, {self.duration:.1f}s)"


class ChannelInfo:
    """Container for channel metadata."""
    
    def __init__(self, channel_key: str, flight_key: str, attributes: Dict):
        """
        Initialize channel information.
        
        Parameters
        ----------
        channel_key : str
            Channel name (e.g., 'accelerometer_x')
        flight_key : str
            Parent flight key
        attributes : dict
            Dictionary of channel attributes
        """
        self.channel_key = channel_key
        self.flight_key = flight_key
        self.full_path = f"{flight_key}/channels/{channel_key}"
        
        # Extract common attributes
        self.units = attributes.get('units', '')
        self.sample_rate = attributes.get('sample_rate', 0.0)
        self.start_time = attributes.get('start_time', 0.0)
        self.description = attributes.get('description', '')
        self.sensor_id = attributes.get('sensor_id', '')
        self.range_min = attributes.get('range_min', None)
        self.range_max = attributes.get('range_max', None)
        self.location = attributes.get('location', '')
        self.attributes = attributes
    
    def __str__(self):
        return f"{self.channel_key} ({self.sample_rate:.0f} Hz, {self.units})"
    
    def get_display_name(self):
        """Get formatted display name for GUI."""
        if self.units:
            return f"{self.channel_key} ({self.sample_rate:.0f} Hz, {self.units})"
        else:
            return f"{self.channel_key} ({self.sample_rate:.0f} Hz)"


class HDF5FlightDataLoader:
    """
    Memory-efficient loader for HDF5 flight test data with comprehensive validation.
    
    This class provides methods to:
    - Load metadata without reading data
    - Read data in chunks
    - Decimate data for display
    - Manage multiple flights and channels
    - Validate file format and provide detailed diagnostics
    
    Expected HDF5 Structure
    -----------------------
    /
    ├── flight_001/
    │   ├── metadata/
    │   │   └── attributes: flight_id, date, duration, description
    │   └── channels/
    │       ├── channel_name (dataset: 1D array)
    │       │   └── attributes: units, sample_rate, start_time
    │       └── ...
    ├── flight_002/
    │   └── ...
    └── ...
    
    Required Attributes
    -------------------
    Channel level (required):
    - units: string (e.g., 'g', 'm/s^2')
    - sample_rate: float (Hz, must be > 0)
    - start_time: float (seconds)
    
    Flight level (optional but recommended):
    - flight_id: string
    - date: string
    - duration: float (seconds)
    - description: string
    """
    
    def __init__(self, file_path: str, verbose: bool = True):
        """
        Initialize HDF5 data loader with validation.
        
        Parameters
        ----------
        file_path : str
            Path to HDF5 file
        verbose : bool, optional
            If True, print detailed diagnostic messages (default: True)
        
        Raises
        ------
        FileNotFoundError
            If file does not exist
        HDF5ValidationError
            If file format is invalid
        """
        self.file_path = file_path
        self.verbose = verbose
        self.h5file = None
        self.flights = {}  # Dict of flight_key -> FlightInfo
        self.channels = {}  # Dict of flight_key -> Dict of channel_key -> ChannelInfo
        self.file_metadata = {}
        self.validation_messages = []  # Store validation messages
        
        # Validate file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"HDF5 file not found: {file_path}")
        
        # Open file and load metadata with validation
        self._load_and_validate_metadata()
    
    def _log(self, message: str, level: str = "INFO"):
        """
        Log validation/diagnostic message.
        
        Parameters
        ----------
        message : str
            Message to log
        level : str
            Message level: INFO, WARNING, ERROR
        """
        formatted_msg = f"[{level}] {message}"
        self.validation_messages.append(formatted_msg)
        if self.verbose:
            print(formatted_msg)
    
    def _load_and_validate_metadata(self):
        """
        Load file and flight metadata with comprehensive validation.
        
        Raises
        ------
        HDF5ValidationError
            If file format is invalid
        """
        self._log("="*60)
        self._log(f"Validating HDF5 file: {Path(self.file_path).name}")
        self._log("="*60)
        
        try:
            self.h5file = h5py.File(self.file_path, 'r')
            self._log(f"✓ File opened successfully")
        except Exception as e:
            raise HDF5ValidationError(f"Failed to open HDF5 file: {e}")
        
        # Load file-level metadata (optional)
        if 'metadata' in self.h5file:
            meta_group = self.h5file['metadata']
            self.file_metadata = dict(meta_group.attrs)
            self._log(f"✓ Found file-level metadata: {list(self.file_metadata.keys())}")
        else:
            self._log("  No file-level metadata (optional)", "WARNING")
        
        # Find all flight groups
        all_keys = list(self.h5file.keys())
        self._log(f"\nTop-level groups found: {all_keys}")
        
        flight_keys = [key for key in all_keys if key.startswith('flight_')]
        
        if not flight_keys:
            error_msg = (
                f"\n❌ ERROR: No flight groups found!\n"
                f"Expected: Groups named 'flight_001', 'flight_002', etc.\n"
                f"Found: {all_keys}\n"
                f"\nYour HDF5 file must have groups starting with 'flight_'.\n"
                f"Example structure:\n"
                f"  /flight_001/\n"
                f"    /channels/\n"
                f"      /channel_name (dataset)\n"
            )
            self._log(error_msg, "ERROR")
            raise HDF5ValidationError(error_msg)
        
        self._log(f"\n✓ Found {len(flight_keys)} flight group(s): {flight_keys}")
        
        # Validate each flight
        for flight_key in flight_keys:
            self._log(f"\n--- Validating {flight_key} ---")
            self._validate_flight_group(flight_key)
        
        # Summary
        total_channels = sum(len(channels) for channels in self.channels.values())
        self._log("\n" + "="*60)
        self._log(f"✓ VALIDATION COMPLETE")
        self._log(f"  Flights: {len(self.flights)}")
        self._log(f"  Total channels: {total_channels}")
        self._log("="*60 + "\n")
    
    def _validate_flight_group(self, flight_key: str):
        """
        Validate a single flight group structure.
        
        Parameters
        ----------
        flight_key : str
            Flight group key (e.g., 'flight_001')
        
        Raises
        ------
        HDF5ValidationError
            If flight group structure is invalid
        """
        flight_group = self.h5file[flight_key]
        
        # Check for metadata group (optional but recommended)
        if 'metadata' in flight_group:
            meta_dict = dict(flight_group['metadata'].attrs)
            self.flights[flight_key] = FlightInfo(flight_key, meta_dict)
            self._log(f"  ✓ Metadata found:")
            for key, value in meta_dict.items():
                self._log(f"      {key}: {value}")
        else:
            self._log(f"  ⚠ No metadata group (optional but recommended)", "WARNING")
            self.flights[flight_key] = FlightInfo(flight_key, {})
        
        # Check for channels group (REQUIRED)
        if 'channels' not in flight_group:
            error_msg = (
                f"\n❌ ERROR: No 'channels' group in {flight_key}!\n"
                f"Expected: {flight_key}/channels/\n"
                f"Found: {list(flight_group.keys())}\n"
                f"\nEach flight group must contain a 'channels' subgroup.\n"
            )
            self._log(error_msg, "ERROR")
            raise HDF5ValidationError(error_msg)
        
        channels_group = flight_group['channels']
        channel_keys = list(channels_group.keys())
        
        if not channel_keys:
            error_msg = (
                f"\n❌ ERROR: No channels found in {flight_key}/channels/!\n"
                f"Each flight must have at least one channel dataset.\n"
            )
            self._log(error_msg, "ERROR")
            raise HDF5ValidationError(error_msg)
        
        self._log(f"  ✓ Found {len(channel_keys)} channel(s): {channel_keys}")
        
        # Validate each channel
        self.channels[flight_key] = {}
        for channel_key in channel_keys:
            self._validate_channel(flight_key, channel_key, channels_group[channel_key])
    
    def _validate_channel(self, flight_key: str, channel_key: str, channel_dataset):
        """
        Validate a single channel dataset.
        
        Parameters
        ----------
        flight_key : str
            Parent flight key
        channel_key : str
            Channel name
        channel_dataset : h5py.Dataset
            HDF5 dataset object
        
        Raises
        ------
        HDF5ValidationError
            If channel format is invalid
        """
        self._log(f"\n    Validating channel: {channel_key}")
        
        # Check it's a dataset
        if not isinstance(channel_dataset, h5py.Dataset):
            error_msg = (
                f"\n❌ ERROR: {channel_key} is not a dataset!\n"
                f"Type: {type(channel_dataset)}\n"
                f"Channels must be HDF5 datasets containing 1D arrays.\n"
            )
            self._log(error_msg, "ERROR")
            raise HDF5ValidationError(error_msg)
        
        # Check data shape (must be 1D)
        shape = channel_dataset.shape
        if len(shape) != 1:
            error_msg = (
                f"\n❌ ERROR: {channel_key} data is not 1D!\n"
                f"Expected: 1D array (shape: (N,))\n"
                f"Found: {len(shape)}D array (shape: {shape})\n"
                f"\nEach channel must be a 1D array of signal values.\n"
                f"If you have multi-axis data, create separate channels:\n"
                f"  - accel_x, accel_y, accel_z (not accel with shape (N, 3))\n"
            )
            self._log(error_msg, "ERROR")
            raise HDF5ValidationError(error_msg)
        
        n_samples = shape[0]
        self._log(f"      ✓ Data shape: {shape} ({n_samples:,} samples)")
        
        # Check required attributes
        attrs = dict(channel_dataset.attrs)
        required_attrs = ['units', 'sample_rate', 'start_time']
        missing_attrs = [attr for attr in required_attrs if attr not in attrs]
        
        if missing_attrs:
            error_msg = (
                f"\n❌ ERROR: {channel_key} missing required attributes!\n"
                f"Required: {required_attrs}\n"
                f"Found: {list(attrs.keys())}\n"
                f"Missing: {missing_attrs}\n"
                f"\nEach channel must have these attributes:\n"
                f"  - units: string (e.g., 'g', 'm/s^2', 'V')\n"
                f"  - sample_rate: float (Hz, must be > 0)\n"
                f"  - start_time: float (seconds, typically 0.0)\n"
            )
            self._log(error_msg, "ERROR")
            raise HDF5ValidationError(error_msg)
        
        # Validate attribute values
        units = attrs['units']
        sample_rate = attrs['sample_rate']
        start_time = attrs['start_time']
        
        self._log(f"      ✓ units: '{units}'")
        self._log(f"      ✓ sample_rate: {sample_rate} Hz")
        self._log(f"      ✓ start_time: {start_time} s")
        
        # Validate sample rate is positive
        if sample_rate <= 0:
            error_msg = (
                f"\n❌ ERROR: {channel_key} has invalid sample_rate!\n"
                f"Expected: Positive number (> 0)\n"
                f"Found: {sample_rate}\n"
                f"\nSample rate must be a positive number in Hz.\n"
            )
            self._log(error_msg, "ERROR")
            raise HDF5ValidationError(error_msg)
        
        # Calculate duration
        duration = n_samples / sample_rate
        self._log(f"      ✓ duration: {duration:.2f} s")
        
        # Log optional attributes if present
        optional_attrs = ['description', 'sensor_id', 'location', 'range_min', 'range_max']
        for attr in optional_attrs:
            if attr in attrs:
                self._log(f"      • {attr}: {attrs[attr]}")
        
        # Store channel info
        self.channels[flight_key][channel_key] = ChannelInfo(
            channel_key, flight_key, attrs
        )
    
    def get_flights(self) -> List[FlightInfo]:
        """
        Get list of all flights in the file.
        
        Returns
        -------
        list of FlightInfo
            List of flight information objects
        """
        return list(self.flights.values())
    
    def get_channels(self, flight_key: str) -> List[ChannelInfo]:
        """
        Get list of channels for a specific flight.
        
        Parameters
        ----------
        flight_key : str
            Flight key (e.g., 'flight_001')
        
        Returns
        -------
        list of ChannelInfo
            List of channel information objects
        """
        if flight_key in self.channels:
            return list(self.channels[flight_key].values())
        return []
    
    def get_channel_info(self, flight_key: str, channel_key: str) -> Optional[ChannelInfo]:
        """
        Get information for a specific channel.
        
        Parameters
        ----------
        flight_key : str
            Flight key
        channel_key : str
            Channel key
        
        Returns
        -------
        ChannelInfo or None
            Channel information object, or None if not found
        """
        if flight_key in self.channels and channel_key in self.channels[flight_key]:
            return self.channels[flight_key][channel_key]
        return None
    
    def load_channel_data(self, flight_key: str, channel_key: str,
                         start_time: Optional[float] = None,
                         end_time: Optional[float] = None,
                         decimate_for_display: bool = True) -> dict:
        """
        Load channel data with optional time range.
        
        Returns both full resolution data (for calculations) and optionally
        decimated data (for display). This ensures PSD calculations always
        use full resolution data while plots remain responsive.
        
        Parameters
        ----------
        flight_key : str
            Flight key (e.g., 'flight_001')
        channel_key : str
            Channel key (e.g., 'accelerometer_x')
        start_time : float, optional
            Start time in seconds (None = beginning)
        end_time : float, optional
            End time in seconds (None = end)
        decimate_for_display : bool, optional
            If True, also returns decimated data for plotting (default: True)
            Decimation targets ~10,000 points for responsive plotting
        
        Returns
        -------
        dict
            Dictionary with keys:
            - 'time_full': ndarray, full resolution time vector
            - 'data_full': ndarray, full resolution signal data
            - 'time_display': ndarray, decimated time vector (if decimate_for_display=True)
            - 'data_display': ndarray, decimated signal data (if decimate_for_display=True)
            - 'sample_rate': float, original sample rate in Hz
            - 'decimation_factor': int, decimation factor used (1 = no decimation)
        
        Raises
        ------
        ValueError
            If flight or channel not found
        """
        # Get channel info
        channel_info = self.get_channel_info(flight_key, channel_key)
        if channel_info is None:
            available_flights = list(self.flights.keys())
            available_channels = list(self.channels.get(flight_key, {}).keys())
            raise ValueError(
                f"Channel not found: {flight_key}/{channel_key}\n"
                f"Available flights: {available_flights}\n"
                f"Available channels in {flight_key}: {available_channels}"
            )
        
        # Get dataset
        dataset_path = f"{flight_key}/channels/{channel_key}"
        dataset = self.h5file[dataset_path]
        
        # Get sample rate
        sample_rate = channel_info.sample_rate
        
        # Calculate time indices
        n_samples = dataset.shape[0]
        start_idx = 0
        end_idx = n_samples
        
        if start_time is not None:
            start_idx = int(start_time * sample_rate)
            start_idx = max(0, min(start_idx, n_samples - 1))
        
        if end_time is not None:
            end_idx = int(end_time * sample_rate)
            end_idx = max(start_idx + 1, min(end_idx, n_samples))
        
        # Load full resolution data
        data_full = dataset[start_idx:end_idx]
        time_full = np.arange(len(data_full)) / sample_rate + (start_idx / sample_rate)
        
        # Calculate decimation factor for display
        decimation_factor = 1
        if decimate_for_display:
            target_points = 10000
            if len(data_full) > target_points:
                decimation_factor = int(np.ceil(len(data_full) / target_points))
        
        # Decimate for display if needed
        if decimation_factor > 1:
            data_display = data_full[::decimation_factor]
            time_display = time_full[::decimation_factor]
        else:
            data_display = data_full
            time_display = time_full
        
        return {
            'time_full': time_full,
            'data_full': data_full,
            'time_display': time_display,
            'data_display': data_display,
            'sample_rate': sample_rate,
            'decimation_factor': decimation_factor
        }
    
    def get_validation_messages(self) -> List[str]:
        """
        Get all validation messages generated during loading.
        
        Returns
        -------
        list of str
            List of validation messages
        """
        return self.validation_messages.copy()
    
    def print_validation_report(self):
        """Print complete validation report."""
        print("\n" + "="*60)
        print("HDF5 VALIDATION REPORT")
        print("="*60)
        for msg in self.validation_messages:
            print(msg)
        print("="*60 + "\n")
    
    def close(self):
        """Close the HDF5 file."""
        if self.h5file is not None:
            self.h5file.close()
            self.h5file = None
    
    def __del__(self):
        """Destructor to ensure file is closed."""
        self.close()
