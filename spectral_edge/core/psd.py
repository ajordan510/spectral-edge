"""
Power Spectral Density (PSD) Calculation Module

This module provides functions for calculating Power Spectral Density (PSD) using
various methods including Welch's method and maximax (envelope) PSD calculation
as defined in SMC-S-016 for aerospace applications.

Functions:
    calculate_psd_welch: Calculate PSD using Welch's method (averaged periodogram)
    calculate_psd_maximax: Calculate maximax PSD (envelope of 1-second PSDs per SMC-S-016)
    calculate_rms_from_psd: Calculate RMS value from PSD using Parseval's theorem
    convert_psd_to_octave_bands: Convert narrowband PSD to octave band representation
    psd_to_db: Convert PSD values to decibel (dB) scale for visualization
    get_window_options: Get available window function options with descriptions

References:
    - Welch, P. (1967). "The use of fast Fourier transform for the estimation of 
      power spectra: A method based on time averaging over short, modified periodograms"
    - SMC-S-016: Test Requirements for Launch, Upper-Stage, and Space Vehicles

Author: SpectralEdge Development Team
Date: 2025-01-22
"""

import logging
from functools import lru_cache
import numpy as np
from scipy import signal
from typing import Optional, Tuple, Union, Dict, Any

logger = logging.getLogger(__name__)


# Cache for octave band frequency grids to avoid recomputation
_octave_cache: Dict[Tuple, Any] = {}
_OCTAVE_CACHE_MAX_SIZE = 32


def _get_cached_octave_grid(
    freq_min: float,
    freq_max: float,
    octave_fraction: float
) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Get or compute cached octave band center frequencies and dense grid.

    Returns cached result if available, otherwise computes and caches.

    Parameters:
    -----------
    freq_min : float
        Minimum frequency in Hz
    freq_max : float
        Maximum frequency in Hz
    octave_fraction : float
        Octave fraction (e.g., 3 for 1/3 octave)

    Returns:
    --------
    Tuple containing:
        - dense_freqs: Dense log-spaced frequency grid for interpolation
        - octave_frequencies: Octave band center frequencies
        - bandwidth_factor: Factor for calculating band edges
    """
    # Create cache key (round to avoid floating point issues)
    cache_key = (round(freq_min, 6), round(freq_max, 6), round(octave_fraction, 6))

    if cache_key in _octave_cache:
        logger.debug(f"Using cached octave grid for {cache_key}")
        return _octave_cache[cache_key]

    # Compute the grid
    logger.debug(f"Computing octave grid for freq_min={freq_min}, freq_max={freq_max}, fraction={octave_fraction}")

    # Build dense log-spaced frequency grid
    log_min = np.log10(freq_min)
    log_max = np.log10(freq_max)
    log_span = max(log_max - log_min, 1e-6)
    points_per_band = 25
    bands_per_decade = octave_fraction * np.log2(10.0)
    points_per_decade = max(300, int(np.ceil(points_per_band * bands_per_decade)))
    points_per_decade = min(points_per_decade, 5000)
    n_points = max(200, int(np.ceil(log_span * points_per_decade)))
    dense_freqs = np.logspace(log_min, log_max, n_points)

    # Reference frequency for octave band calculation (ANSI/IEC standard)
    f_ref = 1000.0  # Hz

    # Calculate band width factor
    bandwidth_factor = 2.0 ** (1.0 / (2.0 * octave_fraction))

    # Find range of octave band indices needed
    n_min = int(np.floor(octave_fraction * np.log2(freq_min / f_ref)))
    n_max = int(np.ceil(octave_fraction * np.log2(freq_max / f_ref)))

    # Generate octave band center frequencies
    octave_indices = np.arange(n_min, n_max + 1)
    octave_frequencies = f_ref * 2.0 ** (octave_indices / octave_fraction)

    # Filter to only include bands within frequency range
    valid_bands = (octave_frequencies >= freq_min) & (octave_frequencies <= freq_max)
    octave_frequencies = octave_frequencies[valid_bands]

    # Cache the result
    if len(_octave_cache) >= _OCTAVE_CACHE_MAX_SIZE:
        # Remove oldest entry (simple FIFO eviction)
        oldest_key = next(iter(_octave_cache))
        del _octave_cache[oldest_key]

    result = (dense_freqs, octave_frequencies, bandwidth_factor)
    _octave_cache[cache_key] = result

    return result


def clear_octave_cache():
    """Clear the octave band calculation cache."""
    global _octave_cache
    _octave_cache = {}
    logger.debug("Octave band cache cleared")


def calculate_psd_welch(
    time_data: np.ndarray,
    sample_rate: float,
    window: str = 'hann',
    nperseg: Optional[int] = None,
    noverlap: Optional[int] = None,
    df: Optional[float] = None,
    use_efficient_fft: bool = False
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate Power Spectral Density using Welch's method.
    
    Welch's method computes an estimate of the power spectral density by dividing
    the data into overlapping segments, computing a modified periodogram for each
    segment, and averaging the periodograms. This reduces noise in the PSD estimate
    compared to a single periodogram.
    
    The window function is applied to each segment to reduce spectral leakage.
    The 'density' scaling is used, which means the PSD is normalized such that
    the integral of the PSD over frequency equals the variance of the signal.
    
    Window Energy Correction:
        scipy.signal.welch automatically applies the proper window energy correction
        factor when scaling='density' is used. This ensures that the total power
        (integral of PSD) equals the signal variance regardless of the window function.
        No manual correction is needed.
    
    Parameters
    ----------
    time_data : np.ndarray
        Input signal array (1D). Can be any length.
        Type: float64 array
        Units: Same as signal (e.g., g for acceleration, Pa for pressure)
        
    sample_rate : float
        Sampling frequency of the input signal in Hz.
        Type: float
        Units: Hz (samples per second)
        Must be positive.
        
    window : str, optional
        Window function to apply to each segment. Default is 'hann'.
        Type: str
        Options: 'hann', 'hamming', 'blackman', 'bartlett', 'flattop', etc.
        See scipy.signal.get_window for full list.
        
    nperseg : int, optional
        Length of each segment in samples. If None, calculated from df or defaults to 256.
        Type: int or None
        Units: samples
        Must be positive and less than length of time_data.
        Larger values give better frequency resolution but worse time resolution.
        
    noverlap : int, optional
        Number of samples to overlap between segments. If None, defaults to nperseg // 2.
        Type: int or None
        Units: samples
        Must be less than nperseg.
        Typical value is 50% (nperseg // 2) for good variance reduction.
        
    df : float, optional
        Desired frequency resolution in Hz. If provided, nperseg is calculated as
        nperseg = sample_rate / df. Takes precedence over nperseg parameter.
        Type: float or None
        Units: Hz
        Must be positive and less than sample_rate / 2.
        
    use_efficient_fft : bool, optional
        If True, rounds nperseg to the nearest power of 2 for faster FFT computation.
        Default is False.
        Type: bool
        Note: This may result in slightly different frequency resolution than requested.
    
    Returns
    -------
    frequencies : np.ndarray
        Array of frequency values in Hz corresponding to the PSD values.
        Type: float64 array
        Units: Hz
        Shape: (n_freqs,) where n_freqs = nperseg // 2 + 1
        
    psd : np.ndarray
        Power Spectral Density values.
        Type: float64 array
        Units: signal_units^2 / Hz (e.g., g^2/Hz for acceleration)
        Shape: (n_freqs,)
        
    Raises
    ------
    ValueError
        If time_data is empty
        If sample_rate is not positive
        If nperseg is larger than time_data length
        If df results in nperseg larger than time_data length
    
    Examples
    --------
    >>> # Generate a test signal with 10 Hz and 60 Hz components
    >>> import numpy as np
    >>> sample_rate = 1000.0  # Hz
    >>> duration = 10.0  # seconds
    >>> t = np.linspace(0, duration, int(sample_rate * duration))
    >>> signal = np.sin(2 * np.pi * 10 * t) + 0.5 * np.sin(2 * np.pi * 60 * t)
    >>> 
    >>> # Calculate PSD with 1 Hz frequency resolution
    >>> frequencies, psd = calculate_psd_welch(signal, sample_rate, df=1.0)
    >>> 
    >>> # Find peaks at 10 Hz and 60 Hz
    >>> peak_10hz = psd[np.argmin(np.abs(frequencies - 10))]
    >>> peak_60hz = psd[np.argmin(np.abs(frequencies - 60))]
    
    Notes
    -----
    - Frequency resolution (df) = sample_rate / nperseg
    - Better frequency resolution requires longer segments (larger nperseg)
    - More segments (smaller nperseg) gives better variance reduction
    - Trade-off between frequency resolution and variance
    - For vibration analysis, typical df is 0.5 to 2 Hz
    - Hann window is recommended for general purpose analysis
    - Flattop window gives better amplitude accuracy but worse frequency resolution
    
    See Also
    --------
    calculate_psd_maximax : Calculate maximax (envelope) PSD per SMC-S-016
    scipy.signal.welch : Underlying SciPy function
    """
    # Input validation
    if time_data.size == 0:
        raise ValueError("Input time_data cannot be empty")

    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")

    # Data quality validation
    if not np.all(np.isfinite(time_data)):
        nan_count = np.sum(np.isnan(time_data))
        inf_count = np.sum(np.isinf(time_data))
        raise ValueError(
            f"Input signal contains invalid values: {nan_count} NaN, {inf_count} Inf. "
            "Please clean or interpolate the data before PSD calculation."
        )

    # Calculate nperseg from df if provided
    if df is not None:
        if df <= 0:
            raise ValueError("df (frequency resolution) must be positive")
        
        if df >= sample_rate / 2:
            raise ValueError(f"df ({df} Hz) must be less than Nyquist frequency ({sample_rate/2} Hz)")
        
        # Calculate nperseg from desired frequency resolution
        # df = sample_rate / nperseg  =>  nperseg = sample_rate / df
        nperseg_calc = int(sample_rate / df)
        
        if use_efficient_fft:
            # Round to nearest power of 2 for faster FFT
            nperseg_calc = 2 ** int(np.ceil(np.log2(nperseg_calc)))
        
        nperseg = nperseg_calc
    
    # Use default if nperseg not specified
    if nperseg is None:
        nperseg = min(256, len(time_data))
    
    # Validate nperseg
    if nperseg > len(time_data):
        raise ValueError(
            f"nperseg ({nperseg}) cannot be larger than signal length ({len(time_data)}). "
            f"Try using a larger df (coarser frequency resolution) or longer signal."
        )
    
    # Calculate noverlap if not provided (default to 50%)
    if noverlap is None:
        noverlap = nperseg // 2
    
    # Validate noverlap
    if noverlap >= nperseg:
        raise ValueError(f"noverlap ({noverlap}) must be less than nperseg ({nperseg})")
    
    # Calculate PSD using Welch's method
    # scaling='density' ensures proper window energy correction
    frequencies, psd = signal.welch(
        time_data,
        fs=sample_rate,
        window=window,
        nperseg=nperseg,
        noverlap=noverlap,
        scaling='density'
    )
    
    return frequencies, psd


def calculate_psd_maximax(
    time_data: np.ndarray,
    sample_rate: float,
    maximax_window: float = 1.0,
    overlap_percent: float = 50.0,
    window: str = 'hann',
    df: Optional[float] = None,
    use_efficient_fft: bool = False
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate maximax (envelope) Power Spectral Density per SMC-S-016.
    
    This function implements the "maxi-max" PSD calculation as defined in SMC-S-016
    (Test Requirements for Launch, Upper-Stage, and Space Vehicles). The method
    divides the signal into overlapping time windows (typically 1 second with 50%
    overlap), calculates a complete PSD spectrum for each window, and then takes
    the maximum value at each frequency bin across all windows to produce an
    envelope spectrum.
    
    This approach produces a more conservative PSD estimate than traditional
    averaging methods and is commonly used for defining Maximum Predicted
    Environment (MPE) specifications in aerospace applications.
    
    Algorithm (per SMC-S-016):
    1. Divide signal into overlapping windows (default: 1-second, 50% overlap)
    2. For each window, calculate a complete PSD using Welch's method
    3. At each frequency bin, take the MAXIMUM across all window PSDs
    4. Result: Envelope PSD representing worst-case at each frequency
    
    Parameters
    ----------
    time_data : np.ndarray
        Input signal array (1D). Should be several seconds long for statistical significance.
        Type: float64 array
        Units: Same as signal (e.g., g for acceleration, Pa for pressure)
        Recommended: At least 10 seconds for meaningful maximax calculation
        
    sample_rate : float
        Sampling frequency of the input signal in Hz.
        Type: float
        Units: Hz (samples per second)
        Must be positive.
        
    maximax_window : float, optional
        Duration of each time window in seconds for maximax calculation.
        Default is 1.0 second per SMC-S-016.
        Type: float
        Units: seconds
        Must be positive and less than signal duration.
        Typical values: 0.5 to 2.0 seconds
        
    overlap_percent : float, optional
        Overlap percentage between consecutive maximax windows.
        Default is 50.0% per SMC-S-016.
        Type: float
        Units: percent
        Range: 0 to 99.9
        50% overlap is standard for SMC-S-016 compliance.
        
    window : str, optional
        Window function to apply within each maximax window for Welch's method.
        Default is 'hann'.
        Type: str
        Options: 'hann', 'hamming', 'blackman', 'bartlett', 'flattop', etc.
        
    df : float, optional
        Desired frequency resolution in Hz for the PSD within each maximax window.
        If None, uses default Welch parameters.
        Type: float or None
        Units: Hz
        Controls nperseg for Welch's method: nperseg = sample_rate / df
        Must result in nperseg < maximax_window * sample_rate
        
    use_efficient_fft : bool, optional
        If True, rounds nperseg to nearest power of 2 for faster FFT.
        Default is False.
        Type: bool
    
    Returns
    -------
    frequencies : np.ndarray
        Array of frequency values in Hz corresponding to the PSD values.
        Type: float64 array
        Units: Hz
        Shape: (n_freqs,)
        
    psd_maximax : np.ndarray
        Maximax (envelope) Power Spectral Density values.
        Type: float64 array
        Units: signal_units^2 / Hz (e.g., g^2/Hz for acceleration)
        Shape: (n_freqs,)
        Values represent the maximum PSD at each frequency across all time windows.
        
    Raises
    ------
    ValueError
        If time_data is empty
        If sample_rate is not positive
        If maximax_window is larger than signal duration
        If maximax_window is not positive
        If overlap_percent is not in range [0, 100)
        If df results in nperseg larger than maximax window
        If no windows can be extracted from signal
    
    Examples
    --------
    >>> # Generate 30 seconds of test data with transient event
    >>> import numpy as np
    >>> sample_rate = 1000.0  # Hz
    >>> duration = 30.0  # seconds
    >>> t = np.linspace(0, duration, int(sample_rate * duration))
    >>> 
    >>> # Background signal + transient spike at t=15s
    >>> signal = np.sin(2 * np.pi * 10 * t) + np.random.normal(0, 0.1, len(t))
    >>> transient = (t > 15) & (t < 16)  # 1-second transient
    >>> signal[transient] += 5 * np.sin(2 * np.pi * 100 * t[transient])
    >>> 
    >>> # Calculate maximax PSD (will capture transient peak)
    >>> frequencies, psd_max = calculate_psd_maximax(
    ...     signal, sample_rate, maximax_window=1.0, overlap_percent=50.0
    ... )
    >>> 
    >>> # Compare with traditional averaged PSD
    >>> from spectral_edge.core.psd import calculate_psd_welch
    >>> freq_avg, psd_avg = calculate_psd_welch(signal, sample_rate)
    >>> 
    >>> # Maximax PSD will show higher values at 100 Hz due to transient
    >>> # Averaged PSD will smooth out the transient
    
    Notes
    -----
    - Maximax PSD is always >= averaged PSD at every frequency
    - More conservative than traditional averaging (captures transients)
    - Standard method for aerospace MPE (Maximum Predicted Environment)
    - Requires longer signal duration for statistical significance
    - Computational cost scales with number of windows
    - For 30s signal with 1s windows at 50% overlap: ~59 windows processed
    - SMC-S-016 specifies 1-second windows with 50% overlap as standard
    - Not suitable for very short signals (< 5 seconds)
    
    References
    ----------
    SMC-S-016: Test Requirements for Launch, Upper-Stage, and Space Vehicles
    Section: Vibration Test Criteria Development
    
    See Also
    --------
    calculate_psd_welch : Calculate averaged PSD using Welch's method
    """
    # Input validation
    if time_data.size == 0:
        raise ValueError("Input time_data cannot be empty")

    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")

    # Data quality validation
    if not np.all(np.isfinite(time_data)):
        nan_count = np.sum(np.isnan(time_data))
        inf_count = np.sum(np.isinf(time_data))
        raise ValueError(
            f"Input signal contains invalid values: {nan_count} NaN, {inf_count} Inf. "
            "Please clean or interpolate the data before PSD calculation."
        )

    if maximax_window <= 0:
        raise ValueError("maximax_window must be positive")
    
    if not (0 <= overlap_percent < 100):
        raise ValueError("overlap_percent must be between 0 and 100 (exclusive)")
    
    # Calculate signal duration from actual time span
    # This works correctly even if data is decimated, as long as sample_rate
    # represents the actual rate of the provided data
    signal_duration = (len(time_data) - 1) / sample_rate
    
    if maximax_window > signal_duration:
        raise ValueError(
            f"maximax_window ({maximax_window}s) is larger than signal duration "
            f"({signal_duration:.2f}s). Use a shorter maximax_window or longer signal."
        )
    
    # Calculate window parameters for sliding maximax windows
    window_samples = int(maximax_window * sample_rate)
    overlap_samples = int(window_samples * overlap_percent / 100)
    step_samples = window_samples - overlap_samples
    
    if step_samples <= 0:
        raise ValueError(
            f"Invalid overlap_percent ({overlap_percent}%). "
            f"Must be less than 100% to allow window progression."
        )
    
    # Calculate nperseg for Welch's method within each maximax window
    # This is the segment length for the PSD calculation of each 1-second window
    if df is not None:
        if df <= 0:
            raise ValueError("df (frequency resolution) must be positive")
        
        # Calculate nperseg from desired frequency resolution
        nperseg_calc = int(sample_rate / df)
        
        if use_efficient_fft:
            # Round to nearest power of 2
            nperseg_calc = 2 ** int(np.ceil(np.log2(nperseg_calc)))
        
        nperseg = nperseg_calc
        
        # Validate that nperseg fits within maximax window
        if nperseg > window_samples:
            raise ValueError(
                f"Requested df ({df} Hz) requires nperseg ({nperseg} samples) "
                f"which is larger than maximax_window ({maximax_window}s = {window_samples} samples). "
                f"Use larger df (coarser resolution) or longer maximax_window."
            )
    else:
        # Default: use reasonable nperseg for the window size
        # Aim for ~8-16 segments within the maximax window for good statistics
        nperseg = min(window_samples // 8, 1024)
        nperseg = max(nperseg, 64)  # Minimum reasonable segment length
    
    # Calculate noverlap for Welch's method (50% of nperseg is standard)
    noverlap = nperseg // 2
    
    # Initialize variables for maximax calculation
    frequencies = None
    psd_maximax = None
    num_windows = 0
    
    # Slide maximax window across signal
    start_idx = 0
    
    while start_idx + window_samples <= len(time_data):
        # Extract current maximax window (e.g., 1 second of data)
        window_data = time_data[start_idx:start_idx + window_samples]
        
        # Calculate complete PSD for this window using Welch's method
        # This gives us one PSD spectrum for this 1-second window
        freqs, psd_window = calculate_psd_welch(
            window_data,
            sample_rate,
            window=window,
            nperseg=nperseg,
            noverlap=noverlap
        )
        
        # Initialize on first window
        if frequencies is None:
            frequencies = freqs
            psd_maximax = psd_window.copy()
        else:
            # Take maximum at each frequency bin (envelope operation)
            psd_maximax = np.maximum(psd_maximax, psd_window)
        
        num_windows += 1
        
        # Move to next window (with overlap)
        start_idx += step_samples
    
    if num_windows == 0:
        raise ValueError(
            f"No windows could be extracted from signal. "
            f"Signal duration ({signal_duration:.2f}s) is too short for "
            f"maximax_window ({maximax_window}s). Use shorter maximax_window."
        )
    
    return frequencies, psd_maximax


def calculate_rms_from_psd(frequencies: np.ndarray, psd: np.ndarray, 
                           freq_min: Optional[float] = None,
                           freq_max: Optional[float] = None) -> float:
    """
    Calculate RMS (Root Mean Square) value from PSD using Parseval's theorem.
    
    This function integrates the Power Spectral Density over a frequency range
    to calculate the RMS value of the signal. By Parseval's theorem, the integral
    of the PSD equals the variance of the signal, and the square root of the
    variance is the RMS value.
    
    For vibration analysis, this is often called "grms" (g-RMS) when the signal
    is acceleration in units of g.
    
    Parameters
    ----------
    frequencies : np.ndarray
        Array of frequency values in Hz.
        Type: float64 array
        Units: Hz
        Must be monotonically increasing.
        
    psd : np.ndarray
        Power Spectral Density values corresponding to frequencies.
        Type: float64 array
        Units: signal_units^2 / Hz (e.g., g^2/Hz)
        Must have same length as frequencies.
        
    freq_min : float, optional
        Minimum frequency for integration in Hz. If None, uses minimum of frequencies array.
        Type: float or None
        Units: Hz
        
    freq_max : float, optional
        Maximum frequency for integration in Hz. If None, uses maximum of frequencies array.
        Type: float or None
        Units: Hz
    
    Returns
    -------
    rms : float
        RMS value of the signal over the specified frequency range.
        Type: float
        Units: Same as signal (e.g., g for acceleration, Pa for pressure)
        
    Raises
    ------
    ValueError
        If frequencies and psd have different lengths
        If freq_min or freq_max are outside the range of frequencies
        If freq_min >= freq_max
    
    Examples
    --------
    >>> # Calculate PSD
    >>> frequencies, psd = calculate_psd_welch(signal, sample_rate)
    >>> 
    >>> # Calculate overall RMS (all frequencies)
    >>> rms_overall = calculate_rms_from_psd(frequencies, psd)
    >>> 
    >>> # Calculate RMS in specific band (e.g., 20-2000 Hz)
    >>> rms_band = calculate_rms_from_psd(frequencies, psd, freq_min=20, freq_max=2000)
    
    Notes
    -----
    - Integration uses trapezoidal rule (np.trapezoid or np.trapz)
    - For accurate RMS, ensure PSD covers the full frequency range of interest
    - RMS^2 = integral of PSD over frequency
    - For acceleration in g: result is grms (g-RMS)
    - Frequency range selection useful for band-limited analysis
    
    See Also
    --------
    calculate_psd_welch : Calculate PSD using Welch's method
    calculate_psd_maximax : Calculate maximax PSD
    """
    # Input validation
    if len(frequencies) != len(psd):
        raise ValueError(
            f"frequencies and psd must have same length. "
            f"Got frequencies: {len(frequencies)}, psd: {len(psd)}"
        )
    
    if len(frequencies) == 0:
        raise ValueError("frequencies and psd cannot be empty")
    
    # Apply frequency range filter if specified
    if freq_min is not None or freq_max is not None:
        if freq_min is None:
            freq_min = frequencies[0]
        if freq_max is None:
            freq_max = frequencies[-1]
        
        if freq_min >= freq_max:
            raise ValueError(f"freq_min ({freq_min}) must be less than freq_max ({freq_max})")
        
        # Clamp to available frequency range (matches plot display behavior)
        orig_min, orig_max = freq_min, freq_max
        freq_min = max(freq_min, frequencies[0])
        freq_max = min(freq_max, frequencies[-1])

        if freq_min >= freq_max:
            raise ValueError(
                f"No valid frequency range after clamping: requested [{orig_min}, {orig_max}] Hz "
                f"does not overlap available range [{frequencies[0]}, {frequencies[-1]}] Hz"
            )
        
        # Create mask for frequency range
        mask = (frequencies >= freq_min) & (frequencies <= freq_max)
        
        if not np.any(mask):
            raise ValueError(f"No frequencies found in range [{freq_min}, {freq_max}] Hz")
        
        frequencies = frequencies[mask]
        psd = psd[mask]
    
    # Integrate PSD using trapezoidal rule
    # variance = integral of PSD over frequency
    # Use trapezoid if available (NumPy 2.0+), otherwise trapz
    try:
        variance = np.trapezoid(psd, frequencies)
    except AttributeError:
        # Fallback for older NumPy versions
        variance = np.trapz(psd, frequencies)
    
    # RMS = sqrt(variance)
    rms = np.sqrt(variance)
    
    return rms


def psd_to_db(psd: np.ndarray, reference: float = 1.0) -> np.ndarray:
    """
    Convert PSD values to decibel (dB) scale.
    
    The decibel scale is a logarithmic scale that is useful for visualizing
    PSD data that spans many orders of magnitude. It is defined as:
    
        PSD_dB = 10 * log10(PSD / reference)
    
    This function is commonly used for plotting PSD results on a logarithmic
    scale, which makes it easier to see features across a wide dynamic range.
    
    Parameters
    ----------
    psd : np.ndarray
        Power spectral density values (linear scale).
        Shape: (n_frequencies,) for single channel or (n_frequencies, n_channels) for multi-channel.
        Units: Typically (unit²/Hz) where unit is the signal unit (e.g., g²/Hz for acceleration).
    
    reference : float, optional
        Reference value for dB conversion. Default is 1.0.
        The reference should have the same units as the PSD.
        Common references:
        - 1.0 for normalized data
        - 1e-6 for microunits (e.g., μg²/Hz)
    
    Returns
    -------
    psd_db : np.ndarray
        PSD values in decibel scale.
        Shape: Same as input psd.
        Units: dB re reference (e.g., "dB re 1.0 g²/Hz")
    
    Notes
    -----
    - Zero or negative PSD values are replaced with a small positive value (1e-20)
      to avoid log(0) errors. This results in very large negative dB values.
    - The dB scale is logarithmic, so equal dB differences represent equal
      ratios in linear scale (e.g., +3 dB ≈ 2x power, +10 dB = 10x power).
    
    Examples
    --------
    >>> frequencies = np.array([0, 1, 2, 3, 4])
    >>> psd = np.array([1.0, 10.0, 100.0, 1000.0, 10000.0])
    >>> psd_db = psd_to_db(psd, reference=1.0)
    >>> print(psd_db)
    [ 0. 10. 20. 30. 40.]
    
    >>> # With different reference
    >>> psd_db = psd_to_db(psd, reference=10.0)
    >>> print(psd_db)
    [-10.   0.  10.  20.  30.]
    """
    # Replace zeros and negative values with small positive value
    psd_safe = np.where(psd > 0, psd, 1e-20)
    
    # Convert to dB: 10 * log10(PSD / reference)
    psd_db = 10 * np.log10(psd_safe / reference)
    
    return psd_db


def get_window_options() -> dict:
    """
    Get available window function options for PSD calculation.
    
    Returns a dictionary of window function names and their descriptions.
    These windows are used to reduce spectral leakage when computing PSDs.
    
    Returns
    -------
    window_options : dict
        Dictionary mapping window names (lowercase) to descriptions.
        Keys are the window names that can be passed to calculate_psd_welch
        and calculate_psd_maximax.
    
    Notes
    -----
    Window Selection Guidelines:
    
    - **Hann (Hanning)**: Best general-purpose window. Good balance between
      frequency resolution and sidelobe suppression. Recommended for most
      applications.
    
    - **Hamming**: Similar to Hann but with slightly better sidelobe suppression
      at the cost of slightly wider main lobe. Good for signals with strong
      narrowband components.
    
    - **Blackman**: Excellent sidelobe suppression (better than Hann/Hamming)
      but wider main lobe. Use when you need to detect weak signals near
      strong ones.
    
    - **Flattop**: Best amplitude accuracy for sinusoidal signals. Very wide
      main lobe but minimal scalloping loss. Use for calibration or when
      accurate amplitude measurement is critical.
    
    - **Bartlett (Triangular)**: Simple triangular window. Moderate performance,
      mainly of historical interest.
    
    - **Boxcar (Rectangular)**: No windowing applied. Best frequency resolution
      but poor sidelobe suppression. Only use if you know your signal has no
      spectral leakage issues (e.g., integer number of periods in window).
    
    All windows are available in scipy.signal.get_window().
    
    Examples
    --------
    >>> options = get_window_options()
    >>> print(options.keys())
    dict_keys(['hann', 'hamming', 'blackman', 'flattop', 'bartlett', 'boxcar'])
    
    >>> print(options['hann'])
    'Hann (Hanning) - Good general purpose, smooth sidelobes'
    
    See Also
    --------
    calculate_psd_welch : Uses these window options
    calculate_psd_maximax : Uses these window options
    scipy.signal.get_window : Underlying window generation function
    """
    return {
        'hann': 'Hann (Hanning) - Good general purpose, smooth sidelobes',
        'hamming': 'Hamming - Similar to Hann, slightly different sidelobe behavior',
        'blackman': 'Blackman - Excellent sidelobe suppression, wider main lobe',
        'flattop': 'Flattop - Best amplitude accuracy, very wide main lobe',
        'bartlett': 'Bartlett (Triangular) - Simple, moderate performance',
        'boxcar': 'Boxcar (Rectangular) - No windowing, best frequency resolution but poor sidelobe suppression'
    }



def convert_psd_to_octave_bands(
    frequencies: np.ndarray,
    psd: np.ndarray,
    octave_fraction: float = 3.0,
    freq_min: Optional[float] = None,
    freq_max: Optional[float] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert narrowband PSD to octave band representation.
    
    Octave bands are logarithmically-spaced frequency bands commonly used in
    acoustics and vibration analysis. This function integrates the narrowband
    PSD energy within each octave band to produce an octave band spectrum.
    
    Common octave fractions:
    - 1/1 octave: Each band spans one octave (factor of 2 in frequency)
    - 1/3 octave: Three bands per octave (most common in acoustics)
    - 1/6 octave: Six bands per octave
    - 1/12 octave: Twelve bands per octave
    - 1/24 octave: Twenty-four bands per octave
    - 1/36 octave: Thirty-six bands per octave (high resolution)
    
    The octave band center frequencies follow the ANSI/IEC preferred series:
        f_center = f_ref * 2^(n / octave_fraction)
    
    where f_ref = 1000 Hz and n is an integer index.
    
    Parameters
    ----------
    frequencies : np.ndarray
        Frequency values from narrowband PSD (Hz).
        Shape: (n_frequencies,)
        Must be monotonically increasing.
    
    psd : np.ndarray
        Power spectral density values (linear scale).
        Shape: (n_frequencies,) for single channel or (n_frequencies, n_channels) for multi-channel.
        Units: Typically (unit²/Hz) where unit is the signal unit.
    
    octave_fraction : float, optional
        Fraction of octave for band spacing. Default is 3.0 (1/3 octave).
        Common values: 1.0, 3.0, 6.0, 12.0, 24.0, 36.0
        Smaller values = wider bands, fewer bands total.
    
    freq_min : float, optional
        Minimum frequency for octave band analysis (Hz).
        If None, uses minimum frequency from input.
        Default: None
    
    freq_max : float, optional
        Maximum frequency for octave band analysis (Hz).
        If None, uses maximum frequency from input.
        Default: None
    
    Returns
    -------
    octave_frequencies : np.ndarray
        Center frequencies of octave bands (Hz).
        Shape: (n_bands,)
    
    octave_psd : np.ndarray
        PSD values for each octave band (linear scale).
        Shape: (n_bands,) for single channel or (n_bands, n_channels) for multi-channel.
        Units: Same as input PSD (unit²/Hz)
        
        Note: The octave band PSD represents the average PSD level within each band,
        NOT the integrated energy. To get total energy in a band, multiply by bandwidth.
    
    Raises
    ------
    ValueError
        If frequencies are not monotonically increasing.
        If octave_fraction is not positive.
        If freq_min >= freq_max.
    
    Notes
    -----
    **Octave Band Calculation:**
    
    For each octave band with center frequency f_c:
    
    1. Calculate band edges:
       - f_lower = f_c / 2^(1 / (2 * octave_fraction))
       - f_upper = f_c * 2^(1 / (2 * octave_fraction))
    
    2. Find all narrowband frequencies within [f_lower, f_upper]
    
    3. Integrate narrowband PSD over the band using trapezoidal rule
    
    4. Divide by bandwidth to get average PSD level:
       - octave_psd = integrated_energy / (f_upper - f_lower)
    
    **Standard Octave Band Center Frequencies (1/3 octave):**
    
    Common 1/3 octave bands (Hz):
    - Low frequency: 1, 1.25, 1.6, 2, 2.5, 3.15, 4, 5, 6.3, 8, 10, ...
    - Mid frequency: 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, ...
    - High frequency: 10k, 12.5k, 16k, 20k
    
    **Applications:**
    
    - Acoustic analysis (sound pressure level vs frequency)
    - Vibration analysis (acceleration vs frequency)
    - Smoothing narrowband spectra for visualization
    - Comparing measurements with octave band specifications
    - Random vibration test specifications
    
    Examples
    --------
    >>> # Generate test signal with narrowband PSD
    >>> frequencies = np.linspace(0, 1000, 1001)
    >>> psd = np.ones_like(frequencies)  # Flat spectrum
    >>> 
    >>> # Convert to 1/3 octave bands
    >>> oct_freq, oct_psd = convert_psd_to_octave_bands(
    ...     frequencies, psd, octave_fraction=3.0
    ... )
    >>> print(f"Narrowband: {len(frequencies)} points")
    >>> print(f"1/3 octave: {len(oct_freq)} bands")
    Narrowband: 1001 points
    1/3 octave: 31 bands
    
    >>> # Convert to 1/6 octave bands (higher resolution)
    >>> oct_freq, oct_psd = convert_psd_to_octave_bands(
    ...     frequencies, psd, octave_fraction=6.0
    ... )
    >>> print(f"1/6 octave: {len(oct_freq)} bands")
    1/6 octave: 61 bands
    
    See Also
    --------
    calculate_psd_welch : Generate narrowband PSD
    calculate_psd_maximax : Generate maximax narrowband PSD
    psd_to_db : Convert PSD to decibel scale for plotting
    
    References
    ----------
    - ANSI S1.11: Specification for Octave-Band and Fractional-Octave-Band Analog and Digital Filters
    - IEC 61260: Electroacoustics - Octave-band and fractional-octave-band filters
    """
    # Input validation
    psd_length = len(psd) if psd.ndim == 1 else psd.shape[0]
    if len(frequencies) != psd_length:
        raise ValueError(
            f"frequencies and psd length mismatch: "
            f"frequencies={len(frequencies)}, psd={psd_length}"
        )
    
    if not np.all(np.diff(frequencies) > 0):
        raise ValueError("frequencies must be monotonically increasing")
    
    if octave_fraction <= 0:
        raise ValueError(f"octave_fraction must be positive, got {octave_fraction}")
    
    # Set frequency range
    if freq_min is None:
        freq_min = frequencies[0]
    if freq_max is None:
        freq_max = frequencies[-1]
    
    # Ensure freq_min is positive (required for log calculation)
    if freq_min <= 0:
        # Find first positive frequency
        positive_freqs = frequencies[frequencies > 0]
        if len(positive_freqs) == 0:
            raise ValueError("No positive frequencies found in input data")
        freq_min = positive_freqs[0]
    
    if freq_min >= freq_max:
        raise ValueError(f"freq_min ({freq_min}) must be less than freq_max ({freq_max})")

    # Get cached octave grid (dense frequencies and band centers)
    dense_freqs, octave_frequencies, bandwidth_factor = _get_cached_octave_grid(
        freq_min, freq_max, octave_fraction
    )

    if len(octave_frequencies) == 0:
        raise ValueError(
            f"No octave bands found in frequency range [{freq_min}, {freq_max}] Hz"
        )

    # Interpolate PSD onto the dense grid (linear PSD values over log-frequency)
    # Use base-10 log frequency for interpolation stability
    log_freqs = np.log10(frequencies)
    dense_log_freqs = np.log10(dense_freqs)

    def _interp_psd(values: np.ndarray) -> np.ndarray:
        # Requires at least 2 points for interpolation
        if len(values) < 2:
            return None
        return np.interp(dense_log_freqs, log_freqs, values, left=values[0], right=values[-1])
    
    # Determine if multi-channel
    is_multichannel = psd.ndim > 1
    n_channels = psd.shape[1] if is_multichannel else 1

    # Interpolate PSD for robust integration
    if is_multichannel:
        interpolated_psd = np.zeros((len(dense_freqs), n_channels))
        for ch in range(n_channels):
            interp_values = _interp_psd(psd[:, ch])
            if interp_values is None:
                interpolated_psd = None
                break
            interpolated_psd[:, ch] = interp_values
    else:
        interp_values = _interp_psd(psd)
        interpolated_psd = interp_values

    # Precompute cumulative integral for stability
    if interpolated_psd is not None:
        if is_multichannel:
            cumulative_energy = np.zeros_like(interpolated_psd)
            for ch in range(n_channels):
                try:
                    cumulative_energy[:, ch] = np.cumsum(
                        np.diff(dense_freqs, prepend=dense_freqs[0])
                        * interpolated_psd[:, ch]
                    )
                except Exception as e:
                    logger.warning(
                        f"Cumulative energy calculation failed for channel {ch}: {e}. "
                        "Falling back to direct integration method."
                    )
                    cumulative_energy = None
                    break
        else:
            cumulative_energy = np.cumsum(
                np.diff(dense_freqs, prepend=dense_freqs[0]) * interpolated_psd
            )
    else:
        cumulative_energy = None
    
    # Initialize output array
    if is_multichannel:
        octave_psd = np.zeros((len(octave_frequencies), n_channels))
    else:
        octave_psd = np.zeros(len(octave_frequencies))
    
    # Calculate PSD for each octave band
    for i, f_center in enumerate(octave_frequencies):
        # Calculate band edges
        f_lower = f_center / bandwidth_factor
        f_upper = f_center * bandwidth_factor
        
        # Find dense frequencies within this octave band
        band_mask = (dense_freqs >= f_lower) & (dense_freqs <= f_upper)
        
        if not np.any(band_mask):
            # No data in this band - leave as NaN to avoid broken segments
            if is_multichannel:
                octave_psd[i, :] = np.nan
            else:
                octave_psd[i] = np.nan
            continue
        
        # Extract frequencies and PSD for this band
        if cumulative_energy is not None:
            bandwidth = f_upper - f_lower
            if bandwidth <= 0:
                if is_multichannel:
                    octave_psd[i, :] = np.nan
                else:
                    octave_psd[i] = np.nan
                continue

            idx_lower = np.searchsorted(dense_freqs, f_lower, side="left")
            idx_upper = np.searchsorted(dense_freqs, f_upper, side="right") - 1
            idx_lower = max(0, min(idx_lower, len(dense_freqs) - 1))
            idx_upper = max(0, min(idx_upper, len(dense_freqs) - 1))

            if is_multichannel:
                energy = cumulative_energy[idx_upper, :] - cumulative_energy[idx_lower, :]
                octave_psd[i, :] = energy / bandwidth
            else:
                energy = cumulative_energy[idx_upper] - cumulative_energy[idx_lower]
                octave_psd[i] = energy / bandwidth
            continue

        # Fallback to original data if interpolation failed
        band_mask = (frequencies >= f_lower) & (frequencies <= f_upper)
        if not np.any(band_mask):
            if is_multichannel:
                octave_psd[i, :] = np.nan
            else:
                octave_psd[i] = np.nan
            continue
        band_frequencies = frequencies[band_mask]
        band_psd = psd[band_mask, :] if is_multichannel else psd[band_mask]
        
        # Check for NaN or invalid values in band
        if is_multichannel:
            if np.any(np.isnan(band_psd)) or np.any(np.isinf(band_psd)):
                # Skip bands with NaN/inf values
                continue
        else:
            if np.any(np.isnan(band_psd)) or np.any(np.isinf(band_psd)):
                # Skip bands with NaN/inf values
                continue
        
        # Need at least 2 points for trapezoidal integration
        if len(band_frequencies) < 2:
            if is_multichannel:
                octave_psd[i, :] = band_psd[0, :]
            else:
                octave_psd[i] = band_psd[0]
            continue
        
        # Integrate PSD over the band using trapezoidal rule
        # This gives total energy in the band
        if is_multichannel:
            for ch in range(n_channels):
                try:
                    integrated_energy = np.trapezoid(band_psd[:, ch], band_frequencies)
                except AttributeError:
                    integrated_energy = np.trapz(band_psd[:, ch], band_frequencies)
                
                # Convert to average PSD level by dividing by bandwidth
                bandwidth = f_upper - f_lower
                if bandwidth > 0:
                    octave_psd[i, ch] = integrated_energy / bandwidth
                else:
                    octave_psd[i, ch] = band_psd[0, ch]
        else:
            try:
                integrated_energy = np.trapezoid(band_psd, band_frequencies)
            except AttributeError:
                integrated_energy = np.trapz(band_psd, band_frequencies)
            
            # Convert to average PSD level by dividing by bandwidth
            bandwidth = f_upper - f_lower
            if bandwidth > 0:
                octave_psd[i] = integrated_energy / bandwidth
            else:
                octave_psd[i] = band_psd[0]
    
    return octave_frequencies, octave_psd


def calculate_csd(
    signal1: np.ndarray,
    signal2: np.ndarray,
    sample_rate: float,
    window: str = 'hann',
    nperseg: Optional[int] = None,
    noverlap: Optional[int] = None,
    df: Optional[float] = None,
    use_efficient_fft: bool = False
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate Cross-Spectral Density between two signals.

    The Cross-Spectral Density (CSD) measures the correlation between two signals
    as a function of frequency. It is complex-valued, with magnitude representing
    the correlation strength and phase representing the phase relationship.

    Parameters
    ----------
    signal1 : np.ndarray
        First input signal array (1D), typically the reference signal.
        Type: float64 array
        Units: Same as signal (e.g., g for acceleration)

    signal2 : np.ndarray
        Second input signal array (1D), typically the response signal.
        Type: float64 array
        Units: Same as signal (e.g., g for acceleration)
        Must have the same length as signal1.

    sample_rate : float
        Sampling frequency of the input signals in Hz.
        Type: float
        Units: Hz (samples per second)
        Must be positive.

    window : str, optional
        Window function to apply to each segment. Default is 'hann'.
        Type: str
        Options: 'hann', 'hamming', 'blackman', 'bartlett', 'flattop', etc.

    nperseg : int, optional
        Length of each segment in samples. If None, calculated from df or defaults to 256.
        Type: int or None
        Units: samples

    noverlap : int, optional
        Number of samples to overlap between segments. If None, defaults to nperseg // 2.
        Type: int or None
        Units: samples

    df : float, optional
        Desired frequency resolution in Hz. If provided, nperseg is calculated as
        nperseg = sample_rate / df. Takes precedence over nperseg parameter.
        Type: float or None
        Units: Hz

    use_efficient_fft : bool, optional
        If True, rounds nperseg to the nearest power of 2 for faster FFT computation.
        Default is False.
        Type: bool

    Returns
    -------
    frequencies : np.ndarray
        Array of frequency values in Hz corresponding to the CSD values.
        Type: float64 array
        Units: Hz
        Shape: (n_freqs,)

    csd : np.ndarray
        Cross-Spectral Density values (complex).
        Type: complex128 array
        Units: signal_units^2 / Hz (e.g., g^2/Hz)
        Shape: (n_freqs,)

    Raises
    ------
    ValueError
        If signals have different lengths
        If signals are empty
        If sample_rate is not positive

    Examples
    --------
    >>> # Generate two correlated signals
    >>> sample_rate = 1000.0
    >>> t = np.linspace(0, 10, 10000)
    >>> signal1 = np.sin(2 * np.pi * 50 * t)
    >>> signal2 = np.sin(2 * np.pi * 50 * t + np.pi/4)  # Phase shifted
    >>>
    >>> frequencies, csd = calculate_csd(signal1, signal2, sample_rate, df=1.0)
    >>>
    >>> # CSD magnitude at 50 Hz will be high
    >>> # CSD phase at 50 Hz will be approximately pi/4

    See Also
    --------
    calculate_coherence : Calculate coherence between two signals
    calculate_psd_welch : Calculate PSD of a single signal
    scipy.signal.csd : Underlying SciPy function
    """
    # Input validation
    if signal1.size == 0 or signal2.size == 0:
        raise ValueError("Input signals cannot be empty")

    if len(signal1) != len(signal2):
        raise ValueError(
            f"Signals must have the same length. "
            f"Got signal1: {len(signal1)}, signal2: {len(signal2)}"
        )

    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")

    # Calculate nperseg from df if provided
    if df is not None:
        if df <= 0:
            raise ValueError("df (frequency resolution) must be positive")

        if df >= sample_rate / 2:
            raise ValueError(f"df ({df} Hz) must be less than Nyquist frequency ({sample_rate/2} Hz)")

        nperseg_calc = int(sample_rate / df)

        if use_efficient_fft:
            nperseg_calc = 2 ** int(np.ceil(np.log2(nperseg_calc)))

        nperseg = nperseg_calc

    # Use default if nperseg not specified
    if nperseg is None:
        nperseg = min(256, len(signal1))

    # Validate nperseg
    if nperseg > len(signal1):
        raise ValueError(
            f"nperseg ({nperseg}) cannot be larger than signal length ({len(signal1)}). "
            f"Try using a larger df (coarser frequency resolution) or longer signal."
        )

    # Calculate noverlap if not provided (default to 50%)
    if noverlap is None:
        noverlap = nperseg // 2

    # Validate noverlap
    if noverlap >= nperseg:
        raise ValueError(f"noverlap ({noverlap}) must be less than nperseg ({nperseg})")

    # Calculate CSD using scipy
    frequencies, csd = signal.csd(
        signal1,
        signal2,
        fs=sample_rate,
        window=window,
        nperseg=nperseg,
        noverlap=noverlap,
        scaling='density'
    )

    return frequencies, csd


def calculate_coherence(
    signal1: np.ndarray,
    signal2: np.ndarray,
    sample_rate: float,
    window: str = 'hann',
    nperseg: Optional[int] = None,
    noverlap: Optional[int] = None,
    df: Optional[float] = None,
    use_efficient_fft: bool = False
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate magnitude-squared coherence between two signals.

    Coherence is a measure of the linear correlation between two signals at each
    frequency. It ranges from 0 (no correlation) to 1 (perfect linear correlation).

    Coherence is defined as:
        Cxy = |Pxy|^2 / (Pxx * Pyy)

    where Pxy is the cross-spectral density and Pxx, Pyy are the auto-spectral
    densities (PSDs) of the two signals.

    Parameters
    ----------
    signal1 : np.ndarray
        First input signal array (1D), typically the reference signal.
        Type: float64 array
        Units: Same as signal (e.g., g for acceleration)

    signal2 : np.ndarray
        Second input signal array (1D), typically the response signal.
        Type: float64 array
        Units: Same as signal (e.g., g for acceleration)
        Must have the same length as signal1.

    sample_rate : float
        Sampling frequency of the input signals in Hz.
        Type: float
        Units: Hz (samples per second)
        Must be positive.

    window : str, optional
        Window function to apply to each segment. Default is 'hann'.
        Type: str
        Options: 'hann', 'hamming', 'blackman', 'bartlett', 'flattop', etc.

    nperseg : int, optional
        Length of each segment in samples. If None, calculated from df or defaults to 256.
        Type: int or None
        Units: samples

    noverlap : int, optional
        Number of samples to overlap between segments. If None, defaults to nperseg // 2.
        Type: int or None
        Units: samples

    df : float, optional
        Desired frequency resolution in Hz. If provided, nperseg is calculated as
        nperseg = sample_rate / df. Takes precedence over nperseg parameter.
        Type: float or None
        Units: Hz

    use_efficient_fft : bool, optional
        If True, rounds nperseg to the nearest power of 2 for faster FFT computation.
        Default is False.
        Type: bool

    Returns
    -------
    frequencies : np.ndarray
        Array of frequency values in Hz corresponding to the coherence values.
        Type: float64 array
        Units: Hz
        Shape: (n_freqs,)

    coherence : np.ndarray
        Magnitude-squared coherence values (dimensionless).
        Type: float64 array
        Units: dimensionless (0 to 1)
        Shape: (n_freqs,)

    Raises
    ------
    ValueError
        If signals have different lengths
        If signals are empty
        If sample_rate is not positive

    Examples
    --------
    >>> # Generate two correlated signals
    >>> sample_rate = 1000.0
    >>> t = np.linspace(0, 10, 10000)
    >>> signal1 = np.sin(2 * np.pi * 50 * t) + 0.1 * np.random.randn(len(t))
    >>> signal2 = np.sin(2 * np.pi * 50 * t) + 0.1 * np.random.randn(len(t))
    >>>
    >>> frequencies, coh = calculate_coherence(signal1, signal2, sample_rate, df=1.0)
    >>>
    >>> # Coherence at 50 Hz will be high (close to 1)
    >>> # Coherence at other frequencies will be low (close to 0)

    Notes
    -----
    - Coherence of 1.0 indicates perfect linear correlation at that frequency
    - Coherence of 0.0 indicates no linear correlation at that frequency
    - A common threshold for "significant" coherence is 0.9
    - Low coherence can indicate:
        - Non-linear relationship between signals
        - Noise contamination
        - Multiple uncorrelated sources
    - Coherence is useful for:
        - Validating transfer function measurements
        - Identifying correlated noise sources
        - Checking sensor placement and data quality

    See Also
    --------
    calculate_csd : Calculate cross-spectral density
    calculate_transfer_function : Calculate transfer function from two signals
    scipy.signal.coherence : Underlying SciPy function
    """
    # Input validation
    if signal1.size == 0 or signal2.size == 0:
        raise ValueError("Input signals cannot be empty")

    if len(signal1) != len(signal2):
        raise ValueError(
            f"Signals must have the same length. "
            f"Got signal1: {len(signal1)}, signal2: {len(signal2)}"
        )

    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")

    # Calculate nperseg from df if provided
    if df is not None:
        if df <= 0:
            raise ValueError("df (frequency resolution) must be positive")

        if df >= sample_rate / 2:
            raise ValueError(f"df ({df} Hz) must be less than Nyquist frequency ({sample_rate/2} Hz)")

        nperseg_calc = int(sample_rate / df)

        if use_efficient_fft:
            nperseg_calc = 2 ** int(np.ceil(np.log2(nperseg_calc)))

        nperseg = nperseg_calc

    # Use default if nperseg not specified
    if nperseg is None:
        nperseg = min(256, len(signal1))

    # Validate nperseg
    if nperseg > len(signal1):
        raise ValueError(
            f"nperseg ({nperseg}) cannot be larger than signal length ({len(signal1)}). "
            f"Try using a larger df (coarser frequency resolution) or longer signal."
        )

    # Calculate noverlap if not provided (default to 50%)
    if noverlap is None:
        noverlap = nperseg // 2

    # Validate noverlap
    if noverlap >= nperseg:
        raise ValueError(f"noverlap ({noverlap}) must be less than nperseg ({nperseg})")

    # Calculate coherence using scipy
    frequencies, coherence = signal.coherence(
        signal1,
        signal2,
        fs=sample_rate,
        window=window,
        nperseg=nperseg,
        noverlap=noverlap
    )

    return frequencies, coherence


def calculate_transfer_function(
    input_signal: np.ndarray,
    output_signal: np.ndarray,
    sample_rate: float,
    window: str = 'hann',
    nperseg: Optional[int] = None,
    noverlap: Optional[int] = None,
    df: Optional[float] = None,
    use_efficient_fft: bool = False
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calculate transfer function (frequency response function) between input and output signals.

    The transfer function H(f) represents how a system transforms an input signal
    to produce an output signal at each frequency. It is calculated using the H1
    estimator which minimizes noise on the output:

        H1(f) = Pxy(f) / Pxx(f)

    where Pxy is the cross-spectral density between input and output, and Pxx is
    the auto-spectral density (PSD) of the input.

    Parameters
    ----------
    input_signal : np.ndarray
        Input signal array (1D), the excitation or reference signal.
        Type: float64 array
        Units: Same as signal (e.g., N for force, V for voltage)

    output_signal : np.ndarray
        Output signal array (1D), the response signal.
        Type: float64 array
        Units: Same as signal (e.g., g for acceleration, m/s for velocity)
        Must have the same length as input_signal.

    sample_rate : float
        Sampling frequency of the input signals in Hz.
        Type: float
        Units: Hz (samples per second)
        Must be positive.

    window : str, optional
        Window function to apply to each segment. Default is 'hann'.
        Type: str
        Options: 'hann', 'hamming', 'blackman', 'bartlett', 'flattop', etc.

    nperseg : int, optional
        Length of each segment in samples. If None, calculated from df or defaults to 256.
        Type: int or None
        Units: samples

    noverlap : int, optional
        Number of samples to overlap between segments. If None, defaults to nperseg // 2.
        Type: int or None
        Units: samples

    df : float, optional
        Desired frequency resolution in Hz. If provided, nperseg is calculated as
        nperseg = sample_rate / df. Takes precedence over nperseg parameter.
        Type: float or None
        Units: Hz

    use_efficient_fft : bool, optional
        If True, rounds nperseg to the nearest power of 2 for faster FFT computation.
        Default is False.
        Type: bool

    Returns
    -------
    frequencies : np.ndarray
        Array of frequency values in Hz.
        Type: float64 array
        Units: Hz
        Shape: (n_freqs,)

    magnitude : np.ndarray
        Transfer function magnitude.
        Type: float64 array
        Units: output_units / input_units (e.g., g/N for accelerance)
        Shape: (n_freqs,)

    phase : np.ndarray
        Transfer function phase in degrees.
        Type: float64 array
        Units: degrees
        Shape: (n_freqs,)
        Range: -180 to 180 degrees

    Raises
    ------
    ValueError
        If signals have different lengths
        If signals are empty
        If sample_rate is not positive

    Examples
    --------
    >>> # Simulate a simple system (low-pass filter response)
    >>> sample_rate = 1000.0
    >>> t = np.linspace(0, 10, 10000)
    >>> input_signal = np.random.randn(len(t))  # White noise input
    >>>
    >>> # Simple first-order low-pass filter
    >>> from scipy import signal as sp
    >>> b, a = sp.butter(1, 100, fs=sample_rate)
    >>> output_signal = sp.lfilter(b, a, input_signal)
    >>>
    >>> frequencies, magnitude, phase = calculate_transfer_function(
    ...     input_signal, output_signal, sample_rate, df=1.0
    ... )

    Notes
    -----
    - The H1 estimator is used, which assumes noise is primarily on the output
    - For noise on the input, use H2 estimator: H2 = Pyy / Pyx (not implemented)
    - Always check coherence to validate transfer function quality
    - Low coherence indicates unreliable transfer function at that frequency
    - Common applications:
        - Modal analysis (structural dynamics)
        - System identification
        - Vibration isolation effectiveness
        - Acoustic transfer paths

    See Also
    --------
    calculate_coherence : Calculate coherence to validate transfer function
    calculate_csd : Calculate cross-spectral density
    """
    # Input validation
    if input_signal.size == 0 or output_signal.size == 0:
        raise ValueError("Input signals cannot be empty")

    if len(input_signal) != len(output_signal):
        raise ValueError(
            f"Signals must have the same length. "
            f"Got input: {len(input_signal)}, output: {len(output_signal)}"
        )

    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")

    # Calculate nperseg from df if provided
    if df is not None:
        if df <= 0:
            raise ValueError("df (frequency resolution) must be positive")

        if df >= sample_rate / 2:
            raise ValueError(f"df ({df} Hz) must be less than Nyquist frequency ({sample_rate/2} Hz)")

        nperseg_calc = int(sample_rate / df)

        if use_efficient_fft:
            nperseg_calc = 2 ** int(np.ceil(np.log2(nperseg_calc)))

        nperseg = nperseg_calc

    # Use default if nperseg not specified
    if nperseg is None:
        nperseg = min(256, len(input_signal))

    # Validate nperseg
    if nperseg > len(input_signal):
        raise ValueError(
            f"nperseg ({nperseg}) cannot be larger than signal length ({len(input_signal)}). "
            f"Try using a larger df (coarser frequency resolution) or longer signal."
        )

    # Calculate noverlap if not provided (default to 50%)
    if noverlap is None:
        noverlap = nperseg // 2

    # Calculate CSD (cross-spectral density) - Pxy
    frequencies, Pxy = signal.csd(
        input_signal,
        output_signal,
        fs=sample_rate,
        window=window,
        nperseg=nperseg,
        noverlap=noverlap,
        scaling='density'
    )

    # Calculate PSD of input - Pxx
    _, Pxx = signal.welch(
        input_signal,
        fs=sample_rate,
        window=window,
        nperseg=nperseg,
        noverlap=noverlap,
        scaling='density'
    )

    # Calculate H1 transfer function estimate
    # H1 = Pxy / Pxx
    # Add small value to avoid division by zero
    H = Pxy / (Pxx + 1e-20)

    # Calculate magnitude and phase
    magnitude = np.abs(H)
    phase = np.angle(H, deg=True)  # Phase in degrees

    return frequencies, magnitude, phase
