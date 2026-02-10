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
        "• <b>Hann:</b> Best general-purpose window (recommended)<br>"
        "• <b>Hamming:</b> Similar to Hann, slightly different sidelobe characteristics<br>"
        "• <b>Blackman:</b> Better frequency resolution, wider main lobe<br>"
        "• <b>Flat Top:</b> Best for amplitude accuracy<br>"
        "• <b>Tukey:</b> Adjustable taper, good for transient signals<br><br>"
        "<b>Aerospace Standard:</b> Hann window (per SMC-S-016)<br>"
        "<b>Typical Use:</b> Hann for vibration testing"
    ),
    
    'frequency_resolution': (
        "<b>Frequency Resolution (Δf)</b><br><br>"
        "Spacing between frequency bins in the PSD.<br><br>"
        "<b>Valid Range:</b> > 0 Hz<br>"
        "<b>Typical Values:</b><br>"
        "• 0.5-2.0 Hz for general vibration<br>"
        "• 0.1-0.5 Hz for low-frequency analysis<br>"
        "• 2.0-10 Hz for high-frequency or quick analysis<br><br>"
        "<b>Aerospace Standard:</b> 5.0 Hz (per SMC-S-016)<br><br>"
        "<b>Trade-offs:</b><br>"
        "• Smaller Δf → Better frequency detail, longer data segments required<br>"
        "• Larger Δf → Faster calculation, less frequency detail<br><br>"
        "<b>Relationship:</b> Δf = Sample_Rate / Segment_Length"
    ),
    
    'overlap': (
        "<b>Overlap Percentage</b><br><br>"
        "Percentage of overlap between consecutive data segments.<br><br>"
        "<b>Valid Range:</b> 0-99%<br>"
        "<b>Typical Values:</b><br>"
        "• 50% - Standard practice (recommended)<br>"
        "• 66.7% - Higher statistical reliability<br>"
        "• 75% - Maximum useful overlap<br><br>"
        "<b>Aerospace Standard:</b> 50% (per SMC-S-016)<br><br>"
        "<b>Trade-offs:</b><br>"
        "• Higher overlap → Better statistical averaging, slower calculation<br>"
        "• Lower overlap → Faster calculation, less averaging<br><br>"
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
        "• Aerospace qualification testing<br>"
        "• Capturing worst-case vibration<br>"
        "• Compliance with SMC-S-016<br><br>"
        "<b>When to Disable:</b><br>"
        "• Statistical analysis of steady-state vibration<br>"
        "• Comparing to non-aerospace standards"
    ),
    
    'maximax_window': (
        "<b>Maximax Window Duration</b><br><br>"
        "Duration of each window for maximax envelope calculation.<br><br>"
        "<b>Valid Range:</b> 0.1-10.0 seconds (must be ≤ data duration)<br>"
        "<b>Typical Values:</b><br>"
        "• 1.0 second - Standard (per SMC-S-016)<br>"
        "• 0.5 second - Shorter transients<br>"
        "• 2.0 seconds - Longer averaging<br><br>"
        "<b>Aerospace Standard:</b> 1.0 second (per SMC-S-016)<br><br>"
        "<b>Trade-offs:</b><br>"
        "• Shorter windows → Capture brief transients<br>"
        "• Longer windows → Better statistical averaging<br><br>"
        "<b>Requirement:</b> Must have at least 2 windows for valid maximax"
    ),
    
    'maximax_overlap': (
        "<b>Maximax Overlap Percentage</b><br><br>"
        "Overlap between consecutive maximax windows.<br><br>"
        "<b>Valid Range:</b> 0-99%<br>"
        "<b>Typical Values:</b><br>"
        "• 50% - Standard (per SMC-S-016)<br>"
        "• 66.7% - Higher density<br><br>"
        "<b>Aerospace Standard:</b> 50% (per SMC-S-016)<br><br>"
        "<b>Purpose:</b> Ensures peak events aren't missed between windows"
    ),
    
    'frequency_range': (
        "<b>Frequency Range (Display)</b><br><br>"
        "Frequency range for plot display and RMS integration.<br><br>"
        "<b>Valid Range:</b><br>"
        "• Min ≥ 0 Hz<br>"
        "• Max ≤ Nyquist Frequency (Sample_Rate / 2)<br>"
        "• Min < Max<br><br>"
        "<b>Typical Ranges:</b><br>"
        "• 10-3000 Hz - General aerospace vibration<br>"
        "• 5-2000 Hz - Launch vehicle<br>"
        "• 20-10000 Hz - High-frequency components<br><br>"
        "<b>Note:</b> PSD is calculated for full frequency range;<br>"
        "this setting only affects display and RMS calculation"
    ),
    
    'efficient_fft': (
        "<b>Use Efficient FFT Size</b><br><br>"
        "Round segment length to nearest power of 2 for faster FFT.<br><br>"
        "<b>When Enabled:</b><br>"
        "• FFT length = nearest power of 2<br>"
        "• Faster computation (2-5x speedup)<br>"
        "• Actual Δf may differ slightly from requested<br><br>"
        "<b>When Disabled:</b><br>"
        "• FFT length = exact value for requested Δf<br>"
        "• Slower computation<br>"
        "• Exact Δf as specified<br><br>"
        "<b>Recommendation:</b> Keep enabled unless exact Δf is critical"
    ),
    
    'remove_mean': (
        "<b>Remove 1-Second Running Mean</b><br><br>"
        "Subtract 1-second running mean from time history display.<br><br>"
        "<b>Purpose:</b> View vibration about slowly-varying mean<br>"
        "<b>Use Case:</b> Visualizing AC component of signal<br><br>"
        "<b>Note:</b> This only affects time history display,<br>"
        "not PSD calculation (which always removes DC)"
    ),
    
    'octave_display': (
        "<b>Octave Band Display</b><br><br>"
        "Convert narrowband PSD to octave bands for visualization.<br><br>"
        "<b>Purpose:</b> Frequency-weighted view of spectral content<br><br>"
        "<b>Common Spacings:</b><br>"
        "• 1/3 Octave - Standard for acoustic analysis<br>"
        "• 1/6 Octave - Finer resolution<br>"
        "• 1/12 Octave - Very fine resolution<br><br>"
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
        "Apply additional bandpass filtering to signal before PSD calculation.<br><br>"
        "<b>Default Processing:</b><br>"
        "• Running mean removal (1 second window)<br>"
        "• Applied automatically to PSD calculation<br><br>"
        "<b>Optional Filtering:</b><br>"
        "• Bandpass filter with custom cutoff frequencies<br>"
        "• Butterworth filter design<br>"
        "• Applied to both time history and PSD<br><br>"
        "<b>Use Case:</b> Isolate specific frequency bands of interest"
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
