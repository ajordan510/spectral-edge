"""
Data loading utilities for SpectralEdge.

This module provides functions for loading time-series data from various
file formats (CSV, HDF5) and validating the data structure.

Author: SpectralEdge Development Team
"""

import logging
import numpy as np
import pandas as pd
from typing import Tuple, List, Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class DataLoadError(Exception):
    """Custom exception for data loading errors."""
    pass


def load_csv_data(
    file_path: str,
    time_column: Optional[str] = None,
    delimiter: str = ',',
    header_row: int = 0,
    skip_rows: Optional[List[int]] = None
) -> Tuple[np.ndarray, np.ndarray, List[str], float]:
    """
    Load time-series data from a CSV file.
    
    This function reads a CSV file containing time-series data with one or
    more channels. It expects the file to have a time column and one or more
    data columns representing different channels.
    
    The function automatically detects the sample rate by analyzing the time
    column spacing.
    
    Parameters:
        file_path (str): Path to the CSV file.
        time_column (str, optional): Name of the time column. If None, assumes
            the first column is time. If the file has no time column, set this
            to None and ensure the data is evenly sampled.
        delimiter (str): Column delimiter in the CSV file. Default is ','.
        header_row (int): Row number containing column headers (0-indexed).
            Default is 0 (first row).
        skip_rows (List[int], optional): List of row numbers to skip when
            reading the file (e.g., for comments or metadata rows).
    
    Returns:
        Tuple containing:
            - time (np.ndarray): Time values in seconds (1D array).
            - data (np.ndarray): Data values. Shape is (num_samples, num_channels).
            - channel_names (List[str]): Names of the data channels.
            - sample_rate (float): Detected sample rate in Hz.
    
    Raises:
        DataLoadError: If the file cannot be read or has invalid structure.
        FileNotFoundError: If the file does not exist.
    
    Example:
        >>> # Load a CSV file with columns: Time, Channel1, Channel2
        >>> time, data, channels, fs = load_csv_data('data.csv')
        >>> print(f"Loaded {len(channels)} channels at {fs} Hz")
        >>> print(f"Channel names: {channels}")
    """
    # Check if file exists
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        # Read CSV file using pandas
        df = pd.read_csv(
            file_path,
            delimiter=delimiter,
            header=header_row,
            skiprows=skip_rows
        )
    except Exception as e:
        raise DataLoadError(f"Failed to read CSV file: {e}")
    
    # Check if dataframe is empty
    if df.empty:
        raise DataLoadError("CSV file is empty or has no valid data")
    
    # Identify time column
    if time_column is None:
        # Assume first column is time
        time_column = df.columns[0]
    
    if time_column not in df.columns:
        raise DataLoadError(f"Time column '{time_column}' not found in CSV file")
    
    # Extract time data
    time = df[time_column].values
    
    # Validate time data
    if len(time) < 2:
        raise DataLoadError("Insufficient data points (need at least 2)")
    
    if not np.all(np.isfinite(time)):
        raise DataLoadError("Time column contains non-finite values (NaN or Inf)")
    
    # Calculate sample rate from time column
    # Use median of time differences to be robust against minor irregularities
    time_diffs = np.diff(time)
    
    if not np.all(time_diffs > 0):
        raise DataLoadError("Time values must be strictly increasing")
    
    median_dt = np.median(time_diffs)
    sample_rate = 1.0 / median_dt
    
    # Check for consistent sampling
    # Allow up to 1% variation in time step
    max_variation = 0.01 * median_dt
    if np.any(np.abs(time_diffs - median_dt) > max_variation):
        # Issue a warning but continue (could make this stricter if needed)
        logger.warning(
            f"Time sampling is not perfectly uniform (max variation: "
            f"{np.max(np.abs(time_diffs - median_dt)):.2e} s)"
        )
    
    # Extract data columns (all columns except time)
    data_columns = [col for col in df.columns if col != time_column]
    
    if len(data_columns) == 0:
        raise DataLoadError("No data columns found in CSV file")
    
    # Extract data as numpy array
    # Shape: (num_samples, num_channels)
    data = df[data_columns].values
    
    # Check for non-finite values
    if not np.all(np.isfinite(data)):
        raise DataLoadError("Data contains non-finite values (NaN or Inf)")
    
    # Keep data in shape (num_samples, num_channels) to match HDF5 format
    # This is the standard format expected by the GUI
    
    # Get channel names
    channel_names = data_columns
    
    return time, data, channel_names, sample_rate


def load_csv_data_simple(
    file_path: str,
    sample_rate: float,
    has_header: bool = True,
    delimiter: str = ','
) -> Tuple[np.ndarray, List[str]]:
    """
    Simplified CSV loader for files without a time column.
    
    This function is useful when you have a CSV file with only data columns
    (no time column) and you know the sample rate in advance.
    
    Parameters:
        file_path (str): Path to the CSV file.
        sample_rate (float): Known sample rate in Hz.
        has_header (bool): Whether the file has a header row with column names.
            Default is True.
        delimiter (str): Column delimiter. Default is ','.
    
    Returns:
        Tuple containing:
            - data (np.ndarray): Data values. Shape is (num_samples, num_channels).
            - channel_names (List[str]): Names of the channels (or generic names
              if no header).
    
    Raises:
        DataLoadError: If the file cannot be read or has invalid structure.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        if has_header:
            df = pd.read_csv(file_path, delimiter=delimiter)
            channel_names = list(df.columns)
        else:
            df = pd.read_csv(file_path, delimiter=delimiter, header=None)
            channel_names = [f"Channel_{i+1}" for i in range(df.shape[1])]
        
        # Extract data in shape (num_samples, num_channels)
        data = df.values
        
        # Validate
        if not np.all(np.isfinite(data)):
            raise DataLoadError("Data contains non-finite values (NaN or Inf)")
        
        return data, channel_names
    
    except Exception as e:
        raise DataLoadError(f"Failed to load CSV file: {e}")


def get_file_info(file_path: str) -> Dict[str, any]:
    """
    Get basic information about a CSV file without loading all data.
    
    This function quickly reads the header and a few rows to provide
    information about the file structure.
    
    Parameters:
        file_path (str): Path to the CSV file.
    
    Returns:
        Dict containing:
            - 'columns': List of column names
            - 'num_rows': Approximate number of rows
            - 'file_size_mb': File size in megabytes
    
    Example:
        >>> info = get_file_info('large_data.csv')
        >>> print(f"File has {info['num_rows']} rows and {len(info['columns'])} columns")
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get file size
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    
    # Read just the header and first few rows
    df_preview = pd.read_csv(file_path, nrows=5)
    columns = list(df_preview.columns)
    
    # Count total rows (approximate for large files)
    # For very large files, this could be slow, so we use a fast method
    with open(file_path, 'r') as f:
        num_rows = sum(1 for _ in f) - 1  # Subtract header row
    
    return {
        'columns': columns,
        'num_rows': num_rows,
        'file_size_mb': file_size_mb
    }


def validate_data_for_analysis(
    data: np.ndarray,
    sample_rate: float,
    min_duration: float = 0.1
) -> bool:
    """
    Validate that data meets minimum requirements for signal processing.
    
    Parameters:
        data (np.ndarray): Data array (1D or 2D).
        sample_rate (float): Sample rate in Hz.
        min_duration (float): Minimum required duration in seconds. Default is 0.1.
    
    Returns:
        bool: True if data is valid, raises exception otherwise.
    
    Raises:
        DataLoadError: If data does not meet requirements.
    """
    if data.size == 0:
        raise DataLoadError("Data array is empty")
    
    if sample_rate <= 0:
        raise DataLoadError("Sample rate must be positive")
    
    # Calculate duration
    if data.ndim == 1:
        num_samples = len(data)
    else:
        num_samples = data.shape[1]
    
    duration = num_samples / sample_rate
    
    if duration < min_duration:
        raise DataLoadError(
            f"Data duration ({duration:.3f} s) is less than minimum "
            f"required ({min_duration} s)"
        )
    
    return True
