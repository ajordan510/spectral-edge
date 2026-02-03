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
    results: Dict[str, Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray]]]],
    output_path: str,
    config: 'BatchConfig'
) -> None:
    """
    Export batch processing results to Excel file.
    
    Creates an Excel workbook where each event has its own sheet containing
    PSD data for all processed channels.
    
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
        Path to save the Excel file
    config : BatchConfig
        Batch configuration object containing processing parameters
        
    Returns:
    --------
    None
    
    Raises:
    -------
    IOError
        If file cannot be written
        
    Notes:
    ------
    - Each sheet is named after the event
    - First sheet contains a summary of all events and channels
    - PSD data is written in columns: Frequency (Hz), Channel1 PSD, Channel2 PSD, ...
    - Units are included in column headers
    
    Example:
    --------
    >>> results = {
    ...     'liftoff': {
    ...         'flight_0001': {
    ...             'accel_x': (freq_array, psd_array),
    ...         }
    ...     }
    ... }
    >>> export_to_excel(results, 'batch_results.xlsx', config)
    """
    try:
        wb = Workbook()
        
        # Remove default sheet
        if 'Sheet' in wb.sheetnames:
            wb.remove(wb['Sheet'])
        
        # Create summary sheet
        _create_summary_sheet(wb, results, config)
        
        # Create a sheet for each event
        for event_name, event_results in results.items():
            _create_event_sheet(wb, event_name, event_results, config)
        
        # Save workbook
        wb.save(output_path)
        logger.info(f"Excel file saved: {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to export to Excel: {str(e)}")
        raise


def _create_summary_sheet(wb: Workbook, results: Dict, config: 'BatchConfig') -> None:
    """
    Create summary sheet with overview of all events and channels.
    
    Parameters:
    -----------
    wb : Workbook
        Excel workbook object
    results : Dict
        Processing results dictionary
    config : BatchConfig
        Batch configuration
    """
    ws = wb.create_sheet("Summary", 0)
    
    # Title
    ws['A1'] = "Batch PSD Processing Summary"
    ws['A1'].font = Font(size=14, bold=True)
    
    # Configuration info
    row = 3
    ws[f'A{row}'] = "Configuration:"
    ws[f'A{row}'].font = Font(bold=True)
    row += 1
    
    ws[f'A{row}'] = "PSD Method:"
    ws[f'B{row}'] = config.psd_config.method
    row += 1
    
    ws[f'A{row}'] = "Frequency Range:"
    ws[f'B{row}'] = f"{config.psd_config.freq_min} - {config.psd_config.freq_max} Hz"
    row += 1
    
    ws[f'A{row}'] = "Frequency Spacing:"
    ws[f'B{row}'] = config.psd_config.frequency_spacing
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
    for event_name, event_results in results.items():
        ws[f'A{row}'] = event_name
        
        # Count channels
        total_channels = sum(len(channels) for channels in event_results.values())
        ws[f'B{row}'] = total_channels
        
        # List sources
        sources = ", ".join(event_results.keys())
        ws[f'C{row}'] = sources
        
        row += 1
    
    # Adjust column widths
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 20
    ws.column_dimensions['C'].width = 40


def _create_event_sheet(wb: Workbook, event_name: str, event_results: Dict, config: 'BatchConfig') -> None:
    """
    Create a sheet for a specific event with PSD data.
    
    Parameters:
    -----------
    wb : Workbook
        Excel workbook object
    event_name : str
        Name of the event
    event_results : Dict
        Results for this event
    config : BatchConfig
        Batch configuration
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
    
    for source_id, channels in event_results.items():
        for channel_name, (frequencies, psd_values) in channels.items():
            # Use first frequency array as reference
            if all_frequencies is None:
                all_frequencies = frequencies
            
            # Create unique column name
            col_name = f"{source_id}_{channel_name}"
            psd_data[col_name] = psd_values
    
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
            except:
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
