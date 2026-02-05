"""
Parameter Presets Module for SpectralEdge GUI

This module provides preset parameter configurations for common use cases,
allowing users to quickly apply standard settings for aerospace testing,
high-resolution analysis, or fast calculations.

Author: SpectralEdge Development Team
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import QComboBox, QMessageBox


class ParameterPreset:
    """A preset configuration for PSD analysis parameters."""
    
    def __init__(self, name: str, description: str, parameters: Dict[str, Any]):
        """
        Initialize a parameter preset.
        
        Args:
            name: Preset name
            description: Description of the preset
            parameters: Dictionary of parameter values
        """
        self.name = name
        self.description = description
        self.parameters = parameters


# Built-in presets
BUILTIN_PRESETS = {
    'aerospace_standard': ParameterPreset(
        name='Aerospace Standard (SMC-S-016)',
        description='Standard aerospace vibration testing per SMC-S-016',
        parameters={
            'window': 'hann',
            'df': 5.0,
            'overlap': 50,
            'maximax_enabled': True,
            'maximax_window': 1.0,
            'maximax_overlap': 50,
            'efficient_fft': False,
            'freq_min': 10.0,
            'freq_max': 3000.0,
        }
    ),
    
    'high_resolution': ParameterPreset(
        name='High Frequency Resolution',
        description='Fine frequency detail for detailed spectral analysis',
        parameters={
            'window': 'hann',
            'df': 0.25,
            'overlap': 75,
            'maximax_enabled': False,
            'maximax_window': 1.0,
            'maximax_overlap': 50,
            'efficient_fft': True,
            'freq_min': 10.0,
            'freq_max': 3000.0,
        }
    ),
    
    'fast_calculation': ParameterPreset(
        name='Fast Calculation',
        description='Quick analysis with reduced frequency resolution',
        parameters={
            'window': 'hann',
            'df': 5.0,
            'overlap': 25,
            'maximax_enabled': False,
            'maximax_window': 1.0,
            'maximax_overlap': 50,
            'efficient_fft': True,
            'freq_min': 10.0,
            'freq_max': 3000.0,
        }
    ),
    
    'low_frequency': ParameterPreset(
        name='Low Frequency Analysis',
        description='Optimized for low-frequency vibration (< 100 Hz)',
        parameters={
            'window': 'hann',
            'df': 0.1,
            'overlap': 66,
            'maximax_enabled': False,
            'maximax_window': 1.0,
            'maximax_overlap': 50,
            'efficient_fft': True,
            'freq_min': 0.1,
            'freq_max': 100.0,
        }
    ),
}


class PresetManager:
    """Manages parameter presets for PSD analysis."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the preset manager.
        
        Args:
            config_dir: Directory for storing custom presets
        """
        if config_dir is None:
            config_dir = Path.home() / '.spectral_edge'
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.presets_file = self.config_dir / 'psd_presets.json'
        
        self.custom_presets = self._load_custom_presets()
    
    def _load_custom_presets(self) -> Dict[str, ParameterPreset]:
        """Load custom presets from file."""
        if not self.presets_file.exists():
            return {}
        
        try:
            with open(self.presets_file, 'r') as f:
                data = json.load(f)
            
            presets = {}
            for key, preset_data in data.items():
                presets[key] = ParameterPreset(
                    name=preset_data['name'],
                    description=preset_data['description'],
                    parameters=preset_data['parameters']
                )
            return presets
        except Exception as e:
            print(f"Error loading custom presets: {e}")
            return {}
    
    def _save_custom_presets(self):
        """Save custom presets to file."""
        try:
            data = {}
            for key, preset in self.custom_presets.items():
                data[key] = {
                    'name': preset.name,
                    'description': preset.description,
                    'parameters': preset.parameters
                }
            
            with open(self.presets_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving custom presets: {e}")
    
    def get_all_presets(self) -> Dict[str, ParameterPreset]:
        """Get all presets (built-in and custom)."""
        all_presets = BUILTIN_PRESETS.copy()
        all_presets.update(self.custom_presets)
        return all_presets
    
    def get_preset(self, key: str) -> Optional[ParameterPreset]:
        """Get a specific preset by key."""
        all_presets = self.get_all_presets()
        return all_presets.get(key)
    
    def save_preset(self, key: str, name: str, description: str, parameters: Dict[str, Any]):
        """
        Save a custom preset.
        
        Args:
            key: Unique key for the preset
            name: Display name
            description: Description
            parameters: Parameter values
        """
        self.custom_presets[key] = ParameterPreset(name, description, parameters)
        self._save_custom_presets()
    
    def delete_preset(self, key: str) -> bool:
        """
        Delete a custom preset.
        
        Args:
            key: Preset key
            
        Returns:
            True if deleted, False if not found or is built-in
        """
        if key in BUILTIN_PRESETS:
            return False  # Can't delete built-in presets
        
        if key in self.custom_presets:
            del self.custom_presets[key]
            self._save_custom_presets()
            return True
        
        return False


def apply_preset_to_window(window, preset: ParameterPreset):
    """
    Apply a preset to the PSD analysis window.
    
    Args:
        window: PSDAnalysisWindow instance
        preset: ParameterPreset to apply
    """
    params = preset.parameters
    
    # Window type
    if 'window' in params and hasattr(window, 'window_combo'):
        window_text = params['window'].capitalize()
        index = window.window_combo.findText(window_text)
        if index >= 0:
            window.window_combo.setCurrentIndex(index)
    
    # Frequency resolution
    if 'df' in params and hasattr(window, 'df_spin'):
        window.df_spin.setValue(params['df'])
    
    # Overlap
    if 'overlap' in params and hasattr(window, 'overlap_spin'):
        window.overlap_spin.setValue(params['overlap'])
    
    # Maximax enabled
    if 'maximax_enabled' in params and hasattr(window, 'maximax_checkbox'):
        window.maximax_checkbox.setChecked(params['maximax_enabled'])
    
    # Maximax window
    if 'maximax_window' in params and hasattr(window, 'maximax_window_spin'):
        window.maximax_window_spin.setValue(params['maximax_window'])
    
    # Maximax overlap
    if 'maximax_overlap' in params and hasattr(window, 'maximax_overlap_spin'):
        window.maximax_overlap_spin.setValue(params['maximax_overlap'])
    
    # Efficient FFT
    if 'efficient_fft' in params and hasattr(window, 'efficient_fft_checkbox'):
        window.efficient_fft_checkbox.setChecked(params['efficient_fft'])
    
    # Frequency range (if using spinboxes)
    if 'freq_min' in params and hasattr(window, 'freq_min_spin'):
        window.freq_min_spin.setValue(params['freq_min'])
    
    if 'freq_max' in params and hasattr(window, 'freq_max_spin'):
        window.freq_max_spin.setValue(params['freq_max'])


def get_current_parameters(window) -> Dict[str, Any]:
    """
    Get current parameter values from the window.
    
    Args:
        window: PSDAnalysisWindow instance
        
    Returns:
        Dictionary of current parameter values
    """
    params = {}
    
    if hasattr(window, 'window_combo'):
        params['window'] = window.window_combo.currentText().lower()
    
    if hasattr(window, 'df_spin'):
        params['df'] = window.df_spin.value()
    
    if hasattr(window, 'overlap_spin'):
        params['overlap'] = window.overlap_spin.value()
    
    if hasattr(window, 'maximax_checkbox'):
        params['maximax_enabled'] = window.maximax_checkbox.isChecked()
    
    if hasattr(window, 'maximax_window_spin'):
        params['maximax_window'] = window.maximax_window_spin.value()
    
    if hasattr(window, 'maximax_overlap_spin'):
        params['maximax_overlap'] = window.maximax_overlap_spin.value()
    
    if hasattr(window, 'efficient_fft_checkbox'):
        params['efficient_fft'] = window.efficient_fft_checkbox.isChecked()
    
    if hasattr(window, 'freq_min_spin'):
        params['freq_min'] = window.freq_min_spin.value()
    
    if hasattr(window, 'freq_max_spin'):
        params['freq_max'] = window.freq_max_spin.value()
    
    return params
