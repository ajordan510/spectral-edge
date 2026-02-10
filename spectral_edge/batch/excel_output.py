"""
Excel Output Module for Batch Processing

This module handles exporting batch PSD processing results to Excel format.
Each event is written to a separate sheet with PSD data and summary statistics.

Author: SpectralEdge Development Team
Date: 2026-02-02
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import logging
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows

logger = logging.getLogger(__name__)


def export_to_excel(
    result: 'BatchProcessingResult',
    output_directory: str,
    config: 'BatchConfig',
    filename: str = "batch_psd_results.xlsx"
) -> str:
    """
    Export batch processing results to Excel file.
    
    Creates an Excel workbook where each event has its own sheet containing
    PSD data for all processed channels.
    
    Parameters:
    -----------
    result : BatchProcessingResult
        Batch processing result object containing channel_results
    output_directory : str
        Directory to save the Excel file
    config : BatchConfig
        Batch configuration object (for spacing conversion)
    filename : str, optional
        Name of the Excel file (default: "batch_psd_results.xlsx")
        
    Returns:
    --------
    str
        Full path to the saved Excel file
    
    Raises:
    -------
    IOError
        If file cannot be written
    """
    try:
        output_path = str(Path(output_directory) / filename)
        wb = Workbook()
        
        # Remove default sheet
        if 'Sheet' in wb.sheetnames:
            wb.remove(wb['Sheet'])
        
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
        
        # Create summary sheet
        _create_summary_sheet(wb, events_data, result, config)
        
        # Create a sheet for each event
        for event_name, event_results in events_data.items():
            _create_event_sheet(wb, event_name, event_results)
        
        # Save workbook
        wb.save(output_path)
        logger.info(f"Excel file saved: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Failed to export to Excel: {str(e)}")
        raise


def _create_summary_sheet(wb: Workbook, events_data: Dict, result: 'BatchProcessingResult', config: 'BatchConfig') -> None:
    """
    Create summary sheet with overview of all events and channels.
    
    Parameters:
    -----------
    wb : Workbook
        Excel workbook object
    events_data : Dict
        Reorganized events data
    result : BatchProcessingResult
        Batch processing result object
    """
    ws = wb.create_sheet("Summary", 0)
    
    # Title
    ws['A1'] = "Batch PSD Processing Summary"
    ws['A1'].font = Font(size=14, bold=True)
    
    # Processing info
    row = 3
    ws[f'A{row}'] = "Processing Summary:"
    ws[f'A{row}'].font = Font(bold=True)
    row += 1

    run_time = result.start_time.strftime("%Y-%m-%d %H:%M:%S") if result.start_time else ""
    ws[f'A{row}'] = "Run Timestamp:"
    ws[f'B{row}'] = run_time
    row += 1

    source_files = ", ".join([Path(p).name for p in config.source_files]) if config.source_files else ""
    ws[f'A{row}'] = "Source Files:"
    ws[f'B{row}'] = source_files
    row += 1

    ws[f'A{row}'] = "Total Channels:"
    ws[f'B{row}'] = len(result.channel_results)
    row += 1
    
    ws[f'A{row}'] = "Total Events:"
    ws[f'B{row}'] = len(events_data)
    row += 1
    
    ws[f'A{row}'] = "Errors:"
    ws[f'B{row}'] = len(result.errors)
    row += 1
    
    ws[f'A{row}'] = "Warnings:"
    ws[f'B{row}'] = len(result.warnings)
    row += 2

    ws[f'A{row}'] = "Processing Parameters:"
    ws[f'A{row}'].font = Font(bold=True)
    row += 1
    ws[f'A{row}'] = "PSD Method:"
    ws[f'B{row}'] = config.psd_config.method
    row += 1
    ws[f'A{row}'] = "Window:"
    ws[f'B{row}'] = config.psd_config.window
    row += 1
    ws[f'A{row}'] = "df (Hz):"
    ws[f'B{row}'] = config.psd_config.desired_df
    row += 1
    ws[f'A{row}'] = "Overlap (%):"
    ws[f'B{row}'] = config.psd_config.overlap_percent
    row += 1
    ws[f'A{row}'] = "Efficient FFT:"
    ws[f'B{row}'] = "On" if config.psd_config.use_efficient_fft else "Off"
    row += 1
    ws[f'A{row}'] = "Frequency Spacing:"
    ws[f'B{row}'] = config.psd_config.frequency_spacing
    row += 1
    if config.filter_config.enabled:
        if config.filter_config.filter_type == "lowpass":
            filt_desc = f"Lowpass @ {config.filter_config.cutoff_high} Hz"
        elif config.filter_config.filter_type == "highpass":
            filt_desc = f"Highpass @ {config.filter_config.cutoff_low} Hz"
        else:
            filt_desc = f"Bandpass {config.filter_config.cutoff_low}-{config.filter_config.cutoff_high} Hz"
    else:
        filt_desc = "None"
    ws[f'A{row}'] = "Filter:"
    ws[f'B{row}'] = filt_desc
    row += 2
    
    # Events summary
    ws[f'A{row}'] = "Events Processed:"
    ws[f'A{row}'].font = Font(bold=True)
    row += 1
    
    # Create table header
    ws[f'A{row}'] = "Event Name"
    ws[f'B{row}'] = "Channels Processed"
    ws[f'C{row}'] = "Sources"
    
    for cell in [ws[f'A{row}'], ws[f'B{row}'], ws[f'C{row}']]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
    
    row += 1
    
    # Fill in event data
    for event_name, event_results in events_data.items():
        ws[f'A{row}'] = event_name
        
        # Count channels
        total_channels = len(event_results)
        ws[f'B{row}'] = total_channels
        
        # List channel IDs
        channels = ", ".join(list(event_results.keys())[:5])  # Show first 5
        if len(event_results) > 5:
            channels += "..."
        ws[f'C{row}'] = channels
        
        row += 1
    
    # Adjust column widths
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 40

    # RMS summary table
    row += 1
    ws[f'A{row}'] = "RMS Summary:"
    ws[f'A{row}'].font = Font(bold=True)
    row += 1
    headers = ["Flight", "Channel", "Event", "RMS", "3-Sigma RMS"]
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        cell.alignment = Alignment(horizontal='center')
    row += 1

    for (flight_key, channel_key), event_dict in result.channel_results.items():
        for event_name, event_result in event_dict.items():
            rms_value = event_result.get('metadata', {}).get('rms')
            ws.cell(row=row, column=1, value=flight_key)
            ws.cell(row=row, column=2, value=channel_key)
            ws.cell(row=row, column=3, value=event_name)
            ws.cell(row=row, column=4, value=None if rms_value is None else float(rms_value))
            ws.cell(row=row, column=5, value=None if rms_value is None else float(3.0 * rms_value))
            row += 1


def _create_event_sheet(wb: Workbook, event_name: str, event_results: Dict) -> None:
    """
    Create a sheet for a specific event with PSD data.
    
    Parameters:
    -----------
    wb : Workbook
        Excel workbook object
    event_name : str
        Name of the event
    event_results : Dict
        Results for this event (channel_id -> {frequencies, psd, metadata})
    """
    # Clean sheet name (Excel has restrictions)
    sheet_name = event_name[:31]  # Max 31 characters
    ws = wb.create_sheet(sheet_name)
    
    # Title
    ws['A1'] = f"Event: {event_name}"
    ws['A1'].font = Font(size=12, bold=True)
    
    # Collect all PSD data
    all_frequencies = None
    psd_data = {}
    frequency_mismatch_warned = False

    for channel_id, result_data in event_results.items():
        frequencies = result_data['frequencies']
        psd_values = result_data['psd']

        # Use first frequency array as reference
        if all_frequencies is None:
            all_frequencies = frequencies
        else:
            # Validate that frequency arrays match
            if len(frequencies) != len(all_frequencies):
                if not frequency_mismatch_warned:
                    logger.warning(
                        f"Event '{event_name}': Frequency array length mismatch. "
                        f"Reference has {len(all_frequencies)} points, "
                        f"channel {channel_id} has {len(frequencies)} points. "
                        f"Using reference frequencies - some channels may be misaligned."
                    )
                    frequency_mismatch_warned = True
                # Truncate or pad PSD values to match reference length
                if len(psd_values) > len(all_frequencies):
                    psd_values = psd_values[:len(all_frequencies)]
                elif len(psd_values) < len(all_frequencies):
                    # Pad with NaN
                    padded = np.full(len(all_frequencies), np.nan)
                    padded[:len(psd_values)] = psd_values
                    psd_values = padded

        # Use channel_id as column name
        psd_data[channel_id] = psd_values

    if all_frequencies is None:
        logger.warning(f"No data for event: {event_name}")
        return
    
    # Create DataFrame
    df = pd.DataFrame(psd_data)
    df.insert(0, 'Frequency (Hz)', all_frequencies)
    
    # Write to sheet starting at row 3
    for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), start=3):
        for c_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            
            # Format header row
            if r_idx == 3:
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
                cell.alignment = Alignment(horizontal='center')
    
    # Adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except (TypeError, AttributeError):
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width


def export_psd_to_csv(
    results: Dict[str, Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray]]]],
    output_directory: str
) -> List[str]:
    """
    Export each event's PSD data to separate CSV files.
    
    Parameters:
    -----------
    results : Dict
        Batch processing results
    output_directory : str
        Directory to save CSV files
        
    Returns:
    --------
    List[str]
        List of created file paths
        
    Notes:
    ------
    - One CSV file per event
    - File naming: {event_name}_psd.csv
    - Format: Frequency (Hz), Channel1 PSD, Channel2 PSD, ...
    """
    output_dir = Path(output_directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    created_files = []
    
    for event_name, event_results in results.items():
        # Collect all PSD data
        all_frequencies = None
        psd_data = {}
        
        for source_id, channels in event_results.items():
            for channel_name, (frequencies, psd_values) in channels.items():
                if all_frequencies is None:
                    all_frequencies = frequencies
                
                col_name = f"{source_id}_{channel_name}"
                psd_data[col_name] = psd_values
        
        if all_frequencies is None:
            continue
        
        # Create DataFrame
        df = pd.DataFrame(psd_data)
        df.insert(0, 'Frequency (Hz)', all_frequencies)
        
        # Save to CSV
        csv_path = output_dir / f"{event_name}_psd.csv"
        df.to_csv(csv_path, index=False)
        created_files.append(str(csv_path))
        logger.info(f"CSV file saved: {csv_path}")
    
    return created_files
