"""
HDF5 Writer for DEWESoft Data Conversion
==========================================

This module provides memory-efficient HDF5 writing with chunked reading,
formatted to match SpectralEdge tool expectations.

Expected HDF5 Structure for SpectralEdge:
-----------------------------------------
/flight_XXX/                    # Top-level flight group (e.g., flight_001)
    /metadata/                  # Flight metadata group
        (attributes)            # flight_id, duration, sample_rate, start_time
    /channels/                  # Channels group
        /channel_name/          # Each channel as a subgroup
            data (dataset)      # Channel values (1D array)
            time (dataset)      # Timestamps (1D array)
            (attributes)        # sample_rate, units, description

Author: SpectralEdge Development Team
License: MIT
"""

import ctypes
import h5py
import numpy as np
from DWDataReaderHeader import *


def write_hdf5_file_chunked(lib, reader_instance, output_path, channels_info, metadata, chunk_size=100000):
    """
    Write channel data to HDF5 file using chunked reading to minimize memory usage.
    
    Creates an HDF5 file compatible with SpectralEdge tools using the structure:
        /flight_001/metadata/  (flight-level metadata as attributes)
        /flight_001/channels/channel_name/data  (channel values)
        /flight_001/channels/channel_name/time  (timestamps)
    
    HDF5 format advantages over CSV:
    - 5-10x smaller file size (binary + compression)
    - Much faster read/write performance
    - Preserves data types and metadata
    - Compatible with MATLAB, Python (pandas, h5py), and SpectralEdge tools
    - Supports lazy loading for memory-efficient access
    
    Parameters
    ----------
    lib : ctypes.CDLL
        The loaded DEWESoft library handle
    reader_instance : READER_HANDLE
        Handle to the opened DEWESoft file
    output_path : str
        Path to the output .h5 file
    channels_info : list of tuple
        List of (channel, samples_to_export, ch_type) tuples where:
        - channel: DWChannel object with name, unit, array_size, index
        - samples_to_export: int, number of samples to write
        - ch_type: DWChannelType enum value
    metadata : dict
        File metadata dictionary with keys:
        - sample_rate: float, sampling rate in Hz
        - duration: float, recording duration in seconds
        - start_time: float, start timestamp (optional)
    chunk_size : int, optional
        Number of samples to read per chunk (default: 100,000)
        Smaller chunks use less memory but may be slower
    
    Returns
    -------
    None
    
    Raises
    ------
    IOError
        If file cannot be created or written
    RuntimeError
        If DEWESoft library calls fail
    
    Examples
    --------
    >>> write_hdf5_file_chunked(lib, reader, 'output.h5', channels, meta, chunk_size=50000)
    
    Notes
    -----
    - Uses GZIP compression level 4 for good balance of size/speed
    - Writes data in chunks to minimize memory usage
    - Compatible with SpectralEdge HDF5FlightDataLoader
    - Each channel group contains 'data' and 'time' datasets
    - Metadata stored as HDF5 attributes for fast access
    """
    print_section_header("Writing HDF5 File (Chunked Mode)")
    print(f"Output file: {output_path}")
    print(f"Chunk size: {chunk_size:,} samples")
    
    # Create output directory if it doesn't exist
    import os
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
    
    # Estimate output HDF5 file size
    # HDF5 with compression: ~4 bytes per value (compressed double)
    # Metadata: ~10 KB
    total_values = 0
    for channel, samples_to_export, _ in channels_info:
        total_values += samples_to_export * channel.array_size
    
    estimated_size_bytes = total_values * 4 + 10240  # 4 bytes per value + 10 KB metadata
    estimated_size_mb = estimated_size_bytes / (1024 * 1024)
    estimated_size_gb = estimated_size_mb / 1024
    
    if estimated_size_gb >= 1.0:
        print(f"Estimated output file size: {estimated_size_gb:.2f} GB (with compression)")
    else:
        print(f"Estimated output file size: {estimated_size_mb:.1f} MB (with compression)")
    
    # Get sample rate for timestamp generation
    sample_rate = metadata['sample_rate']
    time_step = 1.0 / sample_rate if sample_rate > 0 else 0.0
    
    # Create HDF5 file with SpectralEdge-compatible structure
    # SpectralEdge expects: /flight_XXX/metadata/ and /flight_XXX/channels/
    with h5py.File(output_path, 'w') as hf:
        # Create flight group (SpectralEdge expects flight_XXX structure)
        flight_key = 'flight_001'  # Default flight name for single-file conversion
        flight_group = hf.create_group(flight_key)
        
        # Create metadata group with attributes (SpectralEdge format)
        meta_group = flight_group.create_group('metadata')
        meta_group.attrs['flight_id'] = flight_key
        meta_group.attrs['sample_rate'] = metadata['sample_rate']
        meta_group.attrs['duration'] = metadata['duration']
        meta_group.attrs['start_time'] = metadata.get('start_time', 0.0)
        meta_group.attrs['num_channels'] = len(channels_info)
        meta_group.attrs['source'] = 'DEWESoft DXD Conversion'
        
        # Create channels group (SpectralEdge expects this under flight group)
        channels_group = flight_group.create_group('channels')
        
        print(f"\nCreated HDF5 structure: /{flight_key}/metadata/ and /{flight_key}/channels/")
        
        # Process each channel
        for ch_idx, (channel, samples_to_export, ch_type) in enumerate(channels_info):
            ch_name = decode_bytes(channel.name)
            ch_unit = decode_bytes(channel.unit)
            
            print(f"\nProcessing channel {ch_idx + 1}/{len(channels_info)}: {ch_name}")
            
            # Create channel subgroup (SpectralEdge expects each channel as a group)
            ch_group = channels_group.create_group(ch_name)
            
            # Add channel attributes (SpectralEdge format)
            ch_group.attrs['units'] = ch_unit  # Note: 'units' not 'unit'
            ch_group.attrs['sample_rate'] = sample_rate
            ch_group.attrs['description'] = f"{ch_name} from DEWESoft"
            ch_group.attrs['array_size'] = channel.array_size
            ch_group.attrs['index'] = channel.index
            
            # Create datasets for this channel
            # Use chunked storage and compression for efficiency
            if channel.array_size > 1:
                # Array channel: shape is (samples, array_size)
                data_shape = (samples_to_export, channel.array_size)
                chunk_shape = (min(chunk_size, samples_to_export), channel.array_size)
            else:
                # Scalar channel: shape is (samples,)
                data_shape = (samples_to_export,)
                chunk_shape = (min(chunk_size, samples_to_export),)
            
            # Create datasets with compression
            data_dataset = ch_group.create_dataset(
                'data',
                shape=data_shape,
                dtype='float64',
                chunks=chunk_shape,
                compression='gzip',
                compression_opts=4  # Compression level 4 (good balance)
            )
            
            time_dataset = ch_group.create_dataset(
                'time',
                shape=(samples_to_export,),
                dtype='float64',
                chunks=(min(chunk_size, samples_to_export),),
                compression='gzip',
                compression_opts=4
            )
            
            # Read and write data in chunks
            samples_written = 0
            for chunk_start in range(0, samples_to_export, chunk_size):
                chunk_end = min(chunk_start + chunk_size, samples_to_export)
                samples_in_chunk = chunk_end - chunk_start
                
                # Allocate memory for this chunk only
                total_count = samples_in_chunk * channel.array_size
                samples = (ctypes.c_double * total_count)()
                
                # Allocate timestamps for async channels
                timestamps = None
                if ch_type == DWChannelType.DW_CH_TYPE_ASYNC:
                    timestamps = (ctypes.c_double * samples_in_chunk)()
                
                # Read the chunk of scaled samples
                check_error(lib, lib.DWIGetScaledSamples(reader_instance, channel.index,
                                                          chunk_start, samples_in_chunk,
                                                          samples, timestamps))
                
                # Convert to numpy arrays
                if channel.array_size > 1:
                    # Reshape array channel data
                    values_array = np.array(samples).reshape(samples_in_chunk, channel.array_size)
                else:
                    values_array = np.array(samples)
                
                # Generate or convert timestamps
                if timestamps is None:
                    timestamps_array = np.arange(chunk_start, chunk_end) * time_step
                else:
                    timestamps_array = np.array(timestamps)
                
                # Write chunk to HDF5
                data_dataset[chunk_start:chunk_end] = values_array
                time_dataset[chunk_start:chunk_end] = timestamps_array
                
                samples_written += samples_in_chunk
                
                # Progress update
                progress = (samples_written / samples_to_export) * 100
                print(f"\r  Progress: {progress:.1f}% ({samples_written:,}/{samples_to_export:,} samples)", 
                      end='', flush=True)
            
            print()  # New line after progress
        
        print(f"\n✓ HDF5 file written successfully")
        print(f"  Flight: {flight_key}")
        print(f"  Channels: {len(channels_info)}")
        print(f"  Total samples: {max_samples:,}")
        
        # Flush to ensure data is written
        hf.flush()
    
    # Report actual file size
    actual_size = os.path.getsize(output_path)
    actual_size_mb = actual_size / (1024 * 1024)
    actual_size_gb = actual_size_mb / 1024
    
    if actual_size_gb >= 1.0:
        print(f"  Actual file size: {actual_size_gb:.2f} GB")
    else:
        print(f"  Actual file size: {actual_size_mb:.1f} MB")
    
    print(f"\n✓ File is compatible with SpectralEdge HDF5FlightDataLoader")
    print(f"  Structure: /{flight_key}/channels/<channel_name>/{{data, time}}")


def print_section_header(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)
