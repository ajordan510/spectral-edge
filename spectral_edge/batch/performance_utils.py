"""
Performance Optimization Utilities for Batch Processing

This module provides utilities for optimizing memory usage and processing speed
during batch PSD calculations.

Author: SpectralEdge Development Team
Date: 2026-02-02
"""

import gc
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages memory usage during batch processing.
    
    Provides utilities for monitoring memory usage, forcing garbage collection,
    and optimizing data structures for memory efficiency.
    """
    
    @staticmethod
    def optimize_array(array: np.ndarray) -> np.ndarray:
        """
        Optimize numpy array for memory efficiency.
        
        Converts array to most efficient dtype and ensures contiguous memory layout.
        
        Parameters:
        -----------
        array : np.ndarray
            Input array
            
        Returns:
        --------
        np.ndarray
            Optimized array
        """
        # Ensure contiguous memory layout for efficient processing
        if not array.flags['C_CONTIGUOUS']:
            array = np.ascontiguousarray(array)

        # Note: We keep float64 precision for PSD calculations.
        # PSD values can span many orders of magnitude (e.g., 1e-12 to 1e3),
        # and float32 would lose precision for small values.

        return array
    
    @staticmethod
    def clear_memory():
        """Force garbage collection to free memory."""
        gc.collect()
        logger.debug("Forced garbage collection")
    
    @staticmethod
    def estimate_memory_usage(signal_length: int, num_channels: int, 
                            num_events: int) -> float:
        """
        Estimate memory usage for batch processing.
        
        Parameters:
        -----------
        signal_length : int
            Length of signal arrays
        num_channels : int
            Number of channels to process
        num_events : int
            Number of events per channel
            
        Returns:
        --------
        float
            Estimated memory usage in MB
        """
        # Estimate based on typical data structures
        bytes_per_float = 8  # float64
        signal_memory = signal_length * bytes_per_float
        psd_memory = (signal_length // 2) * bytes_per_float  # Approximate PSD length
        
        total_per_channel = signal_memory + (psd_memory * num_events)
        total_memory = total_per_channel * num_channels
        
        return total_memory / (1024 * 1024)  # Convert to MB


class ChunkedProcessor:
    """
    Processes large signals in chunks to reduce memory usage.
    
    Useful for very long time histories that don't fit in memory.
    """
    
    @staticmethod
    def process_in_chunks(signal: np.ndarray, chunk_size: int,
                         process_func, overlap: int = 0) -> list:
        """
        Process signal in overlapping chunks.
        
        Parameters:
        -----------
        signal : np.ndarray
            Input signal
        chunk_size : int
            Size of each chunk
        process_func : callable
            Function to apply to each chunk
        overlap : int, optional
            Overlap between chunks in samples
            
        Returns:
        --------
        list
            List of results from each chunk
        """
        results = []
        stride = chunk_size - overlap
        
        for start_idx in range(0, len(signal), stride):
            end_idx = min(start_idx + chunk_size, len(signal))
            chunk = signal[start_idx:end_idx]
            
            if len(chunk) < chunk_size // 2:
                # Skip very small final chunk
                break
            
            result = process_func(chunk)
            results.append(result)
            
            # Clear memory after each chunk
            del chunk
            if start_idx % (stride * 10) == 0:  # Every 10 chunks
                MemoryManager.clear_memory()
        
        return results


class FFTOptimizer:
    """
    Optimizes FFT calculations for batch processing.
    
    Provides utilities for selecting optimal FFT sizes and caching FFT plans.
    """
    
    @staticmethod
    def next_power_of_2(n: int) -> int:
        """
        Find the next power of 2 greater than or equal to n.
        
        Parameters:
        -----------
        n : int
            Input number
            
        Returns:
        --------
        int
            Next power of 2
        """
        return 2 ** int(np.ceil(np.log2(n)))
    
    @staticmethod
    def optimal_fft_size(signal_length: int, desired_df: float,
                        sample_rate: float) -> int:
        """
        Calculate optimal FFT size for given parameters.
        
        Parameters:
        -----------
        signal_length : int
            Length of signal
        desired_df : float
            Desired frequency resolution in Hz
        sample_rate : float
            Sample rate in Hz
            
        Returns:
        --------
        int
            Optimal FFT size (power of 2)
        """
        # Calculate nperseg from desired df
        nperseg = int(sample_rate / desired_df)
        
        # Limit to signal length
        nperseg = min(nperseg, signal_length)
        
        # Round to next power of 2 for efficiency
        nperseg_efficient = FFTOptimizer.next_power_of_2(nperseg)
        
        # Don't exceed signal length
        if nperseg_efficient > signal_length:
            nperseg_efficient = FFTOptimizer.next_power_of_2(signal_length // 2)
        
        return nperseg_efficient
    
    @staticmethod
    def validate_fft_parameters(nperseg: int, noverlap: int,
                               signal_length: int) -> Tuple[int, int]:
        """
        Validate and adjust FFT parameters if needed.
        
        Parameters:
        -----------
        nperseg : int
            Segment length
        noverlap : int
            Overlap length
        signal_length : int
            Total signal length
            
        Returns:
        --------
        Tuple[int, int]
            Validated (nperseg, noverlap)
        """
        # Ensure nperseg doesn't exceed signal length
        if nperseg > signal_length:
            nperseg = signal_length
            logger.warning(f"nperseg reduced to signal length: {nperseg}")
        
        # Ensure noverlap is less than nperseg
        if noverlap >= nperseg:
            noverlap = nperseg // 2
            logger.warning(f"noverlap reduced to nperseg//2: {noverlap}")
        
        # Ensure at least 2 segments
        if (signal_length - noverlap) < (nperseg - noverlap):
            # Adjust nperseg to allow at least 2 segments
            nperseg = signal_length // 2
            noverlap = nperseg // 2
            logger.warning(f"Parameters adjusted for minimum 2 segments: nperseg={nperseg}, noverlap={noverlap}")
        
        return nperseg, noverlap


def optimize_batch_config(config: 'BatchConfig', 
                         total_signal_length: int) -> 'BatchConfig':
    """
    Optimize batch configuration for performance.
    
    Adjusts parameters based on signal length and available memory.
    
    Parameters:
    -----------
    config : BatchConfig
        Original configuration
    total_signal_length : int
        Total length of signals to process
        
    Returns:
    --------
    BatchConfig
        Optimized configuration
    """
    # Estimate memory usage
    num_channels = len(config.selected_channels) if hasattr(config, 'selected_channels') else 1
    num_events = len(config.events) + (1 if config.process_full_duration else 0)
    
    estimated_mb = MemoryManager.estimate_memory_usage(
        total_signal_length, num_channels, num_events
    )
    
    logger.info(f"Estimated memory usage: {estimated_mb:.1f} MB")
    
    # If memory usage is high, suggest optimizations
    if estimated_mb > 1000:  # > 1 GB
        logger.warning(
            f"High memory usage detected ({estimated_mb:.1f} MB). "
            "Consider processing fewer channels at once or using chunked processing."
        )
    
    return config
