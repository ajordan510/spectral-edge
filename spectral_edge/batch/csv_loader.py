"""
CSV Data Loader for Batch Processing

This module provides functions to load time-series data from CSV files for batch
PSD processing. It supports multiple formats and can handle multiple channels
per file or multiple files.

Author: SpectralEdge Development Team
Date: 2026-02-02
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def load_csv_files(file_paths: List[str]) -> Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray, float, str]]]:
    """
    Load time-series data from multiple CSV files.
    
    This function handles CSV files with the following format:
    - First column: Time (in seconds)
    - Subsequent columns: Channel data
    - Optional header row with channel names
    
    The sample rate is automatically detected from the time column.
    
    Parameters:
    -----------
    file_paths : List[str]
        List of paths to CSV files to load
        
    Returns:
    --------
    Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray, float, str]]]
        Nested dictionary structure:
        {
            file_path: {
                channel_name: (time_array, signal_array, sample_rate, units),
                ...
            },
            ...
        }
        
        Where:
        - time_array: np.ndarray of time values in seconds
        - signal_array: np.ndarray of signal values
        - sample_rate: float, detected sample rate in Hz
        - units: str, units of measurement (empty string if not detected)
        
    Raises:
    -------
    ValueError
        If CSV file format is invalid or cannot be parsed
    FileNotFoundError
        If any file in file_paths does not exist
        
    Notes:
    ------
    - If no header is present, channels are named as 'channel_1', 'channel_2', etc.
    - Sample rate is calculated from the median time difference between samples
    - Units are extracted from column headers if present (e.g., "accel_x (g)")
    
    Example:
    --------
    >>> files = ['test_data_1.csv', 'test_data_2.csv']
    >>> data = load_csv_files(files)
    >>> for file_path, channels in data.items():
    ...     for channel_name, (time, signal, fs, units) in channels.items():
    ...         print(f"{file_path}/{channel_name}: {len(signal)} samples at {fs} Hz")
    """
    result = {}
    
    for file_path in file_paths:
        try:
            file_data = _load_single_csv(file_path)
            result[file_path] = file_data
            logger.info(f"Loaded {len(file_data)} channel(s) from {Path(file_path).name}")
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {str(e)}")
            raise
    
    return result


def _load_single_csv(file_path: str) -> Dict[str, Tuple[np.ndarray, np.ndarray, float, str]]:
    """
    Load a single CSV file and extract all channels.
    
    Parameters:
    -----------
    file_path : str
        Path to CSV file
        
    Returns:
    --------
    Dict[str, Tuple[np.ndarray, np.ndarray, float, str]]
        Dictionary mapping channel names to (time, signal, sample_rate, units) tuples
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    
    # Try to read CSV with pandas
    try:
        # First, try reading with header
        df = pd.read_csv(file_path)
        has_header = True
    except Exception:
        # If that fails, try without header
        df = pd.read_csv(file_path, header=None)
        has_header = False
    
    if df.shape[1] < 2:
        raise ValueError(f"CSV file must have at least 2 columns (time + 1 channel): {file_path}")
    
    # Extract time column (first column)
    time_array = df.iloc[:, 0].values
    
    # Validate time array
    if not np.all(np.diff(time_array) > 0):
        raise ValueError(f"Time column must be monotonically increasing: {file_path}")
    
    # Calculate sample rate from median time difference
    dt = np.median(np.diff(time_array))
    sample_rate = 1.0 / dt
    
    logger.info(f"Detected sample rate: {sample_rate:.2f} Hz")
    
    # Extract each channel
    channels = {}
    
    for col_idx in range(1, df.shape[1]):
        # Get column name
        if has_header:
            col_name = df.columns[col_idx]
            # Try to extract units from column name (e.g., "accel_x (g)")
            units = _extract_units_from_name(col_name)
            # Clean channel name (remove units part)
            channel_name = _clean_channel_name(col_name)
        else:
            channel_name = f"channel_{col_idx}"
            units = ""
        
        # Get signal data
        signal_array = df.iloc[:, col_idx].values
        
        # Validate signal data
        if len(signal_array) != len(time_array):
            raise ValueError(f"Signal length mismatch for {channel_name}")
        
        # Check for NaN values
        if np.any(np.isnan(signal_array)):
            nan_count = np.sum(np.isnan(signal_array))
            logger.warning(f"{channel_name}: Found {nan_count} NaN values, interpolating...")
            signal_array = _interpolate_nans(signal_array)
        
        channels[channel_name] = (time_array, signal_array, sample_rate, units)
    
    return channels


def _extract_units_from_name(column_name: str) -> str:
    """
    Extract units from column name if present.
    
    Looks for patterns like:
    - "channel_name (units)"
    - "channel_name [units]"
    
    Parameters:
    -----------
    column_name : str
        Column name from CSV header
        
    Returns:
    --------
    str
        Extracted units, or empty string if not found
    """
    import re
    
    # Try parentheses pattern
    match = re.search(r'\(([^)]+)\)', column_name)
    if match:
        return match.group(1).strip()
    
    # Try brackets pattern
    match = re.search(r'\[([^\]]+)\]', column_name)
    if match:
        return match.group(1).strip()
    
    return ""


def _clean_channel_name(column_name: str) -> str:
    """
    Remove units and extra whitespace from channel name.
    
    Parameters:
    -----------
    column_name : str
        Original column name
        
    Returns:
    --------
    str
        Cleaned channel name
    """
    import re
    
    # Remove content in parentheses or brackets
    name = re.sub(r'\([^)]*\)', '', column_name)
    name = re.sub(r'\[[^\]]*\]', '', name)
    
    # Remove extra whitespace
    name = name.strip()
    
    return name if name else column_name


def _interpolate_nans(signal: np.ndarray) -> np.ndarray:
    """
    Interpolate NaN values in signal using linear interpolation.
    
    Parameters:
    -----------
    signal : np.ndarray
        Signal array potentially containing NaN values
        
    Returns:
    --------
    np.ndarray
        Signal with NaN values interpolated
    """
    # Find NaN indices
    nan_mask = np.isnan(signal)
    
    if not np.any(nan_mask):
        return signal
    
    # Get valid indices
    valid_mask = ~nan_mask
    valid_indices = np.where(valid_mask)[0]
    valid_values = signal[valid_mask]
    
    # Interpolate
    interpolated = np.interp(
        np.arange(len(signal)),
        valid_indices,
        valid_values
    )
    
    return interpolated


def detect_csv_format(file_path: str) -> Dict[str, any]:
    """
    Analyze CSV file and detect its format.

    This function provides information about the CSV file structure
    without loading the full data into memory. Uses efficient line counting
    and reads only first/last rows for time estimation.

    Parameters:
    -----------
    file_path : str
        Path to CSV file

    Returns:
    --------
    Dict[str, any]
        Dictionary containing:
        - 'has_header': bool
        - 'num_columns': int
        - 'num_rows': int
        - 'column_names': List[str]
        - 'estimated_sample_rate': float
        - 'estimated_duration': float
    """
    if not Path(file_path).exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    # Read first few rows to detect format and header
    try:
        df_sample = pd.read_csv(file_path, nrows=100)
        has_header = True
        column_names = list(df_sample.columns)
    except Exception:
        df_sample = pd.read_csv(file_path, header=None, nrows=100)
        has_header = False
        column_names = [f"column_{i}" for i in range(df_sample.shape[1])]

    num_columns = df_sample.shape[1]

    # Count rows efficiently without loading full file
    with open(file_path, 'r') as f:
        num_rows = sum(1 for _ in f)
    if has_header:
        num_rows -= 1  # Subtract header row

    # Estimate sample rate from first few rows
    time_array = df_sample.iloc[:, 0].values
    if len(time_array) > 1:
        dt = np.median(np.diff(time_array))
        estimated_sample_rate = 1.0 / dt if dt > 0 else 0.0
    else:
        estimated_sample_rate = 0.0

    # Estimate duration using first time and row count
    # Duration ≈ (num_rows - 1) / sample_rate
    if estimated_sample_rate > 0:
        estimated_duration = (num_rows - 1) / estimated_sample_rate
    else:
        # Fallback: read last few rows to get end time
        try:
            # Use skiprows to read only last 10 rows
            df_tail = pd.read_csv(
                file_path,
                header=0 if has_header else None,
                skiprows=range(1 if has_header else 0, max(1, num_rows - 10))
            )
            if len(df_tail) > 0:
                first_time = time_array[0]
                last_time = df_tail.iloc[-1, 0]
                estimated_duration = last_time - first_time
            else:
                estimated_duration = 0.0
        except Exception:
            estimated_duration = 0.0

    return {
        'has_header': has_header,
        'num_columns': num_columns,
        'num_rows': num_rows,
        'column_names': column_names,
        'estimated_sample_rate': estimated_sample_rate,
        'estimated_duration': estimated_duration
    }
