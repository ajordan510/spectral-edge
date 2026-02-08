#!/usr/bin/env python3
"""
DXD to CSV Converter

Converts DEWESoft DXD/DXZ files to CSV format using pure Python.
No vendor DLLs or external dependencies required (beyond numpy/pandas).

Usage:
    python dxd_to_csv.py input.dxd                    # Single file
    python dxd_to_csv.py input.dxd -o output.csv      # Specify output
    python dxd_to_csv.py *.dxd                        # Multiple files
    python dxd_to_csv.py input.dxd --channels "Ch1,Ch2"  # Specific channels
    python dxd_to_csv.py input.dxd --info             # Show file info only

Author: SpectralEdge Development Team
Date: 2026-02-08
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from typing import List, Optional

from spectral_edge.utils.dxd_loader import DXDLoader, DXDFormatError, is_dxd_file


def convert_dxd_to_csv(
    input_path: str,
    output_path: Optional[str] = None,
    channels: Optional[List[str]] = None,
    include_time: bool = True,
    decimal_places: int = 6,
    verbose: bool = True
) -> str:
    """
    Convert a DXD file to CSV format.

    Parameters:
    -----------
    input_path : str
        Path to the input DXD/DXZ file
    output_path : str, optional
        Path for output CSV file. If None, uses input filename with .csv extension
    channels : List[str], optional
        List of channel names to export. If None, exports all channels
    include_time : bool
        Whether to include time column (default: True)
    decimal_places : int
        Number of decimal places for numeric values (default: 6)
    verbose : bool
        Print progress messages (default: True)

    Returns:
    --------
    str
        Path to the created CSV file
    """
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Determine output path
    if output_path is None:
        output_path = input_path.with_suffix('.csv')
    else:
        output_path = Path(output_path)

    if verbose:
        print(f"Loading DXD file: {input_path.name}")

    # Load DXD file
    with DXDLoader(str(input_path)) as loader:
        available_channels = loader.get_channel_names()

        if verbose:
            print(f"  Found {len(available_channels)} channel(s)")

        # Filter channels if specified
        if channels:
            # Validate requested channels exist
            missing = set(channels) - set(available_channels)
            if missing:
                raise ValueError(f"Channels not found: {missing}")
            channels_to_export = channels
        else:
            channels_to_export = available_channels

        if verbose:
            print(f"  Exporting {len(channels_to_export)} channel(s)")

        # Build dataframe
        data_dict = {}
        sample_rate = None
        max_samples = 0

        for ch_name in channels_to_export:
            time_array, data_array = loader.get_channel_data(ch_name)
            ch_info = loader.get_channel_info(ch_name)

            if sample_rate is None:
                sample_rate = ch_info.sample_rate
                if include_time:
                    data_dict['Time_s'] = time_array

            # Handle channels with different lengths
            if len(data_array) > max_samples:
                max_samples = len(data_array)

            # Create column name with units if available
            if ch_info.units:
                col_name = f"{ch_name}_{ch_info.units}"
            else:
                col_name = ch_name

            data_dict[col_name] = data_array

            if verbose:
                print(f"    {ch_name}: {len(data_array)} samples @ {ch_info.sample_rate:.1f} Hz")

    # Create DataFrame
    df = pd.DataFrame(data_dict)

    # Save to CSV
    if verbose:
        print(f"Writing CSV: {output_path.name}")

    df.to_csv(
        output_path,
        index=False,
        float_format=f'%.{decimal_places}f'
    )

    if verbose:
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  Created: {output_path} ({file_size_mb:.2f} MB)")

    return str(output_path)


def show_file_info(input_path: str) -> None:
    """Display information about a DXD file without converting."""
    input_path = Path(input_path)

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return

    print(f"\nFile: {input_path.name}")
    print("-" * 50)

    try:
        with DXDLoader(str(input_path)) as loader:
            print(f"Channels: {len(loader.channels)}")
            print()

            for name, info in loader.channels.items():
                print(f"  {name}")
                print(f"    Sample Rate: {info.sample_rate:.1f} Hz")
                print(f"    Units: {info.units or 'N/A'}")
                print(f"    Data Type: {info.data_type}")
                if info.description:
                    print(f"    Description: {info.description}")
                print()

    except DXDFormatError as e:
        print(f"Error: Invalid DXD format - {e}")
    except Exception as e:
        print(f"Error: {e}")


def batch_convert(
    input_paths: List[str],
    output_dir: Optional[str] = None,
    channels: Optional[List[str]] = None,
    verbose: bool = True
) -> List[str]:
    """
    Convert multiple DXD files to CSV.

    Parameters:
    -----------
    input_paths : List[str]
        List of input DXD file paths
    output_dir : str, optional
        Directory for output files. If None, uses same directory as input
    channels : List[str], optional
        Channels to export (applied to all files)
    verbose : bool
        Print progress messages

    Returns:
    --------
    List[str]
        List of created CSV file paths
    """
    output_files = []
    errors = []

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    for i, input_path in enumerate(input_paths, 1):
        if verbose:
            print(f"\n[{i}/{len(input_paths)}] Processing: {Path(input_path).name}")

        try:
            if output_dir:
                output_path = output_dir / Path(input_path).with_suffix('.csv').name
            else:
                output_path = None

            csv_path = convert_dxd_to_csv(
                input_path,
                output_path=str(output_path) if output_path else None,
                channels=channels,
                verbose=verbose
            )
            output_files.append(csv_path)

        except Exception as e:
            errors.append((input_path, str(e)))
            if verbose:
                print(f"  Error: {e}")

    if verbose:
        print(f"\n{'=' * 50}")
        print(f"Converted: {len(output_files)}/{len(input_paths)} files")
        if errors:
            print(f"Errors: {len(errors)}")
            for path, err in errors:
                print(f"  {Path(path).name}: {err}")

    return output_files


def main():
    parser = argparse.ArgumentParser(
        description="Convert DEWESoft DXD/DXZ files to CSV format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s measurement.dxd                     Convert single file
  %(prog)s measurement.dxd -o output.csv       Specify output filename
  %(prog)s *.dxd --output-dir ./csv_files      Batch convert to directory
  %(prog)s measurement.dxd --channels "Acc_X,Acc_Y,Acc_Z"
  %(prog)s measurement.dxd --info              Show file info only
        """
    )

    parser.add_argument(
        'input_files',
        nargs='+',
        help='Input DXD/DXZ file(s) to convert'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output CSV file path (for single file conversion)'
    )

    parser.add_argument(
        '--output-dir',
        help='Output directory for batch conversion'
    )

    parser.add_argument(
        '--channels',
        help='Comma-separated list of channel names to export'
    )

    parser.add_argument(
        '--no-time',
        action='store_true',
        help='Exclude time column from output'
    )

    parser.add_argument(
        '--decimal-places',
        type=int,
        default=6,
        help='Number of decimal places for numeric values (default: 6)'
    )

    parser.add_argument(
        '--info',
        action='store_true',
        help='Show file information without converting'
    )

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress progress messages'
    )

    args = parser.parse_args()

    # Parse channels if provided
    channels = None
    if args.channels:
        channels = [ch.strip() for ch in args.channels.split(',')]

    verbose = not args.quiet

    # Info mode
    if args.info:
        for input_file in args.input_files:
            show_file_info(input_file)
        return 0

    # Single file conversion
    if len(args.input_files) == 1 and not args.output_dir:
        try:
            convert_dxd_to_csv(
                args.input_files[0],
                output_path=args.output,
                channels=channels,
                include_time=not args.no_time,
                decimal_places=args.decimal_places,
                verbose=verbose
            )
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    # Batch conversion
    try:
        output_files = batch_convert(
            args.input_files,
            output_dir=args.output_dir,
            channels=channels,
            verbose=verbose
        )
        return 0 if output_files else 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
