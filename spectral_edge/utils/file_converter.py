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
import re
import numpy as np
import h5py
from typing import Optional, List, Tuple, Callable, Dict, Any
from pathlib import Path
from scipy.io import savemat

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


def _to_text(value: Any) -> str:
    """Convert metadata value to text for robust MAT-file field assignment."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return ""
        if value.ndim == 0:
            return _to_text(value.item())
        return str(value.tolist())
    if isinstance(value, np.generic):
        return str(value.item())
    return str(value)


def _to_scalar(value: Any) -> Any:
    """Convert numpy/h5py scalar-like values to plain Python scalars."""
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            return _to_scalar(value.item())
        return value.tolist()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _sanitize_matlab_identifier(name: str, prefix: str = "ch", max_len: int = 63) -> str:
    """
    Create a MATLAB-safe identifier.

    Rules:
    - Replace spaces and hyphens with underscores
    - Remove invalid characters
    - Ensure first character is a letter (prefix with `ch_` if needed)
    - Guarantee fallback validity
    """
    text = _to_text(name).strip()
    text = text.replace("-", "_").replace(" ", "_")
    text = re.sub(r"[^A-Za-z0-9_]", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")

    if not text:
        text = "channel"

    if not re.match(r"^[A-Za-z]", text):
        text = f"{prefix}_{text}"

    text = re.sub(r"[^A-Za-z0-9_]", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    if not re.match(r"^[A-Za-z]", text):
        text = f"{prefix}_{text}"

    if len(text) > max_len:
        text = text[:max_len].rstrip("_")

    if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", text):
        return "ch_channel"

    return text


def _sanitize_matlab_field_name(name: str, prefix: str = "meta", max_len: int = 63) -> str:
    """Create a safe MATLAB struct field name."""
    return _sanitize_matlab_identifier(name, prefix=prefix, max_len=max_len)


def _make_unique_output_path(
    output_dir: str,
    base_name: str,
    extension: str,
    reserved_paths: set
) -> str:
    """Return a collision-safe output path."""
    safe_base = _sanitize_filename(base_name) or "output"
    candidate = os.path.join(output_dir, f"{safe_base}{extension}")
    counter = 2
    while candidate in reserved_paths or os.path.exists(candidate):
        candidate = os.path.join(output_dir, f"{safe_base}_{counter:03d}{extension}")
        counter += 1
    reserved_paths.add(candidate)
    return candidate


def _resolve_channel_time_and_sample_rate(
    channel_group: h5py.Group,
    channel_name: str,
    flight_key: str
) -> Tuple[np.ndarray, float]:
    """Resolve channel time vector and sample rate for MARVIN export."""
    if 'data' not in channel_group:
        raise ValueError(
            f"Channel '{channel_name}' in flight '{flight_key}' is missing 'data' dataset"
        )

    data_len = len(channel_group['data'])
    if data_len <= 0:
        raise ValueError(
            f"Channel '{channel_name}' in flight '{flight_key}' has no samples"
        )

    sample_rate_attr = channel_group.attrs.get('sample_rate')
    sample_rate = None
    if sample_rate_attr is not None:
        try:
            sample_rate_candidate = float(_to_scalar(sample_rate_attr))
            if sample_rate_candidate > 0:
                sample_rate = sample_rate_candidate
        except (TypeError, ValueError):
            sample_rate = None

    if 'time' in channel_group:
        time_vec = np.asarray(channel_group['time'][:], dtype=np.float64)
        if len(time_vec) != data_len:
            raise ValueError(
                f"Length mismatch for channel '{channel_name}' in flight '{flight_key}': "
                f"data length {data_len} vs time length {len(time_vec)}"
            )

        if sample_rate is None and len(time_vec) > 1:
            dt = np.diff(time_vec)
            dt = dt[np.isfinite(dt) & (dt > 0)]
            if len(dt) > 0:
                sample_rate = float(1.0 / np.median(dt))

        if sample_rate is None or sample_rate <= 0:
            raise ValueError(
                f"Could not determine sample rate for channel '{channel_name}' in flight '{flight_key}'"
            )

        return time_vec, float(sample_rate)

    if sample_rate is None or sample_rate <= 0:
        raise ValueError(
            f"Missing both time dataset and valid sample_rate for "
            f"channel '{channel_name}' in flight '{flight_key}'"
        )

    start_time_attr = channel_group.attrs.get('start_time', 0.0)
    start_time = float(_to_scalar(start_time_attr)) if start_time_attr is not None else 0.0
    time_vec = start_time + (np.arange(data_len, dtype=np.float64) / sample_rate)
    return time_vec, float(sample_rate)


def _build_marvin_struct(
    input_file_name: str,
    flight_key: str,
    channel_name: str,
    channel_group: h5py.Group
) -> Dict[str, Any]:
    """Build MARVIN output structure with required and optional fields."""
    data = np.asarray(channel_group['data'][:], dtype=np.float64).reshape(-1, 1)
    time_vec, sample_rate = _resolve_channel_time_and_sample_rate(channel_group, channel_name, flight_key)
    time_vec = np.asarray(time_vec, dtype=np.float64).reshape(-1, 1)

    units_value = channel_group.attrs.get('units', channel_group.attrs.get('unit', ""))
    units_text = _to_text(units_value)

    marvin_struct: Dict[str, Any] = {
        'amp': data,
        't': time_vec,
        'sr': float(sample_rate),
        'source': 'MARVIN',
        'units': units_text,
        'name': _to_text(channel_name),
        'desc': input_file_name,
        'flight': _to_text(flight_key),
        'channel_path': f"{flight_key}/channels/{channel_name}",
        'sample_count': int(len(data)),
    }

    # Include additional metadata fields when available, with safe names.
    required_keys = {'amp', 't', 'sr', 'source', 'units', 'name', 'desc'}
    for attr_key, attr_value in channel_group.attrs.items():
        if attr_key in {'units', 'unit', 'sample_rate'}:
            continue
        field_name = _sanitize_matlab_field_name(attr_key, prefix="meta")
        if field_name in required_keys or field_name in marvin_struct:
            field_name = _sanitize_matlab_field_name(f"meta_{attr_key}", prefix="meta")
        if field_name in required_keys or field_name in marvin_struct:
            continue
        marvin_struct[field_name] = _to_scalar(attr_value)

    return marvin_struct


def convert_hdf5_to_marvin_mat(
    input_path: str,
    output_dir: str,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> List[str]:
    """
    Convert SpectralEdge HDF5 data to MARVIN MATLAB files.

    One output .mat file is created for each (flight, channel) pair.
    Each .mat contains one top-level variable named using a MATLAB-safe
    version of the channel name, holding the MARVIN struct fields.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    os.makedirs(output_dir, exist_ok=True)
    input_file_name = Path(input_path).name

    if progress_callback:
        progress_callback(0, "Analyzing HDF5 structure...")

    output_files: List[str] = []
    reserved_paths: set = set()

    with h5py.File(input_path, 'r') as f_in:
        flights = _get_flight_groups(f_in)
        if not flights:
            raise ValueError("No flight groups found in HDF5 file")

        channel_refs: List[Tuple[str, str, h5py.Group]] = []
        for flight_key, flight_group in flights:
            for channel_name in flight_group['channels'].keys():
                channel_refs.append((flight_key, channel_name, flight_group['channels'][channel_name]))

        if not channel_refs:
            raise ValueError("No channels found in HDF5 file")

        total_channels = len(channel_refs)
        for idx, (flight_key, channel_name, channel_group) in enumerate(channel_refs, start=1):
            if progress_callback:
                progress_callback(
                    int((idx - 1) / total_channels * 100),
                    f"Converting {flight_key}/{channel_name} ({idx}/{total_channels})..."
                )

            mat_var_name = _sanitize_matlab_identifier(channel_name, prefix="ch")
            marvin_struct = _build_marvin_struct(
                input_file_name=input_file_name,
                flight_key=flight_key,
                channel_name=channel_name,
                channel_group=channel_group
            )

            base_file_name = f"{flight_key}_{channel_name}"
            output_path = _make_unique_output_path(
                output_dir=output_dir,
                base_name=base_file_name,
                extension=".mat",
                reserved_paths=reserved_paths
            )

            savemat(
                output_path,
                {mat_var_name: marvin_struct},
                long_field_names=True,
                do_compression=True
            )
            output_files.append(output_path)

    if progress_callback:
        progress_callback(100, f"Created {len(output_files)} MATLAB file(s)")

    return output_files


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


def _get_flight_groups(h5_file: h5py.File) -> List[Tuple[str, h5py.Group]]:
    """Return top-level groups that match the SpectralEdge flight structure."""
    flights: List[Tuple[str, h5py.Group]] = []
    for key in h5_file.keys():
        obj = h5_file[key]
        if not isinstance(obj, h5py.Group):
            continue
        if 'channels' not in obj:
            continue
        if not isinstance(obj['channels'], h5py.Group):
            continue
        flights.append((key, obj))
    return flights


def _get_channel_sample_rate(channel_group: h5py.Group, channel_name: str, flight_key: str) -> float:
    """Get validated channel sample rate from attributes."""
    sample_rate = channel_group.attrs.get('sample_rate')
    if sample_rate is None:
        raise ValueError(f"Missing sample_rate for channel '{channel_name}' in flight '{flight_key}'")
    sample_rate = float(sample_rate)
    if sample_rate <= 0:
        raise ValueError(
            f"Invalid sample_rate ({sample_rate}) for channel '{channel_name}' in flight '{flight_key}'"
        )
    return sample_rate


def _get_flight_min_duration(flight_group: h5py.Group, flight_key: str) -> float:
    """Get maximum safe duration common to all channels in a flight."""
    channel_keys = list(flight_group['channels'].keys())
    if not channel_keys:
        raise ValueError(f"No channels found in flight '{flight_key}'")

    durations = []
    for channel_key in channel_keys:
        channel_group = flight_group['channels'][channel_key]
        if 'data' not in channel_group:
            raise ValueError(f"Channel '{channel_key}' in flight '{flight_key}' is missing 'data' dataset")
        data_len = len(channel_group['data'])
        if data_len == 0:
            raise ValueError(f"No samples found in channel '{channel_key}' in flight '{flight_key}'")
        sample_rate = _get_channel_sample_rate(channel_group, channel_key, flight_key)
        durations.append(data_len / sample_rate)

    return min(durations)


def _copy_non_flight_top_level_items(
    f_in: h5py.File,
    f_out: h5py.File,
    flight_keys: List[str]
) -> None:
    """Copy top-level datasets/groups that are not flight groups."""
    flight_key_set = set(flight_keys)
    for key in f_in.keys():
        if key in flight_key_set:
            continue
        f_in.copy(key, f_out, name=key)


def _write_hdf5_segment_file(
    f_in: h5py.File,
    output_path: str,
    flights: List[Tuple[str, h5py.Group]],
    start_time: float,
    end_time: float
) -> None:
    """Write one split HDF5 file for the requested time window."""
    flight_keys = [flight_key for flight_key, _ in flights]
    with h5py.File(output_path, 'w') as f_out:
        _copy_non_flight_top_level_items(f_in, f_out, flight_keys)

        for flight_key, flight_group in flights:
            flight_out = f_out.create_group(flight_key)

            if 'metadata' in flight_group and isinstance(flight_group['metadata'], h5py.Group):
                metadata_out = flight_out.create_group('metadata')
                for key, value in flight_group['metadata'].attrs.items():
                    metadata_out.attrs[key] = value
                metadata_out.attrs['duration'] = end_time - start_time
                metadata_out.attrs['split_start_time'] = start_time
                metadata_out.attrs['split_end_time'] = end_time
                metadata_out.attrs['time_reference'] = 'absolute'

            channels_out = flight_out.create_group('channels')
            for channel_name in flight_group['channels'].keys():
                ch_in = flight_group['channels'][channel_name]
                if 'data' not in ch_in:
                    raise ValueError(
                        f"Channel '{channel_name}' in flight '{flight_key}' is missing 'data' dataset"
                    )

                sample_rate = _get_channel_sample_rate(ch_in, channel_name, flight_key)
                total_samples = len(ch_in['data'])

                start_idx = max(0, min(int(start_time * sample_rate), total_samples))
                end_idx = max(start_idx, min(int(end_time * sample_rate), total_samples))

                ch_out = channels_out.create_group(channel_name)
                ch_out.create_dataset('data', data=ch_in['data'][start_idx:end_idx])

                if 'time' in ch_in:
                    time_slice = ch_in['time'][start_idx:end_idx]
                else:
                    channel_start_time = float(ch_in.attrs.get('start_time', 0.0))
                    time_slice = channel_start_time + (
                        np.arange(start_idx, end_idx, dtype=np.float64) / sample_rate
                    )

                ch_out.create_dataset('time', data=time_slice)

                for key, value in ch_in.attrs.items():
                    ch_out.attrs[key] = value

                if len(time_slice) > 0:
                    ch_out.attrs['start_time'] = float(time_slice[0])


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
        flights = _get_flight_groups(f_in)
        if not flights:
            raise ValueError("No flight groups found in HDF5 file")

        # Use the minimum common duration so every output contains every flight/channel.
        min_duration = min(_get_flight_min_duration(flight_group, flight_key) for flight_key, flight_group in flights)
        if min_duration <= 0:
            raise ValueError("No valid duration found in flight channels")

        base_name = Path(input_path).stem
        output_files = []
        
        for seg_idx in range(num_segments):
            start_time = (seg_idx * min_duration) / num_segments
            end_time = ((seg_idx + 1) * min_duration) / num_segments
            output_name = f"{base_name}_segment_{seg_idx+1:03d}.hdf5"
            output_path = os.path.join(output_dir, output_name)
            _write_hdf5_segment_file(f_in, output_path, flights, start_time, end_time)
            
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
        flights = _get_flight_groups(f_in)
        if not flights:
            raise ValueError("No flight groups found in HDF5 file")

        max_duration = min(_get_flight_min_duration(flight_group, flight_key) for flight_key, flight_group in flights)
        if max_duration <= 0:
            raise ValueError("No valid duration found in flight channels")
        
        # Create output files
        base_name = Path(input_path).stem
        output_files = []
        
        for slice_idx, (start_time, end_time) in enumerate(time_slices):
            if start_time < 0 or end_time <= start_time:
                raise ValueError(f"Invalid time slice ({start_time}, {end_time})")

            if end_time > max_duration:
                raise ValueError(
                    f"Time slice ({start_time}, {end_time}) exceeds available duration ({max_duration:.2f}s)"
                )
            
            output_name = f"{base_name}_slice_{slice_idx+1:03d}.hdf5"
            output_path = os.path.join(output_dir, output_name)
            _write_hdf5_segment_file(f_in, output_path, flights, start_time, end_time)
            
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
