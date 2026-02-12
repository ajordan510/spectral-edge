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
from typing import Dict, List, Tuple, Optional, Any, Callable, TypedDict, NotRequired
from pathlib import Path
from datetime import datetime
from spectral_edge.core.psd import (
    calculate_psd_welch, calculate_psd_maximax, calculate_rms_from_psd
)
from spectral_edge.batch.spectrogram_generator import generate_spectrogram
from ..utils.hdf5_loader import HDF5FlightDataLoader
from ..utils.signal_conditioning import apply_robust_filtering
from .config import BatchConfig, EventDefinition
from .progress_tracker import ProgressTracker, ProgressInfo
from .performance_utils import MemoryManager, FFTOptimizer
from .error_handler import ErrorHandler, BatchError, log_error_with_recovery


# Get module logger - configuration should be done at application entry point
logger = logging.getLogger(__name__)


class SpectrogramResult(TypedDict):
    """Spectrogram arrays produced by generate_spectrogram."""

    frequencies: np.ndarray  # 1-D, frequency bins in Hz
    times: np.ndarray        # 1-D, time bins in seconds
    Sxx: np.ndarray          # 2-D (frequencies x times), spectral power


class PSDResultMetadata(TypedDict, total=False):
    """Metadata recorded alongside each PSD result.

    All keys are written by ``_process_event``; consumers may read any
    subset via ``.get()``.
    """

    sample_rate: float
    units: str
    rms: float
    method: str                      # "welch" or "maximax"
    window: str                      # e.g. "hann"
    overlap_percent: float
    frequency_spacing: str           # "constant_bandwidth" or "1/N"
    requested_df_hz: float
    actual_df_hz: Optional[float]
    filter_applied: bool
    user_filter_enabled: bool
    user_highpass_hz: Optional[float]
    user_lowpass_hz: Optional[float]
    applied_highpass_hz: float
    applied_lowpass_hz: float
    filter_messages: List[str]
    event_start_time: Optional[float]
    event_end_time: Optional[float]
    timestamp: str                   # ISO-8601
    spectrogram_generated: bool


class PSDEventResult(TypedDict, total=False):
    """Single event result stored in ``channel_results``."""

    frequencies: np.ndarray
    psd: np.ndarray
    metadata: PSDResultMetadata
    spectrogram: Optional[SpectrogramResult]
    conditioned_time: np.ndarray     # present when processor caches time data
    conditioned_signal: np.ndarray   # present when processor caches signal data


class BatchProcessingResult:
    """Container for batch processing results."""
    
    def __init__(self):
        """Initialize empty result container."""
        self.channel_results: Dict[Tuple[str, str], Dict[str, PSDEventResult]] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.processing_log = []  # Detailed processing log
        self.start_time = None
        self.end_time = None
        
    def add_psd_result(
        self,
        flight_key: str,
        channel_key: str,
        event_name: str,
        frequencies: np.ndarray,
        psd: np.ndarray,
        metadata: PSDResultMetadata,
        spectrogram_data: Optional[SpectrogramResult] = None,
        conditioned_time: Optional[np.ndarray] = None,
        conditioned_signal: Optional[np.ndarray] = None,
    ):
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
        metadata : PSDResultMetadata
            Processing metadata (sample_rate, units, filter params, etc.)
        spectrogram_data : SpectrogramResult, optional
            Spectrogram arrays (frequencies, times, Sxx)
        conditioned_time : np.ndarray, optional
            Time array for the conditioned event signal (avoids re-loading for reports)
        conditioned_signal : np.ndarray, optional
            Conditioned (filtered) event signal (avoids re-conditioning for reports)
        """
        channel_id = (flight_key, channel_key)

        if channel_id not in self.channel_results:
            self.channel_results[channel_id] = {}

        result_entry: PSDEventResult = {
            'frequencies': frequencies,
            'psd': psd,
            'metadata': metadata,
            'spectrogram': spectrogram_data,
        }
        if conditioned_time is not None and conditioned_signal is not None:
            result_entry['conditioned_time'] = conditioned_time
            result_entry['conditioned_signal'] = conditioned_signal
        self.channel_results[channel_id][event_name] = result_entry
    
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
        self._flight_to_file_cache = None  # Cache for flight -> file mapping

    def _resolve_user_filter_overrides(self) -> Tuple[Optional[float], Optional[float]]:
        """Resolve optional user highpass/lowpass overrides from batch config."""
        fc = self.config.filter_config
        if not getattr(fc, "enabled", False):
            return None, None

        user_highpass = getattr(fc, "user_highpass_hz", None)
        user_lowpass = getattr(fc, "user_lowpass_hz", None)

        filter_type = str(getattr(fc, "filter_type", "bandpass")).strip().lower()
        if user_highpass is None and filter_type in {"highpass", "bandpass"}:
            user_highpass = getattr(fc, "cutoff_low", None)
        if user_lowpass is None and filter_type in {"lowpass", "bandpass"}:
            user_lowpass = getattr(fc, "cutoff_high", None)

        try:
            user_highpass = float(user_highpass) if user_highpass is not None else None
        except (TypeError, ValueError):
            user_highpass = None

        try:
            user_lowpass = float(user_lowpass) if user_lowpass is not None else None
        except (TypeError, ValueError):
            user_lowpass = None

        return user_highpass, user_lowpass
        
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
        
        if self.progress_tracker:
            self.progress_tracker.finish_all()

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
        Uses cached flight-to-file mapping to avoid re-opening files.

        Returns:
        --------
        dict
            Mapping of file_path -> [(flight_key, channel_key), ...]
        """
        channels_by_file = {}

        # Build flight-to-file mapping (cached to avoid re-opening files)
        flight_to_file = self._get_flight_to_file_mapping()

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

    def _get_flight_to_file_mapping(self) -> Dict[str, str]:
        """
        Get or build the flight-to-file mapping.

        This mapping is cached to avoid re-opening HDF5 files multiple times.

        Returns:
        --------
        dict
            Mapping of flight_key -> file_path
        """
        if self._flight_to_file_cache is not None:
            return self._flight_to_file_cache

        # Build the mapping by reading metadata from each file
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

        self._flight_to_file_cache = flight_to_file
        return flight_to_file
    
    def _get_event_time_bounds(self) -> tuple:
        """
        Calculate the min/max time bounds across all events.

        Returns:
        --------
        tuple
            (min_time, max_time) or (None, None) if full duration is requested
        """
        if self._include_full_duration():
            return None, None

        if not self.config.events:
            return None, None

        min_time = min(event.start_time for event in self.config.events)
        max_time = max(event.end_time for event in self.config.events)

        return min_time, max_time

    def _include_full_duration(self) -> bool:
        """Return True if full-duration outputs should be included."""
        return bool(self.config.process_full_duration)

    def _process_channel_hdf5(self, flight_key: str, channel_key: str):
        """
        Process a single channel from HDF5 source.

        Uses optimized data loading - only loads the time range needed
        for all events when full duration is not requested.

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

        # Calculate time bounds to optimize data loading
        # Only load the data range needed for all events (with small buffer)
        event_min_time, event_max_time = self._get_event_time_bounds()

        # Add buffer for filter edge effects during event-only loads.
        buffer_seconds = 2.0

        load_start = time.perf_counter()
        if event_min_time is not None and event_max_time is not None:
            # Load only the time range needed for events (with buffer)
            start_time = max(0, event_min_time - buffer_seconds)
            end_time = event_max_time + buffer_seconds
            data = loader.load_channel_data(
                flight_key, channel_key, decimate_for_display=False,
                start_time=start_time, end_time=end_time
            )
            self.result.add_log_entry(
                f"  Optimized load: time range [{start_time:.1f}s, {end_time:.1f}s] for events"
            )
        else:
            # Load full time history
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
        if self._include_full_duration():
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
        if self._include_full_duration():
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
            # Validate time range (allow tolerance of one sample period to
            # accommodate sample-alignment offsets from optimized loading)
            sample_period = 1.0 / sample_rate if sample_rate > 0 else 0.0
            if start_time < time_array[0] - sample_period or end_time > time_array[-1] + sample_period:
                raise ValueError(
                    f"Event time range [{start_time}, {end_time}] outside data range "
                    f"[{time_array[0]:.2f}, {time_array[-1]:.2f}]"
                )
            
            # Extract event segment
            mask = (time_array >= start_time) & (time_array <= end_time)
            event_time = time_array[mask]
            event_signal = signal_array[mask]

            if len(event_signal) == 0:
                raise ValueError(f"No data points in event time range")
        else:
            # Use full signal
            event_time = time_array
            event_signal = signal_array
        
        # Check for cancellation
        if self.cancel_requested:
            raise InterruptedError("Processing cancelled by user")

        # Apply baseline robust filtering (always), with optional user overrides.
        user_highpass, user_lowpass = self._resolve_user_filter_overrides()
        filter_start = time.perf_counter()
        event_signal, applied_highpass, applied_lowpass, filter_messages = apply_robust_filtering(
            event_signal,
            sample_rate,
            user_highpass=user_highpass,
            user_lowpass=user_lowpass,
        )
        filter_time = time.perf_counter() - filter_start
        logger.debug(f"    Baseline/user filtering applied in {filter_time:.3f}s")
        for msg in filter_messages:
            self.result.add_log_entry(
                f"  Filter info ({flight_key}/{channel_key}/{event_name}): {msg}"
            )

        # Check for cancellation
        if self.cancel_requested:
            raise InterruptedError("Processing cancelled by user")

        # Calculate PSD
        psd_start = time.perf_counter()
        frequencies, psd = self._calculate_psd(event_signal, sample_rate)
        psd_time = time.perf_counter() - psd_start
        logger.debug(f"    PSD calculated in {psd_time:.3f}s ({len(event_signal)} samples)")
        actual_df_hz = float(frequencies[1] - frequencies[0]) if len(frequencies) > 1 else None

        # Calculate RMS
        rms = calculate_rms_from_psd(frequencies, psd)

        # Check for cancellation
        if self.cancel_requested:
            raise InterruptedError("Processing cancelled by user")

        # Generate spectrogram if enabled
        spectrogram_data: Optional[SpectrogramResult] = None
        if self.config.spectrogram_config.enabled:
            try:
                spec_start = time.perf_counter()
                spec_frequencies, spec_times, Sxx = generate_spectrogram(
                    event_signal,
                    sample_rate,
                    desired_df=self.config.spectrogram_config.desired_df,
                    overlap_percent=self.config.spectrogram_config.overlap_percent,
                    snr_threshold=self.config.spectrogram_config.snr_threshold,
                    use_efficient_fft=self.config.spectrogram_config.use_efficient_fft
                )
                spec_time = time.perf_counter() - spec_start
                logger.debug(f"    Spectrogram generated in {spec_time:.3f}s")
                spectrogram_data = SpectrogramResult(
                    frequencies=spec_frequencies,
                    times=spec_times,
                    Sxx=Sxx,
                )
            except Exception as e:
                self.result.add_warning(
                    f"Failed to generate spectrogram for {flight_key}/{channel_key}/{event_name}: {str(e)}"
                )
        
        # Store result
        metadata: PSDResultMetadata = {
            'sample_rate': sample_rate,
            'units': units,
            'rms': rms,
            'method': self.config.psd_config.method,
            'window': self.config.psd_config.window,
            'overlap_percent': self.config.psd_config.overlap_percent,
            'frequency_spacing': self.config.psd_config.frequency_spacing,
            'requested_df_hz': float(self.config.psd_config.desired_df),
            'actual_df_hz': actual_df_hz,
            'filter_applied': True,
            'user_filter_enabled': bool(self.config.filter_config.enabled),
            'user_highpass_hz': user_highpass,
            'user_lowpass_hz': user_lowpass,
            'applied_highpass_hz': applied_highpass,
            'applied_lowpass_hz': applied_lowpass,
            'filter_messages': list(filter_messages),
            'event_start_time': start_time,
            'event_end_time': end_time,
            'timestamp': datetime.now().isoformat(),
            'spectrogram_generated': spectrogram_data is not None
        }
        
        self.result.add_psd_result(
            flight_key, channel_key, event_name,
            frequencies, psd, metadata, spectrogram_data,
            conditioned_time=event_time,
            conditioned_signal=event_signal,
        )
        
        event_total_time = time.perf_counter() - event_start_time_perf
        self.result.add_log_entry(
            f"  Event '{event_name}': RMS = {rms:.4f} {units} (processed in {event_total_time:.2f}s)"
        )
    
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
                window=pc.window,
                overlap_percent=pc.overlap_percent,
                df=pc.desired_df,
                use_efficient_fft=pc.use_efficient_fft,
            )
        else:
            raise ValueError(f"Unknown PSD method: {pc.method}")
        
        return frequencies, psd
