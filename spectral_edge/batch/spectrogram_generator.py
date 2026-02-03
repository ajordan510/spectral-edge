"""
Spectrogram generation for batch processing.

This module provides functions to generate spectrograms for batch-processed
signals, with configurable parameters matching the spectrogram GUI.

Author: SpectralEdge Development Team
"""

import numpy as np
from scipy import signal as scipy_signal
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def generate_spectrogram(
    signal_data: np.ndarray,
    sample_rate: float,
    desired_df: float = 1.0,
    overlap_percent: int = 50,
    snr_threshold: float = 0.0,
    use_efficient_fft: bool = True
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate spectrogram for a signal using Short-Time Fourier Transform (STFT).
    
    This function computes a spectrogram by dividing the signal into overlapping
    segments, applying a Hann window to each segment, computing the FFT, and
    assembling the results into a time-frequency representation.
    
    Parameters
    ----------
    signal_data : np.ndarray
        Input signal array (1D)
    sample_rate : float
        Sample rate in Hz
    desired_df : float, optional
        Desired frequency resolution in Hz (default: 1.0)
    overlap_percent : int, optional
        Overlap percentage between segments (default: 50)
    snr_threshold : float, optional
        SNR threshold in dB for noise floor suppression (default: 0.0)
    use_efficient_fft : bool, optional
        Whether to use efficient FFT size (power of 2) (default: True)
        
    Returns
    -------
    frequencies : np.ndarray
        Frequency array in Hz (1D)
    times : np.ndarray
        Time array in seconds (1D)
    Sxx : np.ndarray
        Spectrogram values in (frequency, time) format (2D)
        Values are in power spectral density units (signal_units^2/Hz)
        
    Notes
    -----
    The spectrogram is computed using scipy.signal.spectrogram with the following
    processing steps:
    1. Signal is divided into overlapping segments
    2. Hann window is applied to each segment
    3. FFT is computed for each windowed segment
    4. Power spectral density is calculated
    5. Results are assembled into time-frequency matrix
    
    The SNR threshold is applied to suppress noise floor by setting values below
    the threshold (relative to maximum) to the threshold value.
    
    Examples
    --------
    >>> signal = np.random.randn(10000)
    >>> sample_rate = 1000.0
    >>> f, t, Sxx = generate_spectrogram(signal, sample_rate, desired_df=1.0)
    >>> print(f"Frequency range: {f[0]:.1f} - {f[-1]:.1f} Hz")
    >>> print(f"Time range: {t[0]:.1f} - {t[-1]:.1f} s")
    >>> print(f"Spectrogram shape: {Sxx.shape}")
    """
    # Calculate nperseg from desired frequency resolution
    nperseg = int(sample_rate / desired_df)
    
    # Use efficient FFT size if requested
    if use_efficient_fft:
        nperseg = 2 ** int(np.ceil(np.log2(nperseg)))
    
    # Ensure nperseg is not larger than signal length
    nperseg = min(nperseg, len(signal_data))
    
    # Calculate noverlap from overlap percentage
    noverlap = int(nperseg * overlap_percent / 100)
    
    # Compute spectrogram using scipy
    try:
        frequencies, times, Sxx = scipy_signal.spectrogram(
            signal_data,
            fs=sample_rate,
            window='hann',
            nperseg=nperseg,
            noverlap=noverlap,
            scaling='density',
            mode='psd'
        )
        
        # Apply SNR threshold if specified
        if snr_threshold > 0:
            Sxx = apply_snr_threshold(Sxx, snr_threshold)
        
        logger.info(
            f"Generated spectrogram: {Sxx.shape[0]} frequencies x {Sxx.shape[1]} time steps"
        )
        
        return frequencies, times, Sxx
        
    except Exception as e:
        logger.error(f"Failed to generate spectrogram: {str(e)}")
        raise


def apply_snr_threshold(Sxx: np.ndarray, snr_threshold_db: float) -> np.ndarray:
    """
    Apply SNR threshold to spectrogram to suppress noise floor.
    
    This function suppresses values in the spectrogram that are below a specified
    SNR threshold relative to the maximum value. This helps visualize the signal
    content by reducing the noise floor.
    
    Parameters
    ----------
    Sxx : np.ndarray
        Input spectrogram array (2D)
    snr_threshold_db : float
        SNR threshold in dB relative to maximum value
        
    Returns
    -------
    np.ndarray
        Thresholded spectrogram array (same shape as input)
        
    Notes
    -----
    The threshold is applied as follows:
    1. Find maximum value in spectrogram
    2. Calculate threshold = max_value * 10^(-snr_threshold_db/10)
    3. Set all values below threshold to threshold value
    
    This prevents log-scale artifacts when plotting and improves visualization
    of signal content above the noise floor.
    
    Examples
    --------
    >>> Sxx = np.random.rand(100, 200)
    >>> Sxx_thresholded = apply_snr_threshold(Sxx, snr_threshold_db=20.0)
    """
    # Find maximum value
    max_value = np.max(Sxx)
    
    # Calculate threshold in linear scale
    threshold_linear = max_value * (10 ** (-snr_threshold_db / 10))
    
    # Apply threshold
    Sxx_thresholded = np.maximum(Sxx, threshold_linear)
    
    return Sxx_thresholded


def save_spectrogram_plot(
    frequencies: np.ndarray,
    times: np.ndarray,
    Sxx: np.ndarray,
    output_path: str,
    title: str = "Spectrogram",
    freq_min: Optional[float] = None,
    freq_max: Optional[float] = None,
    colormap: str = "viridis",
    show_colorbar: bool = True
) -> None:
    """
    Save spectrogram as an image file.
    
    This function creates a publication-quality spectrogram plot and saves it
    to a file. The plot includes proper axis labels, title, and optional colorbar.
    
    Parameters
    ----------
    frequencies : np.ndarray
        Frequency array in Hz (1D)
    times : np.ndarray
        Time array in seconds (1D)
    Sxx : np.ndarray
        Spectrogram values (2D)
    output_path : str
        Path to save the image file
    title : str, optional
        Plot title (default: "Spectrogram")
    freq_min : float, optional
        Minimum frequency to display (default: None, uses data minimum)
    freq_max : float, optional
        Maximum frequency to display (default: None, uses data maximum)
    colormap : str, optional
        Matplotlib colormap name (default: "viridis")
    show_colorbar : bool, optional
        Whether to show colorbar (default: True)
        
    Returns
    -------
    None
        
    Notes
    -----
    The spectrogram is plotted in dB scale (10*log10(Sxx)) for better visualization
    of the dynamic range. The frequency axis can be limited using freq_min and
    freq_max parameters.
    
    Supported image formats are determined by the file extension in output_path:
    - .png: PNG format (recommended for reports)
    - .jpg/.jpeg: JPEG format
    - .pdf: PDF format (vector graphics)
    - .svg: SVG format (vector graphics)
    
    Examples
    --------
    >>> f, t, Sxx = generate_spectrogram(signal, sample_rate)
    >>> save_spectrogram_plot(f, t, Sxx, "spectrogram.png", title="Test Signal")
    """
    import matplotlib.pyplot as plt
    
    # Apply frequency limits if specified
    if freq_min is not None or freq_max is not None:
        freq_min = freq_min if freq_min is not None else frequencies[0]
        freq_max = freq_max if freq_max is not None else frequencies[-1]
        
        # Find indices within frequency range
        freq_mask = (frequencies >= freq_min) & (frequencies <= freq_max)
        frequencies = frequencies[freq_mask]
        Sxx = Sxx[freq_mask, :]
    
    # Convert to dB scale
    Sxx_db = 10 * np.log10(Sxx + 1e-12)  # Add small value to avoid log(0)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot spectrogram
    im = ax.pcolormesh(
        times, frequencies, Sxx_db,
        cmap=colormap,
        shading='gouraud'
    )
    
    # Set labels and title
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Frequency (Hz)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    
    # Add colorbar if requested
    if show_colorbar:
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Power/Frequency (dB/Hz)', fontsize=12)
    
    # Tight layout
    plt.tight_layout()
    
    # Save figure
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    
    logger.info(f"Saved spectrogram plot to {output_path}")
