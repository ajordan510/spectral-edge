#!/usr/bin/env python3
"""
HDF5 File Diagnostic Tool

This script inspects an HDF5 file and provides detailed information about its structure,
identifying what's present and what's missing compared to SpectralEdge requirements.

Usage:
    python diagnose_hdf5.py your_file.h5

Requirements:
    - Python 3.7+
    - h5py library (install: pip install h5py)

Author: SpectralEdge Development Team
Date: 2025-01-23
"""

import sys
import h5py
import numpy as np
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text, indent=0):
    """Print info message."""
    prefix = "  " * indent
    print(f"{prefix}{Colors.BLUE}{text}{Colors.END}")


def diagnose_file(file_path):
    """
    Perform comprehensive diagnostic on HDF5 file.
    
    Parameters
    ----------
    file_path : str
        Path to HDF5 file to diagnose
    
    Returns
    -------
    bool
        True if file is valid, False otherwise
    """
    print_header(f"HDF5 FILE DIAGNOSTIC: {Path(file_path).name}")
    
    # Check file exists
    if not Path(file_path).exists():
        print_error(f"File not found: {file_path}")
        return False
    
    print_success(f"File exists: {file_path}")
    print_info(f"File size: {Path(file_path).stat().st_size / 1024 / 1024:.2f} MB")
    
    # Try to open file
    try:
        f = h5py.File(file_path, 'r')
        print_success("File opened successfully")
    except Exception as e:
        print_error(f"Failed to open file: {e}")
        return False
    
    is_valid = True
    
    # Check top-level structure
    print_header("TOP-LEVEL STRUCTURE")
    
    all_keys = list(f.keys())
    print_info(f"Found {len(all_keys)} top-level group(s)/dataset(s):")
    for key in all_keys:
        obj = f[key]
        obj_type = "Group" if isinstance(obj, h5py.Group) else "Dataset"
        print_info(f"  - {key} ({obj_type})", indent=1)
    
    # Check for flight groups
    flight_keys = [key for key in all_keys if key.startswith('flight_')]
    
    if not flight_keys:
        print_error("NO FLIGHT GROUPS FOUND!")
        print_info("Required: At least one group starting with 'flight_'", indent=1)
        print_info("Found: " + str(all_keys), indent=1)
        print_info("", indent=1)
        print_info("FIX: Rename your groups to start with 'flight_':", indent=1)
        print_info("  Example: 'data' → 'flight_001'", indent=2)
        print_info("  Example: 'test' → 'flight_test_1'", indent=2)
        is_valid = False
    else:
        print_success(f"Found {len(flight_keys)} flight group(s): {flight_keys}")
    
    # Check file-level metadata
    if 'metadata' in f:
        meta = f['metadata']
        if isinstance(meta, h5py.Group):
            attrs = dict(meta.attrs)
            print_success(f"File-level metadata found: {list(attrs.keys())}")
        else:
            print_warning("'metadata' exists but is not a group")
    else:
        print_warning("No file-level metadata (optional)")
    
    # Diagnose each flight
    for flight_key in flight_keys:
        diagnose_flight(f, flight_key)
    
    f.close()
    
    # Final summary
    print_header("DIAGNOSTIC SUMMARY")
    
    if is_valid:
        print_success("File structure appears valid!")
        print_info("The file should load in SpectralEdge.", indent=1)
    else:
        print_error("File structure has issues!")
        print_info("Fix the issues listed above and try again.", indent=1)
        print_info("See docs/HDF5_MANDATORY_FIELDS_CHECKLIST.md for details.", indent=1)
    
    return is_valid


def diagnose_flight(f, flight_key):
    """
    Diagnose a single flight group.
    
    Parameters
    ----------
    f : h5py.File
        Open HDF5 file
    flight_key : str
        Flight group key
    """
    print_header(f"FLIGHT: {flight_key}")
    
    flight = f[flight_key]
    
    # Check flight metadata
    if 'metadata' in flight:
        meta = flight['metadata']
        if isinstance(meta, h5py.Group):
            attrs = dict(meta.attrs)
            print_success("Flight metadata found:")
            for key, value in attrs.items():
                print_info(f"  {key}: {value}", indent=1)
        else:
            print_warning("'metadata' exists but is not a group")
    else:
        print_warning("No flight metadata (optional but recommended)")
    
    # Check for channels group
    if 'channels' not in flight:
        print_error("NO 'channels' GROUP FOUND!")
        print_info(f"Required: {flight_key}/channels/", indent=1)
        print_info(f"Found: {list(flight.keys())}", indent=1)
        print_info("", indent=1)
        print_info("FIX: Create a 'channels' subgroup:", indent=1)
        print_info(f"  flight = f.create_group('{flight_key}')", indent=2)
        print_info(f"  channels = flight.create_group('channels')", indent=2)
        return
    
    channels_group = flight['channels']
    
    if not isinstance(channels_group, h5py.Group):
        print_error("'channels' is not a group!")
        print_info(f"Type: {type(channels_group)}", indent=1)
        return
    
    channel_keys = list(channels_group.keys())
    
    if not channel_keys:
        print_error("NO CHANNELS FOUND!")
        print_info("Required: At least one channel dataset", indent=1)
        return
    
    print_success(f"Found {len(channel_keys)} channel(s): {channel_keys}")
    
    # Diagnose each channel
    for channel_key in channel_keys:
        diagnose_channel(channels_group, channel_key, flight_key)


def diagnose_channel(channels_group, channel_key, flight_key):
    """
    Diagnose a single channel dataset.
    
    Parameters
    ----------
    channels_group : h5py.Group
        Channels group
    channel_key : str
        Channel name
    flight_key : str
        Parent flight key
    """
    print(f"\n{Colors.BOLD}  Channel: {channel_key}{Colors.END}")
    
    channel = channels_group[channel_key]
    
    # Check if it's a dataset
    if not isinstance(channel, h5py.Dataset):
        print_error(f"    NOT A DATASET! Type: {type(channel)}", indent=1)
        print_info("    FIX: Channels must be datasets, not groups", indent=1)
        print_info("    Example: channels.create_dataset('name', data=array)", indent=1)
        return
    
    print_success("    Is a dataset")
    
    # Check data shape
    shape = channel.shape
    ndim = len(shape)
    
    if ndim != 1:
        print_error(f"    DATA IS NOT 1D! Shape: {shape} ({ndim}D)")
        print_info("    Required: 1D array with shape (N,)", indent=1)
        print_info("    FIX: If you have multi-axis data, create separate channels:", indent=1)
        print_info("      - accel_x (1D)", indent=2)
        print_info("      - accel_y (1D)", indent=2)
        print_info("      - accel_z (1D)", indent=2)
        print_info("    NOT: accel (2D with shape (N, 3))", indent=1)
        return
    
    n_samples = shape[0]
    print_success(f"    Shape: {shape} ({n_samples:,} samples)")
    
    # Check data type
    dtype = channel.dtype
    
    # Check for problematic data types
    dtype_str = str(dtype)
    is_problematic = False
    problem_description = None
    
    # Check for object dtype (often strings or mixed types)
    if dtype == np.object_:
        is_problematic = True
        problem_description = "Object dtype (likely strings or mixed types)"
    
    # Check for structured/compound dtypes
    elif dtype.names is not None:
        is_problematic = True
        problem_description = f"Structured dtype with fields: {dtype.names}"
    
    # Check for string dtypes
    elif np.issubdtype(dtype, np.str_) or np.issubdtype(dtype, np.bytes_):
        is_problematic = True
        problem_description = "String/bytes dtype"
    
    # Check for datetime dtypes
    elif np.issubdtype(dtype, np.datetime64) or np.issubdtype(dtype, np.timedelta64):
        is_problematic = True
        problem_description = "Datetime/timedelta dtype"
    
    # Check for void dtype
    elif dtype == np.void:
        is_problematic = True
        problem_description = "Void dtype (raw binary data)"
    
    if is_problematic:
        print_error(f"    Data type: {dtype} (PROBLEMATIC!)")
        print_error(f"    Issue: {problem_description}")
        print_info("    This will cause: 'unsupported format string passed to numpy.ndarray'", indent=1)
        print_info("    Required: Numeric data (int or float)", indent=1)
        print_info("    ", indent=1)
        print_info("    FIX: Convert data to numeric type in MATLAB:", indent=1)
        print_info("      data = double(your_data);  % Convert to float64", indent=2)
        print_info("      channel = channels.create_dataset('name', data=data);", indent=2)
        print_info("    ", indent=1)
        print_info("    Or in Python:", indent=1)
        print_info("      data = np.array(your_data, dtype=np.float64)", indent=2)
        print_info("      channel = channels.create_dataset('name', data=data)", indent=2)
        return
    
    # Check if numeric
    if np.issubdtype(dtype, np.number):
        print_success(f"    Data type: {dtype} (numeric)")
        
        # Show sample values to help identify issues
        try:
            sample_data = channel[:min(5, n_samples)]
            print_info(f"    Sample values: {sample_data}", indent=1)
        except Exception as e:
            print_warning(f"    Could not read sample data: {e}")
    else:
        print_error(f"    Data type: {dtype} (NOT numeric!)")
        print_info("    Required: Numeric data (int or float)", indent=1)
        return
    
    # Check for required attributes
    attrs = dict(channel.attrs)
    required_attrs = ['units', 'sample_rate', 'start_time']
    
    print(f"\n    {Colors.BOLD}Attributes:{Colors.END}")
    
    has_all_required = True
    
    for attr_name in required_attrs:
        if attr_name in attrs:
            attr_value = attrs[attr_name]
            attr_type = type(attr_value).__name__
            
            # Validate specific attributes
            if attr_name == 'units':
                if isinstance(attr_value, (str, bytes)):
                    print_success(f"      {attr_name}: \"{attr_value}\" (string)")
                else:
                    print_error(f"      {attr_name}: {attr_value} (type: {attr_type}, should be string!)")
                    has_all_required = False
            
            elif attr_name == 'sample_rate':
                if isinstance(attr_value, (int, float, np.number)):
                    if attr_value > 0:
                        print_success(f"      {attr_name}: {attr_value} Hz (float)")
                        
                        # Calculate duration
                        duration = n_samples / float(attr_value)
                        print_info(f"      → Duration: {duration:.2f} seconds", indent=1)
                    else:
                        print_error(f"      {attr_name}: {attr_value} (MUST BE > 0!)")
                        has_all_required = False
                else:
                    print_error(f"      {attr_name}: {attr_value} (type: {attr_type}, should be float!)")
                    has_all_required = False
            
            elif attr_name == 'start_time':
                if isinstance(attr_value, (int, float, np.number)):
                    print_success(f"      {attr_name}: {attr_value} s (float)")
                else:
                    print_error(f"      {attr_name}: {attr_value} (type: {attr_type}, should be float!)")
                    has_all_required = False
        else:
            print_error(f"      {attr_name}: MISSING!")
            has_all_required = False
    
    # Show optional attributes
    optional_attrs = ['description', 'sensor_id', 'location', 'range_min', 'range_max']
    found_optional = [attr for attr in optional_attrs if attr in attrs]
    
    if found_optional:
        print(f"\n    {Colors.BOLD}Optional attributes:{Colors.END}")
        for attr_name in found_optional:
            attr_value = attrs[attr_name]
            print_info(f"      {attr_name}: {attr_value}", indent=1)
    
    # Show any extra attributes
    known_attrs = required_attrs + optional_attrs
    extra_attrs = [attr for attr in attrs.keys() if attr not in known_attrs]
    
    if extra_attrs:
        print(f"\n    {Colors.BOLD}Extra attributes:{Colors.END}")
        for attr_name in extra_attrs:
            attr_value = attrs[attr_name]
            print_info(f"      {attr_name}: {attr_value}", indent=1)
    
    # Summary for this channel
    if not has_all_required:
        print_error("\n    CHANNEL HAS MISSING/INVALID ATTRIBUTES!")
        print_info("    FIX: Add all required attributes:", indent=1)
        print_info(f"      channel.attrs['units'] = 'g'  # string", indent=2)
        print_info(f"      channel.attrs['sample_rate'] = 1000.0  # float > 0", indent=2)
        print_info(f"      channel.attrs['start_time'] = 0.0  # float", indent=2)


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <hdf5_file>")
        print(f"\nExample:")
        print(f"  {sys.argv[0]} my_data.h5")
        print(f"\nThis script will inspect your HDF5 file and tell you:")
        print(f"  - What structure exists")
        print(f"  - What's missing")
        print(f"  - How to fix any issues")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    is_valid = diagnose_file(file_path)
    
    if not is_valid:
        print(f"\n{Colors.BOLD}For detailed requirements, see:{Colors.END}")
        print(f"  docs/HDF5_MANDATORY_FIELDS_CHECKLIST.md")
        print(f"\n{Colors.BOLD}For MATLAB conversion help, see:{Colors.END}")
        print(f"  matlab/README_MATLAB_CONVERSION.md")
        print(f"  matlab/QUICK_START.md")
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
