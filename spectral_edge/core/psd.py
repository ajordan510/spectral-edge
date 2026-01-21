"""
Power Spectral Density (PSD) calculation module for SpectralEdge.

This module provides functions for calculating the Power Spectral Density
of time-series signals using Welch's method. Welch's method is a widely-used
technique that reduces noise in the PSD estimate by averaging multiple
overlapping segments of the signal.

Author: SpectralEdge Development Team
"""

import numpy as np
from scipy import signal
from typing import Tuple, Optional, Union


def calculate_psd_welch(
    time_data: np.ndarray,
    sample_rate: float,
    window: str = 'hann',
    nperseg: Optional[int] = None,
    noverlap: Optional[int] = None,
    nfft: Optional[int] = None,
    scaling: str = 'density',
    detrend: str = 'constant'
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate Power Spectral Density using Welch's method.
    
    Welch's method divides the time-series data into overlapping segments,
    applies a window function to each segment, computes the FFT (Fast Fourier
    Transform) of each windowed segment, and then averages the squared
    magnitude of the FFTs to produce the PSD estimate.
    
    This approach reduces the variance (noise) in the PSD estimate compared
    to computing the FFT of the entire signal at once.
    
    Parameters:
        time_data (np.ndarray): Input time-series data. Can be 1D (single channel)
            or 2D (multiple channels, where each row is a channel).
        sample_rate (float): Sampling rate of the data in Hz (samples per second).
        window (str): Type of window function to apply to each segment.
            Common options: 'hann', 'hamming', 'blackman', 'bartlett', 'boxcar'.
            Default is 'hann' (Hanning window), which provides good frequency
            resolution and sidelobe suppression.
        nperseg (int, optional): Length of each segment in samples. If None,
            defaults to 256 samples. Longer segments provide better frequency
            resolution but less averaging (more variance). Shorter segments
            provide more averaging (less variance) but worse frequency resolution.
        noverlap (int, optional): Number of samples to overlap between segments.
            If None, defaults to nperseg // 2 (50% overlap). More overlap
            provides more averaging but increases computation time.
        nfft (int, optional): Length of the FFT. If None, defaults to nperseg.
            Using a larger nfft than nperseg zero-pads the signal, which
            interpolates the frequency spectrum but does not improve resolution.
        scaling (str): Type of scaling to apply. Options:
            - 'density': Returns power spectral density in units^2/Hz
            - 'spectrum': Returns power spectrum in units^2
            Default is 'density'.
        detrend (str): Type of detrending to apply to each segment.
            Options: 'constant' (remove mean), 'linear' (remove linear trend),
            or False (no detrending). Default is 'constant'.
    
    Returns:
        Tuple[np.ndarray, np.ndarray]: A tuple containing:
            - frequencies (np.ndarray): Array of frequency values in Hz
            - psd (np.ndarray): Power spectral density values. If input is 1D,
              output is 1D. If input is 2D (multiple channels), output is 2D
              where each row corresponds to a channel.
    
    Raises:
        ValueError: If input data is empty or sample_rate is not positive.
    
    Example:
        >>> # Generate a test signal with two frequency components
        >>> sample_rate = 1000.0  # 1000 Hz
        >>> duration = 10.0  # 10 seconds
        >>> t = np.linspace(0, duration, int(sample_rate * duration))
        >>> signal = np.sin(2 * np.pi * 10 * t) + 0.5 * np.sin(2 * np.pi * 50 * t)
        >>> 
        >>> # Calculate PSD
        >>> frequencies, psd = calculate_psd_welch(signal, sample_rate)
        >>> 
        >>> # The PSD should show peaks at 10 Hz and 50 Hz
    """
    # Input validation
    if time_data.size == 0:
        raise ValueError("Input time_data cannot be empty")
    
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    
    # Set default values for segment parameters if not provided
    if nperseg is None:
        nperseg = min(256, len(time_data))
    
    if noverlap is None:
        noverlap = nperseg // 2
    
    # Note: scipy.signal.welch with scaling='density' automatically applies
    # the proper window energy correction factor. This ensures that the
    # total power (integral of PSD) equals the variance of the signal,
    # regardless of which window function is used.
    
    # Handle multi-channel data (2D array)
    # If input is 1D, we'll process it directly
    # If input is 2D, we'll process each channel (row) separately
    if time_data.ndim == 1:
        # Single channel case
        frequencies, psd = signal.welch(
            time_data,
            fs=sample_rate,
            window=window,
            nperseg=nperseg,
            noverlap=noverlap,
            nfft=nfft,
            scaling=scaling,
            detrend=detrend
        )
    elif time_data.ndim == 2:
        # Multi-channel case: process each channel separately
        num_channels = time_data.shape[0]
        
        # Calculate PSD for the first channel to get frequency array
        frequencies, psd_first = signal.welch(
            time_data[0, :],
            fs=sample_rate,
            window=window,
            nperseg=nperseg,
            noverlap=noverlap,
            nfft=nfft,
            scaling=scaling,
            detrend=detrend
        )
        
        # Initialize PSD array for all channels
        psd = np.zeros((num_channels, len(frequencies)))
        psd[0, :] = psd_first
        
        # Calculate PSD for remaining channels
        for i in range(1, num_channels):
            _, psd[i, :] = signal.welch(
                time_data[i, :],
                fs=sample_rate,
                window=window,
                nperseg=nperseg,
                noverlap=noverlap,
                nfft=nfft,
                scaling=scaling,
                detrend=detrend
            )
    else:
        raise ValueError("time_data must be 1D or 2D array")
    
    return frequencies, psd


def psd_to_db(psd: np.ndarray, reference: float = 1.0) -> np.ndarray:
    """
    Convert PSD values to decibel (dB) scale.
    
    The decibel scale is a logarithmic scale that is useful for visualizing
    PSD data that spans many orders of magnitude. It is defined as:
    
        PSD_dB = 10 * log10(PSD / reference)
    
    Parameters:
        psd (np.ndarray): Power spectral density values (linear scale).
        reference (float): Reference value for dB conversion. Default is 1.0.
            For acceleration data in g^2/Hz, use reference = 1.0.
            For pressure data in Pa^2/Hz, use reference = (20e-6)^2 for SPL.
    
    Returns:
        np.ndarray: PSD values in decibel scale.
    
    Example:
        >>> psd_linear = np.array([1.0, 10.0, 100.0])
        >>> psd_db = psd_to_db(psd_linear)
        >>> print(psd_db)
        [  0.  10.  20.]
    """
    # Avoid log of zero by replacing zeros with a very small number
    psd_safe = np.where(psd > 0, psd, 1e-20)
    return 10 * np.log10(psd_safe / reference)


def calculate_rms_from_psd(
    frequencies: np.ndarray,
    psd: np.ndarray,
    freq_range: Optional[Tuple[float, float]] = None
) -> float:
    """
    Calculate the RMS (Root Mean Square) value from PSD data.
    
    The RMS value represents the overall amplitude of the signal and can be
    calculated from the PSD by integrating over the frequency range:
    
        RMS = sqrt(integral of PSD over frequency)
    
    For discrete data, this is approximated using the trapezoidal rule.
    
    Parameters:
        frequencies (np.ndarray): Array of frequency values in Hz.
        psd (np.ndarray): Power spectral density values (must be 1D).
        freq_range (Tuple[float, float], optional): Frequency range (f_min, f_max)
            over which to calculate RMS. If None, uses the entire frequency range.
    
    Returns:
        float: RMS value in the same units as the original time-series data.
    
    Example:
        >>> frequencies = np.linspace(0, 500, 1000)
        >>> psd = np.ones_like(frequencies)  # Flat PSD
        >>> rms = calculate_rms_from_psd(frequencies, psd, freq_range=(10, 100))
    """
    if psd.ndim != 1:
        raise ValueError("PSD must be 1D array for RMS calculation")
    
    # Apply frequency range filter if specified
    if freq_range is not None:
        f_min, f_max = freq_range
        mask = (frequencies >= f_min) & (frequencies <= f_max)
        frequencies = frequencies[mask]
        psd = psd[mask]
    
    # Integrate PSD using trapezoidal rule
    # The integral of PSD gives the mean square value
    # Use trapezoid (NumPy 2.0+) with fallback to trapz for older versions
    try:
        mean_square = np.trapezoid(psd, frequencies)
    except AttributeError:
        mean_square = np.trapz(psd, frequencies)
    
    # RMS is the square root of the mean square
    rms = np.sqrt(mean_square)
    
    return rms


def get_window_options() -> dict:
    """
    Get available window function options for PSD calculation.
    
    Returns:
        dict: Dictionary mapping window names to descriptions.
    """
    return {
        'hann': 'Hann (Hanning) - Good general purpose, smooth sidelobes',
        'hamming': 'Hamming - Similar to Hann, slightly different sidelobe behavior',
        'blackman': 'Blackman - Excellent sidelobe suppression, wider main lobe',
        'bartlett': 'Bartlett (Triangular) - Simple, moderate performance',
        'boxcar': 'Boxcar (Rectangular) - No windowing, best frequency resolution but poor sidelobe suppression'
    }


def calculate_psd_maximax(
    time_data: np.ndarray,
    sample_rate: float,
    maximax_window: float = 1.0,
    overlap_percent: float = 50.0,
    window: str = 'hann',
    df: Optional[float] = None,
    nperseg: Optional[int] = None,
    use_efficient_fft: bool = True
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate Maximax PSD using sliding window approach.
    
    This function implements the Maximum Predicted Environment (MPE) style PSD
    calculation commonly used in aerospace applications. Instead of averaging
    PSDs across time segments (as in traditional Welch's method), this function
    calculates PSDs over short time windows and takes the maximum value at each
    frequency bin across all windows.
    
    This produces a conservative envelope PSD that represents the worst-case
    spectral content at each frequency throughout the signal duration.
    
    Algorithm:
    1. Divide the signal into overlapping windows of specified duration
    2. Calculate PSD for each window using Welch's method
    3. At each frequency bin, take the maximum value across all window PSDs
    4. Return the envelope PSD
    
    Parameters:
    -----------
    time_data : np.ndarray
        Input time-series data (1D array)
    sample_rate : float
        Sampling rate in Hz
    maximax_window : float
        Duration of each maximax window in seconds (default 1.0)
        Typical values: 0.5 to 2.0 seconds
    overlap_percent : float
        Overlap percentage between maximax windows (default 50.0)
        Range: 0 to 90
    window : str
        Window function type for PSD calculation
        Options: 'hann', 'hamming', 'blackman', 'bartlett', 'boxcar'
    df : float, optional
        Desired frequency resolution in Hz
        If provided, nperseg is calculated from df
    nperseg : int, optional
        Segment length for Welch's method within each maximax window
        If None and df is None, uses 256 samples
    use_efficient_fft : bool
        If True, rounds nperseg to nearest power of 2 for faster FFT
    
    Returns:
    --------
    frequencies : np.ndarray
        Array of frequency values in Hz
    psd_maximax : np.ndarray
        Maximax PSD values (envelope of all window PSDs)
    
    Raises:
    -------
    ValueError
        If input data is empty, sample_rate is not positive, or
        maximax_window is too large for the signal duration
    
    Example:
    --------
    >>> # Generate 30 seconds of test data
    >>> sample_rate = 1000.0
    >>> duration = 30.0
    >>> t = np.linspace(0, duration, int(sample_rate * duration))
    >>> signal = np.sin(2 * np.pi * 10 * t) + np.random.normal(0, 0.1, len(t))
    >>> 
    >>> # Calculate maximax PSD with 1-second windows
    >>> frequencies, psd_max = calculate_psd_maximax(
    ...     signal, sample_rate, maximax_window=1.0, overlap_percent=50.0
    ... )
    >>> 
    >>> # psd_max represents the envelope of PSDs from all 1-second windows
    
    Notes:
    ------
    - Maximax PSD is more conservative than averaged PSD
    - Useful for defining test specifications (MPE)
    - Requires longer signal duration for statistical significance
    - Computational cost scales with number of windows
    """
    # Input validation
    if time_data.size == 0:
        raise ValueError("Input time_data cannot be empty")
    
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    
    # Calculate signal duration
    signal_duration = len(time_data) / sample_rate
    
    if maximax_window > signal_duration:
        raise ValueError(f"Maximax window ({maximax_window}s) is larger than signal duration ({signal_duration:.2f}s)")
    
    if maximax_window <= 0:
        raise ValueError("Maximax window must be positive")
    
    if not (0 <= overlap_percent < 100):
        raise ValueError("Overlap percent must be between 0 and 100")
    
    # Calculate window parameters
    window_samples = int(maximax_window * sample_rate)
    overlap_samples = int(window_samples * overlap_percent / 100)
    step_samples = window_samples - overlap_samples
    
    # Calculate nperseg for Welch's method within each window
    if df is not None:
        # Calculate nperseg from desired frequency resolution
        nperseg_calc = int(sample_rate / df)
        
        if use_efficient_fft:
            # Round to nearest power of 2
            nperseg_calc = 2 ** int(np.ceil(np.log2(nperseg_calc)))
        
        nperseg = nperseg_calc
    elif nperseg is None:
        # Default to 256 samples
        nperseg = min(256, window_samples)
    
    # Ensure nperseg doesn't exceed window size
    nperseg = min(nperseg, window_samples)
    
    # Calculate noverlap for Welch's method (50% of nperseg)
    noverlap = nperseg // 2
    
    # Initialize variables for maximax calculation
    frequencies = None
    psd_maximax = None
    num_windows = 0
    
    # Slide window across signal
    start_idx = 0
    
    while start_idx + window_samples <= len(time_data):
        # Extract window
        window_data = time_data[start_idx:start_idx + window_samples]
        
        # Calculate PSD for this window using Welch's method
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
            psd_maximax = psd_window
        else:
            # Take maximum at each frequency bin
            psd_maximax = np.maximum(psd_maximax, psd_window)
        
        num_windows += 1
        
        # Move to next window
        start_idx += step_samples
    
    if num_windows == 0:
        raise ValueError("No windows could be extracted from signal. Check maximax_window parameter.")
    
    return frequencies, psd_maximax


def calculate_rms_from_psd(frequencies: np.ndarray, psd: np.ndarray) -> float:
    """
    Calculate RMS (Root Mean Square) value from PSD using Parseval's theorem.
    
    The RMS value represents the overall amplitude of the signal and is calculated
    by integrating the PSD over frequency and taking the square root.
    
    Mathematically:
        RMS = sqrt(integral of PSD over frequency)
    
    For discrete data, the integral is approximated using the trapezoidal rule.
    
    Parameters:
    -----------
    frequencies : np.ndarray
        Array of frequency values in Hz (must be equally spaced or monotonically increasing)
    psd : np.ndarray
        Power spectral density values corresponding to the frequencies
    
    Returns:
    --------
    float
        RMS value in the same units as the original signal
    
    Example:
    --------
    >>> # Generate a sine wave with known RMS
    >>> sample_rate = 1000.0
    >>> t = np.linspace(0, 10, int(sample_rate * 10))
    >>> amplitude = 2.0
    >>> signal = amplitude * np.sin(2 * np.pi * 10 * t)
    >>> 
    >>> # Calculate PSD and RMS
    >>> frequencies, psd = calculate_psd_welch(signal, sample_rate)
    >>> rms = calculate_rms_from_psd(frequencies, psd)
    >>> 
    >>> # For a sine wave, RMS = amplitude / sqrt(2) ≈ 1.414
    >>> print(f"RMS: {rms:.3f}")  # Should be close to 1.414
    
    Notes:
    ------
    - This function uses trapezoidal integration (np.trapezoid or np.trapz)
    - The PSD must be in 'density' scaling (units^2/Hz)
    - For accurate results, ensure adequate frequency resolution
    """
    # Input validation
    if len(frequencies) != len(psd):
        raise ValueError("frequencies and psd must have the same length")
    
    if len(frequencies) < 2:
        raise ValueError("Need at least 2 frequency points to calculate RMS")
    
    # Integrate PSD using trapezoidal rule
    # Use np.trapezoid for NumPy 2.0+, fall back to np.trapz for older versions
    try:
        power = np.trapezoid(psd, frequencies)
    except AttributeError:
        power = np.trapz(psd, frequencies)
    
    # RMS is square root of integrated power
    rms = np.sqrt(power)
    
    return rms
