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
from typing import Dict, Tuple, List, Any
import logging

logger = logging.getLogger(__name__)


def write_psds_to_hdf5(
    result: 'BatchProcessingResult',
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
    result : BatchProcessingResult
        Batch processing result object containing channel_results
    source_file : str
        Path to the HDF5 file to write to
    config : BatchConfig
        Batch configuration object (for spacing conversion)
        
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
            # Reorganize results by flight and event
            from spectral_edge.batch.output_psd import apply_frequency_spacing

            for (flight_key, channel_key), event_dict in result.channel_results.items():
                for event_name, event_result in event_dict.items():
                    frequencies_out, psd_out = apply_frequency_spacing(
                        event_result['frequencies'],
                        event_result['psd'],
                        config.psd_config
                    )
                    _write_channel_psd_to_event(
                        hdf_file, 
                        flight_key, 
                        event_name, 
                        channel_key,
                        frequencies_out,
                        psd_out,
                        event_result['metadata'],
                        config.psd_config
                    )
        
        logger.info(f"PSDs written to HDF5: {source_file}")
        
    except Exception as e:
        logger.error(f"Failed to write PSDs to HDF5: {str(e)}")
        raise


def _write_channel_psd_to_event(
    hdf_file: h5py.File,
    flight_key: str,
    event_name: str,
    channel_key: str,
    frequencies: np.ndarray,
    psd_values: np.ndarray,
    metadata: Dict,
    psd_config
) -> None:
    """
    Write a single channel's PSD data to HDF5 for a specific event.
    
    Parameters:
    -----------
    hdf_file : h5py.File
        Open HDF5 file object
    flight_key : str
        Flight identifier
    event_name : str
        Event name
    channel_key : str
        Channel identifier
    frequencies : np.ndarray
        Frequency array
    psd_values : np.ndarray
        PSD values
    metadata : Dict
        Processing metadata
    psd_config : PSDConfig
        PSD configuration (for spacing metadata)
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
    
    # Create event group if it doesn't exist
    if event_name not in processed_psds_group:
        event_group = processed_psds_group.create_group(event_name)
        event_group.attrs['event_name'] = event_name
    else:
        event_group = processed_psds_group[event_name]
    
    # Create or overwrite channel group
    if channel_key in event_group:
        del event_group[channel_key]
    
    channel_group = event_group.create_group(channel_key)
    
    # Write datasets
    freq_dataset = channel_group.create_dataset('frequencies', data=frequencies, compression='gzip')
    freq_dataset.attrs['units'] = 'Hz'
    freq_dataset.attrs['description'] = 'Frequency array for PSD'
    
    psd_dataset = channel_group.create_dataset('psd', data=psd_values, compression='gzip')
    psd_dataset.attrs['units'] = metadata.get('units', 'unknown')
    psd_dataset.attrs['description'] = 'Power Spectral Density values'
    
    # Add processing metadata
    channel_group.attrs['channel_name'] = channel_key
    channel_group.attrs['freq_min'] = float(frequencies[0])
    channel_group.attrs['freq_max'] = float(frequencies[-1])
    channel_group.attrs['num_points'] = len(frequencies)
    channel_group.attrs['sample_rate'] = metadata.get('sample_rate', 0.0)
    channel_group.attrs['psd_method'] = metadata.get('method', 'unknown')
    channel_group.attrs['window'] = metadata.get('window', 'unknown')
    channel_group.attrs['frequency_spacing'] = getattr(psd_config, "frequency_spacing", "constant_bandwidth")
    octave_fraction = None
    if hasattr(psd_config, "get_octave_fraction"):
        octave_fraction = psd_config.get_octave_fraction()
    if octave_fraction:
        channel_group.attrs['octave_fraction'] = float(octave_fraction)


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
