"""
CSV Output Module for Batch Processing

This module handles exporting batch PSD processing results to CSV format.
Each event is written to a separate CSV file with PSD data for all channels.

Author: SpectralEdge Development Team
Date: 2026-02-04
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)


def export_to_csv(
    result: 'BatchProcessingResult',
    output_directory: str
) -> List[str]:
    """
    Export batch processing results to CSV files.

    Creates one CSV file per event containing PSD data for all processed channels.

    Parameters:
    -----------
    result : BatchProcessingResult
        Batch processing result object containing channel_results
    output_directory : str
        Directory to save the CSV files

    Returns:
    --------
    List[str]
        List of paths to the saved CSV files

    Raises:
    -------
    IOError
        If files cannot be written
    """
    try:
        output_dir = Path(output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        created_files = []

        # Reorganize results by event
        events_data = {}
        for (flight_key, channel_key), event_dict in result.channel_results.items():
            for event_name, event_result in event_dict.items():
                if event_name not in events_data:
                    events_data[event_name] = {}
                channel_id = f"{flight_key}_{channel_key}"
                events_data[event_name][channel_id] = {
                    'frequencies': event_result['frequencies'],
                    'psd': event_result['psd'],
                    'metadata': event_result['metadata']
                }

        # Create a CSV file for each event
        for event_name, event_results in events_data.items():
            csv_path = _create_event_csv(output_dir, event_name, event_results)
            if csv_path:
                created_files.append(csv_path)

        logger.info(f"CSV export complete: {len(created_files)} files created")
        return created_files

    except Exception as e:
        logger.error(f"Failed to export to CSV: {str(e)}")
        raise


def _create_event_csv(
    output_dir: Path,
    event_name: str,
    event_results: dict
) -> str:
    """
    Create a CSV file for a specific event with PSD data.

    Parameters:
    -----------
    output_dir : Path
        Output directory path
    event_name : str
        Name of the event
    event_results : dict
        Results for this event (channel_id -> {frequencies, psd, metadata})

    Returns:
    --------
    str
        Path to the created CSV file, or None if no data
    """
    # Collect all PSD data
    all_frequencies = None
    psd_data = {}

    for channel_id, result_data in event_results.items():
        frequencies = result_data['frequencies']
        psd_values = result_data['psd']

        # Use first frequency array as reference
        if all_frequencies is None:
            all_frequencies = frequencies
        else:
            # Handle frequency array length mismatch
            if len(psd_values) > len(all_frequencies):
                psd_values = psd_values[:len(all_frequencies)]
            elif len(psd_values) < len(all_frequencies):
                padded = np.full(len(all_frequencies), np.nan)
                padded[:len(psd_values)] = psd_values
                psd_values = padded

        psd_data[channel_id] = psd_values

    if all_frequencies is None:
        logger.warning(f"No data for event: {event_name}")
        return None

    # Create DataFrame
    df = pd.DataFrame(psd_data)
    df.insert(0, 'Frequency_Hz', all_frequencies)

    # Clean filename
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in event_name)
    csv_path = output_dir / f"{safe_name}_psd.csv"

    # Save to CSV
    df.to_csv(csv_path, index=False)
    logger.info(f"CSV file saved: {csv_path}")

    return str(csv_path)
