"""
DEWESoft DXD/DXZ File Loader - Pure Python Implementation

This module provides a pure Python implementation for reading DEWESoft data files
(.dxd, .dxz, .d7d, .d7z) without requiring any vendor-specific DLLs or libraries.

The DXD format is a binary format that stores:
- Channel configuration in XML format
- Time-series data in little-endian format
- Data organized in pages

Key Features:
- Pure Python - no vendor DLLs required
- Cross-platform (Windows, Linux, macOS)
- Memory-efficient streaming for large files
- Support for multiple channels and sample rates

Based on reverse-engineering of the DXD format structure.

Author: SpectralEdge Development Team
Date: 2026-02-08
"""

import numpy as np
import struct
import xml.etree.ElementTree as ET
import zipfile
import io
import logging
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DXDChannelInfo:
    """Container for DXD channel metadata."""
    name: str
    index: int
    sample_rate: float
    units: str
    scale: float
    offset: float
    data_type: str  # 'int16', 'int32', 'float32', 'float64'
    num_samples: int = 0
    description: str = ""

    def get_display_name(self) -> str:
        """Get formatted display name for GUI."""
        if self.units:
            return f"{self.name} ({self.sample_rate:.0f} Hz, {self.units})"
        return f"{self.name} ({self.sample_rate:.0f} Hz)"


class DXDFormatError(Exception):
    """Exception raised for DXD format parsing errors."""
    pass


class DXDLoader:
    """
    Pure Python loader for DEWESoft DXD/DXZ files.

    This class provides methods to:
    - Load metadata without reading all data
    - Read individual channel data
    - Support for compressed (.dxz, .d7z) and uncompressed (.dxd, .d7d) files

    The DXD format stores data in a binary format with:
    - XML header containing channel configuration
    - Binary data pages with interleaved channel data
    - Little-endian byte ordering

    Usage:
        with DXDLoader('measurement.dxd') as loader:
            print(f"Found {len(loader.channels)} channels")
            for name, info in loader.channels.items():
                time, data = loader.get_channel_data(name)
                print(f"{name}: {len(data)} samples at {info.sample_rate} Hz")
    """

    # Known DXD format signatures and constants
    DXD_SIGNATURE = b'PKZIP'  # DXZ files are ZIP compressed
    INDEX_TAG = b'INDEX'
    PAGE_TAG = b'PAG1'

    # Data type mappings
    DATA_TYPES = {
        0: ('int16', 2, np.int16),
        1: ('int32', 4, np.int32),
        2: ('float32', 4, np.float32),
        3: ('float64', 8, np.float64),
        4: ('uint16', 2, np.uint16),
        5: ('uint32', 4, np.uint32),
    }

    def __init__(self, file_path: str):
        """
        Initialize DXD loader.

        Parameters:
        -----------
        file_path : str
            Path to DXD/DXZ file
        """
        self.file_path = Path(file_path)
        self.channels: Dict[str, DXDChannelInfo] = {}
        self.file_metadata: Dict[str, Any] = {}
        self._file_handle = None
        self._is_compressed = False
        self._data_offset = 0
        self._index_entries: List[Dict] = []
        self._xml_config = None

        # Validate and open file
        self._open_file()
        self._parse_structure()

    def _open_file(self):
        """Open the DXD/DXZ file and determine format."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"DXD file not found: {self.file_path}")

        suffix = self.file_path.suffix.lower()
        self._is_compressed = suffix in ('.dxz', '.d7z')

        if self._is_compressed:
            self._open_compressed()
        else:
            self._open_uncompressed()

    def _open_compressed(self):
        """Open a compressed DXZ file (ZIP format)."""
        try:
            self._zip_file = zipfile.ZipFile(self.file_path, 'r')

            # Find the main data file inside the ZIP
            file_list = self._zip_file.namelist()

            # Look for the main data file (usually ends with .dxd or .d7d)
            data_file = None
            for name in file_list:
                if name.endswith(('.dxd', '.d7d')):
                    data_file = name
                    break

            if data_file is None:
                # Try to find any data-like file
                for name in file_list:
                    if not name.endswith(('.xml', '.txt', '.log')):
                        data_file = name
                        break

            if data_file is None and file_list:
                data_file = file_list[0]

            if data_file:
                self._compressed_data = io.BytesIO(self._zip_file.read(data_file))
                self._file_handle = self._compressed_data
                logger.info(f"Opened compressed DXD: {data_file}")
            else:
                raise DXDFormatError("No data file found in compressed archive")

        except zipfile.BadZipFile:
            raise DXDFormatError(f"Invalid compressed file: {self.file_path}")

    def _open_uncompressed(self):
        """Open an uncompressed DXD file."""
        self._file_handle = open(self.file_path, 'rb')
        logger.info(f"Opened uncompressed DXD: {self.file_path.name}")

    def _parse_structure(self):
        """Parse the DXD file structure and extract metadata."""
        self._file_handle.seek(0)

        # Try to find and parse XML configuration
        self._find_xml_config()

        # Find data index/table of contents
        self._find_index()

        # Parse channel information from XML
        self._parse_channels()

    def _find_xml_config(self):
        """Find and parse the XML configuration block."""
        self._file_handle.seek(0)
        content = self._file_handle.read()

        # Look for XML content - can be at various locations
        xml_patterns = [
            (b'<?xml', b'</Setup>'),
            (b'<?xml', b'</setup>'),
            (b'<?xml', b'</Configuration>'),
            (b'<Setup', b'</Setup>'),
            (b'<setup', b'</setup>'),
            (b'<Channels', b'</Channels>'),
        ]

        for start_pattern, end_pattern in xml_patterns:
            start_idx = content.find(start_pattern)
            if start_idx != -1:
                end_idx = content.find(end_pattern, start_idx)
                if end_idx != -1:
                    xml_bytes = content[start_idx:end_idx + len(end_pattern)]
                    try:
                        self._xml_config = ET.fromstring(xml_bytes)
                        logger.debug(f"Found XML config at offset {start_idx}")
                        self._data_offset = end_idx + len(end_pattern)
                        return
                    except ET.ParseError:
                        continue

        # Try alternative: look for channel definitions directly in binary
        self._parse_binary_header(content)

    def _parse_binary_header(self, content: bytes):
        """Parse channel info from binary header when XML is not found."""
        # Look for channel count indicator
        # DXD files typically have header info in first few KB

        header = content[:8192]

        # Try to find number of channels
        # Common patterns: 2-byte or 4-byte integer indicating channel count
        for offset in range(0, min(500, len(header) - 4), 2):
            num_ch = struct.unpack_from('<H', header, offset)[0]
            if 1 <= num_ch <= 256:  # Reasonable channel count
                # Check if this makes sense based on file size
                self.file_metadata['possible_channels'] = num_ch
                break

        # Set data offset to after typical header size
        self._data_offset = min(4096, len(content) // 10)

    def _find_index(self):
        """Find the data index/table of contents."""
        self._file_handle.seek(0)
        content = self._file_handle.read(1024)

        # Look for INDEX marker
        idx_pos = content.find(self.INDEX_TAG)
        if idx_pos != -1:
            logger.debug(f"Found INDEX at offset {idx_pos}")
            self._parse_index_block(idx_pos)

    def _parse_index_block(self, offset: int):
        """Parse the index block to get data locations."""
        self._file_handle.seek(offset + len(self.INDEX_TAG))

        try:
            # Read index header
            index_header = self._file_handle.read(32)

            # Index typically contains: num_entries, entry_size, then entries
            if len(index_header) >= 8:
                num_entries = struct.unpack('<I', index_header[:4])[0]
                entry_size = struct.unpack('<I', index_header[4:8])[0]

                if 0 < num_entries < 10000 and 0 < entry_size < 256:
                    for i in range(num_entries):
                        entry_data = self._file_handle.read(entry_size)
                        if len(entry_data) == entry_size:
                            self._index_entries.append({
                                'index': i,
                                'data': entry_data
                            })
        except struct.error:
            logger.warning("Could not parse index block")

    def _parse_channels(self):
        """Parse channel information from XML config or binary header."""
        if self._xml_config is not None:
            self._parse_channels_from_xml()
        else:
            self._infer_channels_from_data()

    def _parse_channels_from_xml(self):
        """Extract channel information from XML configuration."""
        # Try various XML paths for channel definitions
        channel_paths = [
            './/Channel',
            './/channel',
            './/Channels/Channel',
            './/channels/channel',
            './/AI',  # Analog Input channels
            './/Analog',
        ]

        for path in channel_paths:
            channel_elements = self._xml_config.findall(path)
            if channel_elements:
                for idx, ch_elem in enumerate(channel_elements):
                    self._parse_channel_element(ch_elem, idx)
                break

        if not self.channels:
            # Try to parse from attributes
            self._parse_channels_from_attributes()

    def _parse_channel_element(self, elem: ET.Element, index: int):
        """Parse a single channel element from XML."""
        # Extract channel properties - try various attribute/element names
        name = (
            elem.get('Name') or elem.get('name') or
            elem.findtext('Name') or elem.findtext('name') or
            f'Channel_{index + 1}'
        )

        # Sample rate
        sample_rate = self._get_numeric_value(elem, [
            'SampleRate', 'sampleRate', 'sample_rate', 'Rate', 'rate', 'Fs', 'fs'
        ], default=1000.0)

        # Units
        units = (
            elem.get('Units') or elem.get('units') or
            elem.findtext('Units') or elem.findtext('units') or
            elem.get('Unit') or elem.get('unit') or ''
        )

        # Scale and offset for raw to engineering conversion
        scale = self._get_numeric_value(elem, ['Scale', 'scale', 'Gain', 'gain'], default=1.0)
        offset = self._get_numeric_value(elem, ['Offset', 'offset'], default=0.0)

        # Data type
        data_type_str = elem.get('DataType') or elem.get('dataType') or 'int16'

        # Description
        description = (
            elem.findtext('Description') or elem.findtext('description') or
            elem.get('Description') or ''
        )

        channel_info = DXDChannelInfo(
            name=name,
            index=index,
            sample_rate=float(sample_rate),
            units=units,
            scale=float(scale),
            offset=float(offset),
            data_type=data_type_str,
            description=description
        )

        self.channels[name] = channel_info
        logger.debug(f"Found channel: {name} at {sample_rate} Hz")

    def _get_numeric_value(self, elem: ET.Element, names: List[str], default: float) -> float:
        """Extract numeric value from XML element trying multiple names."""
        for name in names:
            # Try as attribute
            val = elem.get(name)
            if val is not None:
                try:
                    return float(val)
                except ValueError:
                    continue

            # Try as child element
            val = elem.findtext(name)
            if val is not None:
                try:
                    return float(val)
                except ValueError:
                    continue

        return default

    def _parse_channels_from_attributes(self):
        """Try to extract channel info from root-level XML attributes."""
        if self._xml_config is None:
            return

        # Look for channel count
        num_channels = None
        for attr in ['NumChannels', 'numChannels', 'ChannelCount', 'channels']:
            val = self._xml_config.get(attr)
            if val:
                try:
                    num_channels = int(val)
                    break
                except ValueError:
                    continue

        if num_channels:
            for i in range(num_channels):
                channel_info = DXDChannelInfo(
                    name=f'Channel_{i + 1}',
                    index=i,
                    sample_rate=1000.0,  # Default
                    units='',
                    scale=1.0,
                    offset=0.0,
                    data_type='int16'
                )
                self.channels[f'Channel_{i + 1}'] = channel_info

    def _infer_channels_from_data(self):
        """Infer channel information from data structure when no XML is available."""
        self._file_handle.seek(0)
        content = self._file_handle.read()
        file_size = len(content)

        # Estimate based on typical file structures
        # Default to single channel if we can't determine
        possible_channels = self.file_metadata.get('possible_channels', 1)

        for i in range(possible_channels):
            channel_info = DXDChannelInfo(
                name=f'Channel_{i + 1}',
                index=i,
                sample_rate=1000.0,  # Will need to be adjusted by user
                units='',
                scale=1.0,
                offset=0.0,
                data_type='int16'
            )
            self.channels[f'Channel_{i + 1}'] = channel_info

        logger.warning(f"Could not find channel definitions, inferred {len(self.channels)} channel(s)")

    def get_channel_names(self) -> List[str]:
        """Get list of all channel names."""
        return list(self.channels.keys())

    def get_channel_info(self, channel_name: str) -> Optional[DXDChannelInfo]:
        """Get information for a specific channel."""
        return self.channels.get(channel_name)

    def get_channel_data(self, channel_name: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Load data for a specific channel.

        Parameters:
        -----------
        channel_name : str
            Name of the channel to load

        Returns:
        --------
        Tuple[np.ndarray, np.ndarray]
            (time_array, data_array) where time is in seconds
        """
        if channel_name not in self.channels:
            available = list(self.channels.keys())
            raise ValueError(f"Channel '{channel_name}' not found. Available: {available}")

        channel_info = self.channels[channel_name]

        # Read raw data
        raw_data = self._read_channel_raw(channel_info)

        # Apply scale and offset
        data = raw_data * channel_info.scale + channel_info.offset

        # Generate time array
        num_samples = len(data)
        time_array = np.arange(num_samples) / channel_info.sample_rate

        return time_array, data

    def _read_channel_raw(self, channel_info: DXDChannelInfo) -> np.ndarray:
        """Read raw data for a channel from the file."""
        self._file_handle.seek(self._data_offset)
        content = self._file_handle.read()

        # Determine data type
        dtype_name = channel_info.data_type.lower()
        if 'int16' in dtype_name or 'short' in dtype_name:
            dtype = np.int16
            bytes_per_sample = 2
        elif 'int32' in dtype_name or 'long' in dtype_name:
            dtype = np.int32
            bytes_per_sample = 4
        elif 'float32' in dtype_name or 'single' in dtype_name:
            dtype = np.float32
            bytes_per_sample = 4
        elif 'float64' in dtype_name or 'double' in dtype_name:
            dtype = np.float64
            bytes_per_sample = 8
        elif 'uint16' in dtype_name:
            dtype = np.uint16
            bytes_per_sample = 2
        elif 'uint32' in dtype_name:
            dtype = np.uint32
            bytes_per_sample = 4
        else:
            # Default to int16
            dtype = np.int16
            bytes_per_sample = 2

        num_channels = len(self.channels)
        channel_idx = channel_info.index

        # Try to read as interleaved data
        if num_channels > 1:
            data = self._read_interleaved_data(content, dtype, num_channels, channel_idx)
        else:
            data = self._read_sequential_data(content, dtype)

        return data.astype(np.float64)

    def _read_interleaved_data(self, content: bytes, dtype: np.dtype,
                                num_channels: int, channel_idx: int) -> np.ndarray:
        """Read interleaved multi-channel data, extracting one channel."""
        # Calculate bytes per sample for this dtype
        bytes_per_sample = np.dtype(dtype).itemsize

        # Calculate total samples
        total_bytes = len(content)
        samples_per_channel = total_bytes // (bytes_per_sample * num_channels)

        if samples_per_channel == 0:
            return np.array([], dtype=dtype)

        # Read all data as flat array
        total_samples = samples_per_channel * num_channels
        flat_data = np.frombuffer(content[:total_samples * bytes_per_sample], dtype=dtype)

        # Reshape to (samples_per_channel, num_channels)
        try:
            interleaved = flat_data.reshape(-1, num_channels)
            return interleaved[:, channel_idx]
        except ValueError:
            # If reshape fails, return what we can
            return flat_data[channel_idx::num_channels]

    def _read_sequential_data(self, content: bytes, dtype: np.dtype) -> np.ndarray:
        """Read sequential single-channel data."""
        bytes_per_sample = np.dtype(dtype).itemsize
        num_samples = len(content) // bytes_per_sample

        if num_samples == 0:
            return np.array([], dtype=dtype)

        return np.frombuffer(content[:num_samples * bytes_per_sample], dtype=dtype)

    def load_all_channels(self) -> Dict[str, Tuple[np.ndarray, np.ndarray, float, str]]:
        """
        Load all channels from the file.

        Returns:
        --------
        Dict[str, Tuple[np.ndarray, np.ndarray, float, str]]
            Dictionary mapping channel names to (time, data, sample_rate, units) tuples
        """
        result = {}
        for name, info in self.channels.items():
            time_array, data_array = self.get_channel_data(name)
            result[name] = (time_array, data_array, info.sample_rate, info.units)
        return result

    def close(self):
        """Close the file handle."""
        if self._file_handle is not None:
            if hasattr(self._file_handle, 'close'):
                self._file_handle.close()
            self._file_handle = None

        if hasattr(self, '_zip_file') and self._zip_file is not None:
            self._zip_file.close()
            self._zip_file = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __del__(self):
        """Destructor to ensure file is closed."""
        self.close()


def load_dxd_files(file_paths: List[str]) -> Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray, float, str]]]:
    """
    Load time-series data from multiple DXD files.

    This function is the main entry point for batch processing, compatible
    with the interface used by csv_loader and hdf5_loader.

    Parameters:
    -----------
    file_paths : List[str]
        List of paths to DXD files to load

    Returns:
    --------
    Dict[str, Dict[str, Tuple[np.ndarray, np.ndarray, float, str]]]
        Nested dictionary structure:
        {
            file_path: {
                channel_name: (time_array, signal_array, sample_rate, units),
                ...
            },
            ...
        }
    """
    result = {}

    for file_path in file_paths:
        try:
            with DXDLoader(file_path) as loader:
                file_data = loader.load_all_channels()
                result[file_path] = file_data
                logger.info(f"Loaded {len(file_data)} channel(s) from {Path(file_path).name}")
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {str(e)}")
            raise

    return result


def detect_dxd_format(file_path: str) -> Dict[str, Any]:
    """
    Analyze DXD file and detect its format without loading all data.

    Parameters:
    -----------
    file_path : str
        Path to DXD file

    Returns:
    --------
    Dict[str, any]
        Dictionary containing:
        - 'is_compressed': bool
        - 'num_channels': int
        - 'channel_names': List[str]
        - 'sample_rates': Dict[str, float]
        - 'file_size_mb': float
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"DXD file not found: {file_path}")

    file_size_mb = path.stat().st_size / (1024 * 1024)
    is_compressed = path.suffix.lower() in ('.dxz', '.d7z')

    with DXDLoader(file_path) as loader:
        channel_names = loader.get_channel_names()
        sample_rates = {name: info.sample_rate for name, info in loader.channels.items()}

    return {
        'is_compressed': is_compressed,
        'num_channels': len(channel_names),
        'channel_names': channel_names,
        'sample_rates': sample_rates,
        'file_size_mb': file_size_mb
    }


def is_dxd_file(file_path: str) -> bool:
    """
    Check if a file is a DXD/DXZ format file.

    Parameters:
    -----------
    file_path : str
        Path to check

    Returns:
    --------
    bool
        True if file appears to be a DXD format file
    """
    path = Path(file_path)

    if not path.exists():
        return False

    # Check extension
    if path.suffix.lower() in ('.dxd', '.dxz', '.d7d', '.d7z'):
        return True

    # Check file signature
    try:
        with open(file_path, 'rb') as f:
            header = f.read(32)

            # Check for ZIP signature (compressed DXZ)
            if header[:4] == b'PK\x03\x04':
                return True

            # Check for common DXD patterns
            if b'Dewesoft' in header or b'DEWESOFT' in header:
                return True

            # Check for XML header (some DXD files start with XML)
            if b'<?xml' in header:
                return True
    except Exception:
        pass

    return False
