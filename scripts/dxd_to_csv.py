#!/usr/bin/env python3
"""
DEWESoft DXD to CSV Converter
==============================

This script converts DEWESoft data files (.dxd or .dxz format) to CSV format using
the official DEWESoft Data Reader Library.

Author: SpectralEdge Development Team
License: MIT
Python Version: 3.8+

Dependencies:
    - ctypes (standard library)
    - csv (standard library)
    - argparse (standard library)
    - DEWESoft Data Reader Library (included in dewesoft/ directory)

Usage:
    python dxd_to_csv.py input.dxd output.csv
    python dxd_to_csv.py input.dxd output.csv --channels "Channel1,Channel2"
    python dxd_to_csv.py input.dxd output.csv --all-channels
    python dxd_to_csv.py input.dxd output.csv --max-samples 10000

Examples:
    # Convert all channels to CSV
    python dxd_to_csv.py data/flight_test.dxd output/flight_test.csv

    # Convert specific channels only
    python dxd_to_csv.py data/vibration.dxd output/vibration.csv --channels "Accel_X,Accel_Y,Accel_Z"

    # Limit output to first 10000 samples per channel
    python dxd_to_csv.py data/large_file.dxd output/preview.csv --max-samples 10000
"""

import sys
import os
import argparse
import csv
from pathlib import Path

# Try to import h5py for HDF5 support (optional)
try:
    import h5py
    import numpy as np
    HDF5_AVAILABLE = True
except ImportError:
    HDF5_AVAILABLE = False
    print("Warning: h5py not available. HDF5 output format will be disabled.")
    print("Install with: sudo pip3 install h5py numpy")

# Add the dewesoft directory to the Python path so we can import the library wrapper
script_dir = Path(__file__).parent
dewesoft_dir = script_dir / "dewesoft"
sys.path.insert(0, str(dewesoft_dir))

# Import the DEWESoft Data Reader Library wrapper
# This provides Python bindings to the native C library
try:
    from DWDataReaderHeader import *
except ImportError as e:
    print("ERROR: Could not import DEWESoft Data Reader Library wrapper.")
    print(f"Make sure DWDataReaderHeader.py is in: {dewesoft_dir}")
    print(f"Import error: {e}")
    sys.exit(1)


def print_section_header(title):
    """
    Print a formatted section header for better readability.
    
    Args:
        title (str): The title to display
    """
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def validate_input_file(file_path):
    """
    Validate that the input file exists and has a valid extension.
    
    Args:
        file_path (str): Path to the input file
        
    Returns:
        bool: True if file is valid, False otherwise
    """
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"ERROR: Input file does not exist: {file_path}")
        return False
    
    # Check if file has valid extension (.dxd or .dxz)
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in ['.dxd', '.dxz']:
        print(f"WARNING: File extension '{file_ext}' is not .dxd or .dxz")
        print("The file may not be a valid DEWESoft data file.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return False
    
    return True


def load_dewesoft_library():
    """
    Load the DEWESoft Data Reader Library.
    
    The library is a native shared library (.dll on Windows, .so on Linux)
    that provides functions to read DEWESoft data files.
    
    Returns:
        ctypes.CDLL: The loaded library object
        
    Raises:
        OSError: If the library cannot be loaded
    """
    print("Loading DEWESoft Data Reader Library...")
    
    try:
        # The load_library() function is defined in DWDataReaderHeader.py
        # It automatically selects the correct library based on platform and architecture
        lib = load_library()
        print("✓ Library loaded successfully")
        return lib
    except OSError as e:
        print(f"ERROR: Failed to load DEWESoft Data Reader Library")
        print(f"Details: {e}")
        print(f"\nMake sure the library files are in: {dewesoft_dir}")
        print("Required files:")
        print("  - Windows 64-bit: DWDataReaderLib64.dll")
        print("  - Windows 32-bit: DWDataReaderLib.dll")
        print("  - Linux 64-bit: DWDataReaderLib64.so")
        raise


def open_dxd_file(lib, file_path):
    """
    Open a DEWESoft data file and create a reader instance.
    
    Args:
        lib: The loaded DEWESoft library
        file_path (str): Path to the .dxd or .dxz file
        
    Returns:
        READER_HANDLE: Handle to the opened file reader
        
    Raises:
        RuntimeError: If the file cannot be opened
    """
    print(f"\nOpening file: {file_path}")
    
    # Step 1: Create a reader instance
    # This is a handle (pointer) that will be used for all subsequent operations
    reader_instance = READER_HANDLE()
    
    # Call DWICreateReader to initialize the reader handle
    # This MUST be called before DWIOpenDataFile
    print("Creating reader instance...")
    status = lib.DWICreateReader(ctypes.byref(reader_instance))
    check_error(lib, status)
    print("✓ Reader instance created")
    
    # Step 2: Open the data file
    # The file path is converted to bytes for the C library
    print("Opening data file...")
    c_filename = ctypes.c_char_p(file_path.encode('utf-8'))
    file_info = DWFileInfo(0, 0, 0)
    status = lib.DWIOpenDataFile(reader_instance, c_filename, ctypes.byref(file_info))
    
    # Check if the operation was successful
    check_error(lib, status)
    
    # Display file information
    print("\nFile Info:")
    print(f"  Sample rate:      {file_info.sample_rate:.2f} Hz")
    print(f"  Start store time: {file_info.start_store_time:.6f} s")
    print(f"  Duration:         {file_info.duration:.2f} s")
    
    print("✓ File opened successfully")
    return reader_instance


def get_file_metadata(lib, reader_instance):
    """
    Extract metadata from the DEWESoft file.
    
    Metadata includes sample rate, start time, duration, and other file-level information.
    
    Args:
        lib: The loaded DEWESoft library
        reader_instance: Handle to the opened file
        
    Returns:
        dict: Dictionary containing metadata fields
    """
    print_section_header("File Metadata")
    
    # Create a structure to hold measurement information
    # This structure is defined in DWDataReaderHeader.py
    measurement_info = DWMeasurementInfo(0, 0, 0, 0)
    
    # Get measurement information from the file
    check_error(lib, lib.DWIGetMeasurementInfo(reader_instance, ctypes.byref(measurement_info)))
    
    # Extract and display the metadata
    metadata = {
        'sample_rate': measurement_info.sample_rate,
        'start_measure_time': measurement_info.start_measure_time,
        'start_store_time': measurement_info.start_store_time,
        'duration': measurement_info.duration
    }
    
    print(f"Sample Rate:         {metadata['sample_rate']:.2f} Hz")
    print(f"Start Measure Time:  {metadata['start_measure_time']:.6f} s")
    print(f"Start Store Time:    {metadata['start_store_time']:.6f} s")
    print(f"Duration:            {metadata['duration']:.2f} s")
    
    # Get storing type (how data was recorded)
    storing_type_c = ctypes.c_int(DWStoringType.ST_ALWAYS_FAST)
    check_error(lib, lib.DWIGetStoringType(reader_instance, ctypes.byref(storing_type_c)))
    storing_type = DWStoringType(storing_type_c.value)
    print(f"Storing Type:        {storing_type.name}")
    
    return metadata


def get_channel_list(lib, reader_instance):
    """
    Get a list of all channels in the DEWESoft file.
    
    Channels are individual data streams (e.g., sensor readings, calculated values).
    Each channel has a name, unit, description, and data type.
    
    Args:
        lib: The loaded DEWESoft library
        reader_instance: Handle to the opened file
        
    Returns:
        list: List of DWChannel objects
    """
    print_section_header("Available Channels")
    
    # Get the number of channels in the file
    ch_count = ctypes.c_int()
    check_error(lib, lib.DWIGetChannelListCount(reader_instance, ctypes.byref(ch_count)))
    
    print(f"Total channels: {ch_count.value}")
    
    # Create an array to hold channel information
    # DWChannel is a structure defined in DWDataReaderHeader.py
    channel_list = (DWChannel * ch_count.value)()
    
    # Get the list of channels
    check_error(lib, lib.DWIGetChannelList(reader_instance, channel_list))
    
    # Display channel information
    print("\nChannel List:")
    print(f"{'Index':<8} {'Name':<30} {'Unit':<15} {'Type':<15}")
    print("-" * 70)
    
    for i, ch in enumerate(channel_list):
        # Decode bytes to strings for display
        ch_name = decode_bytes(ch.name)
        ch_unit = decode_bytes(ch.unit)
        ch_type = DWDataType(ch.data_type).name
        
        print(f"{ch.index:<8} {ch_name:<30} {ch_unit:<15} {ch_type:<15}")
    
    return list(channel_list)


def select_channels(channel_list, channel_names=None):
    """
    Select which channels to export based on user input.
    
    Args:
        channel_list (list): List of all available channels
        channel_names (str, optional): Comma-separated list of channel names to export
        
    Returns:
        list: List of selected DWChannel objects
    """
    # If no specific channels requested, return all channels
    if channel_names is None:
        print("\nExporting all channels")
        return channel_list
    
    # Parse the comma-separated channel names
    requested_names = [name.strip() for name in channel_names.split(',')]
    
    # Find matching channels
    selected_channels = []
    for requested_name in requested_names:
        # Search for the channel by name
        found = False
        for ch in channel_list:
            ch_name = decode_bytes(ch.name)
            if ch_name == requested_name:
                selected_channels.append(ch)
                found = True
                break
        
        if not found:
            print(f"WARNING: Channel '{requested_name}' not found in file")
    
    if not selected_channels:
        print("ERROR: No valid channels selected")
        sys.exit(1)
    
    print(f"\nExporting {len(selected_channels)} selected channel(s):")
    for ch in selected_channels:
        print(f"  - {decode_bytes(ch.name)}")
    
    return selected_channels


def get_channel_data(lib, reader_instance, channel, max_samples=None):
    """
    Read data from a specific channel.
    
    This function reads scaled samples (real engineering units) and timestamps
    for a given channel.
    
    Args:
        lib: The loaded DEWESoft library
        reader_instance: Handle to the opened file
        channel: DWChannel object to read
        max_samples (int, optional): Maximum number of samples to read
        
    Returns:
        tuple: (timestamps, values) where both are lists of floats
    """
    # Get the total number of samples for this channel
    sample_cnt = ctypes.c_longlong()
    check_error(lib, lib.DWIGetScaledSamplesCount(reader_instance, channel.index, 
                                                    ctypes.byref(sample_cnt)))
    
    total_samples = sample_cnt.value
    
    # Limit samples if requested
    if max_samples is not None and total_samples > max_samples:
        samples_to_read = max_samples
        print(f"  Limiting to first {max_samples} samples (file has {total_samples})")
    else:
        samples_to_read = total_samples
    
    # Allocate memory for the data
    # For array channels, we need to multiply by array_size
    total_count = samples_to_read * channel.array_size
    samples = (ctypes.c_double * total_count)()
    
    # Check if this is an asynchronous channel (has individual timestamps)
    # Get channel type property
    buf_len = ctypes.c_int(INT_SIZE)
    buff = create_string_buffer('', buf_len.value)
    p_buff = ctypes.cast(buff, ctypes.POINTER(ctypes.c_void_p))
    check_error(lib, lib.DWIGetChannelProps(reader_instance, channel.index, 
                                             DWChannelProps.DW_CH_TYPE, p_buff, 
                                             ctypes.byref(buf_len)))
    ch_type_val = ctypes.cast(p_buff, ctypes.POINTER(ctypes.c_int)).contents
    ch_type = DWChannelType(ch_type_val.value)
    
    # Allocate timestamps array for async channels
    timestamps = None
    if ch_type == DWChannelType.DW_CH_TYPE_ASYNC:
        timestamps = (ctypes.c_double * samples_to_read)()
    
    # Read the scaled samples from the file
    # Scaled samples are in engineering units (e.g., volts, g's, psi)
    check_error(lib, lib.DWIGetScaledSamples(reader_instance, channel.index, 0, 
                                              samples_to_read, samples, timestamps))
    
    # Convert ctypes arrays to Python lists
    values = list(samples)
    
    # For synchronous channels, generate timestamps based on sample rate
    if timestamps is None:
        # Get the file sample rate
        measurement_info = DWMeasurementInfo(0, 0, 0, 0)
        check_error(lib, lib.DWIGetMeasurementInfo(reader_instance, 
                                                     ctypes.byref(measurement_info)))
        sample_rate = measurement_info.sample_rate
        
        # Generate evenly-spaced timestamps
        if sample_rate > 0:
            time_step = 1.0 / sample_rate
            timestamps = [i * time_step for i in range(samples_to_read)]
        else:
            # If sample rate is unknown, use sample index
            timestamps = list(range(samples_to_read))
    else:
        # Convert timestamps to Python list
        timestamps = list(timestamps)
    
    return timestamps, values


def write_csv_file_chunked(lib, reader_instance, output_path, channels_info, metadata, chunk_size=100000):
    """
    Write channel data to CSV file using chunked reading to minimize memory usage.
    
    This function reads and writes data in chunks, so only a small portion of the file
    is in memory at any given time. This allows processing of very large files that
    would otherwise exceed available RAM.
    
    Args:
        lib: The loaded DEWESoft library
        reader_instance: Handle to the opened file
        output_path (str): Path to the output CSV file
        channels_info (list): List of tuples (channel, samples_to_export, ch_type)
        metadata (dict): File metadata dictionary
        chunk_size (int): Number of samples to read per chunk (default: 100,000)
    """
    print_section_header("Writing CSV File (Chunked Mode)")
    print(f"Output file: {output_path}")
    print(f"Chunk size: {chunk_size:,} samples")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    # Determine the maximum number of samples across all channels
    max_samples = 0
    for _, samples_to_export, _ in channels_info:
        max_samples = max(max_samples, samples_to_export)
    
    print(f"Total samples to write: {max_samples:,}")
    print(f"Number of chunks: {(max_samples + chunk_size - 1) // chunk_size}")
    
    # Estimate output CSV file size
    # Each value: ~10 bytes average (number + comma/newline)
    # Metadata + headers: ~1 KB
    num_columns = 1  # Time column
    for channel, _, _ in channels_info:
        num_columns += channel.array_size
    
    estimated_size_bytes = max_samples * num_columns * 10 + 1024
    estimated_size_mb = estimated_size_bytes / (1024 * 1024)
    estimated_size_gb = estimated_size_mb / 1024
    
    if estimated_size_gb >= 1.0:
        print(f"Estimated output file size: {estimated_size_gb:.2f} GB")
    else:
        print(f"Estimated output file size: {estimated_size_mb:.1f} MB")
    
    # Open the CSV file for writing (unbuffered for real-time growth)
    with open(output_path, 'w', newline='', buffering=1) as csvfile:
        writer = csv.writer(csvfile)
        
        # Write metadata as comments
        writer.writerow(['# DEWESoft Data Export'])
        writer.writerow([f'# Sample Rate: {metadata["sample_rate"]:.2f} Hz'])
        writer.writerow([f'# Duration: {metadata["duration"]:.2f} s'])
        writer.writerow([f'# Channels: {len(channels_info)}'])
        writer.writerow([])  # Empty row
        
        # Prepare header rows
        header_names = ['Time (s)']
        header_units = ['s']
        
        for channel, _, _ in channels_info:
            ch_name = decode_bytes(channel.name)
            ch_unit = decode_bytes(channel.unit)
            
            # Handle array channels (multiple values per timestamp)
            if channel.array_size > 1:
                for i in range(channel.array_size):
                    header_names.append(f"{ch_name}[{i}]")
                    header_units.append(ch_unit)
            else:
                header_names.append(ch_name)
                header_units.append(ch_unit)
        
        # Write header rows
        writer.writerow(header_names)
        writer.writerow(header_units)
        
        # Get sample rate for timestamp generation
        sample_rate = metadata['sample_rate']
        time_step = 1.0 / sample_rate if sample_rate > 0 else 0.0
        
        # Process data in chunks
        rows_written = 0
        chunk_num = 0
        
        for chunk_start in range(0, max_samples, chunk_size):
            chunk_num += 1
            chunk_end = min(chunk_start + chunk_size, max_samples)
            samples_in_chunk = chunk_end - chunk_start
            
            print(f"\rProcessing chunk {chunk_num}: samples {chunk_start:,} to {chunk_end:,}...", end='', flush=True)
            
            # Read data for all channels in this chunk
            chunk_data = []
            for channel, samples_to_export, ch_type in channels_info:
                # Determine how many samples to read for this channel in this chunk
                channel_chunk_end = min(chunk_end, samples_to_export)
                if chunk_start >= samples_to_export:
                    # This channel has no more data
                    chunk_data.append((channel, [], []))
                    continue
                
                channel_samples_in_chunk = channel_chunk_end - chunk_start
                
                # Allocate memory for this chunk only
                total_count = channel_samples_in_chunk * channel.array_size
                samples = (ctypes.c_double * total_count)()
                
                # Allocate timestamps for async channels
                timestamps = None
                if ch_type == DWChannelType.DW_CH_TYPE_ASYNC:
                    timestamps = (ctypes.c_double * channel_samples_in_chunk)()
                
                # Read the chunk of scaled samples
                check_error(lib, lib.DWIGetScaledSamples(reader_instance, channel.index, 
                                                          chunk_start, channel_samples_in_chunk, 
                                                          samples, timestamps))
                
                # Convert to Python lists (only for this chunk)
                values = list(samples)
                
                # For synchronous channels, generate timestamps
                if timestamps is None:
                    timestamps_list = [chunk_start * time_step + i * time_step for i in range(channel_samples_in_chunk)]
                else:
                    timestamps_list = list(timestamps)
                
                chunk_data.append((channel, timestamps_list, values))
            
            # Write this chunk to CSV
            for i in range(samples_in_chunk):
                row = []
                
                # Use the first channel's timestamps as the time column
                if chunk_data[0][1]:  # Check if first channel has data
                    row.append(f"{chunk_data[0][1][i]:.6f}")
                else:
                    row.append(f"{(chunk_start + i) * time_step:.6f}")
                
                # Add values from each channel
                for channel, timestamps_list, values in chunk_data:
                    if i < len(timestamps_list):
                        # Handle array channels
                        if channel.array_size > 1:
                            for j in range(channel.array_size):
                                idx = i * channel.array_size + j
                                if idx < len(values):
                                    row.append(f"{values[idx]:.6f}")
                                else:
                                    row.append('')
                        else:
                            row.append(f"{values[i]:.6f}")
                    else:
                        # Fill with empty values if this channel has no data at this index
                        if channel.array_size > 1:
                            row.extend([''] * channel.array_size)
                        else:
                            row.append('')
                
                writer.writerow(row)
                rows_written += 1
            
            # Flush to disk after each chunk for visible file growth
            csvfile.flush()
            os.fsync(csvfile.fileno())
        
        print()  # New line after progress
        print(f"✓ CSV file written successfully")
        print(f"  Rows: {rows_written:,}")
        print(f"  Columns: {len(header_names)}")


def write_csv_file(output_path, channels_data, metadata):
    """
    Write channel data to a CSV file.
    
    The CSV file will have the following structure:
    - Header row 1: Channel names
    - Header row 2: Channel units
    - Data rows: Time column followed by channel value columns
    
    Args:
        output_path (str): Path to the output CSV file
        channels_data (list): List of tuples (channel, timestamps, values)
        metadata (dict): File metadata dictionary
    """
    print_section_header("Writing CSV File")
    print(f"Output file: {output_path}")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    # Open the CSV file for writing (unbuffered for real-time growth)
    with open(output_path, 'w', newline='', buffering=1) as csvfile:
        writer = csv.writer(csvfile)
        
        # Write metadata as comments (some CSV readers support this)
        writer.writerow(['# DEWESoft Data Export'])
        writer.writerow([f'# Sample Rate: {metadata["sample_rate"]} Hz'])
        writer.writerow([f'# Duration: {metadata["duration"]} s'])
        writer.writerow([f'# Channels: {len(channels_data)}'])
        writer.writerow([])  # Empty row
        
        # Prepare header rows
        # Row 1: Channel names
        header_names = ['Time (s)']
        # Row 2: Channel units
        header_units = ['s']
        
        for channel, _, _ in channels_data:
            ch_name = decode_bytes(channel.name)
            ch_unit = decode_bytes(channel.unit)
            
            # Handle array channels (multiple values per timestamp)
            if channel.array_size > 1:
                for i in range(channel.array_size):
                    header_names.append(f"{ch_name}[{i}]")
                    header_units.append(ch_unit)
            else:
                header_names.append(ch_name)
                header_units.append(ch_unit)
        
        # Write header rows
        writer.writerow(header_names)
        writer.writerow(header_units)
        
        # Determine the maximum number of samples across all channels
        max_samples = 0
        for _, timestamps, _ in channels_data:
            max_samples = max(max_samples, len(timestamps))
        
        print(f"Writing {max_samples} rows...")
        
        # Write data rows
        for i in range(max_samples):
            row = []
            
            # Use the first channel's timestamps as the time column
            # (all synchronous channels should have the same time base)
            if i < len(channels_data[0][1]):
                row.append(f"{channels_data[0][1][i]:.6f}")
            else:
                row.append('')
            
            # Add values from each channel
            for channel, timestamps, values in channels_data:
                if i < len(timestamps):
                    # Handle array channels
                    if channel.array_size > 1:
                        for j in range(channel.array_size):
                            idx = i * channel.array_size + j
                            if idx < len(values):
                                row.append(f"{values[idx]:.6f}")
                            else:
                                row.append('')
                    else:
                        row.append(f"{values[i]:.6f}")
                else:
                    # Fill with empty values if this channel has fewer samples
                    if channel.array_size > 1:
                        row.extend([''] * channel.array_size)
                    else:
                        row.append('')
            
            writer.writerow(row)
        
        print(f"✓ CSV file written successfully")
        print(f"  Rows: {max_samples}")
        print(f"  Columns: {len(header_names)}")


def determine_output_format(args, channels_info, max_samples):
    """
    Determine output format and path based on arguments or interactive selection.
    
    Args:
        args: Parsed command-line arguments
        channels_info: List of (channel, samples_to_export, ch_type) tuples
        max_samples: Maximum number of samples across all channels
        
    Returns:
        tuple: (format_str, output_path) where format_str is 'csv' or 'hdf5'
    """
    # Calculate size estimates
    num_columns = 1  # Time column
    for channel, _, _ in channels_info:
        num_columns += channel.array_size
    
    # CSV estimate: ~10 bytes per value (text representation)
    csv_size_bytes = max_samples * num_columns * 10 + 1024
    csv_size_mb = csv_size_bytes / (1024 * 1024)
    csv_size_gb = csv_size_mb / 1024
    
    # HDF5 estimate: ~4 bytes per value (compressed binary)
    total_values = sum(samples * ch.array_size for ch, samples, _ in channels_info)
    hdf5_size_bytes = total_values * 4 + 10240
    hdf5_size_mb = hdf5_size_bytes / (1024 * 1024)
    hdf5_size_gb = hdf5_size_mb / 1024
    
    # Interactive mode or no output file specified
    if args.interactive or args.output_file is None:
        print_section_header("Output Format Selection")
        print("\nEstimated output file sizes:")
        print("\n1. CSV Format:")
        if csv_size_gb >= 1.0:
            print(f"   Size: {csv_size_gb:.2f} GB")
        else:
            print(f"   Size: {csv_size_mb:.1f} MB")
        print("   Pros: Universal compatibility, human-readable, works with Excel")
        print("   Cons: Large file size, slower read/write, text-based")
        
        if HDF5_AVAILABLE:
            print("\n2. HDF5 Format:")
            if hdf5_size_gb >= 1.0:
                print(f"   Size: {hdf5_size_gb:.2f} GB (compressed)")
            else:
                print(f"   Size: {hdf5_size_mb:.1f} MB (compressed)")
            print(f"   Compression ratio: {csv_size_mb / hdf5_size_mb:.1f}x smaller than CSV")
            print("   Pros: Compact, fast, preserves metadata, works with MATLAB/Python/SpectralEdge")
            print("   Cons: Requires HDF5-compatible tools")
        else:
            print("\n2. HDF5 Format: NOT AVAILABLE (h5py not installed)")
            print("   Install with: sudo pip3 install h5py numpy")
        
        # Prompt for selection
        while True:
            if HDF5_AVAILABLE:
                choice = input("\nSelect format (1=CSV, 2=HDF5): ").strip()
                if choice == '1':
                    output_format = 'csv'
                    break
                elif choice == '2':
                    output_format = 'hdf5'
                    break
                else:
                    print("Invalid choice. Please enter 1 or 2.")
            else:
                choice = input("\nOnly CSV format available. Press Enter to continue: ")
                output_format = 'csv'
                break
        
        # Get output path
        if args.output_file:
            output_path = args.output_file
        else:
            default_ext = '.h5' if output_format == 'hdf5' else '.csv'
            default_name = args.input_file.replace('.dxd', default_ext).replace('.dxz', default_ext)
            output_path = input(f"\nOutput file path [{default_name}]: ").strip()
            if not output_path:
                output_path = default_name
        
        return output_format, output_path
    
    # Non-interactive mode: determine from arguments
    output_path = args.output_file
    
    # Check if format specified explicitly
    if args.format:
        if args.format in ['hdf5', 'h5']:
            if not HDF5_AVAILABLE:
                print("ERROR: HDF5 format requested but h5py is not installed.")
                print("Install with: sudo pip3 install h5py numpy")
                sys.exit(1)
            return 'hdf5', output_path
        else:
            return 'csv', output_path
    
    # Auto-detect from file extension
    if output_path.endswith('.h5') or output_path.endswith('.hdf5'):
        if not HDF5_AVAILABLE:
            print("ERROR: HDF5 output requested (file extension .h5/.hdf5) but h5py is not installed.")
            print("Install with: sudo pip3 install h5py numpy")
            sys.exit(1)
        return 'hdf5', output_path
    else:
        return 'csv', output_path


def main():
    """
    Main function to orchestrate the DXD file conversion process.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Convert DEWESoft .dxd files to CSV format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.dxd output.csv
  %(prog)s input.dxd output.csv --channels "Accel_X,Accel_Y,Accel_Z"
  %(prog)s input.dxd output.csv --max-samples 10000
        """
    )
    
    parser.add_argument('input_file', help='Path to input .dxd or .dxz file')
    parser.add_argument('output_file', nargs='?', help='Path to output file (extension determines format: .csv or .h5)')
    parser.add_argument('--format', choices=['csv', 'hdf5', 'h5'], help='Output format (csv or hdf5/h5). Auto-detected from output_file extension if not specified.')
    parser.add_argument('--channels', help='Comma-separated list of channel names to export (default: all)')
    parser.add_argument('--max-samples', type=int, help='Maximum number of samples to export per channel')
    parser.add_argument('--all-channels', action='store_true', help='Export all channels (default behavior)')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode: prompts for format selection with size estimates')
    
    args = parser.parse_args()
    
    # Display script header
    print_section_header("DEWESoft DXD to CSV Converter")
    print("This script converts DEWESoft data files to CSV format")
    print("using the official DEWESoft Data Reader Library.")
    
    # Validate input file
    if not validate_input_file(args.input_file):
        sys.exit(1)
    
    try:
        # Step 1: Load the DEWESoft library
        lib = load_dewesoft_library()
        
        # Step 2: Open the DXD file
        reader_instance = open_dxd_file(lib, args.input_file)
        
        # Step 3: Get file metadata
        metadata = get_file_metadata(lib, reader_instance)
        
        # Step 4: Get list of available channels
        channel_list = get_channel_list(lib, reader_instance)
        
        # Step 5: Select channels to export
        selected_channels = select_channels(channel_list, args.channels)
        
        # Step 6: Get channel information (without loading all data)
        print_section_header("Analyzing Channels")
        channels_info = []
        total_data_size = 0
        
        for i, channel in enumerate(selected_channels):
            ch_name = decode_bytes(channel.name)
            print(f"\nChannel {i+1}/{len(selected_channels)}: {ch_name}")
            
            # Get sample count and type without loading data
            sample_cnt = ctypes.c_longlong()
            check_error(lib, lib.DWIGetScaledSamplesCount(reader_instance, channel.index, 
                                                            ctypes.byref(sample_cnt)))
            total_samples = sample_cnt.value
            
            # Limit samples if requested
            if args.max_samples is not None and total_samples > args.max_samples:
                samples_to_export = args.max_samples
                print(f"  Total samples: {total_samples:,} (limiting to {args.max_samples:,})")
            else:
                samples_to_export = total_samples
                print(f"  Total samples: {total_samples:,}")
            
            print(f"  Array size: {channel.array_size}")
            
            # Get channel type
            buf_len = ctypes.c_int(INT_SIZE)
            buff = create_string_buffer('', buf_len.value)
            p_buff = ctypes.cast(buff, ctypes.POINTER(ctypes.c_void_p))
            check_error(lib, lib.DWIGetChannelProps(reader_instance, channel.index, 
                                                     DWChannelProps.DW_CH_TYPE, p_buff, 
                                                     ctypes.byref(buf_len)))
            ch_type_val = ctypes.cast(p_buff, ctypes.POINTER(ctypes.c_int)).contents
            ch_type = DWChannelType(ch_type_val.value)
            
            # Estimate memory usage
            data_size_mb = (samples_to_export * channel.array_size * 8) / (1024 * 1024)  # 8 bytes per double
            total_data_size += data_size_mb
            print(f"  Estimated data size: {data_size_mb:.1f} MB")
            
            channels_info.append((channel, samples_to_export, ch_type))
        
        print(f"\nTotal estimated data size: {total_data_size:.1f} MB")
        
        # Calculate max samples across all channels
        max_samples = max(samples for _, samples, _ in channels_info)
        
        # Step 6.5: Determine output format and file path
        output_format, output_path = determine_output_format(args, channels_info, max_samples)
        
        # Determine if we should use chunked reading
        # Use chunked reading if total data > 500 MB to prevent memory errors
        use_chunked = total_data_size > 500
        
        if use_chunked:
            print("\n⚠ Large file detected - using memory-efficient chunked reading")
            chunk_size = 100000  # Read 100k samples at a time
            
            # Step 7: Write data to file using chunked reading
            if output_format == 'hdf5':
                # Import HDF5 writer
                from hdf5_writer import write_hdf5_file_chunked
                write_hdf5_file_chunked(lib, reader_instance, output_path,
                                        channels_info, metadata, chunk_size)
            else:
                write_csv_file_chunked(lib, reader_instance, output_path,
                                       channels_info, metadata, chunk_size)
        else:
            print("\n✓ File size is manageable - using standard reading")
            
            # Step 6b: Read all data into memory (original method)
            print_section_header("Reading Channel Data")
            channels_data = []
            
            for i, (channel, samples_to_export, ch_type) in enumerate(channels_info):
                ch_name = decode_bytes(channel.name)
                print(f"\nReading channel {i+1}/{len(selected_channels)}: {ch_name}")
                
                timestamps, values = get_channel_data(lib, reader_instance, channel, 
                                                       samples_to_export)
                
                print(f"  Samples read: {len(timestamps)}")
                
                channels_data.append((channel, timestamps, values))
            
            # Step 7: Write data to file
            if output_format == 'hdf5':
                # For small files, still use chunked HDF5 writer
                sys.path.insert(0, str(script_dir))
                from hdf5_writer import write_hdf5_file_chunked
                write_hdf5_file_chunked(lib, reader_instance, output_path,
                                        channels_info, metadata, chunk_size=100000)
            else:
                write_csv_file(output_path, channels_data, metadata)
        
        # Step 8: Clean up - close the file and destroy reader
        print("\nClosing file...")
        lib.DWICloseDataFile(reader_instance)
        print("✓ File closed")
        
        print("Destroying reader instance...")
        lib.DWIDestroyReader(reader_instance)
        print("✓ Reader destroyed")
        
        # Success message
        print_section_header("Conversion Complete")
        print(f"✓ Successfully converted {args.input_file}")
        print(f"✓ Output saved to {output_path}")
        print(f"✓ Format: {output_format.upper()}")
        print(f"✓ Exported {len(selected_channels)} channel(s)")
        
    except Exception as e:
        # Handle any errors that occurred during the conversion
        print(f"\n{'='*70}")
        print("ERROR: Conversion failed")
        print(f"{'='*70}")
        print(f"Error details: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
