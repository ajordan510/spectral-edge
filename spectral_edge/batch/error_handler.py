"""
Error Handling and Recovery Module for Batch Processing

This module provides detailed error messages with actionable recovery suggestions
to help users diagnose and fix issues during batch processing.

Author: SpectralEdge Development Team
Date: 2026-02-02
"""

import logging
from typing import Optional, Dict, List
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors that can occur during batch processing."""
    DATA_LOADING = "data_loading"
    DATA_VALIDATION = "data_validation"
    PROCESSING = "processing"
    OUTPUT = "output"
    CONFIGURATION = "configuration"


class BatchError(Exception):
    """
    Custom exception for batch processing errors with recovery suggestions.
    
    Attributes:
    -----------
    message : str
        Error message
    category : ErrorCategory
        Category of error
    suggestions : List[str]
        List of recovery suggestions
    context : Dict
        Additional context about the error
    """
    
    def __init__(self, message: str, category: ErrorCategory,
                 suggestions: Optional[List[str]] = None,
                 context: Optional[Dict] = None):
        """
        Initialize batch error with recovery information.
        
        Parameters:
        -----------
        message : str
            Error message
        category : ErrorCategory
            Category of error
        suggestions : List[str], optional
            List of recovery suggestions
        context : Dict, optional
            Additional context
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.suggestions = suggestions or []
        self.context = context or {}
    
    def get_full_message(self) -> str:
        """
        Get full error message with suggestions.
        
        Returns:
        --------
        str
            Formatted error message with suggestions
        """
        msg = f"[{self.category.value.upper()}] {self.message}"
        
        if self.suggestions:
            msg += "\n\nSuggestions:"
            for i, suggestion in enumerate(self.suggestions, 1):
                msg += f"\n  {i}. {suggestion}"
        
        if self.context:
            msg += "\n\nContext:"
            for key, value in self.context.items():
                msg += f"\n  - {key}: {value}"
        
        return msg


class ErrorHandler:
    """
    Handles errors during batch processing with detailed diagnostics.
    
    Provides methods for common error scenarios with actionable recovery suggestions.
    """
    
    @staticmethod
    def handle_file_not_found(file_path: str) -> BatchError:
        """
        Handle file not found error.
        
        Parameters:
        -----------
        file_path : str
            Path to missing file
            
        Returns:
        --------
        BatchError
            Error with recovery suggestions
        """
        return BatchError(
            f"File not found: {file_path}",
            ErrorCategory.DATA_LOADING,
            suggestions=[
                "Verify the file path is correct",
                "Check that the file has not been moved or deleted",
                "Ensure you have read permissions for the file",
                "If using relative paths, verify your working directory"
            ],
            context={"file_path": file_path}
        )
    
    @staticmethod
    def handle_invalid_hdf5(file_path: str, error_msg: str) -> BatchError:
        """
        Handle invalid HDF5 file error.
        
        Parameters:
        -----------
        file_path : str
            Path to HDF5 file
        error_msg : str
            Original error message
            
        Returns:
        --------
        BatchError
            Error with recovery suggestions
        """
        return BatchError(
            f"Invalid or corrupted HDF5 file: {file_path}",
            ErrorCategory.DATA_LOADING,
            suggestions=[
                "Verify the file is a valid HDF5 file",
                "Check if the file is corrupted (try opening with h5py directly)",
                "Ensure the file follows the expected SpectralEdge structure",
                "Try re-exporting the data from the original source"
            ],
            context={"file_path": file_path, "original_error": error_msg}
        )
    
    @staticmethod
    def handle_missing_channel(flight_key: str, channel_key: str,
                              available_channels: List[str]) -> BatchError:
        """
        Handle missing channel error.
        
        Parameters:
        -----------
        flight_key : str
            Flight identifier
        channel_key : str
            Missing channel identifier
        available_channels : List[str]
            List of available channels
            
        Returns:
        --------
        BatchError
            Error with recovery suggestions
        """
        return BatchError(
            f"Channel not found: {flight_key}/{channel_key}",
            ErrorCategory.DATA_VALIDATION,
            suggestions=[
                "Verify the channel name is correct",
                f"Available channels: {', '.join(available_channels[:10])}{'...' if len(available_channels) > 10 else ''}",
                "Check if the channel was renamed or removed",
                "Update your configuration file with correct channel names"
            ],
            context={
                "flight_key": flight_key,
                "channel_key": channel_key,
                "num_available": len(available_channels)
            }
        )
    
    @staticmethod
    def handle_invalid_time_range(event_name: str, start_time: float,
                                  end_time: float, data_start: float,
                                  data_end: float) -> BatchError:
        """
        Handle invalid time range error.
        
        Parameters:
        -----------
        event_name : str
            Event name
        start_time : float
            Event start time
        end_time : float
            Event end time
        data_start : float
            Data start time
        data_end : float
            Data end time
            
        Returns:
        --------
        BatchError
            Error with recovery suggestions
        """
        return BatchError(
            f"Event '{event_name}' time range [{start_time}, {end_time}] "
            f"outside data range [{data_start:.2f}, {data_end:.2f}]",
            ErrorCategory.DATA_VALIDATION,
            suggestions=[
                f"Adjust event start time to be >= {data_start:.2f}",
                f"Adjust event end time to be <= {data_end:.2f}",
                "Check if the time units are correct (seconds expected)",
                "Verify the event definition matches the actual data"
            ],
            context={
                "event_name": event_name,
                "event_range": [start_time, end_time],
                "data_range": [data_start, data_end]
            }
        )
    
    @staticmethod
    def handle_insufficient_data(channel_key: str, data_length: int,
                                required_length: int) -> BatchError:
        """
        Handle insufficient data error.
        
        Parameters:
        -----------
        channel_key : str
            Channel identifier
        data_length : int
            Actual data length
        required_length : int
            Required data length
            
        Returns:
        --------
        BatchError
            Error with recovery suggestions
        """
        return BatchError(
            f"Insufficient data for channel '{channel_key}': "
            f"{data_length} samples (need {required_length})",
            ErrorCategory.DATA_VALIDATION,
            suggestions=[
                "Reduce the segment length (nperseg) in PSD parameters",
                "Increase the frequency resolution (larger df)",
                "Check if the data was truncated during loading",
                "Verify the event time range is appropriate"
            ],
            context={
                "channel_key": channel_key,
                "data_length": data_length,
                "required_length": required_length
            }
        )
    
    @staticmethod
    def handle_psd_calculation_error(channel_key: str, event_name: str,
                                    error_msg: str) -> BatchError:
        """
        Handle PSD calculation error.
        
        Parameters:
        -----------
        channel_key : str
            Channel identifier
        event_name : str
            Event name
        error_msg : str
            Original error message
            
        Returns:
        --------
        BatchError
            Error with recovery suggestions
        """
        return BatchError(
            f"PSD calculation failed for {channel_key}/{event_name}",
            ErrorCategory.PROCESSING,
            suggestions=[
                "Check if the signal contains NaN or Inf values",
                "Verify the sample rate is correct",
                "Try reducing the segment length or increasing overlap",
                "Check if the signal is too short for the selected parameters",
                "Review the filter settings (may be causing instability)"
            ],
            context={
                "channel_key": channel_key,
                "event_name": event_name,
                "original_error": error_msg
            }
        )
    
    @staticmethod
    def handle_output_error(output_type: str, file_path: str,
                           error_msg: str) -> BatchError:
        """
        Handle output generation error.
        
        Parameters:
        -----------
        output_type : str
            Type of output (Excel, PowerPoint, HDF5, CSV)
        file_path : str
            Output file path
        error_msg : str
            Original error message
            
        Returns:
        --------
        BatchError
            Error with recovery suggestions
        """
        return BatchError(
            f"Failed to generate {output_type} output: {file_path}",
            ErrorCategory.OUTPUT,
            suggestions=[
                "Check if you have write permissions for the output directory",
                "Verify the output directory exists",
                "Close the file if it's already open in another application",
                "Check if there's sufficient disk space",
                "Try a different output file name or location"
            ],
            context={
                "output_type": output_type,
                "file_path": file_path,
                "original_error": error_msg
            }
        )
    
    @staticmethod
    def handle_filter_error(filter_type: str, cutoff_freq: float,
                           sample_rate: float, error_msg: str) -> BatchError:
        """
        Handle filter application error.
        
        Parameters:
        -----------
        filter_type : str
            Type of filter
        cutoff_freq : float
            Cutoff frequency
        sample_rate : float
            Sample rate
        error_msg : str
            Original error message
            
        Returns:
        --------
        BatchError
            Error with recovery suggestions
        """
        nyquist = sample_rate / 2
        return BatchError(
            f"Filter application failed: {filter_type} at {cutoff_freq} Hz",
            ErrorCategory.PROCESSING,
            suggestions=[
                f"Ensure cutoff frequency ({cutoff_freq} Hz) is below Nyquist ({nyquist} Hz)",
                "Try reducing the filter order",
                "Check if the signal contains NaN or Inf values",
                "Verify the sample rate is correct",
                "Consider using a different filter type"
            ],
            context={
                "filter_type": filter_type,
                "cutoff_freq": cutoff_freq,
                "sample_rate": sample_rate,
                "nyquist": nyquist,
                "original_error": error_msg
            }
        )


def log_error_with_recovery(error: BatchError):
    """
    Log error with full recovery information.
    
    Parameters:
    -----------
    error : BatchError
        Error to log
    """
    logger.error(error.get_full_message())
