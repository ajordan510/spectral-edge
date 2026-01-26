"""
HDF5 Data Loader Utility

This module provides memory-efficient loading and management of large HDF5 flight test data files.
It supports lazy loading, chunked reading, and metadata extraction without loading entire datasets
into memory.

Key Features:
- Lazy loading: Only metadata is read initially
- Chunked reading: Data loaded in segments as needed
- Decimation: Automatic downsampling for display
- Cross-flight support: Identify common channels across flights

Author: SpectralEdge Development Team
Date: 2025-01-21
"""

import h5py
import numpy as np
import json
from typing import Dict, List, Tuple, Optional


class FlightInfo:
    """Container for flight metadata."""
    
    def __init__(self, flight_key: str, metadata: Dict):
        """
        Initialize flight information.
        
        Parameters:
        -----------
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
        
        Parameters:
        -----------
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
    Memory-efficient loader for HDF5 flight test data.
    
    This class provides methods to:
    - Load metadata without reading data
    - Read data in chunks
    - Decimate data for display
    - Manage multiple flights and channels
    """
    
    def __init__(self, file_path: str):
        """
        Initialize HDF5 data loader.
        
        Parameters:
        -----------
        file_path : str
            Path to HDF5 file
        """
        self.file_path = file_path
        self.h5file = None
        self.flights = {}  # Dict of flight_key -> FlightInfo
        self.channels = {}  # Dict of flight_key -> Dict of channel_key -> ChannelInfo
        self.file_metadata = {}
        
        # Open file and load metadata
        self._load_metadata()
    
    def _load_metadata(self):
        """Load file and flight metadata without reading data arrays."""
        self.h5file = h5py.File(self.file_path, 'r')
        
        # Load file-level metadata
        if 'metadata' in self.h5file:
            meta_group = self.h5file['metadata']
            self.file_metadata = dict(meta_group.attrs)
        
        # Find all flight groups
        for key in self.h5file.keys():
            if key.startswith('flight_'):
                # Load flight metadata
                flight_group = self.h5file[key]
                
                if 'metadata' in flight_group:
                    meta_dict = dict(flight_group['metadata'].attrs)
                    self.flights[key] = FlightInfo(key, meta_dict)
                
                # Load channel metadata for this flight
                if 'channels' in flight_group:
                    channels_group = flight_group['channels']
                    self.channels[key] = {}
                    
                    for channel_key in channels_group.keys():
                        channel_group = channels_group[channel_key]
                        channel_attrs = dict(channel_group.attrs)
                        self.channels[key][channel_key] = ChannelInfo(
                            channel_key, key, channel_attrs
                        )
    
    def get_flights(self) -> List[FlightInfo]:
        """
        Get list of all flights in the file.
        
        Returns:
        --------
        list of FlightInfo
            List of flight information objects
        """
        return list(self.flights.values())
    
    def get_channels(self, flight_key: str) -> List[ChannelInfo]:
        """
        Get list of channels for a specific flight.
        
        Parameters:
        -----------
        flight_key : str
            Flight key (e.g., 'flight_001')
        
        Returns:
        --------
        list of ChannelInfo
            List of channel information objects
        """
        if flight_key in self.channels:
            return list(self.channels[flight_key].values())
        return []
    
    def get_channel_info(self, flight_key: str, channel_key: str) -> Optional[ChannelInfo]:
        """
        Get information for a specific channel.
        
        Parameters:
        -----------
        flight_key : str
            Flight key
        channel_key : str
            Channel key
        
        Returns:
        --------
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
        
        Parameters:
        -----------
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
        
        Returns:
        --------
        dict with keys:
            'time_full' : ndarray
                Full resolution time vector
            'data_full' : ndarray
                Full resolution signal data
            'time_display' : ndarray
                Decimated time vector for plotting (if decimate_for_display=True)
            'data_display' : ndarray
                Decimated signal data for plotting (if decimate_for_display=True)
            'sample_rate' : float
                Original sample rate in Hz
            'decimation_factor' : int
                Decimation factor used (1 = no decimation)
        """
        try:
            # Validate HDF5 file is open
            if self.h5file is None:
                raise RuntimeError("HDF5 file is not open. Call load() first.")
            
            # Get channel info
            channel_info = self.get_channel_info(flight_key, channel_key)
            if channel_info is None:
                available_flights = list(self.flights.keys())
                available_channels = list(self.channels.get(flight_key, {}).keys()) if flight_key in self.channels else []
                raise ValueError(
                    f"Channel '{channel_key}' not found in flight '{flight_key}'.\n"
                    f"Available flights: {available_flights}\n"
                    f"Available channels in {flight_key}: {available_channels}"
                )
            
            # Access datasets with error handling
            try:
                channel_group = self.h5file[channel_info.full_path]
            except KeyError as e:
                raise KeyError(f"Cannot access path '{channel_info.full_path}' in HDF5 file: {e}")
            
            # Verify required datasets exist
            if 'time' not in channel_group:
                raise ValueError(f"Missing 'time' dataset in {channel_info.full_path}")
            if 'data' not in channel_group:
                raise ValueError(f"Missing 'data' dataset in {channel_info.full_path}")
            
            time_dataset = channel_group['time']
            data_dataset = channel_group['data']
            
        except Exception as e:
            # Re-raise with context
            raise RuntimeError(f"Error accessing HDF5 data: {str(e)}") from e
        
        # Determine indices for time range
        if start_time is not None or end_time is not None:
            # Load time vector to find indices
            # For large files, we could optimize this by storing time range in metadata
            time_full = time_dataset[:]
            
            start_idx = 0
            if start_time is not None:
                start_idx = np.searchsorted(time_full, start_time)
            
            end_idx = len(time_full)
            if end_time is not None:
                end_idx = np.searchsorted(time_full, end_time)
            
            # Load data slice
            time = time_full[start_idx:end_idx]
            data = data_dataset[start_idx:end_idx]
        else:
            # Load full data
            time_full = time_dataset[:]
            data_full = data_dataset[:]
        
        # Get sample rate from channel info
        channel_info = self.get_channel_info(flight_key, channel_key)
        sample_rate = channel_info.sample_rate
        
        # Prepare result dictionary with full resolution data
        result = {
            'time_full': time_full,
            'data_full': data_full,
            'sample_rate': sample_rate,
            'decimation_factor': 1
        }
        
        # Calculate decimated data for display if requested
        if decimate_for_display and len(data_full) > 10000:
            # Auto-decimate to ~10k points for responsive plotting
            decimate_factor = max(1, len(data_full) // 10000)
            time_display = time_full[::decimate_factor]
            data_display = data_full[::decimate_factor]
            
            result['time_display'] = time_display
            result['data_display'] = data_display
            result['decimation_factor'] = decimate_factor
        else:
            # No decimation needed or not requested
            result['time_display'] = time_full
            result['data_display'] = data_full
        
        return result
    
    def load_channel_chunk(self, flight_key: str, channel_key: str,
                          start_idx: int, end_idx: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Load a chunk of channel data by index.
        
        This is more efficient than time-based loading when you know the indices.
        
        Parameters:
        -----------
        flight_key : str
            Flight key
        channel_key : str
            Channel key
        start_idx : int
            Starting index
        end_idx : int
            Ending index
        
        Returns:
        --------
        time : ndarray
            Time vector chunk
        data : ndarray
            Signal data chunk
        """
        channel_info = self.get_channel_info(flight_key, channel_key)
        if channel_info is None:
            raise ValueError(f"Channel {channel_key} not found in {flight_key}")
        
        channel_group = self.h5file[channel_info.full_path]
        time = channel_group['time'][start_idx:end_idx]
        data = channel_group['data'][start_idx:end_idx]
        
        return time, data
    
    def get_channel_length(self, flight_key: str, channel_key: str) -> int:
        """
        Get the number of samples in a channel without loading data.
        
        Parameters:
        -----------
        flight_key : str
            Flight key
        channel_key : str
            Channel key
        
        Returns:
        --------
        int
            Number of samples
        """
        channel_info = self.get_channel_info(flight_key, channel_key)
        if channel_info is None:
            raise ValueError(f"Channel {channel_key} not found in {flight_key}")
        
        channel_group = self.h5file[channel_info.full_path]
        return len(channel_group['data'])
    
    def get_common_channels(self) -> Dict[str, List[str]]:
        """
        Identify channels that are common across multiple flights.
        
        Returns:
        --------
        dict
            Dictionary mapping channel names to list of full paths
            Example: {'accelerometer_x': ['flight_001/channels/accelerometer_x', 
                                          'flight_002/channels/accelerometer_x']}
        """
        # Check if common channels mapping exists in file
        if 'common_channels_mapping' in self.h5file:
            mapping_str = self.h5file['common_channels_mapping'][()]
            if isinstance(mapping_str, bytes):
                mapping_str = mapping_str.decode('utf-8')
            return json.loads(mapping_str)
        
        # Otherwise, compute it
        common = {}
        
        # Collect all channel names across flights
        for flight_key, channels in self.channels.items():
            for channel_key in channels.keys():
                if channel_key not in common:
                    common[channel_key] = []
                common[channel_key].append(f"{flight_key}/channels/{channel_key}")
        
        # Filter to only channels present in multiple flights
        common = {k: v for k, v in common.items() if len(v) > 1}
        
        return common
    
    def close(self):
        """Close the HDF5 file."""
        if self.h5file is not None:
            self.h5file.close()
            self.h5file = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def __del__(self):
        """Destructor to ensure file is closed."""
        self.close()
