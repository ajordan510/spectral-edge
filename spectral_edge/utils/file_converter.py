"""
File Format Conversion Utilities

This module provides backend functions for converting between different file formats
used in signal processing and vibration analysis. Supports DXD, CSV, HDF5, and MATLAB formats.

Key Features:
- DXD to CSV/HDF5 conversion with time slicing
- HDF5 file splitting by count or time slices
- Memory-efficient chunked processing for large files
- SpectralEdge-compatible HDF5 structure
- Progress callback support for GUI integration

Author: SpectralEdge Development Team
Date: 2026-02-08
"""

import os
import sys
import ctypes
import warnings
import numpy as np
import h5py
from typing import Optional, List, Tuple, Callable, Dict, Any
from pathlib import Path

# Import DEWESoft library wrapper
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'dewesoft'))
from DWDataReaderHeader import *


def get_dxd_file_info(file_path: str) -> Dict[str, Any]:
    """
    Extract metadata from a DXD file without loading signal data.
    
    Parameters
    ----------
    file_path : str
        Path to the .dxd or .dxz file
    
    Returns
    -------
    dict
        Dictionary containing:
        - 'duration' : float - Recording duration in seconds
        - 'sample_rate' : float - Maximum sample rate across all channels (Hz)
        - 'channels' : list of dict - Channel information
            Each dict contains: 'name', 'unit', 'sample_rate', 'sample_count'
        - 'file_size' : int - File size in bytes
        - 'start_time' : str - Recording start time
    
    Raises
    ------
    FileNotFoundError
        If the input file does not exist
    RuntimeError
        If the file cannot be opened or is corrupted
    
    Examples
    --------
    >>> info = get_dxd_file_info('test_data.dxd')
    >>> print(f"Duration: {info['duration']:.2f}s")
    >>> print(f"Channels: {len(info['channels'])}")
    >>> for ch in info['channels']:
    ...     print(f"  {ch['name']}: {ch['sample_rate']} Hz")
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Load DEWESoft library
    lib_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'dewesoft')
    lib = load_library(lib_dir)
    
    # Create reader instance
    reader_instance = READER_HANDLE()
    status = lib.DWICreateReader(ctypes.byref(reader_instance))
    check_error(lib, status)
    
    try:
        # Open file
        c_filename = ctypes.c_char_p(file_path.encode('utf-8'))
        file_info = DWFileInfo()
        status = lib.DWIOpenDataFile(reader_instance, c_filename, ctypes.byref(file_info))
        check_error(lib, status)
        
        # Get channel count
        channel_list_count = ctypes.c_int()
        status = lib.DWIGetChannelListCount(reader_instance, ctypes.byref(channel_list_count))
        check_error(lib, status)
        
        # Extract channel information
        channels = []
        max_sample_rate = 0
        max_duration = 0
        
        for i in range(channel_list_count.value):
            channel_index = ctypes.c_int(i)
            
            # Get channel name
            name_length = ctypes.c_int()
            lib.DWIGetChannelListName(reader_instance, channel_index, None, ctypes.byref(name_length))
            name_buffer = ctypes.create_string_buffer(name_length.value)
            lib.DWIGetChannelListName(reader_instance, channel_index, name_buffer, ctypes.byref(name_length))
            channel_name = name_buffer.value.decode('utf-8')
            
            # Get channel unit
            unit_length = ctypes.c_int()
            lib.DWIGetChannelListUnit(reader_instance, channel_index, None, ctypes.byref(unit_length))
            unit_buffer = ctypes.create_string_buffer(unit_length.value)
            lib.DWIGetChannelListUnit(reader_instance, channel_index, unit_buffer, ctypes.byref(unit_length))
            unit = unit_buffer.value.decode('utf-8')
            
            # Get sample rate
            sample_rate = ctypes.c_double()
            lib.DWIGetChannelListSampleRate(reader_instance, channel_index, ctypes.byref(sample_rate))
            
            # Get sample count
            sample_count = ctypes.c_int64()
            lib.DWIGetChannelListSampleCount(reader_instance, channel_index, ctypes.byref(sample_count))
            
            # Calculate duration for this channel
            duration = sample_count.value / sample_rate.value if sample_rate.value > 0 else 0
            
            channels.append({
                'name': channel_name,
                'unit': unit,
                'sample_rate': sample_rate.value,
                'sample_count': sample_count.value,
                'duration': duration
            })
            
            # Track maximum sample rate and duration
            if sample_rate.value > max_sample_rate:
                max_sample_rate = sample_rate.value
            if duration > max_duration:
                max_duration = duration
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Get start time from file info
        start_time = file_info.start_store_time.decode('utf-8') if file_info.start_store_time else "Unknown"
        
        return {
            'duration': max_duration,
            'sample_rate': max_sample_rate,
            'channels': channels,
            'file_size': file_size,
            'start_time': start_time
        }
    
    finally:
        # Clean up
        lib.DWICloseDataFile(reader_instance)
        lib.DWIDestroyReader(reader_instance)


def convert_dxd_to_format(
    input_path: str,
    output_path: str,
    output_format: str,
    time_range: Optional[Tuple[float, float]] = None,
    channels: Optional[List[str]] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> List[str]:
    """
    Convert DXD file to CSV or HDF5 format with optional time slicing.
    
    This function reads a DEWESoft .dxd file and converts it to the specified output format.
    Supports time-based slicing to extract specific portions of the recording.
    Uses memory-efficient chunked reading for large files.
    
    Parameters
    ----------
    input_path : str
        Path to input .dxd or .dxz file
    output_path : str
        Path for output file (.csv or .h5/.hdf5)
    output_format : str
        Output format: 'csv' or 'hdf5'
    time_range : tuple of (float, float), optional
        Time range to extract in seconds (start_time, end_time).
        If None, converts entire file.
    channels : list of str, optional
        List of channel names to include.
        If None, includes all channels.
    progress_callback : callable, optional
        Function(percentage: int, message: str) called to report progress.
        Percentage is 0-100, message describes current operation.
    
    Raises
    ------
    FileNotFoundError
        If input file does not exist
    ValueError
        If output_format is not 'csv' or 'hdf5'
        If time_range is invalid
        If specified channels don't exist in file
    RuntimeError
        If conversion fails

    Returns
    -------
    list of str
        Paths to created output files. CSV conversion may return multiple files
        when channels have different time vectors.
    
    Examples
    --------
    # Convert entire file to HDF5
    >>> convert_dxd_to_format('data.dxd', 'output.h5', 'hdf5')
    
    # Convert time slice to CSV
    >>> convert_dxd_to_format(
    ...     'data.dxd', 'slice.csv', 'csv',
    ...     time_range=(10.0, 30.0)
    ... )
    
    # Convert specific channels with progress tracking
    >>> def progress(pct, msg):
    ...     print(f"{pct}%: {msg}")
    >>> convert_dxd_to_format(
    ...     'data.dxd', 'output.h5', 'hdf5',
    ...     channels=['Accel_X', 'Accel_Y'],
    ...     progress_callback=progress
    ... )
    
    Notes
    -----
    - HDF5 output uses SpectralEdge-compatible structure
    - CSV output includes header row with channel names
    - Large files are processed in chunks to minimize memory usage
    - Time slicing is sample-accurate based on channel sample rates
    """
    # Validate inputs
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    if output_format not in ['csv', 'hdf5']:
        raise ValueError(f"Invalid output format: {output_format}. Must be 'csv' or 'hdf5'")
    
    # Import conversion script functions
    script_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts')
    sys.path.insert(0, script_dir)
    
    if output_format == 'hdf5':
        sys.path.insert(0, os.path.join(script_dir, 'dewesoft'))
        from hdf5_writer import write_hdf5_file_chunked
    
    # Get file info
    if progress_callback:
        progress_callback(5, "Analyzing file...")
    
    file_info = get_dxd_file_info(input_path)
    
    # Validate channels
    available_channels = [ch['name'] for ch in file_info['channels']]
    if channels:
        invalid_channels = set(channels) - set(available_channels)
        if invalid_channels:
            raise ValueError(f"Channels not found in file: {invalid_channels}")
        selected_channels = channels
    else:
        selected_channels = available_channels
    
    # Validate time range
    if time_range:
        start_time, end_time = time_range
        if start_time < 0 or end_time > file_info['duration']:
            raise ValueError(
                f"Invalid time range: ({start_time}, {end_time}). "
                f"File duration is {file_info['duration']:.2f}s"
            )
        if start_time >= end_time:
            raise ValueError(f"Start time ({start_time}) must be less than end time ({end_time})")
    
    # Load library and open file
    if progress_callback:
        progress_callback(10, "Opening file...")
    
    lib_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'dewesoft')
    lib = load_library(lib_dir)
    
    reader_instance = READER_HANDLE()
    status = lib.DWICreateReader(ctypes.byref(reader_instance))
    check_error(lib, status)
    
    try:
        c_filename = ctypes.c_char_p(input_path.encode('utf-8'))
        dw_file_info = DWFileInfo()
        status = lib.DWIOpenDataFile(reader_instance, c_filename, ctypes.byref(dw_file_info))
        check_error(lib, status)
        
        # Read channel data
        if progress_callback:
            progress_callback(20, f"Reading {len(selected_channels)} channels...")
        
        channel_data_dict = {}
        for idx, channel_name in enumerate(selected_channels):
            # Find channel info
            ch_info = next(ch for ch in file_info['channels'] if ch['name'] == channel_name)
            sample_rate = ch_info['sample_rate']
            total_samples = ch_info['sample_count']

            if sample_rate <= 0:
                raise ValueError(f"Invalid sample rate for channel '{channel_name}': {sample_rate}")
            if total_samples <= 0:
                raise ValueError(f"No samples available for channel '{channel_name}'")
            
            # Calculate sample range for time slicing
            if time_range:
                start_sample = int(time_range[0] * sample_rate)
                requested_end_sample = int(time_range[1] * sample_rate)
                if start_sample >= total_samples:
                    raise ValueError(
                        f"Time range starts after channel '{channel_name}' ends "
                        f"({time_range[0]}s >= {total_samples / sample_rate:.2f}s)"
                    )
                if requested_end_sample > total_samples:
                    warnings.warn(
                        f"Time range end exceeds channel '{channel_name}' duration; "
                        f"clamping to {total_samples / sample_rate:.2f}s.",
                        RuntimeWarning
                    )
                end_sample = min(requested_end_sample, total_samples)
                num_samples = end_sample - start_sample
            else:
                start_sample = 0
                num_samples = total_samples

            if num_samples <= 0:
                raise ValueError(
                    f"No samples to extract for channel '{channel_name}' with time range {time_range}"
                )
            
            # Get channel index
            channel_list_count = ctypes.c_int()
            lib.DWIGetChannelListCount(reader_instance, ctypes.byref(channel_list_count))
            
            channel_index = None
            for i in range(channel_list_count.value):
                ch_idx = ctypes.c_int(i)
                name_length = ctypes.c_int()
                lib.DWIGetChannelListName(reader_instance, ch_idx, None, ctypes.byref(name_length))
                name_buffer = ctypes.create_string_buffer(name_length.value)
                lib.DWIGetChannelListName(reader_instance, ch_idx, name_buffer, ctypes.byref(name_length))
                if name_buffer.value.decode('utf-8') == channel_name:
                    channel_index = i
                    break
            
            if channel_index is None:
                raise RuntimeError(f"Channel not found: {channel_name}")
            
            # Read data in chunks
            chunk_size = 100000
            all_samples = []
            
            for chunk_start in range(0, num_samples, chunk_size):
                chunk_end = min(chunk_start + chunk_size, num_samples)
                chunk_count = chunk_end - chunk_start
                
                # Allocate buffer
                samples = (ctypes.c_double * chunk_count)()
                
                # Read scaled samples
                status = lib.DWIGetScaledSamples(
                    reader_instance,
                    ctypes.c_int(channel_index),
                    ctypes.c_int64(start_sample + chunk_start),
                    ctypes.c_int(chunk_count),
                    samples
                )
                check_error(lib, status)
                
                # Convert to numpy array
                chunk_data = np.array(samples)
                all_samples.append(chunk_data)
                
                # Update progress
                if progress_callback:
                    channel_progress = 20 + int((idx + (chunk_end / num_samples)) / len(selected_channels) * 60)
                    progress_callback(
                        channel_progress,
                        f"Reading channel {idx+1}/{len(selected_channels)}: {channel_name} "
                        f"({chunk_end}/{num_samples} samples)"
                    )
            
            # Combine chunks
            signal_data = np.concatenate(all_samples)
            
            # Generate time array
            time_data = np.arange(len(signal_data)) / sample_rate
            if time_range:
                time_data += time_range[0]  # Offset by start time
            
            channel_data_dict[channel_name] = {
                'data': signal_data,
                'time': time_data,
                'sample_rate': sample_rate,
                'unit': ch_info['unit']
            }
        
        # Write output file
        if progress_callback:
            progress_callback(85, f"Writing {output_format.upper()} file...")
        
        output_files: List[str] = []
        if output_format == 'csv':
            output_files = _write_csv_files(output_path, channel_data_dict, selected_channels)
        else:  # hdf5
            write_hdf5_file_chunked(
                lib, reader_instance, output_path, selected_channels,
                time_range=time_range,
                progress_callback=lambda p, m: progress_callback(85 + int(p * 0.15), m) if progress_callback else None
            )
            output_files = [output_path]
        
        if progress_callback:
            progress_callback(100, "Conversion complete!")

        return output_files
    
    finally:
        lib.DWICloseDataFile(reader_instance)
        lib.DWIDestroyReader(reader_instance)


def _sanitize_filename(value: str) -> str:
    """Sanitize a string for safe filenames."""
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value.strip())
    return cleaned or "channel"


def _write_csv_file(output_path: str, channel_data_dict: Dict, channel_names: List[str]) -> None:
    """
    Write channel data to CSV file.
    
    Parameters
    ----------
    output_path : str
        Path to output CSV file
    channel_data_dict : dict
        Dictionary mapping channel names to data dictionaries
    channel_names : list of str
        Ordered list of channel names to write
    """
    import csv
    
    # Get reference time array (use first channel)
    time_data = channel_data_dict[channel_names[0]]['time']
    
    # Open CSV file
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        header = ['Time (s)'] + [f"{name} ({channel_data_dict[name]['unit']})" for name in channel_names]
        writer.writerow(header)
        
        # Write data rows
        for i in range(len(time_data)):
            row = [time_data[i]] + [channel_data_dict[name]['data'][i] for name in channel_names]
            writer.writerow(row)


def _write_csv_files(output_path: str, channel_data_dict: Dict, channel_names: List[str]) -> List[str]:
    """
    Write channel data to one or multiple CSV files.

    If channels have different time vectors, write one CSV per channel.
    """
    if not channel_names:
        raise ValueError("No channels provided for CSV export")

    def time_signature(name: str) -> Tuple[int, float, float]:
        time_data = channel_data_dict[name]['time']
        return (len(time_data), float(channel_data_dict[name]['sample_rate']), float(time_data[0]))

    signatures = {name: time_signature(name) for name in channel_names}
    unique_signatures = set(signatures.values())

    output_paths: List[str] = []
    output_path_obj = Path(output_path)
    base_path = output_path_obj.with_suffix("")

    if len(unique_signatures) == 1:
        csv_path = str(output_path_obj.with_suffix(".csv"))
        _write_csv_file(csv_path, channel_data_dict, channel_names)
        output_paths.append(csv_path)
    else:
        for name in channel_names:
            safe_name = _sanitize_filename(name)
            csv_path = f"{base_path}_{safe_name}.csv"
            _write_csv_file(csv_path, channel_data_dict, [name])
            output_paths.append(csv_path)

    return output_paths


def convert_dxd_with_splitting(
    input_path: str,
    output_dir: str,
    output_format: str,
    split_mode: str = 'none',
    num_segments: Optional[int] = None,
    time_slices: Optional[List[Tuple[float, float]]] = None,
    channels: Optional[List[str]] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> List[str]:
    """
    Convert DXD file to CSV or HDF5 with optional splitting into multiple files.
    
    This function reads a DXD file and converts it to the specified format.
    If splitting is enabled, it creates multiple output files instead of one large file.
    Each segment is processed independently for memory efficiency.
    
    Parameters
    ----------
    input_path : str
        Path to input .dxd file
    output_dir : str
        Directory for output files
    output_format : str
        'csv' or 'hdf5'
    split_mode : str, default='none'
        Splitting mode:
        - 'none': Single output file
        - 'count': Split into N equal segments
        - 'time_slices': Split by custom time ranges
    num_segments : int, optional
        Number of segments (required if split_mode='count')
    time_slices : list of (start_time, end_time) tuples, optional
        Time ranges in seconds (required if split_mode='time_slices')
    channels : list of str, optional
        Channel names to include (None = all channels)
    progress_callback : callable, optional
        Function(percentage: int, message: str) for progress updates
    
    Returns
    -------
    list of str
        Paths to created output files
    
    Raises
    ------
    ValueError
        If split_mode is invalid or required parameters are missing
    
    Examples
    --------
    # Single file conversion
    >>> files = convert_dxd_with_splitting(
    ...     'data.dxd', '/output', 'hdf5', split_mode='none'
    ... )
    >>> print(files)
    ['/output/data.h5']
    
    # Split into 10 equal segments
    >>> files = convert_dxd_with_splitting(
    ...     'data.dxd', '/output', 'hdf5',
    ...     split_mode='count', num_segments=10
    ... )
    >>> print(len(files))
    10
    
    # Split by custom time ranges
    >>> time_slices = [(0, 60), (60, 120), (120, 180)]
    >>> files = convert_dxd_with_splitting(
    ...     'data.dxd', '/output', 'csv',
    ...     split_mode='time_slices', time_slices=time_slices
    ... )
    
    Notes
    -----
    - Memory efficient: Processes one segment at a time
    - Each segment is a complete, standalone file
    - HDF5 segments maintain SpectralEdge-compatible structure
    - Output files are named: basename_segment_001.ext, basename_segment_002.ext, etc.
    """
    # Validate inputs
    if split_mode not in ['none', 'count', 'time_slices']:
        raise ValueError(f"Invalid split_mode: {split_mode}")
    
    if split_mode == 'count' and num_segments is None:
        raise ValueError("num_segments required when split_mode='count'")
    
    if split_mode == 'time_slices' and time_slices is None:
        raise ValueError("time_slices required when split_mode='time_slices'")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get file info
    if progress_callback:
        progress_callback(0, "Analyzing file...")
    
    file_info = get_dxd_file_info(input_path)
    duration = file_info['duration']
    
    # Determine file extension
    ext = 'h5' if output_format == 'hdf5' else 'csv'
    base_name = Path(input_path).stem
    
    # Calculate time slices based on split mode
    if split_mode == 'none':
        time_ranges = [(0, duration)]
        output_names = [f"{base_name}.{ext}"]
    elif split_mode == 'count':
        segment_duration = duration / num_segments
        time_ranges = [
            (i * segment_duration, min((i + 1) * segment_duration, duration))
            for i in range(num_segments)
        ]
        output_names = [
            f"{base_name}_segment_{i+1:03d}.{ext}"
            for i in range(num_segments)
        ]
    else:  # time_slices
        time_ranges = time_slices
        output_names = [
            f"{base_name}_slice_{i+1:03d}.{ext}"
            for i in range(len(time_slices))
        ]
    
    # Convert each segment
    output_files = []
    total_segments = len(time_ranges)
    
    for i, ((start, end), output_name) in enumerate(zip(time_ranges, output_names)):
        output_path = os.path.join(output_dir, output_name)
        
        # Calculate progress range for this segment
        segment_start_pct = int(i / total_segments * 100)
        segment_end_pct = int((i + 1) / total_segments * 100)
        
        # Progress callback wrapper for this segment
        def segment_progress(pct, msg):
            if progress_callback:
                overall_pct = segment_start_pct + int(pct * (segment_end_pct - segment_start_pct) / 100)
                progress_callback(overall_pct, f"Segment {i+1}/{total_segments}: {msg}")
        
        # Convert this time slice
        convert_dxd_to_format(
            input_path, output_path, output_format,
            time_range=(start, end),
            channels=channels,
            progress_callback=segment_progress
        )
        
        output_files.append(output_path)
    
    if progress_callback:
        progress_callback(100, f"Created {len(output_files)} file(s)")
    
    return output_files


def split_hdf5_by_count(
    input_path: str,
    output_dir: str,
    num_segments: int,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> List[str]:
    """
    Split an HDF5 file into N equal segments.
    
    Parameters
    ----------
    input_path : str
        Path to input HDF5 file
    output_dir : str
        Directory for output segment files
    num_segments : int
        Number of segments to create
    progress_callback : callable, optional
        Function(percentage: int, message: str) for progress updates
    
    Returns
    -------
    list of str
        Paths to created segment files
    
    Raises
    ------
    ValueError
        If num_segments < 1
    FileNotFoundError
        If input file doesn't exist
    
    Examples
    --------
    >>> files = split_hdf5_by_count('large.h5', '/output', 10)
    >>> print(f"Created {len(files)} segments")
    
    Notes
    -----
    - Each segment contains equal duration of data
    - Maintains SpectralEdge-compatible HDF5 structure
    - Preserves all metadata in each segment
    """
    if num_segments < 1:
        raise ValueError("num_segments must be >= 1")
    
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Open input file
    with h5py.File(input_path, 'r') as f_in:
        # Get first flight key
        flight_keys = list(f_in.keys())
        if not flight_keys:
            raise ValueError("No flights found in HDF5 file")
        
        flight_key = flight_keys[0]
        flight_group = f_in[flight_key]
        
        # Get first channel to determine total samples
        channel_keys = list(flight_group['channels'].keys())
        if not channel_keys:
            raise ValueError("No channels found in flight")
        
        first_channel = flight_group['channels'][channel_keys[0]]
        total_samples = len(first_channel['data'])
        sample_rate = first_channel.attrs['sample_rate']
        
        # Calculate segment boundaries
        samples_per_segment = total_samples // num_segments
        
        # Create output files
        base_name = Path(input_path).stem
        output_files = []
        
        for seg_idx in range(num_segments):
            start_idx = seg_idx * samples_per_segment
            if seg_idx == num_segments - 1:
                end_idx = total_samples  # Last segment gets remainder
            else:
                end_idx = (seg_idx + 1) * samples_per_segment
            
            output_name = f"{base_name}_segment_{seg_idx+1:03d}.h5"
            output_path = os.path.join(output_dir, output_name)
            
            # Create output file
            with h5py.File(output_path, 'w') as f_out:
                # Create flight group
                flight_out = f_out.create_group(flight_key)
                
                # Copy metadata
                metadata_group = flight_out.create_group('metadata')
                for key, value in flight_group['metadata'].attrs.items():
                    metadata_group.attrs[key] = value
                
                # Update duration for this segment
                segment_duration = (end_idx - start_idx) / sample_rate
                metadata_group.attrs['duration'] = segment_duration
                
                # Create channels group
                channels_out = flight_out.create_group('channels')
                
                # Copy each channel (sliced)
                for ch_name in channel_keys:
                    ch_in = flight_group['channels'][ch_name]
                    ch_out = channels_out.create_group(ch_name)
                    
                    # Copy sliced data
                    ch_out.create_dataset('data', data=ch_in['data'][start_idx:end_idx])
                    ch_out.create_dataset('time', data=ch_in['time'][start_idx:end_idx] - ch_in['time'][start_idx])
                    
                    # Copy attributes
                    for key, value in ch_in.attrs.items():
                        ch_out.attrs[key] = value
            
            output_files.append(output_path)
            
            if progress_callback:
                progress_callback(
                    int((seg_idx + 1) / num_segments * 100),
                    f"Created segment {seg_idx + 1}/{num_segments}"
                )
    
    return output_files


def split_hdf5_by_time_slices(
    input_path: str,
    output_dir: str,
    time_slices: List[Tuple[float, float]],
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> List[str]:
    """
    Split an HDF5 file by custom time ranges.
    
    Parameters
    ----------
    input_path : str
        Path to input HDF5 file
    output_dir : str
        Directory for output slice files
    time_slices : list of (start_time, end_time) tuples
        Time ranges in seconds to extract
    progress_callback : callable, optional
        Function(percentage: int, message: str) for progress updates
    
    Returns
    -------
    list of str
        Paths to created slice files
    
    Examples
    --------
    >>> slices = [(0, 60), (60, 120), (120, 180)]
    >>> files = split_hdf5_by_time_slices('data.h5', '/output', slices)
    
    Notes
    -----
    - Time slices can overlap or have gaps
    - Each slice is an independent HDF5 file
    - Maintains SpectralEdge-compatible structure
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Open input file
    with h5py.File(input_path, 'r') as f_in:
        # Get first flight
        flight_keys = list(f_in.keys())
        if not flight_keys:
            raise ValueError("No flights found in HDF5 file")
        
        flight_key = flight_keys[0]
        flight_group = f_in[flight_key]
        
        # Get channel info
        channel_keys = list(flight_group['channels'].keys())
        first_channel = flight_group['channels'][channel_keys[0]]
        sample_rate = first_channel.attrs['sample_rate']
        
        # Create output files
        base_name = Path(input_path).stem
        output_files = []
        
        for slice_idx, (start_time, end_time) in enumerate(time_slices):
            # Convert time to sample indices
            start_idx = int(start_time * sample_rate)
            end_idx = int(end_time * sample_rate)
            
            output_name = f"{base_name}_slice_{slice_idx+1:03d}.h5"
            output_path = os.path.join(output_dir, output_name)
            
            # Create output file (same logic as split_by_count)
            with h5py.File(output_path, 'w') as f_out:
                flight_out = f_out.create_group(flight_key)
                
                # Copy metadata
                metadata_group = flight_out.create_group('metadata')
                for key, value in flight_group['metadata'].attrs.items():
                    metadata_group.attrs[key] = value
                
                metadata_group.attrs['duration'] = end_time - start_time
                
                # Create channels
                channels_out = flight_out.create_group('channels')
                
                for ch_name in channel_keys:
                    ch_in = flight_group['channels'][ch_name]
                    ch_out = channels_out.create_group(ch_name)
                    
                    ch_out.create_dataset('data', data=ch_in['data'][start_idx:end_idx])
                    ch_out.create_dataset('time', data=ch_in['time'][start_idx:end_idx] - start_time)
                    
                    for key, value in ch_in.attrs.items():
                        ch_out.attrs[key] = value
            
            output_files.append(output_path)
            
            if progress_callback:
                progress_callback(
                    int((slice_idx + 1) / len(time_slices) * 100),
                    f"Created slice {slice_idx + 1}/{len(time_slices)}"
                )
    
    return output_files


def load_library(lib_dir: str):
    """Load DEWESoft library based on platform."""
    import platform
    
    system = platform.system()
    machine = platform.machine()
    
    if system == 'Windows':
        if machine.endswith('64'):
            lib_name = 'DWDataReaderLib64.dll'
        else:
            lib_name = 'DWDataReaderLib.dll'
    elif system == 'Linux':
        lib_name = 'libDWDataReaderLib64.so'
    elif system == 'Darwin':  # macOS
        lib_name = 'libDWDataReaderLib.dylib'
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
    
    lib_path = os.path.join(lib_dir, lib_name)
    
    if not os.path.exists(lib_path):
        raise FileNotFoundError(f"DEWESoft library not found: {lib_path}")
    
    return ctypes.CDLL(lib_path)


def check_error(lib, status):
    """Check DEWESoft library error status."""
    if status != 0:
        error_msg = ctypes.create_string_buffer(256)
        lib.DWGetLastError(error_msg, 256)
        raise RuntimeError(f"DEWESoft error {status}: {error_msg.value.decode('utf-8')}")
