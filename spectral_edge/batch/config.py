"""
Batch Processing Configuration Module

This module handles configuration management for batch PSD processing operations.
Configurations can be saved to and loaded from JSON files to ensure consistent
batch processing runs.

Author: SpectralEdge Development Team
Date: 2026-02-02
"""

import json
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime


@dataclass
class FilterConfig:
    """Configuration for signal filtering."""
    
    enabled: bool = False
    filter_type: str = "lowpass"  # lowpass, highpass, bandpass
    filter_design: str = "butterworth"  # butterworth, chebyshev, bessel
    filter_order: int = 4
    cutoff_low: Optional[float] = None
    cutoff_high: Optional[float] = None
    
    def validate(self):
        """
        Validate filter configuration parameters.
        
        Raises:
        -------
        ValueError
            If configuration parameters are invalid
        """
        if not self.enabled:
            return
            
        if self.filter_type not in ["lowpass", "highpass", "bandpass"]:
            raise ValueError(f"Invalid filter_type: {self.filter_type}")
            
        if self.filter_design not in ["butterworth", "chebyshev", "bessel"]:
            raise ValueError(f"Invalid filter_design: {self.filter_design}")
            
        if self.filter_order < 1 or self.filter_order > 10:
            raise ValueError(f"Invalid filter_order: {self.filter_order}")
            
        if self.filter_type in ["lowpass", "bandpass"] and self.cutoff_high is None:
            raise ValueError(f"{self.filter_type} requires cutoff_high")
            
        if self.filter_type in ["highpass", "bandpass"] and self.cutoff_low is None:
            raise ValueError(f"{self.filter_type} requires cutoff_low")


@dataclass
class PSDConfig:
    """Configuration for PSD calculation parameters."""
    
    method: str = "welch"  # welch or maximax
    window: str = "hann"
    overlap_percent: float = 50.0
    use_efficient_fft: bool = True
    desired_df: float = 1.0
    freq_min: float = 20.0
    freq_max: float = 2000.0
    remove_running_mean: bool = True
    frequency_spacing: str = "linear"  # linear or octave
    
    def validate(self):
        """
        Validate PSD configuration parameters.
        
        Raises:
        -------
        ValueError
            If configuration parameters are invalid
        """
        if self.method not in ["welch", "maximax"]:
            raise ValueError(f"Invalid method: {self.method}")
            
        if self.window not in ["hann", "hamming", "blackman", "bartlett"]:
            raise ValueError(f"Invalid window: {self.window}")
            
        if not 0 <= self.overlap_percent < 100:
            raise ValueError(f"Invalid overlap_percent: {self.overlap_percent}")
            
        if self.desired_df <= 0:
            raise ValueError(f"Invalid desired_df: {self.desired_df}")
            
        if self.freq_min >= self.freq_max:
            raise ValueError("freq_min must be less than freq_max")
            
        if self.frequency_spacing not in ["linear", "octave"]:
            raise ValueError(f"Invalid frequency_spacing: {self.frequency_spacing}")


@dataclass
class SpectrogramConfig:
    """Configuration for spectrogram generation."""
    
    enabled: bool = False
    desired_df: float = 1.0
    overlap_percent: float = 50.0
    use_efficient_fft: bool = True
    snr_threshold: float = 20.0
    freq_min: float = 20.0
    freq_max: float = 2000.0
    colormap: str = "viridis"
    
    def validate(self):
        """
        Validate spectrogram configuration parameters.
        
        Raises:
        -------
        ValueError
            If configuration parameters are invalid
        """
        if not self.enabled:
            return
            
        if self.desired_df <= 0:
            raise ValueError(f"Invalid desired_df: {self.desired_df}")
            
        if not 0 <= self.overlap_percent < 100:
            raise ValueError(f"Invalid overlap_percent: {self.overlap_percent}")
            
        if self.freq_min >= self.freq_max:
            raise ValueError("freq_min must be less than freq_max")


@dataclass
class OutputConfig:
    """Configuration for output generation."""
    
    excel_enabled: bool = True
    powerpoint_enabled: bool = True
    pdf_enabled: bool = False
    hdf5_writeback_enabled: bool = True
    output_directory: str = ""
    
    def validate(self):
        """
        Validate output configuration parameters.
        
        Raises:
        -------
        ValueError
            If configuration parameters are invalid
        """
        if not any([self.excel_enabled, self.powerpoint_enabled, 
                    self.pdf_enabled, self.hdf5_writeback_enabled]):
            raise ValueError("At least one output format must be enabled")
            
        if self.output_directory and not Path(self.output_directory).exists():
            raise ValueError(f"Output directory does not exist: {self.output_directory}")


@dataclass
class EventDefinition:
    """Definition of a time-based event for processing."""
    
    name: str
    start_time: float
    end_time: float
    description: str = ""
    
    def validate(self):
        """
        Validate event definition.
        
        Raises:
        -------
        ValueError
            If event parameters are invalid
        """
        if not self.name:
            raise ValueError("Event name cannot be empty")
            
        if self.start_time >= self.end_time:
            raise ValueError(f"Event {self.name}: start_time must be less than end_time")
            
        if self.start_time < 0:
            raise ValueError(f"Event {self.name}: start_time cannot be negative")


@dataclass
class BatchConfig:
    """
    Complete configuration for a batch PSD processing run.
    
    This class encapsulates all parameters needed to perform a batch processing
    operation, including data source, processing parameters, and output options.
    """
    
    # Data source
    source_type: str = "hdf5"  # hdf5 or csv
    source_files: List[str] = field(default_factory=list)
    
    # Channel selection (for HDF5)
    selected_channels: List[tuple] = field(default_factory=list)  # [(flight_key, channel_key), ...]
    
    # Event definitions
    events: List[EventDefinition] = field(default_factory=list)
    process_full_duration: bool = True
    
    # Processing configurations
    filter_config: FilterConfig = field(default_factory=FilterConfig)
    psd_config: PSDConfig = field(default_factory=PSDConfig)
    spectrogram_config: SpectrogramConfig = field(default_factory=SpectrogramConfig)
    output_config: OutputConfig = field(default_factory=OutputConfig)
    
    # Metadata
    config_name: str = ""
    created_timestamp: str = ""
    modified_timestamp: str = ""
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        if not self.created_timestamp:
            self.created_timestamp = datetime.now().isoformat()
        if not self.modified_timestamp:
            self.modified_timestamp = self.created_timestamp
    
    def validate(self):
        """
        Validate the complete batch configuration.
        
        Raises:
        -------
        ValueError
            If any configuration parameters are invalid
        """
        # Validate source
        if self.source_type not in ["hdf5", "csv"]:
            raise ValueError(f"Invalid source_type: {self.source_type}")
            
        if not self.source_files:
            raise ValueError("No source files specified")
            
        for file_path in self.source_files:
            if not Path(file_path).exists():
                raise ValueError(f"Source file does not exist: {file_path}")
        
        # Validate HDF5-specific requirements
        if self.source_type == "hdf5" and not self.selected_channels:
            raise ValueError("No channels selected for HDF5 source")
        
        # Validate events
        for event in self.events:
            event.validate()
        
        # Validate sub-configurations
        self.filter_config.validate()
        self.psd_config.validate()
        self.spectrogram_config.validate()
        self.output_config.validate()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
        --------
        dict
            Configuration as dictionary
        """
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchConfig':
        """
        Create configuration from dictionary.
        
        Parameters:
        -----------
        data : dict
            Configuration dictionary
            
        Returns:
        --------
        BatchConfig
            Configuration object
        """
        # Convert nested dictionaries to dataclass instances
        if 'filter_config' in data and isinstance(data['filter_config'], dict):
            data['filter_config'] = FilterConfig(**data['filter_config'])
            
        if 'psd_config' in data and isinstance(data['psd_config'], dict):
            data['psd_config'] = PSDConfig(**data['psd_config'])
            
        if 'spectrogram_config' in data and isinstance(data['spectrogram_config'], dict):
            data['spectrogram_config'] = SpectrogramConfig(**data['spectrogram_config'])
            
        if 'output_config' in data and isinstance(data['output_config'], dict):
            data['output_config'] = OutputConfig(**data['output_config'])
            
        if 'events' in data and isinstance(data['events'], list):
            data['events'] = [EventDefinition(**e) if isinstance(e, dict) else e 
                            for e in data['events']]
        
        return cls(**data)
    
    def save(self, file_path: str):
        """
        Save configuration to JSON file.
        
        Parameters:
        -----------
        file_path : str
            Path to save configuration file
        """
        self.modified_timestamp = datetime.now().isoformat()
        
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, file_path: str) -> 'BatchConfig':
        """
        Load configuration from JSON file.
        
        Parameters:
        -----------
        file_path : str
            Path to configuration file
            
        Returns:
        --------
        BatchConfig
            Loaded configuration object
        """
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        return cls.from_dict(data)
