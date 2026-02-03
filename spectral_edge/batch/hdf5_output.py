"""
HDF5 Output Module for Batch Processing

This module handles writing processed PSD results back to HDF5 files.
Uses the approved structure: /flight_xxx/processed_psds/event_name/channel_name

Author: SpectralEdge Development Team
Date: 2026-02-02
"""

import h5py
import numpy as np
from pathlib import Path
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


def write_psds_to_hdf5(
    results: Dict[str, Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray]]]],
    source_file: str,
    config: 'BatchConfig'
) -> None:
    """
    Write processed PSD results back to the source HDF5 file.
    
    Creates a parallel structure under /flight_xxx/processed_psds/ to store
    the calculated PSDs without affecting the existing time history data.
    
    Structure:
    ----------
    /flight_001/
      ├── channels/          (existing - untouched)
      │   ├── accel_x
      │   └── accel_y
      └── processed_psds/    (new - created by this function)
          ├── liftoff/
          │   ├── accel_x/
          │   │   ├── frequencies
          │   │   ├── psd
          │   │   └── metadata (attributes)
          │   └── accel_y/
          │       ├── frequencies
          │       ├── psd
          │       └── metadata (attributes)
          └── ascent/
              └── ...
    
    Parameters:
    -----------
    results : Dict[str, Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray]]]]
        Nested dictionary structure:
        {
            event_name: {
                flight_key: {
                    channel_name: (frequencies, psd_values),
                    ...
                },
                ...
            },
            ...
        }
    source_file : str
        Path to the HDF5 file to write to
    config : BatchConfig
        Batch configuration containing processing parameters
        
    Returns:
    --------
    None
    
    Raises:
    -------
    IOError
        If file cannot be opened or written
    ValueError
        If flight key format is invalid
        
    Notes:
    ------
    - Existing processed_psds data for the same event will be overwritten
    - Metadata attributes are added to each PSD dataset
    - The function is safe to call multiple times
    
    Example:
    --------
    >>> results = {
    ...     'liftoff': {
    ...         'flight_0001': {
    ...             'accel_x': (freq_array, psd_array),
    ...         }
    ...     }
    ... }
    >>> write_psds_to_hdf5(results, 'data.h5', config)
    """
    try:
        with h5py.File(source_file, 'a') as hdf_file:
            for event_name, event_results in results.items():
                for flight_key, channels in event_results.items():
                    _write_event_psds(hdf_file, flight_key, event_name, channels, config)
        
        logger.info(f"PSDs written to HDF5: {source_file}")
        
    except Exception as e:
        logger.error(f"Failed to write PSDs to HDF5: {str(e)}")
        raise


def _write_event_psds(
    hdf_file: h5py.File,
    flight_key: str,
    event_name: str,
    channels: Dict[str, Tuple[np.ndarray, np.ndarray]],
    config: 'BatchConfig'
) -> None:
    """
    Write PSD data for one event to HDF5 file.
    
    Parameters:
    -----------
    hdf_file : h5py.File
        Open HDF5 file object
    flight_key : str
        Flight identifier (e.g., 'flight_0001')
    event_name : str
        Name of the event
    channels : Dict[str, Tuple[np.ndarray, np.ndarray]]
        Dictionary mapping channel names to (frequencies, psd) tuples
    config : BatchConfig
        Batch configuration
    """
    # Ensure flight group exists
    if flight_key not in hdf_file:
        logger.warning(f"Flight group not found: {flight_key}")
        return
    
    flight_group = hdf_file[flight_key]
    
    # Create processed_psds group if it doesn't exist
    if 'processed_psds' not in flight_group:
        processed_psds_group = flight_group.create_group('processed_psds')
        processed_psds_group.attrs['description'] = 'Processed PSD results from batch processing'
    else:
        processed_psds_group = flight_group['processed_psds']
    
    # Create or overwrite event group
    if event_name in processed_psds_group:
        del processed_psds_group[event_name]
    
    event_group = processed_psds_group.create_group(event_name)
    
    # Add event metadata
    event_group.attrs['event_name'] = event_name
    event_group.attrs['psd_method'] = config.psd_config.method
    event_group.attrs['window'] = config.psd_config.window
    event_group.attrs['overlap_percent'] = config.psd_config.overlap_percent
    event_group.attrs['frequency_spacing'] = config.psd_config.frequency_spacing
    
    # Write each channel's PSD
    for channel_name, (frequencies, psd_values) in channels.items():
        _write_channel_psd(event_group, channel_name, frequencies, psd_values, config)


def _write_channel_psd(
    event_group: h5py.Group,
    channel_name: str,
    frequencies: np.ndarray,
    psd_values: np.ndarray,
    config: 'BatchConfig'
) -> None:
    """
    Write a single channel's PSD data to HDF5.
    
    Parameters:
    -----------
    event_group : h5py.Group
        HDF5 group for the event
    channel_name : str
        Name of the channel
    frequencies : np.ndarray
        Frequency array
    psd_values : np.ndarray
        PSD values array
    config : BatchConfig
        Batch configuration
    """
    # Create channel group
    channel_group = event_group.create_group(channel_name)
    
    # Write datasets
    freq_dataset = channel_group.create_dataset('frequencies', data=frequencies, compression='gzip')
    freq_dataset.attrs['units'] = 'Hz'
    freq_dataset.attrs['description'] = 'Frequency array for PSD'
    
    psd_dataset = channel_group.create_dataset('psd', data=psd_values, compression='gzip')
    psd_dataset.attrs['units'] = 'g^2/Hz'  # TODO: Get actual units from channel info
    psd_dataset.attrs['description'] = 'Power Spectral Density values'
    
    # Add processing metadata
    channel_group.attrs['channel_name'] = channel_name
    channel_group.attrs['freq_min'] = float(frequencies[0])
    channel_group.attrs['freq_max'] = float(frequencies[-1])
    channel_group.attrs['num_points'] = len(frequencies)
    
    # Add filter info if filtering was applied
    if config.filter_config.enabled:
        channel_group.attrs['filtered'] = True
        channel_group.attrs['filter_type'] = config.filter_config.filter_type
        channel_group.attrs['filter_design'] = config.filter_config.filter_design
        channel_group.attrs['filter_order'] = config.filter_config.filter_order
    else:
        channel_group.attrs['filtered'] = False


def read_psds_from_hdf5(
    hdf5_file: str,
    flight_key: str,
    event_name: str
) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
    """
    Read processed PSDs from HDF5 file.
    
    Parameters:
    -----------
    hdf5_file : str
        Path to HDF5 file
    flight_key : str
        Flight identifier (e.g., 'flight_0001')
    event_name : str
        Name of the event
        
    Returns:
    --------
    Dict[str, Tuple[np.ndarray, np.ndarray]]
        Dictionary mapping channel names to (frequencies, psd) tuples
        
    Raises:
    -------
    KeyError
        If flight, event, or processed_psds group not found
    """
    results = {}
    
    try:
        with h5py.File(hdf5_file, 'r') as hdf_file:
            # Navigate to event group
            event_path = f"{flight_key}/processed_psds/{event_name}"
            
            if event_path not in hdf_file:
                raise KeyError(f"Event not found: {event_path}")
            
            event_group = hdf_file[event_path]
            
            # Read each channel
            for channel_name in event_group.keys():
                channel_group = event_group[channel_name]
                
                frequencies = channel_group['frequencies'][:]
                psd_values = channel_group['psd'][:]
                
                results[channel_name] = (frequencies, psd_values)
        
        logger.info(f"Read {len(results)} channels from {event_path}")
        return results
        
    except Exception as e:
        logger.error(f"Failed to read PSDs from HDF5: {str(e)}")
        raise


def list_processed_events(hdf5_file: str, flight_key: str) -> List[str]:
    """
    List all processed events available in HDF5 file for a given flight.
    
    Parameters:
    -----------
    hdf5_file : str
        Path to HDF5 file
    flight_key : str
        Flight identifier
        
    Returns:
    --------
    List[str]
        List of event names
    """
    try:
        with h5py.File(hdf5_file, 'r') as hdf_file:
            processed_psds_path = f"{flight_key}/processed_psds"
            
            if processed_psds_path not in hdf_file:
                return []
            
            return list(hdf_file[processed_psds_path].keys())
            
    except Exception as e:
        logger.error(f"Failed to list processed events: {str(e)}")
        return []
