"""
Batch PSD Processing Engine

This module provides the core batch processing engine for calculating PSDs across
multiple channels and events. It is designed to be GUI-independent for testability
and can process data from both HDF5 and CSV sources.

Author: SpectralEdge Development Team
Date: 2026-02-02
"""

import numpy as np
import logging
import time
from typing import Dict, List, Tuple, Optional, Any, Callable
from pathlib import Path
from datetime import datetime
from spectral_edge.core.psd import (
    calculate_psd_welch, calculate_psd_maximax, calculate_rms_from_psd
)
from spectral_edge.batch.spectrogram_generator import generate_spectrogram
from ..utils.hdf5_loader import HDF5FlightDataLoader
from .config import BatchConfig, EventDefinition
from .progress_tracker import ProgressTracker, ProgressInfo
from .performance_utils import MemoryManager, FFTOptimizer
from .error_handler import ErrorHandler, BatchError, log_error_with_recovery
from scipy import signal as scipy_signal


# Get module logger - configuration should be done at application entry point
logger = logging.getLogger(__name__)


class BatchProcessingResult:
    """Container for batch processing results."""
    
    def __init__(self):
        """Initialize empty result container."""
        self.channel_results = {}  # {(flight_key, channel_key): {event_name: PSDResult}}
        self.errors = []  # List of error messages
        self.warnings = []  # List of warning messages
        self.processing_log = []  # Detailed processing log
        self.start_time = None
        self.end_time = None
        
    def add_psd_result(self, flight_key: str, channel_key: str, event_name: str, 
                       frequencies: np.ndarray, psd: np.ndarray, 
                       metadata: Dict[str, Any], spectrogram_data: Optional[Dict[str, Any]] = None):
        """
        Add a PSD result to the container.
        
        Parameters:
        -----------
        flight_key : str
            Flight identifier
        channel_key : str
            Channel identifier
        event_name : str
            Event name (or 'full_duration')
        frequencies : np.ndarray
            Frequency array in Hz
        psd : np.ndarray
            PSD values
        metadata : dict
            Additional metadata (sample_rate, units, processing params, etc.)
        spectrogram_data : dict, optional
            Spectrogram data containing 'frequencies', 'times', and 'Sxx' arrays
        """
        channel_id = (flight_key, channel_key)
        
        if channel_id not in self.channel_results:
            self.channel_results[channel_id] = {}
        
        self.channel_results[channel_id][event_name] = {
            'frequencies': frequencies,
            'psd': psd,
            'metadata': metadata,
            'spectrogram': spectrogram_data
        }
    
    def add_error(self, message: str):
        """Add an error message to the log."""
        self.errors.append(message)
        logger.error(message)
    
    def add_warning(self, message: str):
        """Add a warning message to the log."""
        self.warnings.append(message)
        logger.warning(message)
    
    def add_log_entry(self, message: str):
        """Add an entry to the processing log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.processing_log.append(log_entry)
        logger.info(message)
    
    @property
    def channels_processed(self) -> int:
        """Get number of successfully processed channels."""
        return len(self.channel_results)
    
    @property
    def channels_failed(self) -> int:
        """Get number of failed channels."""
        return len(self.errors)
    
    @property
    def processing_time(self) -> float:
        """Get total processing time in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def success(self) -> bool:
        """Check if processing was successful (at least one channel processed)."""
        return len(self.channel_results) > 0


class BatchProcessor:
    """
    Core batch processing engine for PSD calculations.
    
    This class handles the orchestration of batch PSD processing operations,
    including data loading, filtering, PSD calculation, and result aggregation.
    It is designed to be GUI-independent for testability.
    """
    
    def __init__(self, config: BatchConfig, progress_callback: Optional[Callable] = None):
        """
        Initialize batch processor with configuration.
        
        Parameters:
        -----------
        config : BatchConfig
            Complete batch processing configuration
        progress_callback : callable, optional
            Callback for detailed progress updates
        """
        self.config = config
        self.result = BatchProcessingResult()
        self.hdf5_loaders = {}  # Cache of HDF5 loaders
        self.cancel_requested = False  # Flag for cancellation
        self.progress_callback = progress_callback
        self.progress_tracker = None
        
    def process(self) -> BatchProcessingResult:
        """
        Execute the batch processing operation.
        
        Returns:
        --------
        BatchProcessingResult
            Container with all processing results, errors, and logs
        """
        self.result.start_time = datetime.now()
        self.result.add_log_entry("=== Batch Processing Started ===")
        self.result.add_log_entry(f"Configuration: {self.config.config_name}")
        
        try:
            # Validate configuration
            self.config.validate()
            self.result.add_log_entry("Configuration validated successfully")
            
            # Process based on source type
            if self.config.source_type == "hdf5":
                self._process_hdf5_sources()
            elif self.config.source_type == "csv":
                self._process_csv_sources()
            else:
                raise ValueError(f"Unsupported source type: {self.config.source_type}")
                
        except Exception as e:
            self.result.add_error(f"Fatal error during batch processing: {str(e)}")
            logger.exception("Fatal error during batch processing")
        
        self.result.end_time = datetime.now()
        duration = (self.result.end_time - self.result.start_time).total_seconds()
        self.result.add_log_entry(f"=== Batch Processing Completed in {duration:.2f}s ===")
        self.result.add_log_entry(f"Processed {len(self.result.channel_results)} channels")
        self.result.add_log_entry(f"Errors: {len(self.result.errors)}, Warnings: {len(self.result.warnings)}")
        
        return self.result
    
    def _process_hdf5_sources(self):
        """Process HDF5 data sources one file at a time to minimize memory usage."""
        self.result.add_log_entry(f"Processing {len(self.config.source_files)} HDF5 file(s)")

        # Group selected channels by file for efficient sequential processing
        # This allows us to open one file, process all its channels, then close it
        channels_by_file = self._group_channels_by_file()

        # Process each selected channel
        total_channels = len(self.config.selected_channels)
        self.progress_tracker = ProgressTracker(total_channels, self.progress_callback)
        channel_idx = 0

        # Process one HDF5 file at a time
        for file_path in self.config.source_files:
            if self.cancel_requested:
                self.result.add_warning("Processing cancelled by user")
                break

            # Get channels to process from this file
            file_channels = channels_by_file.get(file_path, [])
            if not file_channels:
                continue

            # Open HDF5 file
            try:
                loader = HDF5FlightDataLoader(file_path)
                self.hdf5_loaders[file_path] = loader
                self.result.add_log_entry(f"Opened HDF5 file: {Path(file_path).name} ({len(file_channels)} channels)")
            except FileNotFoundError:
                error = ErrorHandler.handle_file_not_found(file_path)
                log_error_with_recovery(error)
                self.result.add_error(error.get_full_message())
                continue
            except Exception as e:
                error = ErrorHandler.handle_invalid_hdf5(file_path, str(e))
                log_error_with_recovery(error)
                self.result.add_error(error.get_full_message())
                continue

            # Process all channels from this file
            for flight_key, channel_key in file_channels:
                if self.cancel_requested:
                    self.result.add_warning("Processing cancelled by user")
                    break

                channel_idx += 1
                self.progress_tracker.start_channel(flight_key, channel_key)
                self.result.add_log_entry(f"Processing channel {channel_idx}/{total_channels}: {flight_key}/{channel_key}")

                try:
                    self._process_channel_hdf5(flight_key, channel_key)
                    self.progress_tracker.finish_channel()
                except Exception as e:
                    self.result.add_error(f"Failed to process {flight_key}/{channel_key}: {str(e)}")
                    self.progress_tracker.finish_channel()
                    continue
                finally:
                    # Clear memory after EVERY channel
                    MemoryManager.clear_memory()

            # Close this HDF5 file before opening the next one
            try:
                loader.close()
                self.result.add_log_entry(f"Closed HDF5 file: {Path(file_path).name}")
            except Exception as e:
                logger.warning(f"Error closing HDF5 file {file_path}: {e}")
            finally:
                del self.hdf5_loaders[file_path]
                MemoryManager.clear_memory()

    def _group_channels_by_file(self) -> Dict[str, List[Tuple[str, str]]]:
        """
        Group selected channels by their source HDF5 file.

        This enables sequential file processing to minimize memory usage.

        Returns:
        --------
        dict
            Mapping of file_path -> [(flight_key, channel_key), ...]
        """
        channels_by_file = {}

        # First, we need to determine which file contains which flight
        # Load metadata from all files to build the mapping
        flight_to_file = {}
        for file_path in self.config.source_files:
            try:
                loader = HDF5FlightDataLoader(file_path)
                for flight_key in loader.flights.keys():
                    flight_to_file[flight_key] = file_path
                loader.close()
            except Exception as e:
                logger.warning(f"Could not read metadata from {file_path}: {e}")
                continue

        # Group channels by file
        for flight_key, channel_key in self.config.selected_channels:
            file_path = flight_to_file.get(flight_key)
            if file_path:
                if file_path not in channels_by_file:
                    channels_by_file[file_path] = []
                channels_by_file[file_path].append((flight_key, channel_key))
            else:
                logger.warning(f"Flight {flight_key} not found in any HDF5 file")

        return channels_by_file
    
    def _process_channel_hdf5(self, flight_key: str, channel_key: str):
        """
        Process a single channel from HDF5 source.
        
        Parameters:
        -----------
        flight_key : str
            Flight identifier
        channel_key : str
            Channel identifier
        """
        # Find the loader that contains this flight
        loader = None
        for file_loader in self.hdf5_loaders.values():
            if flight_key in file_loader.flights:
                loader = file_loader
                break
        
        if loader is None:
            raise ValueError(f"Flight {flight_key} not found in any loaded HDF5 file")
        
        # Get channel info
        channel_info = loader.channels[flight_key][channel_key]
        sample_rate = channel_info.sample_rate
        units = channel_info.units

        # Check for cancellation before loading data
        if self.cancel_requested:
            raise InterruptedError("Processing cancelled by user")

        # Load full time history data (not decimated)
        load_start = time.perf_counter()
        data = loader.load_channel_data(
            flight_key, channel_key, decimate_for_display=False
        )
        time_array = data['time_full']
        signal_array = data['data_full']
        load_time = time.perf_counter() - load_start
        self.result.add_log_entry(
            f"  Data loaded: {len(signal_array)} samples ({len(signal_array)/sample_rate:.1f}s) in {load_time:.2f}s"
        )

        # Process full duration if requested
        if self.config.process_full_duration:
            self._process_event(
                flight_key, channel_key, "full_duration",
                time_array, signal_array, sample_rate, units,
                start_time=None, end_time=None
            )

        # Process each event
        for event in self.config.events:
            try:
                self._process_event(
                    flight_key, channel_key, event.name,
                    time_array, signal_array, sample_rate, units,
                    start_time=event.start_time, end_time=event.end_time
                )
            except Exception as e:
                self.result.add_warning(
                    f"Skipped event '{event.name}' for {flight_key}/{channel_key}: {str(e)}"
                )

        # Explicitly delete large arrays to free memory immediately
        del time_array, signal_array, data

    def _close_hdf5_loaders(self):
        """Close all HDF5 file loaders to free memory and file handles."""
        for file_path, loader in self.hdf5_loaders.items():
            try:
                loader.close()
                logger.debug(f"Closed HDF5 loader for {Path(file_path).name}")
            except Exception as e:
                logger.warning(f"Error closing HDF5 loader {file_path}: {e}")
        self.hdf5_loaders.clear()

    def _process_csv_sources(self):
        """Process CSV data sources."""
        self.result.add_log_entry(f"Processing {len(self.config.source_files)} CSV file(s)")
        
        # Import CSV loader (will be implemented in next phase)
        from .csv_loader import load_csv_files
        
        # Load all CSV files
        csv_data = load_csv_files(self.config.source_files)
        
        # Process each channel found in CSV files
        for file_path, channels_data in csv_data.items():
            for channel_key, (time_array, signal_array, sample_rate, units) in channels_data.items():
                try:
                    self._process_channel_csv(
                        file_path, channel_key, time_array, signal_array, 
                        sample_rate, units
                    )
                except Exception as e:
                    self.result.add_error(
                        f"Failed to process {file_path}/{channel_key}: {str(e)}"
                    )
    
    def _process_channel_csv(self, file_path: str, channel_key: str,
                            time_array: np.ndarray, signal_array: np.ndarray,
                            sample_rate: float, units: str):
        """
        Process a single channel from CSV source.
        
        Parameters:
        -----------
        file_path : str
            Source CSV file path
        channel_key : str
            Channel identifier
        time_array : np.ndarray
            Time array
        signal_array : np.ndarray
            Signal data array
        sample_rate : float
            Sample rate in Hz
        units : str
            Signal units
        """
        flight_key = Path(file_path).stem  # Use filename as flight key
        
        # Process full duration if requested
        if self.config.process_full_duration:
            self._process_event(
                flight_key, channel_key, "full_duration",
                time_array, signal_array, sample_rate, units,
                start_time=None, end_time=None
            )
        
        # Process each event
        for event in self.config.events:
            try:
                self._process_event(
                    flight_key, channel_key, event.name,
                    time_array, signal_array, sample_rate, units,
                    start_time=event.start_time, end_time=event.end_time
                )
            except Exception as e:
                self.result.add_warning(
                    f"Skipped event '{event.name}' for {flight_key}/{channel_key}: {str(e)}"
                )
    
    def _process_event(self, flight_key: str, channel_key: str, event_name: str,
                      time_array: np.ndarray, signal_array: np.ndarray,
                      sample_rate: float, units: str,
                      start_time: Optional[float] = None,
                      end_time: Optional[float] = None):
        """
        Process a single event (time range) for a channel.
        
        Parameters:
        -----------
        flight_key : str
            Flight identifier
        channel_key : str
            Channel identifier
        event_name : str
            Event name
        time_array : np.ndarray
            Time array
        signal_array : np.ndarray
            Signal data array
        sample_rate : float
            Sample rate in Hz
        units : str
            Signal units
        start_time : float, optional
            Event start time in seconds
        end_time : float, optional
            Event end time in seconds
        """
        # Check for cancellation
        if self.cancel_requested:
            raise InterruptedError("Processing cancelled by user")

        # Update progress tracker
        if self.progress_tracker:
            self.progress_tracker.update_event(event_name)

        event_start_time_perf = time.perf_counter()
        self.result.add_log_entry(f"  Starting event '{event_name}' processing...")

        # Extract event data
        if start_time is not None and end_time is not None:
            # Validate time range
            if start_time < time_array[0] or end_time > time_array[-1]:
                raise ValueError(
                    f"Event time range [{start_time}, {end_time}] outside data range "
                    f"[{time_array[0]:.2f}, {time_array[-1]:.2f}]"
                )
            
            # Extract event segment
            mask = (time_array >= start_time) & (time_array <= end_time)
            event_signal = signal_array[mask]
            
            if len(event_signal) == 0:
                raise ValueError(f"No data points in event time range")
        else:
            # Use full signal
            event_signal = signal_array
        
        # Check for cancellation
        if self.cancel_requested:
            raise InterruptedError("Processing cancelled by user")

        # Apply filtering if enabled
        if self.config.filter_config.enabled:
            filter_start = time.perf_counter()
            event_signal = self._apply_filter(event_signal, sample_rate)
            filter_time = time.perf_counter() - filter_start
            logger.debug(f"    Filter applied in {filter_time:.3f}s")

        # Check for cancellation
        if self.cancel_requested:
            raise InterruptedError("Processing cancelled by user")

        # Apply running mean removal if enabled
        if self.config.psd_config.remove_running_mean:
            mean_start = time.perf_counter()
            event_signal = self._remove_running_mean(event_signal, sample_rate)
            mean_time = time.perf_counter() - mean_start
            logger.debug(f"    Running mean removed in {mean_time:.3f}s")

        # Check for cancellation
        if self.cancel_requested:
            raise InterruptedError("Processing cancelled by user")

        # Calculate PSD
        psd_start = time.perf_counter()
        frequencies, psd = self._calculate_psd(event_signal, sample_rate)
        psd_time = time.perf_counter() - psd_start
        logger.debug(f"    PSD calculated in {psd_time:.3f}s ({len(event_signal)} samples)")

        # Calculate RMS
        rms = calculate_rms_from_psd(frequencies, psd)

        # Check for cancellation
        if self.cancel_requested:
            raise InterruptedError("Processing cancelled by user")

        # Generate spectrogram if enabled
        spectrogram_data = None
        if self.config.spectrogram_config.enabled:
            try:
                spec_start = time.perf_counter()
                spec_frequencies, spec_times, Sxx = generate_spectrogram(
                    event_signal,
                    sample_rate,
                    desired_df=self.config.spectrogram_config.desired_df,
                    overlap_percent=self.config.spectrogram_config.overlap_percent,
                    snr_threshold=self.config.spectrogram_config.snr_threshold,
                    use_efficient_fft=True
                )
                spec_time = time.perf_counter() - spec_start
                logger.debug(f"    Spectrogram generated in {spec_time:.3f}s")
                spectrogram_data = {
                    'frequencies': spec_frequencies,
                    'times': spec_times,
                    'Sxx': Sxx
                }
            except Exception as e:
                self.result.add_warning(
                    f"Failed to generate spectrogram for {flight_key}/{channel_key}/{event_name}: {str(e)}"
                )
        
        # Store result
        metadata = {
            'sample_rate': sample_rate,
            'units': units,
            'rms': rms,
            'method': self.config.psd_config.method,
            'window': self.config.psd_config.window,
            'overlap_percent': self.config.psd_config.overlap_percent,
            'frequency_spacing': self.config.psd_config.frequency_spacing,
            'filter_applied': self.config.filter_config.enabled,
            'mean_removed': self.config.psd_config.remove_running_mean,
            'event_start_time': start_time,
            'event_end_time': end_time,
            'timestamp': datetime.now().isoformat(),
            'spectrogram_generated': spectrogram_data is not None
        }
        
        self.result.add_psd_result(
            flight_key, channel_key, event_name,
            frequencies, psd, metadata, spectrogram_data
        )
        
        event_total_time = time.perf_counter() - event_start_time_perf
        self.result.add_log_entry(
            f"  Event '{event_name}': RMS = {rms:.4f} {units} (processed in {event_total_time:.2f}s)"
        )
    
    def _apply_filter(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        """
        Apply digital filter to signal.
        
        Parameters:
        -----------
        signal : np.ndarray
            Input signal
        sample_rate : float
            Sample rate in Hz
            
        Returns:
        --------
        np.ndarray
            Filtered signal
        """
        fc = self.config.filter_config
        nyquist = sample_rate / 2.0
        
        # Prepare cutoff frequencies (normalized to Nyquist)
        if fc.filter_type == "lowpass":
            Wn = min(fc.cutoff_high / nyquist, 0.95)
            btype = "lowpass"
        elif fc.filter_type == "highpass":
            Wn = max(fc.cutoff_low / nyquist, 0.01)
            btype = "highpass"
        elif fc.filter_type == "bandpass":
            Wn = [max(fc.cutoff_low / nyquist, 0.01), 
                  min(fc.cutoff_high / nyquist, 0.95)]
            btype = "bandpass"
        else:
            raise ValueError(f"Unknown filter type: {fc.filter_type}")
        
        # Design filter using SOS format for numerical stability
        if fc.filter_design == "butterworth":
            sos = scipy_signal.butter(fc.filter_order, Wn, btype=btype, output='sos')
        elif fc.filter_design == "chebyshev":
            sos = scipy_signal.cheby1(fc.filter_order, 0.5, Wn, btype=btype, output='sos')
        elif fc.filter_design == "bessel":
            sos = scipy_signal.bessel(fc.filter_order, Wn, btype=btype, output='sos')
        else:
            raise ValueError(f"Unknown filter design: {fc.filter_design}")
        
        # Apply filter
        filtered_signal = scipy_signal.sosfiltfilt(sos, signal)
        
        return filtered_signal
    
    def _remove_running_mean(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        """
        Remove running mean from signal using configurable window.

        Parameters:
        -----------
        signal : np.ndarray
            Input signal
        sample_rate : float
            Sample rate in Hz

        Returns:
        --------
        np.ndarray
            Signal with running mean removed
        """
        # Use configurable window size (default 1.0 seconds)
        window_seconds = self.config.psd_config.running_mean_window
        window_size = int(sample_rate * window_seconds)

        # Ensure minimum window size
        window_size = max(1, window_size)

        if len(signal) < window_size:
            # If signal is shorter than window, just remove overall mean
            return signal - np.mean(signal)

        # Calculate running mean using convolution
        kernel = np.ones(window_size) / window_size
        running_mean = np.convolve(signal, kernel, mode='same')

        return signal - running_mean
    
    def _calculate_psd(self, signal: np.ndarray, sample_rate: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate PSD using configured method.
        
        Parameters:
        -----------
        signal : np.ndarray
            Input signal
        sample_rate : float
            Sample rate in Hz
            
        Returns:
        --------
        frequencies : np.ndarray
            Frequency array in Hz
        psd : np.ndarray
            PSD values
        """
        pc = self.config.psd_config
        
        if pc.method == "welch":
            frequencies, psd = calculate_psd_welch(
                signal, sample_rate,
                window=pc.window,
                df=pc.desired_df,
                use_efficient_fft=pc.use_efficient_fft
            )
        elif pc.method == "maximax":
            frequencies, psd = calculate_psd_maximax(
                signal, sample_rate,
                window=pc.window
            )
        else:
            raise ValueError(f"Unknown PSD method: {pc.method}")
        
        return frequencies, psd
