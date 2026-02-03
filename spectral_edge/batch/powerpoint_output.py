"""
PowerPoint Output Module for Batch Processing

This module generates PowerPoint presentations from batch PSD processing results.
Leverages the existing report_generator utility for consistent formatting.

Author: SpectralEdge Development Team
Date: 2026-02-02
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, Tuple, List
import logging
import tempfile
from datetime import datetime

from spectral_edge.utils.report_generator import ReportGenerator

logger = logging.getLogger(__name__)


def generate_powerpoint_report(
    results: Dict[str, Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray]]]],
    output_path: str,
    config: 'BatchConfig',
    title: str = "Batch PSD Processing Report"
) -> None:
    """
    Generate a PowerPoint presentation from batch processing results.
    
    Creates a professional report with:
    - Title slide
    - Configuration summary
    - One slide per event showing PSD plots
    - Summary statistics
    
    Parameters:
    -----------
    results : Dict[str, Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray]]]]
        Nested dictionary structure:
        {
            event_name: {
                source_identifier: {
                    channel_name: (frequencies, psd_values),
                    ...
                },
                ...
            },
            ...
        }
    output_path : str
        Path to save the PowerPoint file
    config : BatchConfig
        Batch configuration object
    title : str, optional
        Title for the presentation
        
    Returns:
    --------
    None
    
    Raises:
    -------
    IOError
        If file cannot be written
        
    Example:
    --------
    >>> generate_powerpoint_report(results, 'batch_report.pptx', config)
    """
    try:
        # Initialize report generator with title
        report_gen = ReportGenerator(title=title)
        
        # Create title slide
        report_gen.add_title_slide(
            subtitle=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Add configuration summary slide
        _add_config_slide(report_gen, config)
        
        # Add event slides
        for event_name, event_results in results.items():
            _add_event_slide(report_gen, event_name, event_results, config)
        
        # Save presentation
        report_gen.save(output_path)
        logger.info(f"PowerPoint report saved: {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to generate PowerPoint report: {str(e)}")
        raise


def _add_config_slide(report_gen: ReportGenerator, config: 'BatchConfig') -> None:
    """
    Add configuration summary slide.
    
    Parameters:
    -----------
    report_gen : ReportGenerator
        Report generator instance
    config : BatchConfig
        Batch configuration
    """
    config_text = f"""
Processing Configuration:

PSD Method: {config.psd_config.method}
Window Function: {config.psd_config.window}
Overlap: {config.psd_config.overlap_percent}%
Frequency Range: {config.psd_config.freq_min} - {config.psd_config.freq_max} Hz
Frequency Spacing: {config.psd_config.frequency_spacing}

Filtering: {'Enabled' if config.filter_config.enabled else 'Disabled'}
"""
    
    if config.filter_config.enabled:
        config_text += f"""
Filter Type: {config.filter_config.filter_type}
Filter Design: {config.filter_config.filter_design}
Filter Order: {config.filter_config.filter_order}
"""
    
    report_gen.add_text_slide(
        title="Processing Configuration",
        content=config_text
    )


def _add_event_slide(
    report_gen: ReportGenerator,
    event_name: str,
    event_results: Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray]]],
    config: 'BatchConfig'
) -> None:
    """
    Add a slide for a specific event with PSD plots.
    
    Parameters:
    -----------
    report_gen : ReportGenerator
        Report generator instance
    event_name : str
        Name of the event
    event_results : Dict
        Results for this event
    config : BatchConfig
        Batch configuration
    """
    # Create PSD plot
    fig = _create_psd_plot(event_name, event_results, config)
    
    # Save plot to temporary file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        temp_path = tmp_file.name
        fig.savefig(temp_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
    
    try:
        # Add slide with plot
        report_gen.add_image_slide(
            title=f"Event: {event_name}",
            image_path=temp_path
        )
    finally:
        # Clean up temporary file
        Path(temp_path).unlink()


def _create_psd_plot(
    event_name: str,
    event_results: Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray]]],
    config: 'BatchConfig'
) -> plt.Figure:
    """
    Create a PSD plot for an event.
    
    Parameters:
    -----------
    event_name : str
        Name of the event
    event_results : Dict
        Results for this event
    config : BatchConfig
        Batch configuration
        
    Returns:
    --------
    plt.Figure
        Matplotlib figure object
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot each channel
    for source_id, channels in event_results.items():
        for channel_name, (frequencies, psd_values) in channels.items():
            label = f"{source_id}_{channel_name}"
            ax.loglog(frequencies, psd_values, label=label, linewidth=1.5)
    
    # Configure plot
    ax.set_xlabel('Frequency (Hz)', fontsize=12)
    ax.set_ylabel('PSD (g²/Hz)', fontsize=12)
    ax.set_title(f'Power Spectral Density - {event_name}', fontsize=14, fontweight='bold')
    ax.grid(True, which='both', alpha=0.3)
    ax.legend(loc='best', fontsize=10)
    
    # Apply display settings if not auto-scale
    if not config.display_config.psd_auto_scale:
        if config.display_config.psd_x_axis_min and config.display_config.psd_x_axis_max:
            ax.set_xlim(config.display_config.psd_x_axis_min, config.display_config.psd_x_axis_max)
        if config.display_config.psd_y_axis_min and config.display_config.psd_y_axis_max:
            ax.set_ylim(config.display_config.psd_y_axis_min, config.display_config.psd_y_axis_max)
    
    plt.tight_layout()
    return fig


def generate_spectrogram_slides(
    spectrograms: Dict[str, Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]]]],
    output_path: str,
    config: 'BatchConfig'
) -> None:
    """
    Generate PowerPoint slides for spectrograms.
    
    Parameters:
    -----------
    spectrograms : Dict[str, Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]]]]
        Nested dictionary structure:
        {
            event_name: {
                source_identifier: {
                    channel_name: (time, frequencies, Sxx),
                    ...
                },
                ...
            },
            ...
        }
    output_path : str
        Path to save the PowerPoint file
    config : BatchConfig
        Batch configuration
        
    Notes:
    ------
    This function creates a separate presentation for spectrograms.
    Can be merged with PSD report if desired.
    """
    try:
        report_gen = ReportGenerator()
        
        # Title slide
        report_gen.add_title_slide(
            title="Batch Spectrogram Report",
            subtitle=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Add spectrogram slides
        for event_name, event_results in spectrograms.items():
            for source_id, channels in event_results.items():
                for channel_name, (time, frequencies, Sxx) in channels.items():
                    _add_spectrogram_slide(
                        report_gen,
                        event_name,
                        source_id,
                        channel_name,
                        time,
                        frequencies,
                        Sxx,
                        config
                    )
        
        # Save presentation
        report_gen.save(output_path)
        logger.info(f"Spectrogram report saved: {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to generate spectrogram report: {str(e)}")
        raise


def _add_spectrogram_slide(
    report_gen: ReportGenerator,
    event_name: str,
    source_id: str,
    channel_name: str,
    time: np.ndarray,
    frequencies: np.ndarray,
    Sxx: np.ndarray,
    config: 'BatchConfig'
) -> None:
    """
    Add a slide with a spectrogram plot.
    
    Parameters:
    -----------
    report_gen : ReportGenerator
        Report generator instance
    event_name : str
        Event name
    source_id : str
        Source identifier
    channel_name : str
        Channel name
    time : np.ndarray
        Time array
    frequencies : np.ndarray
        Frequency array
    Sxx : np.ndarray
        Spectrogram data
    config : BatchConfig
        Batch configuration
    """
    # Create spectrogram plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Convert to dB
    Sxx_dB = 10 * np.log10(Sxx + 1e-12)
    
    # Plot spectrogram
    im = ax.pcolormesh(
        time,
        frequencies,
        Sxx_dB.T,  # Transpose so frequency is on y-axis
        shading='gouraud',
        cmap=config.spectrogram_config.colormap
    )
    
    # Configure plot
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Frequency (Hz)', fontsize=12)
    ax.set_title(f'{event_name} - {source_id}_{channel_name}', fontsize=14, fontweight='bold')
    
    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('PSD (dB)', fontsize=10)
    
    # Apply display settings
    if not config.display_config.spectrogram_auto_scale:
        if config.display_config.spectrogram_time_min and config.display_config.spectrogram_time_max:
            ax.set_xlim(config.display_config.spectrogram_time_min, config.display_config.spectrogram_time_max)
        if config.display_config.spectrogram_freq_min and config.display_config.spectrogram_freq_max:
            ax.set_ylim(config.display_config.spectrogram_freq_min, config.display_config.spectrogram_freq_max)
    
    plt.tight_layout()
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
        temp_path = tmp_file.name
        fig.savefig(temp_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
    
    try:
        # Add slide
        report_gen.add_image_slide(
            title=f"Spectrogram: {event_name}",
            image_path=temp_path
        )
    finally:
        # Clean up
        Path(temp_path).unlink()
