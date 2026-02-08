"""
Core Parameter Validation Module

This module provides GUI-independent validation for PSD and signal processing
parameters. It can be used by both the GUI and batch processing components.

The validation functions return standardized ValidationResult objects that
include:
- Whether the value is valid
- Error or warning messages
- Severity level (error, warning, info)

Author: SpectralEdge Development Team
Date: 2026-02-08
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity level for validation messages."""
    OK = "ok"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationResult:
    """
    Result of a parameter validation check.

    Attributes:
        is_valid: Whether the parameter value is acceptable
        severity: Severity level of any issues found
        message: Human-readable message describing the issue
        details: Optional dict with additional context
    """
    is_valid: bool
    severity: ValidationSeverity = ValidationSeverity.OK
    message: str = ""
    details: Optional[Dict[str, Any]] = None

    @classmethod
    def ok(cls) -> 'ValidationResult':
        """Create a successful validation result."""
        return cls(is_valid=True, severity=ValidationSeverity.OK)

    @classmethod
    def warning(cls, message: str, details: Optional[Dict] = None) -> 'ValidationResult':
        """Create a warning result (valid but with concerns)."""
        return cls(
            is_valid=True,
            severity=ValidationSeverity.WARNING,
            message=message,
            details=details
        )

    @classmethod
    def error(cls, message: str, details: Optional[Dict] = None) -> 'ValidationResult':
        """Create an error result (invalid value)."""
        return cls(
            is_valid=False,
            severity=ValidationSeverity.ERROR,
            message=message,
            details=details
        )


class PSDParameterValidator:
    """
    Validates PSD calculation parameters.

    This class provides validation for all PSD-related parameters used in
    both GUI and batch processing. It is GUI-independent and can be used
    anywhere in the application.

    Example:
        validator = PSDParameterValidator(sample_rate=10000.0)
        result = validator.validate_frequency_resolution(df=1.0)
        if not result.is_valid:
            print(f"Error: {result.message}")
    """

    def __init__(self, sample_rate: Optional[float] = None):
        """
        Initialize the validator.

        Args:
            sample_rate: Sample rate in Hz (optional, enables Nyquist checks)
        """
        self.sample_rate = sample_rate

    @property
    def nyquist_frequency(self) -> Optional[float]:
        """Get Nyquist frequency if sample rate is set."""
        if self.sample_rate is not None:
            return self.sample_rate / 2.0
        return None

    def set_sample_rate(self, sample_rate: float):
        """Update the sample rate for validation."""
        if sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
        self.sample_rate = sample_rate

    def validate_overlap(self, overlap_percent: float) -> ValidationResult:
        """
        Validate overlap percentage for PSD calculation.

        Valid range: 0% to <100%
        Recommended: 50% for Welch's method

        Args:
            overlap_percent: Overlap as a percentage (0-100)

        Returns:
            ValidationResult with status and any messages
        """
        if overlap_percent < 0:
            return ValidationResult.error(
                "Overlap must be non-negative (0-99%)",
                details={"value": overlap_percent, "min": 0}
            )

        if overlap_percent >= 100:
            return ValidationResult.error(
                "Overlap must be less than 100% (100% overlap is undefined)",
                details={"value": overlap_percent, "max": 99.99}
            )

        if overlap_percent > 95:
            return ValidationResult.warning(
                f"Very high overlap ({overlap_percent:.1f}%) may significantly increase computation time",
                details={"value": overlap_percent, "threshold": 95}
            )

        if overlap_percent < 25:
            return ValidationResult.warning(
                f"Low overlap ({overlap_percent:.1f}%) may reduce spectral averaging quality",
                details={"value": overlap_percent, "recommended_min": 50}
            )

        return ValidationResult.ok()

    def validate_frequency_resolution(self, df: float) -> ValidationResult:
        """
        Validate frequency resolution (df) parameter.

        Args:
            df: Desired frequency resolution in Hz

        Returns:
            ValidationResult with status and any messages
        """
        if df <= 0:
            return ValidationResult.error(
                "Frequency resolution must be positive",
                details={"value": df}
            )

        if self.nyquist_frequency is not None:
            if df >= self.nyquist_frequency:
                return ValidationResult.error(
                    f"Frequency resolution ({df:.2f} Hz) must be less than "
                    f"Nyquist frequency ({self.nyquist_frequency:.2f} Hz)",
                    details={"value": df, "nyquist": self.nyquist_frequency}
                )

        if df > 10:
            return ValidationResult.warning(
                f"Large frequency resolution ({df:.1f} Hz) may miss narrow spectral features",
                details={"value": df, "threshold": 10}
            )

        if df < 0.01:
            return ValidationResult.warning(
                f"Very fine resolution ({df:.4f} Hz) requires long data segments "
                "and increases computation time",
                details={"value": df, "threshold": 0.01}
            )

        return ValidationResult.ok()

    def validate_frequency_range(
        self,
        freq_min: float,
        freq_max: float
    ) -> ValidationResult:
        """
        Validate frequency range for PSD analysis.

        Args:
            freq_min: Minimum frequency in Hz
            freq_max: Maximum frequency in Hz

        Returns:
            ValidationResult with status and any messages
        """
        if freq_min < 0:
            return ValidationResult.error(
                "Minimum frequency cannot be negative",
                details={"value": freq_min}
            )

        if freq_max <= freq_min:
            return ValidationResult.error(
                f"Maximum frequency ({freq_max:.2f} Hz) must be greater than "
                f"minimum frequency ({freq_min:.2f} Hz)",
                details={"min": freq_min, "max": freq_max}
            )

        if self.nyquist_frequency is not None:
            if freq_max > self.nyquist_frequency:
                return ValidationResult.warning(
                    f"Maximum frequency ({freq_max:.2f} Hz) exceeds Nyquist "
                    f"frequency ({self.nyquist_frequency:.2f} Hz). "
                    "Results will be limited to Nyquist.",
                    details={"max": freq_max, "nyquist": self.nyquist_frequency}
                )

        if freq_min < 1.0:
            return ValidationResult.warning(
                f"Very low minimum frequency ({freq_min:.2f} Hz) may include "
                "DC offset and low-frequency noise",
                details={"value": freq_min, "threshold": 1.0}
            )

        return ValidationResult.ok()

    def validate_maximax_window(self, window_seconds: float) -> ValidationResult:
        """
        Validate maximax window duration.

        Per SMC-S-016, the standard window is 1 second with 50% overlap.

        Args:
            window_seconds: Window duration in seconds

        Returns:
            ValidationResult with status and any messages
        """
        if window_seconds <= 0:
            return ValidationResult.error(
                "Maximax window duration must be positive",
                details={"value": window_seconds}
            )

        if window_seconds < 0.1:
            return ValidationResult.error(
                f"Maximax window ({window_seconds:.3f}s) is too short. "
                "Minimum recommended: 0.1 seconds",
                details={"value": window_seconds, "min": 0.1}
            )

        if window_seconds > 10:
            return ValidationResult.warning(
                f"Large maximax window ({window_seconds:.1f}s) may not capture "
                "transient events effectively",
                details={"value": window_seconds, "threshold": 10}
            )

        return ValidationResult.ok()

    def validate_filter_parameters(
        self,
        filter_type: str,
        cutoff_low: Optional[float] = None,
        cutoff_high: Optional[float] = None,
        filter_order: int = 4
    ) -> ValidationResult:
        """
        Validate filter configuration parameters.

        Args:
            filter_type: Type of filter ('lowpass', 'highpass', 'bandpass')
            cutoff_low: Low cutoff frequency for highpass/bandpass
            cutoff_high: High cutoff frequency for lowpass/bandpass
            filter_order: Filter order (typically 1-10)

        Returns:
            ValidationResult with status and any messages
        """
        valid_types = ('lowpass', 'highpass', 'bandpass')
        if filter_type not in valid_types:
            return ValidationResult.error(
                f"Invalid filter type '{filter_type}'. Must be one of: {valid_types}",
                details={"value": filter_type, "valid": valid_types}
            )

        if filter_order < 1 or filter_order > 10:
            return ValidationResult.error(
                f"Filter order must be between 1 and 10, got {filter_order}",
                details={"value": filter_order, "min": 1, "max": 10}
            )

        # Check cutoff frequencies based on filter type
        if filter_type in ('lowpass', 'bandpass'):
            if cutoff_high is None:
                return ValidationResult.error(
                    f"{filter_type} filter requires high cutoff frequency"
                )
            if cutoff_high <= 0:
                return ValidationResult.error(
                    "High cutoff frequency must be positive",
                    details={"value": cutoff_high}
                )

        if filter_type in ('highpass', 'bandpass'):
            if cutoff_low is None:
                return ValidationResult.error(
                    f"{filter_type} filter requires low cutoff frequency"
                )
            if cutoff_low <= 0:
                return ValidationResult.error(
                    "Low cutoff frequency must be positive",
                    details={"value": cutoff_low}
                )

        if filter_type == 'bandpass':
            if cutoff_low >= cutoff_high:
                return ValidationResult.error(
                    f"Low cutoff ({cutoff_low} Hz) must be less than "
                    f"high cutoff ({cutoff_high} Hz)",
                    details={"low": cutoff_low, "high": cutoff_high}
                )

        # Check against Nyquist
        if self.nyquist_frequency is not None:
            if cutoff_high is not None and cutoff_high >= self.nyquist_frequency:
                return ValidationResult.error(
                    f"High cutoff ({cutoff_high} Hz) must be less than "
                    f"Nyquist frequency ({self.nyquist_frequency} Hz)",
                    details={"cutoff": cutoff_high, "nyquist": self.nyquist_frequency}
                )
            if cutoff_low is not None and cutoff_low >= self.nyquist_frequency:
                return ValidationResult.error(
                    f"Low cutoff ({cutoff_low} Hz) must be less than "
                    f"Nyquist frequency ({self.nyquist_frequency} Hz)",
                    details={"cutoff": cutoff_low, "nyquist": self.nyquist_frequency}
                )

        return ValidationResult.ok()

    def validate_all(self, config: Dict[str, Any]) -> List[ValidationResult]:
        """
        Validate all parameters in a configuration dictionary.

        Args:
            config: Dictionary containing PSD configuration parameters
                Expected keys: overlap_percent, df, freq_min, freq_max, etc.

        Returns:
            List of ValidationResult objects for each checked parameter
        """
        results = []

        if 'overlap_percent' in config:
            results.append(self.validate_overlap(config['overlap_percent']))

        if 'df' in config or 'desired_df' in config:
            df = config.get('df') or config.get('desired_df')
            results.append(self.validate_frequency_resolution(df))

        if 'freq_min' in config and 'freq_max' in config:
            results.append(self.validate_frequency_range(
                config['freq_min'], config['freq_max']
            ))

        if 'maximax_window' in config:
            results.append(self.validate_maximax_window(config['maximax_window']))

        return results


def validate_signal_data(
    signal: np.ndarray,
    sample_rate: float,
    min_duration: float = 0.1
) -> ValidationResult:
    """
    Validate signal data for PSD calculation.

    Checks for:
    - Empty arrays
    - NaN/Inf values
    - Minimum duration
    - Constant signals (no variance)

    Args:
        signal: Input signal array
        sample_rate: Sample rate in Hz
        min_duration: Minimum required duration in seconds

    Returns:
        ValidationResult with status and any messages
    """
    if signal.size == 0:
        return ValidationResult.error("Signal array is empty")

    if sample_rate <= 0:
        return ValidationResult.error(
            f"Sample rate must be positive, got {sample_rate}",
            details={"value": sample_rate}
        )

    # Check for invalid values
    nan_count = np.sum(np.isnan(signal))
    inf_count = np.sum(np.isinf(signal))

    if nan_count > 0 or inf_count > 0:
        return ValidationResult.error(
            f"Signal contains invalid values: {nan_count} NaN, {inf_count} Inf. "
            "Please clean or interpolate the data before analysis.",
            details={"nan_count": int(nan_count), "inf_count": int(inf_count)}
        )

    # Check duration
    duration = len(signal) / sample_rate
    if duration < min_duration:
        return ValidationResult.error(
            f"Signal duration ({duration:.3f}s) is less than minimum required "
            f"({min_duration}s)",
            details={"duration": duration, "min_duration": min_duration}
        )

    # Check for constant signal (no variance)
    if np.std(signal) == 0:
        return ValidationResult.warning(
            "Signal has zero variance (constant value). "
            "PSD will be zero at all frequencies.",
            details={"mean": float(np.mean(signal))}
        )

    # Check for DC offset
    mean_val = np.mean(signal)
    std_val = np.std(signal)
    if abs(mean_val) > 10 * std_val:
        return ValidationResult.warning(
            f"Signal has large DC offset (mean={mean_val:.2f}, std={std_val:.2f}). "
            "Consider removing running mean before PSD calculation.",
            details={"mean": float(mean_val), "std": float(std_val)}
        )

    return ValidationResult.ok()


def validate_time_range(
    start_time: float,
    end_time: float,
    data_start: float = 0.0,
    data_end: Optional[float] = None
) -> ValidationResult:
    """
    Validate a time range for event/segment extraction.

    Args:
        start_time: Requested start time in seconds
        end_time: Requested end time in seconds
        data_start: Actual data start time (default 0)
        data_end: Actual data end time (optional)

    Returns:
        ValidationResult with status and any messages
    """
    if start_time < 0:
        return ValidationResult.error(
            f"Start time cannot be negative ({start_time:.3f}s)",
            details={"value": start_time}
        )

    if end_time <= start_time:
        return ValidationResult.error(
            f"End time ({end_time:.3f}s) must be greater than "
            f"start time ({start_time:.3f}s)",
            details={"start": start_time, "end": end_time}
        )

    if start_time < data_start:
        return ValidationResult.warning(
            f"Start time ({start_time:.3f}s) is before data start ({data_start:.3f}s). "
            "Will use data start instead.",
            details={"requested": start_time, "actual": data_start}
        )

    if data_end is not None and end_time > data_end:
        return ValidationResult.warning(
            f"End time ({end_time:.3f}s) is after data end ({data_end:.3f}s). "
            "Will use data end instead.",
            details={"requested": end_time, "actual": data_end}
        )

    return ValidationResult.ok()
