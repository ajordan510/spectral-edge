"""
Channel Data Container Module

Provides data structures for managing multi-channel data with different sample rates and time lengths.
Supports backward compatibility with existing 4-tuple format while enabling future enhancements.

Key Features:
- Stores channel metadata and signal data
- Handles different sample rates per channel
- Handles different time lengths per channel
- Provides zero-padding for time alignment
- Maintains backward compatibility

Author: SpectralEdge Development Team
Date: 2025-01-28
Version: 1.0
"""

import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class ChannelData:
    """
    Container for channel data with metadata.
    
    This class wraps channel information to support multi-rate, multi-length analysis
    while maintaining backward compatibility with the existing 4-tuple format.
    
    Attributes
    ----------
    name : str
        Channel name (e.g., "Accel_X", "Mic_1")
    signal : np.ndarray
        Time-domain signal data, shape=(n_samples,), dtype=float64
    units : str
        Physical units (e.g., "g", "Pa", "V")
    flight_name : str
        Flight identifier (e.g., "FT-001", "TEST-2024-01-15")
    sample_rate : float
        Sample rate in Hz (e.g., 10000.0, 25600.0)
    start_time : float, optional
        Start time in seconds relative to flight start (default: 0.0)
    end_time : float, optional
        End time in seconds relative to flight start (default: computed from signal length)
    
    Notes
    -----
    - Signal data is always stored as float64 for numerical precision
    - Sample rate is required for PSD calculations
    - Time information enables proper alignment of multi-length channels
    
    Examples
    --------
    Create from existing 4-tuple format:
    
    >>> tuple_data = ("Accel_X", signal_array, "g", "FT-001")
    >>> channel = ChannelData.from_tuple(tuple_data, sample_rate=10000.0)
    
    Create directly:
    
    >>> channel = ChannelData(
    ...     name="Accel_X",
    ...     signal=signal_array,
    ...     units="g",
    ...     flight_name="FT-001",
    ...     sample_rate=10000.0
    ... )
    
    Convert back to tuple:
    
    >>> tuple_data = channel.to_tuple()
    """
    
    name: str
    signal: np.ndarray
    units: str
    flight_name: str
    sample_rate: float
    start_time: float = 0.0
    end_time: Optional[float] = None
    
    def __post_init__(self):
        """
        Validate and initialize derived attributes after dataclass initialization.
        
        Raises
        ------
        ValueError
            If signal is not a 1D numpy array
        ValueError
            If signal is empty
        ValueError
            If sample_rate is not positive
        TypeError
            If signal is not a numpy array
        """
        # Validate signal
        if not isinstance(self.signal, np.ndarray):
            raise TypeError(f"signal must be np.ndarray, got {type(self.signal)}")
        
        if self.signal.ndim != 1:
            raise ValueError(f"signal must be 1D, got shape {self.signal.shape}")
        
        if len(self.signal) == 0:
            raise ValueError("signal cannot be empty")
        
        # Ensure float64
        if self.signal.dtype != np.float64:
            self.signal = self.signal.astype(np.float64)
        
        # Validate sample rate
        if self.sample_rate <= 0:
            raise ValueError(f"sample_rate must be positive, got {self.sample_rate}")
        
        # Compute end_time if not provided
        if self.end_time is None:
            duration = len(self.signal) / self.sample_rate
            self.end_time = self.start_time + duration
    
    @property
    def duration(self) -> float:
        """
        Get signal duration in seconds.
        
        Returns
        -------
        float
            Duration in seconds
        """
        return self.end_time - self.start_time
    
    @property
    def n_samples(self) -> int:
        """
        Get number of samples in signal.
        
        Returns
        -------
        int
            Number of samples
        """
        return len(self.signal)
    
    @property
    def time_vector(self) -> np.ndarray:
        """
        Get time vector for signal.
        
        Returns
        -------
        np.ndarray
            Time vector in seconds, shape=(n_samples,)
        """
        return np.linspace(self.start_time, self.end_time, self.n_samples)
    
    def to_tuple(self) -> Tuple[str, np.ndarray, str, str]:
        """
        Convert to legacy 4-tuple format for backward compatibility.
        
        Returns
        -------
        tuple
            (name, signal, units, flight_name)
        
        Notes
        -----
        This enables seamless integration with existing code that expects 4-tuples.
        Sample rate and time information are lost in this conversion.
        
        Examples
        --------
        >>> channel = ChannelData("Accel_X", signal, "g", "FT-001", 10000.0)
        >>> tuple_data = channel.to_tuple()
        >>> name, signal, units, flight = tuple_data
        """
        return (self.name, self.signal, self.units, self.flight_name)
    
    @classmethod
    def from_tuple(
        cls,
        tuple_data: Tuple[str, np.ndarray, str, str],
        sample_rate: float,
        start_time: float = 0.0
    ) -> 'ChannelData':
        """
        Create ChannelData from legacy 4-tuple format.
        
        Parameters
        ----------
        tuple_data : tuple
            (name, signal, units, flight_name)
        sample_rate : float
            Sample rate in Hz
        start_time : float, optional
            Start time in seconds (default: 0.0)
        
        Returns
        -------
        ChannelData
            New ChannelData instance
        
        Raises
        ------
        ValueError
            If tuple_data doesn't have exactly 4 elements
        
        Examples
        --------
        >>> tuple_data = ("Accel_X", signal_array, "g", "FT-001")
        >>> channel = ChannelData.from_tuple(tuple_data, sample_rate=10000.0)
        """
        if len(tuple_data) != 4:
            raise ValueError(f"tuple_data must have 4 elements, got {len(tuple_data)}")
        
        name, signal, units, flight_name = tuple_data
        
        return cls(
            name=name,
            signal=signal,
            units=units,
            flight_name=flight_name,
            sample_rate=sample_rate,
            start_time=start_time
        )
    
    def get_aligned_signal(self, target_length: int, pad_value: float = 0.0) -> np.ndarray:
        """
        Get signal aligned to target length via zero-padding or truncation.
        
        Parameters
        ----------
        target_length : int
            Desired signal length in samples
        pad_value : float, optional
            Value to use for padding (default: 0.0)
        
        Returns
        -------
        np.ndarray
            Aligned signal, shape=(target_length,)
        
        Notes
        -----
        - If signal is shorter than target: zero-pad at end
        - If signal is longer than target: truncate at end
        - Original signal is not modified
        
        Examples
        --------
        >>> channel = ChannelData("Accel_X", np.array([1, 2, 3]), "g", "FT-001", 1000.0)
        >>> aligned = channel.get_aligned_signal(target_length=5)
        >>> print(aligned)
        [1. 2. 3. 0. 0.]
        """
        if target_length == len(self.signal):
            return self.signal.copy()
        elif target_length > len(self.signal):
            # Pad with zeros
            padded = np.full(target_length, pad_value, dtype=np.float64)
            padded[:len(self.signal)] = self.signal
            return padded
        else:
            # Truncate
            return self.signal[:target_length].copy()
    
    def __repr__(self) -> str:
        """
        Get string representation for debugging.
        
        Returns
        -------
        str
            String representation
        """
        return (
            f"ChannelData(name='{self.name}', "
            f"n_samples={self.n_samples}, "
            f"sample_rate={self.sample_rate:.1f} Hz, "
            f"duration={self.duration:.3f} s, "
            f"units='{self.units}', "
            f"flight='{self.flight_name}')"
        )
    
    def __str__(self) -> str:
        """
        Get human-readable string representation.
        
        Returns
        -------
        str
            Human-readable string
        """
        return f"{self.name} ({self.sample_rate:.0f} Hz, {self.units})"


def align_channels_by_time(
    channels: list,
    pad_value: float = 0.0
) -> list:
    """
    Align multiple channels to the same time length via zero-padding.
    
    Parameters
    ----------
    channels : list of ChannelData
        Channels to align
    pad_value : float, optional
        Value to use for padding (default: 0.0)
    
    Returns
    -------
    list of ChannelData
        New ChannelData objects with aligned signals
    
    Notes
    -----
    - Finds the maximum duration across all channels
    - Pads shorter channels to match the longest
    - Original ChannelData objects are not modified
    - Sample rates are preserved (different sample rates OK)
    
    Examples
    --------
    >>> ch1 = ChannelData("Ch1", np.array([1, 2, 3]), "V", "FT-001", 1000.0)
    >>> ch2 = ChannelData("Ch2", np.array([4, 5]), "V", "FT-001", 1000.0)
    >>> aligned = align_channels_by_time([ch1, ch2])
    >>> print(len(aligned[0].signal), len(aligned[1].signal))
    3 3
    """
    if not channels:
        return []
    
    # Find maximum duration
    max_duration = max(ch.duration for ch in channels)
    
    # Align each channel
    aligned = []
    for ch in channels:
        # Calculate target length for this channel's sample rate
        target_length = int(np.ceil(max_duration * ch.sample_rate))
        
        # Create aligned signal
        aligned_signal = ch.get_aligned_signal(target_length, pad_value)
        
        # Create new ChannelData with aligned signal
        aligned_ch = ChannelData(
            name=ch.name,
            signal=aligned_signal,
            units=ch.units,
            flight_name=ch.flight_name,
            sample_rate=ch.sample_rate,
            start_time=ch.start_time,
            end_time=ch.start_time + (target_length / ch.sample_rate)
        )
        
        aligned.append(aligned_ch)
    
    return aligned


def get_max_sample_rate(channels: list) -> float:
    """
    Get the maximum sample rate across multiple channels.
    
    Parameters
    ----------
    channels : list of ChannelData
        Channels to analyze
    
    Returns
    -------
    float
        Maximum sample rate in Hz
    
    Examples
    --------
    >>> ch1 = ChannelData("Ch1", signal1, "V", "FT-001", 10000.0)
    >>> ch2 = ChannelData("Ch2", signal2, "V", "FT-001", 25600.0)
    >>> max_rate = get_max_sample_rate([ch1, ch2])
    >>> print(max_rate)
    25600.0
    """
    if not channels:
        return 0.0
    return max(ch.sample_rate for ch in channels)


def get_sample_rate_summary(channels: list) -> str:
    """
    Get human-readable summary of sample rates in channel list.
    
    Parameters
    ----------
    channels : list of ChannelData
        Channels to summarize
    
    Returns
    -------
    str
        Summary string
    
    Examples
    --------
    >>> summary = get_sample_rate_summary(channels)
    >>> print(summary)
    "3 channels: 10.0 kHz (2), 25.6 kHz (1)"
    """
    if not channels:
        return "No channels"
    
    # Count sample rates
    rate_counts = {}
    for ch in channels:
        rate = ch.sample_rate
        rate_counts[rate] = rate_counts.get(rate, 0) + 1
    
    # Format summary
    n_channels = len(channels)
    rate_strs = []
    for rate in sorted(rate_counts.keys()):
        count = rate_counts[rate]
        rate_khz = rate / 1000.0
        rate_strs.append(f"{rate_khz:.1f} kHz ({count})")
    
    return f"{n_channels} channels: {', '.join(rate_strs)}"
