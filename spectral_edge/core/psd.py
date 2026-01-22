"""
Power Spectral Density (PSD) Calculation Module

This module provides functions for calculating Power Spectral Density (PSD) using
various methods including Welch's method and maximax (envelope) PSD calculation
as defined in SMC-S-016 for aerospace applications.

Functions:
    calculate_psd_welch: Calculate PSD using Welch's method (averaged periodogram)
    calculate_psd_maximax: Calculate maximax PSD (envelope of 1-second PSDs per SMC-S-016)
    calculate_rms_from_psd: Calculate RMS value from PSD using Parseval's theorem
    psd_to_db: Convert PSD values to decibel (dB) scale for visualization
    get_window_options: Get available window function options with descriptions

References:
    - Welch, P. (1967). "The use of fast Fourier transform for the estimation of 
      power spectra: A method based on time averaging over short, modified periodograms"
    - SMC-S-016: Test Requirements for Launch, Upper-Stage, and Space Vehicles

Author: SpectralEdge Development Team
Date: 2025-01-22
"""

import numpy as np
from scipy import signal
from typing import Optional, Tuple, Union


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
        
        if freq_min < frequencies[0] or freq_max > frequencies[-1]:
            raise ValueError(
                f"Frequency range [{freq_min}, {freq_max}] Hz is outside "
                f"available range [{frequencies[0]}, {frequencies[-1]}] Hz"
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
