"""
Parameter Tooltips Module for SpectralEdge GUI

This module provides comprehensive, aerospace-specific tooltips for all
PSD analysis parameters to help users understand valid ranges, typical
values, and best practices.

Author: SpectralEdge Development Team
"""

# PSD Parameter Tooltips
TOOLTIPS = {
    'window_type': (
        "<b>Window Type</b><br><br>"
        "Windowing function applied to each data segment before FFT.<br><br>"
        "<b>Common Options:</b><br>"
        "&bull; <b>Hann:</b> Best general-purpose window (recommended)<br>"
        "&bull; <b>Hamming:</b> Similar to Hann, slightly different sidelobe characteristics<br>"
        "&bull; <b>Blackman:</b> Better frequency resolution, wider main lobe<br>"
        "&bull; <b>Flat Top:</b> Best for amplitude accuracy<br>"
        "&bull; <b>Tukey:</b> Adjustable taper, good for transient signals<br><br>"
        "<b>Aerospace Standard:</b> Hann window (per SMC-S-016)<br>"
        "<b>Typical Use:</b> Hann for vibration testing"
    ),

    'frequency_resolution': (
        "<b>Frequency Resolution (&Delta;f)</b><br><br>"
        "Spacing between frequency bins in the PSD.<br><br>"
        "<b>Valid Range:</b> > 0 Hz<br>"
        "<b>Typical Values:</b><br>"
        "&bull; 0.5-2.0 Hz for general vibration<br>"
        "&bull; 0.1-0.5 Hz for low-frequency analysis<br>"
        "&bull; 2.0-10 Hz for high-frequency or quick analysis<br><br>"
        "<b>Aerospace Standard:</b> 5.0 Hz (per SMC-S-016)<br><br>"
        "<b>Trade-offs:</b><br>"
        "&bull; Smaller &Delta;f &rarr; Better frequency detail, longer data segments required<br>"
        "&bull; Larger &Delta;f &rarr; Faster calculation, less frequency detail<br><br>"
        "<b>Relationship:</b> &Delta;f = Sample_Rate / Segment_Length"
    ),

    'overlap': (
        "<b>Overlap Percentage</b><br><br>"
        "Percentage of overlap between consecutive data segments.<br><br>"
        "<b>Valid Range:</b> 0-99%<br>"
        "<b>Typical Values:</b><br>"
        "&bull; 50% - Standard practice (recommended)<br>"
        "&bull; 66.7% - Higher statistical reliability<br>"
        "&bull; 75% - Maximum useful overlap<br><br>"
        "<b>Aerospace Standard:</b> 50% (per SMC-S-016)<br><br>"
        "<b>Trade-offs:</b><br>"
        "&bull; Higher overlap &rarr; Better statistical averaging, slower calculation<br>"
        "&bull; Lower overlap &rarr; Faster calculation, less averaging<br><br>"
        "<b>Note:</b> Overlap > 95% provides diminishing returns"
    ),

    'maximax_psd': (
        "<b>Maximax PSD (Envelope PSD)</b><br><br>"
        "Calculate envelope PSD using sliding window maximax method.<br><br>"
        "<b>Purpose:</b> Captures peak spectral content over time<br>"
        "<b>Use Case:</b> Aerospace vibration testing per SMC-S-016<br><br>"
        "<b>Method:</b><br>"
        "1. Divide data into overlapping windows<br>"
        "2. Calculate PSD for each window<br>"
        "3. Take maximum value at each frequency<br><br>"
        "<b>Aerospace Standard:</b> Enabled with 1-second windows, 50% overlap<br><br>"
        "<b>When to Use:</b><br>"
        "&bull; Aerospace qualification testing<br>"
        "&bull; Capturing worst-case vibration<br>"
        "&bull; Compliance with SMC-S-016<br><br>"
        "<b>When to Disable:</b><br>"
        "&bull; Statistical analysis of steady-state vibration<br>"
        "&bull; Comparing to non-aerospace standards"
    ),

    'maximax_window': (
        "<b>Maximax Window Duration</b><br><br>"
        "Duration of each window for maximax envelope calculation.<br><br>"
        "<b>Valid Range:</b> 0.1-10.0 seconds (must be &le; data duration)<br>"
        "<b>Typical Values:</b><br>"
        "&bull; 1.0 second - Standard (per SMC-S-016)<br>"
        "&bull; 0.5 second - Shorter transients<br>"
        "&bull; 2.0 seconds - Longer averaging<br><br>"
        "<b>Aerospace Standard:</b> 1.0 second (per SMC-S-016)<br><br>"
        "<b>Trade-offs:</b><br>"
        "&bull; Shorter windows &rarr; Capture brief transients<br>"
        "&bull; Longer windows &rarr; Better statistical averaging<br><br>"
        "<b>Requirement:</b> Must have at least 2 windows for valid maximax"
    ),

    'maximax_overlap': (
        "<b>Maximax Overlap Percentage</b><br><br>"
        "Overlap between consecutive maximax windows.<br><br>"
        "<b>Valid Range:</b> 0-99%<br>"
        "<b>Typical Values:</b><br>"
        "&bull; 50% - Standard (per SMC-S-016)<br>"
        "&bull; 66.7% - Higher density<br><br>"
        "<b>Aerospace Standard:</b> 50% (per SMC-S-016)<br><br>"
        "<b>Purpose:</b> Ensures peak events are not missed between windows"
    ),

    'frequency_range': (
        "<b>Frequency Range (Display)</b><br><br>"
        "Frequency range for plot display and RMS integration.<br><br>"
        "<b>Valid Range:</b><br>"
        "&bull; Min &ge; 0 Hz<br>"
        "&bull; Max &le; Nyquist Frequency (Sample_Rate / 2)<br>"
        "&bull; Min < Max<br><br>"
        "<b>Typical Ranges:</b><br>"
        "&bull; 10-3000 Hz - General aerospace vibration<br>"
        "&bull; 5-2000 Hz - Launch vehicle<br>"
        "&bull; 20-10000 Hz - High-frequency components<br><br>"
        "<b>Note:</b> PSD is calculated for full frequency range;<br>"
        "this setting only affects display and RMS calculation"
    ),

    'efficient_fft': (
        "<b>Use Efficient FFT Size</b><br><br>"
        "Round segment length to nearest power of 2 for faster FFT.<br><br>"
        "<b>When Enabled:</b><br>"
        "&bull; FFT length = nearest power of 2<br>"
        "&bull; Faster computation (2-5x speedup)<br>"
        "&bull; Actual &Delta;f may differ slightly from requested<br><br>"
        "<b>When Disabled:</b><br>"
        "&bull; FFT length = exact value for requested &Delta;f<br>"
        "&bull; Slower computation<br>"
        "&bull; Exact &Delta;f as specified<br><br>"
        "<b>Recommendation:</b> Keep enabled unless exact &Delta;f is critical"
    ),

    'remove_mean': (
        "<b>Remove 1-Second Running Mean</b><br><br>"
        "Subtract 1-second running mean from time history display.<br><br>"
        "<b>Purpose:</b> View vibration about slowly-varying mean<br>"
        "<b>Use Case:</b> Visualizing AC component when raw view is enabled<br><br>"
        "<b>Note:</b> This only affects time history display,<br>"
        "not PSD calculation. Baseline 1 Hz highpass filtering already removes DC/mean."
    ),

    'octave_display': (
        "<b>Octave Band Display</b><br><br>"
        "Convert narrowband PSD to octave bands for visualization.<br><br>"
        "<b>Purpose:</b> Frequency-weighted view of spectral content<br><br>"
        "<b>Common Spacings:</b><br>"
        "&bull; 1/3 Octave - Standard for acoustic analysis<br>"
        "&bull; 1/6 Octave - Finer resolution<br>"
        "&bull; 1/12 Octave - Very fine resolution<br><br>"
        "<b>Note:</b> This only affects display;<br>"
        "narrowband PSD is still calculated"
    ),

    'crosshair': (
        "<b>Show Crosshair</b><br><br>"
        "Display interactive crosshair on PSD plot for precise reading.<br><br>"
        "<b>Usage:</b> Hover mouse over plot to see exact values<br>"
        "<b>Display:</b> Shows frequency and PSD value at cursor"
    ),

    'filtering': (
        "<b>Signal Filtering</b><br><br>"
        "Baseline filtering is always applied for processing outputs:<br>"
        "&bull; Highpass: 1.0 Hz (DC/drift removal)<br>"
        "&bull; Lowpass: 0.45 &times; sample rate (anti-aliasing)<br><br>"
        "<b>Optional User Overrides:</b><br>"
        "&bull; User highpass and lowpass values are accepted<br>"
        "&bull; Values outside valid range are auto-clamped (non-blocking info shown)<br>"
        "&bull; Applied to both time history (filtered view) and PSD<br><br>"
        "<b>Use Case:</b> Restrict analysis bandwidth while remaining robust"
    ),
}


def get_tooltip(parameter_name: str) -> str:
    """
    Get tooltip text for a parameter.

    Args:
        parameter_name: Name of the parameter

    Returns:
        Tooltip HTML text, or empty string if not found
    """
    return TOOLTIPS.get(parameter_name, "")


def apply_tooltips_to_window(window):
    """
    Apply comprehensive tooltips to all parameters in the PSD window.

    Args:
        window: PSDAnalysisWindow instance
    """
    # Window type
    if hasattr(window, 'window_combo'):
        window.window_combo.setToolTip(get_tooltip('window_type'))

    # Frequency resolution
    if hasattr(window, 'df_spin'):
        window.df_spin.setToolTip(get_tooltip('frequency_resolution'))

    # Overlap
    if hasattr(window, 'overlap_spin'):
        window.overlap_spin.setToolTip(get_tooltip('overlap'))

    # Maximax PSD
    if hasattr(window, 'maximax_checkbox'):
        window.maximax_checkbox.setToolTip(get_tooltip('maximax_psd'))

    # Maximax window
    if hasattr(window, 'maximax_window_spin'):
        window.maximax_window_spin.setToolTip(get_tooltip('maximax_window'))

    # Maximax overlap
    if hasattr(window, 'maximax_overlap_spin'):
        window.maximax_overlap_spin.setToolTip(get_tooltip('maximax_overlap'))

    # Efficient FFT
    if hasattr(window, 'efficient_fft_checkbox'):
        window.efficient_fft_checkbox.setToolTip(get_tooltip('efficient_fft'))

    # Remove mean
    if hasattr(window, 'remove_mean_checkbox'):
        window.remove_mean_checkbox.setToolTip(get_tooltip('remove_mean'))

    # Octave display
    if hasattr(window, 'octave_checkbox'):
        window.octave_checkbox.setToolTip(get_tooltip('octave_display'))

    # Crosshair
    if hasattr(window, 'show_crosshair_checkbox'):
        window.show_crosshair_checkbox.setToolTip(get_tooltip('crosshair'))

    # Filtering
    if hasattr(window, 'enable_filter_checkbox'):
        window.enable_filter_checkbox.setToolTip(get_tooltip('filtering'))
