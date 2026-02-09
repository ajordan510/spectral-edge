"""
Input Validation Module for SpectralEdge GUI

This module provides real-time input validation for GUI parameters,
ensuring that user inputs are within valid ranges and providing
visual feedback for invalid values.

Author: SpectralEdge Development Team
"""

from PyQt6.QtWidgets import QWidget, QDoubleSpinBox, QSpinBox
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import pyqtSignal
from typing import Optional, Tuple


class ValidationResult:
    """Result of a validation check."""
    
    def __init__(self, is_valid: bool, message: str = ""):
        """
        Initialize validation result.
        
        Args:
            is_valid: Whether the value is valid
            message: Error message if invalid
        """
        self.is_valid = is_valid
        self.message = message


class ParameterValidator:
    """
    Validates GUI parameter inputs with real-time feedback.
    
    Provides validation for:
    - Overlap percentages (0-99%)
    - Frequency resolution (> 0)
    - Frequency ranges (Min < Max, Max ≤ Nyquist)
    """
    
    def __init__(self):
        """Initialize the parameter validator."""
        self.nyquist_frequency = None  # Set when data is loaded
        self.original_palette = None
        
    def set_nyquist_frequency(self, nyquist_freq: Optional[float]):
        """
        Set the Nyquist frequency for validation.
        
        Args:
            nyquist_freq: Nyquist frequency in Hz (sample_rate / 2)
        """
        self.nyquist_frequency = nyquist_freq
    
    def validate_overlap(self, overlap: float) -> ValidationResult:
        """
        Validate overlap percentage.
        
        Valid range: 0-99% (100% overlap is mathematically invalid)
        
        Args:
            overlap: Overlap percentage
            
        Returns:
            ValidationResult with validation status and message
        """
        if overlap < 0:
            return ValidationResult(False, "Overlap must be non-negative (0-99%)")
        if overlap >= 100:
            return ValidationResult(False, "Overlap must be less than 100%")
        if overlap > 95:
            return ValidationResult(True, "Warning: Very high overlap (>95%) may slow calculations")
        return ValidationResult(True)
    
    def validate_frequency_resolution(self, df: float) -> ValidationResult:
        """
        Validate frequency resolution.
        
        Valid range: > 0 Hz
        
        Args:
            df: Frequency resolution in Hz
            
        Returns:
            ValidationResult with validation status and message
        """
        if df <= 0:
            return ValidationResult(False, "Frequency resolution must be positive")
        if df > 10:
            return ValidationResult(True, "Warning: Large Δf (>10 Hz) may reduce frequency detail")
        if df < 0.01:
            return ValidationResult(True, "Warning: Very small Δf (<0.01 Hz) requires long data segments")
        return ValidationResult(True)
    
    def validate_frequency_range(self, min_freq: float, max_freq: float) -> ValidationResult:
        """
        Validate frequency range.
        
        Requirements:
        - min_freq < max_freq
        - max_freq ≤ Nyquist frequency (if known)
        
        Args:
            min_freq: Minimum frequency in Hz
            max_freq: Maximum frequency in Hz
            
        Returns:
            ValidationResult with validation status and message
        """
        if min_freq < 0:
            return ValidationResult(False, "Minimum frequency must be non-negative")
        if max_freq <= 0:
            return ValidationResult(False, "Maximum frequency must be positive")
        if min_freq >= max_freq:
            return ValidationResult(False, "Minimum frequency must be less than maximum frequency")
        
        if self.nyquist_frequency is not None:
            if max_freq > self.nyquist_frequency:
                return ValidationResult(
                    False, 
                    f"Maximum frequency ({max_freq:.1f} Hz) exceeds Nyquist frequency ({self.nyquist_frequency:.1f} Hz)"
                )
        
        return ValidationResult(True)
    
    def validate_maximax_window(self, window_duration: float, data_duration: Optional[float] = None) -> ValidationResult:
        """
        Validate maximax window duration.
        
        Args:
            window_duration: Window duration in seconds
            data_duration: Total data duration in seconds (optional)
            
        Returns:
            ValidationResult with validation status and message
        """
        if window_duration <= 0:
            return ValidationResult(False, "Maximax window duration must be positive")
        
        if data_duration is not None and window_duration > data_duration:
            return ValidationResult(
                False,
                f"Maximax window ({window_duration:.1f}s) exceeds data duration ({data_duration:.1f}s)"
            )
        
        return ValidationResult(True)
    
    def apply_validation_style(self, widget: QWidget, result: ValidationResult):
        """
        Apply visual styling to widget based on validation result.
        
        Args:
            widget: The widget to style
            result: Validation result
        """
        if self.original_palette is None:
            self.original_palette = widget.palette()
        
        if not result.is_valid:
            # Invalid - red background
            palette = widget.palette()
            palette.setColor(QPalette.ColorRole.Base, QColor(255, 200, 200))  # Light red
            widget.setPalette(palette)
            widget.setToolTip(f"❌ {result.message}")
        elif result.message and result.message.startswith("Warning"):
            # Warning - yellow background
            palette = widget.palette()
            palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 200))  # Light yellow
            widget.setPalette(palette)
            widget.setToolTip(f"⚠️ {result.message}")
        else:
            # Valid - restore original palette
            widget.setPalette(self.original_palette)
            # Keep original tooltip if it exists
            if hasattr(widget, '_original_tooltip'):
                widget.setToolTip(widget._original_tooltip)
    
    def validate_all_parameters(self, params: dict) -> Tuple[bool, list]:
        """
        Validate all parameters at once.
        
        Args:
            params: Dictionary of parameter names and values
            
        Returns:
            Tuple of (all_valid, error_messages)
        """
        errors = []
        
        if 'overlap' in params:
            result = self.validate_overlap(params['overlap'])
            if not result.is_valid:
                errors.append(result.message)
        
        if 'df' in params:
            result = self.validate_frequency_resolution(params['df'])
            if not result.is_valid:
                errors.append(result.message)
        
        if 'min_freq' in params and 'max_freq' in params:
            result = self.validate_frequency_range(params['min_freq'], params['max_freq'])
            if not result.is_valid:
                errors.append(result.message)
        
        if 'maximax_window' in params and params['maximax_window'] is not None:
            data_duration = params.get('data_duration')
            result = self.validate_maximax_window(params['maximax_window'], data_duration)
            if not result.is_valid:
                errors.append(result.message)
        
        return len(errors) == 0, errors
