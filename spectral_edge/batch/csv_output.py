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
from typing import List, Optional
import logging

from spectral_edge.batch.output_utils import sanitize_filename_component as _sanitize_filename_component

logger = logging.getLogger(__name__)


def export_to_csv(
    result: 'BatchProcessingResult',
    output_directory: str,
    config: 'BatchConfig'
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
    config : BatchConfig
        Batch configuration object (for spacing conversion)

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
        from spectral_edge.batch.output_psd import apply_frequency_spacing

        events_data = {}
        for (flight_key, channel_key), event_dict in result.channel_results.items():
            for event_name, event_result in event_dict.items():
                if event_name not in events_data:
                    events_data[event_name] = {}
                channel_id = f"{flight_key}_{channel_key}"
                frequencies_out, psd_out = apply_frequency_spacing(
                    event_result['frequencies'],
                    event_result['psd'],
                    config.psd_config
                )
                events_data[event_name][channel_id] = {
                    'frequencies': frequencies_out,
                    'psd': psd_out,
                    'metadata': event_result['metadata']
                }

        filename_prefix = _sanitize_filename_component(
            getattr(config.output_config, "filename_prefix", "")
        )

        # Create a CSV file for each event
        for event_name, event_results in events_data.items():
            csv_path = _create_event_csv(
                output_dir,
                event_name,
                event_results,
                filename_prefix=filename_prefix,
            )
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
    event_results: dict,
    filename_prefix: str = "",
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
    merged_df = None
    for channel_id, result_data in event_results.items():
        frequencies = np.asarray(result_data['frequencies'])
        psd_values = np.asarray(result_data['psd'])
        if frequencies.size == 0 or psd_values.size == 0:
            continue
        length = min(frequencies.size, psd_values.size)
        channel_df = pd.DataFrame(
            {
                "Frequency_Hz": frequencies[:length],
                channel_id: psd_values[:length],
            }
        ).drop_duplicates(subset=["Frequency_Hz"], keep="first")
        if merged_df is None:
            merged_df = channel_df
        else:
            merged_df = merged_df.merge(channel_df, on="Frequency_Hz", how="outer")

    if merged_df is None or merged_df.empty:
        logger.warning(f"No data for event: {event_name}")
        return None

    merged_df = merged_df.sort_values("Frequency_Hz").reset_index(drop=True)

    # Clean filename
    safe_name = _sanitize_filename_component(event_name) or "event"
    prefix = _sanitize_filename_component(filename_prefix)
    file_name = f"{safe_name}_psd.csv" if not prefix else f"{prefix}_{safe_name}_psd.csv"
    csv_path = output_dir / file_name

    # Save to CSV
    merged_df.to_csv(csv_path, index=False)
    logger.info(f"CSV file saved: {csv_path}")

    return str(csv_path)
