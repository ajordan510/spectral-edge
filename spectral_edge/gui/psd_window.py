"""
PSD Analysis GUI window for SpectralEdge.

This module provides the graphical user interface for Power Spectral Density
analysis, including file loading, parameter configuration, calculation, and
interactive plotting.

Author: SpectralEdge Development Team
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QFileDialog,
    QGroupBox, QGridLayout, QMessageBox, QCheckBox, QScrollArea, QTabWidget, QLineEdit,
    QDialog, QProgressDialog, QApplication, QSizePolicy, QRadioButton, QButtonGroup, QStyle
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import json
import os
import io
import pyqtgraph as pg
import numpy as np
from pathlib import Path
from typing import Optional

# Import our custom modules
from spectral_edge.utils.data_loader import load_csv_data, DataLoadError
from spectral_edge.utils.hdf5_loader import HDF5FlightDataLoader
from spectral_edge.core.psd import (
    calculate_psd_welch, calculate_psd_maximax, psd_to_db, calculate_rms_from_psd,
    get_window_options, convert_psd_to_octave_bands,
    calculate_csd, calculate_coherence, calculate_transfer_function
)
from spectral_edge.core.channel_data import ChannelData, align_channels_by_time
from spectral_edge.gui.spectrogram_window import SpectrogramWindow
from spectral_edge.gui.event_manager import EventManagerWindow, Event
from spectral_edge.gui.flight_navigator_enhanced import FlightNavigator
from spectral_edge.utils.message_box import show_information, show_warning, show_critical
from spectral_edge.utils.report_generator import ReportGenerator, export_plot_to_image, PPTX_AVAILABLE
from spectral_edge.gui.cross_spectrum_window import CrossSpectrumWindow
from spectral_edge.gui.statistics_window import create_statistics_window
from spectral_edge.utils.theme import apply_context_menu_style, apply_dark_dialog_theme
from spectral_edge.utils.signal_conditioning import (
    apply_processing_pipeline,
    apply_robust_filtering,
    build_processing_note,
    calculate_baseline_filters,
)
from spectral_edge.utils.reference_curves import (
    REFERENCE_CURVE_COLOR_PALETTE,
    build_builtin_reference_curve,
    dedupe_reference_curves,
    load_reference_curve_csv,
    sanitize_reference_curve,
)
from spectral_edge.gui.input_validator import ParameterValidator
from spectral_edge.gui.parameter_tooltips import apply_tooltips_to_window
from spectral_edge.gui.parameter_presets import PresetManager, apply_preset_to_window
from spectral_edge.batch.spectrogram_generator import generate_spectrogram
from spectral_edge.batch.statistics import compute_statistics, plot_pdf, plot_running_stat
from spectral_edge.utils.plot_theme import (
    apply_light_matplotlib_theme,
    style_axes,
    style_colorbar,
    apply_axis_styling,
    BASE_FONT_SIZE,
    get_watermark_text,
)


class ChannelSelectorDialog(QDialog):
    """Pop-out dialog for channel selection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Channel Selection")
        self.setMinimumSize(280, 300)
        self.setModal(False)

        self.channel_checkboxes = []
        self.channel_layout = None

        self._apply_styling()
        self._create_ui()

    def _apply_styling(self):
        """Apply dark theme styling consistent with main GUI."""
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1f2e;
            }
            QLabel {
                color: #e0e0e0;
            }
            QGroupBox {
                color: #e0e0e0;
                border: 2px solid #4a5568;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QCheckBox {
                color: #e0e0e0;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #4a5568;
                border-radius: 3px;
                background-color: #2d3748;
            }
            QCheckBox::indicator:checked {
                background-color: #60a5fa;
                border-color: #60a5fa;
            }
            QScrollArea {
                border: none;
                background-color: #1a1f2e;
            }
            QWidget#channelWidget {
                background-color: #1a1f2e;
            }
        """)

    def _create_ui(self):
        """Create channel selector UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        group = QGroupBox("Channel Selection")
        group_layout = QVBoxLayout(group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(200)

        channel_widget = QWidget()
        channel_widget.setObjectName("channelWidget")
        self.channel_layout = QVBoxLayout(channel_widget)
        self.channel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(channel_widget)
        group_layout.addWidget(scroll)

        layout.addWidget(group)


class PSDReportOptionsDialog(QDialog):
    """Prompt for PowerPoint report layout/toggles before report generation."""

    LAYOUT_OPTIONS = [
        ("time_psd_spec_one_slide", "Time + PSD + Spectrogram (one slide)"),
        ("all_plots_individual", "All plots on individual slides"),
        ("psd_spec_side_by_side", "PSD + Spectrogram (side-by-side)"),
        ("psd_only", "PSD only"),
        ("spectrogram_only", "Spectrogram only"),
        ("time_history_only", "Time history only"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Report Options")
        self.setMinimumWidth(500)
        apply_dark_dialog_theme(self, object_name="psdReportOptionsDialog")
        self._build_ui()

    def showEvent(self, event):
        """Re-assert dialog-scoped dark theme in case parent styles are re-applied."""
        apply_dark_dialog_theme(self, object_name="psdReportOptionsDialog")
        super().showEvent(event)

    @classmethod
    def get_default_options(cls) -> dict:
        """Return default report options without creating UI elements."""
        return {
            "layout": "psd_only",
            "include_parameters": True,
            "include_statistics": False,
            "include_rms_table": False,
            "include_3sigma_columns": False,
        }

    def _build_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("PowerPoint Layout:"))
        self.layout_combo = QComboBox()
        for value, label in self.LAYOUT_OPTIONS:
            self.layout_combo.addItem(label, value)
        self.layout_combo.setCurrentIndex(3)  # PSD only default
        layout.addWidget(self.layout_combo)

        self.include_parameters_checkbox = QCheckBox("Include calculation parameters")
        self.include_parameters_checkbox.setChecked(True)
        layout.addWidget(self.include_parameters_checkbox)

        self.include_statistics_checkbox = QCheckBox("Include statistics slides")
        self.include_statistics_checkbox.setChecked(False)
        layout.addWidget(self.include_statistics_checkbox)

        self.include_rms_table_checkbox = QCheckBox("Include RMS summary table")
        self.include_rms_table_checkbox.setChecked(False)
        layout.addWidget(self.include_rms_table_checkbox)

        self.include_3sigma_checkbox = QCheckBox("Include 3-sigma columns in RMS summary")
        self.include_3sigma_checkbox.setChecked(False)
        self.include_3sigma_checkbox.setEnabled(False)
        layout.addWidget(self.include_3sigma_checkbox)

        self.include_rms_table_checkbox.toggled.connect(self.include_3sigma_checkbox.setEnabled)

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        generate_btn = QPushButton("Continue")
        generate_btn.clicked.connect(self.accept)
        button_row.addWidget(cancel_btn)
        button_row.addWidget(generate_btn)
        layout.addLayout(button_row)

    def get_options(self) -> dict:
        return {
            "layout": self.layout_combo.currentData(),
            "include_parameters": self.include_parameters_checkbox.isChecked(),
            "include_statistics": self.include_statistics_checkbox.isChecked(),
            "include_rms_table": self.include_rms_table_checkbox.isChecked(),
            "include_3sigma_columns": self.include_3sigma_checkbox.isChecked(),
        }

class ScientificAxisItem(pg.AxisItem):
    """
    Custom axis item that always displays values in scientific notation.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)
    
    def tickStrings(self, values, scale, spacing):
        """
        Override tick string generation to always use scientific notation.
        
        Args:
            values: The tick values to display
            scale: The scale factor
            spacing: The spacing between ticks
        
        Returns:
            List of strings for tick labels in scientific notation
        """
        strings = []
        for v in values:
            # Convert from log scale to linear
            actual_value = 10 ** v
            
            # Format in scientific notation
            strings.append(f"{actual_value:.2e}")
        
        return strings


class PSDAnalysisWindow(QMainWindow):
    """
    Main window for PSD Analysis tool.
    
    This window provides a complete interface for:
    - Loading CSV data files
    - Configuring PSD calculation parameters
    - Computing and displaying PSD results
    - Interactive plotting with zoom and pan
    - Multi-channel selection and display
    - Time history visualization
    - Spectrogram generation
    """
    
    def __init__(self):
        """Initialize the PSD Analysis window."""
        super().__init__()
        
        # Window properties
        self.setWindowTitle("SpectralEdge - PSD Analysis")
        self.setMinimumSize(1400, 1000)
        
        # Data storage
        # Display data (decimated for plotting)
        self.time_data_display = None
        self.signal_data_display = None
        
        # Full resolution data (for calculations - NEVER decimated)
        self.time_data_full = None
        self.signal_data_full = None

        # Per-channel storage (supports mixed sample rates and lengths)
        self.channel_time_full = []
        self.channel_signal_full = []
        self.channel_time_display = []
        self.channel_signal_display = []
        
        # Sample rate (always represents full resolution rate)
        self.channel_names = None
        self.channel_units = []  # Store units for each channel
        self.channel_flight_names = []  # Store flight name for each channel (for multi-flight HDF5)
        self.channel_sample_rates = []  # Store sample rate for each channel (for multi-rate support)
        self.sample_rate = None  # Reference sample rate (highest or first channel)
        self.current_file = None
        self.flight_name = ""  # Flight name for HDF5 data, empty for CSV
        
        # PSD results storage (dictionary keyed by channel name)
        self.frequencies = {}  # Changed to dict for per-channel frequencies
        self.psd_results = {}
        self.rms_values = {}
        
        # Channel selection checkboxes
        self.channel_checkboxes = []
        self.channel_selector_dialog = None
        
        # Spectrogram windows
        self.spectrogram_windows = {}
        
        # Event management
        self.event_manager = None
        self.events = []  # List of Event objects
        self.event_regions = []  # List of LinearRegionItem for visualization
        self.interactive_selection_mode = False
        self.selection_start = None
        self.temp_selection_line = None
        
        # HDF5 data management
        self.hdf5_loader = None
        self.flight_navigator = None

        # Comparison curves storage
        # Each curve is a dict: {name, frequencies, psd, color, line_style, visible}
        self.comparison_curves = []
        self.minimum_screening_checkbox = None
        self.minimum_screening_plus_3db_checkbox = None

        # Cross-spectrum window
        self.cross_spectrum_window = None

        # Statistics window
        self.statistics_window = None

        # Input validator
        self.validator = ParameterValidator()
        
        # Preset manager
        self.preset_manager = PresetManager()
        self.applying_preset = False  # Flag to prevent recursive preset changes

        # Time-history visualization state
        self.time_resolution_mode = "decimated"  # decimated | full
        self.time_filtering_mode = "filtered"  # filtered | raw
        self.time_history_cache = {}
        self._cached_filter_messages = []
        self._full_resolution_warning_shown = False

        # Apply styling
        self._apply_styling()
        
        # Create UI
        self._create_ui()
        self._update_filter_info_display()
        
        # Apply comprehensive tooltips
        apply_tooltips_to_window(self)

    def _is_multi_rate_loaded(self) -> bool:
        """Return True when loaded channels have different sample rates."""
        return bool(self.channel_sample_rates) and len(set(self.channel_sample_rates)) > 1

    def _get_time_bounds(self):
        """Get global time bounds across loaded channels."""
        starts = []
        ends = []

        for time_data in self.channel_time_full:
            if time_data is not None and len(time_data) > 0:
                starts.append(float(time_data[0]))
                ends.append(float(time_data[-1]))

        if starts and ends:
            return min(starts), max(ends)

        if self.time_data_full is not None and len(self.time_data_full) > 0:
            return float(self.time_data_full[0]), float(self.time_data_full[-1])

        return 0.0, 0.0

    def _get_channel_full(self, channel_idx: int):
        """Get full-resolution (time, signal, sample_rate) for one channel."""
        if 0 <= channel_idx < len(self.channel_signal_full):
            time_data = self.channel_time_full[channel_idx]
            signal = self.channel_signal_full[channel_idx]
        else:
            # Fallback for legacy paths
            if self.signal_data_full is None:
                return None, None, None
            if self.signal_data_full.ndim == 1:
                signal = self.signal_data_full
            else:
                signal = self.signal_data_full[:, channel_idx]
            time_data = self.time_data_full

        if 0 <= channel_idx < len(self.channel_sample_rates):
            sample_rate = self.channel_sample_rates[channel_idx]
        else:
            sample_rate = self.sample_rate

        return time_data, signal, sample_rate

    def _get_channel_display(self, channel_idx: int):
        """Get display-resolution (time, signal, sample_rate) for one channel."""
        if 0 <= channel_idx < len(self.channel_signal_display):
            time_data = self.channel_time_display[channel_idx]
            signal = self.channel_signal_display[channel_idx]
        else:
            if self.signal_data_display is None:
                return None, None, None
            if self.signal_data_display.ndim == 1:
                signal = self.signal_data_display
            else:
                signal = self.signal_data_display[:, channel_idx]
            time_data = self.time_data_display

        if 0 <= channel_idx < len(self.channel_sample_rates):
            sample_rate = self.channel_sample_rates[channel_idx]
        else:
            sample_rate = self.sample_rate

        return time_data, signal, sample_rate

    def _compute_display_indices(self, time_full, time_display) -> np.ndarray:
        """Map display timestamps to deterministic indices in the full-resolution array."""
        full = np.asarray(time_full, dtype=np.float64)
        display = np.asarray(time_display, dtype=np.float64)
        if full.size == 0 or display.size == 0:
            return np.array([], dtype=np.int64)
        if full.size == display.size and np.array_equal(full, display):
            return np.arange(full.size, dtype=np.int64)

        try:
            indices = np.searchsorted(full, display, side="left")
            indices = np.clip(indices, 0, full.size - 1)

            prev_indices = np.clip(indices - 1, 0, full.size - 1)
            left_delta = np.abs(display - full[prev_indices])
            right_delta = np.abs(full[indices] - display)
            use_prev = left_delta <= right_delta
            indices = np.where(use_prev, prev_indices, indices).astype(np.int64)

            if indices.size > 1:
                indices = np.maximum.accumulate(indices)
            return indices
        except Exception:
            if display.size == 1:
                return np.array([0], dtype=np.int64)
            return np.linspace(0, full.size - 1, num=display.size, dtype=np.int64)

    def _predict_applied_filter_bounds(
        self,
        sample_rate: float,
        user_highpass: Optional[float],
        user_lowpass: Optional[float],
    ) -> tuple[float, float]:
        """Predict applied filter cutoffs without filtering data."""
        baseline = calculate_baseline_filters(sample_rate)
        applied_highpass = float(baseline["highpass"])
        applied_lowpass = float(baseline["lowpass"])

        def _parse(value):
            if value is None:
                return None
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return None
            return numeric if np.isfinite(numeric) else None

        parsed_highpass = _parse(user_highpass)
        parsed_lowpass = _parse(user_lowpass)

        if parsed_highpass is not None:
            applied_highpass = max(parsed_highpass, applied_highpass)
        if parsed_lowpass is not None:
            applied_lowpass = min(parsed_lowpass, applied_lowpass)

        if applied_highpass >= applied_lowpass:
            applied_highpass = max(0.01, applied_lowpass * 0.5)

        return float(applied_highpass), float(applied_lowpass)

    def _show_info_banner(self, message: str):
        """Show a non-blocking inline info banner message."""
        if not hasattr(self, "info_banner_label"):
            return
        msg = (message or "").strip()
        if not msg:
            self.info_banner_label.clear()
            self.info_banner_label.setVisible(False)
            return
        self.info_banner_label.setText(msg)
        self.info_banner_label.setVisible(True)

    def _set_info_messages(self, messages):
        """Render one or more informational messages in the inline banner."""
        if not messages:
            self._show_info_banner("")
            return
        unique_messages = []
        for message in messages:
            text = str(message).strip()
            if text and text not in unique_messages:
                unique_messages.append(text)
        if not unique_messages:
            self._show_info_banner("")
            return
        preview = unique_messages[:3]
        if len(unique_messages) > 3:
            preview.append(f"... and {len(unique_messages) - 3} more")
        self._show_info_banner("\n".join(preview))

    def _get_user_filter_inputs(self):
        """Return optional user cutoff overrides from UI."""
        if not hasattr(self, "enable_filter_checkbox") or not self.enable_filter_checkbox.isChecked():
            return None, None
        highpass = float(self.low_cutoff_spin.value()) if hasattr(self, "low_cutoff_spin") else None
        lowpass = float(self.high_cutoff_spin.value()) if hasattr(self, "high_cutoff_spin") else None
        return highpass, lowpass

    def _reset_time_history_defaults(self):
        """Reset time-history controls to default decimated+filtered view."""
        self.time_resolution_mode = "decimated"
        self.time_filtering_mode = "filtered"
        self._full_resolution_warning_shown = False
        if hasattr(self, "decimated_radio"):
            self.decimated_radio.blockSignals(True)
            self.decimated_radio.setChecked(True)
            self.decimated_radio.blockSignals(False)
        if hasattr(self, "filtered_radio"):
            self.filtered_radio.blockSignals(True)
            self.filtered_radio.setChecked(True)
            self.filtered_radio.blockSignals(False)

    def _update_filter_info_display(self, sample_rate_override: Optional[float] = None):
        """Refresh baseline/actual filter informational labels."""
        sample_rate = float(sample_rate_override) if sample_rate_override else (
            float(self.sample_rate) if self.sample_rate else 0.0
        )
        baseline = calculate_baseline_filters(sample_rate) if sample_rate > 0 else None
        if hasattr(self, "baseline_highpass_label"):
            self.baseline_highpass_label.setText("Baseline Highpass: 1.00 Hz (DC/drift removal)")
        if hasattr(self, "baseline_lowpass_label"):
            if baseline is None:
                self.baseline_lowpass_label.setText("Baseline Lowpass: N/A")
            else:
                self.baseline_lowpass_label.setText(
                    f"Baseline Lowpass: {baseline['lowpass']:.2f} Hz (0.45xfs anti-aliasing)"
                )
        if hasattr(self, "baseline_rate_label"):
            if baseline is None:
                self.baseline_rate_label.setText("Sample Rate: N/A -> Nyquist: N/A")
            else:
                self.baseline_rate_label.setText(
                    f"Sample Rate: {sample_rate:.2f} Hz -> Nyquist: {baseline['nyquist']:.2f} Hz"
                )
        if hasattr(self, "soft_filter_guidance_label"):
            if baseline is None:
                self.soft_filter_guidance_label.setText("Valid range: Highpass >= 1.0 Hz, Lowpass <= 0.45xfs")
            else:
                self.soft_filter_guidance_label.setText(
                    f"Valid range: Highpass >= 1.0 Hz, Lowpass <= {baseline['lowpass']:.2f} Hz"
                )

    def _build_time_history_cache(self):
        """Pre-compute raw/filtered decimated/full cache variants for quick toggles."""
        self.time_history_cache = {}
        all_messages = []
        user_highpass, user_lowpass = self._get_user_filter_inputs()
        large_data_threshold = 10_000_000

        for channel_idx, channel_name in enumerate(self.channel_names or []):
            time_display, signal_display, sample_rate = self._get_channel_display(channel_idx)
            time_full, signal_full, _ = self._get_channel_full(channel_idx)
            if signal_display is None or time_display is None or sample_rate is None:
                continue
            if signal_full is None or time_full is None:
                signal_full = signal_display
                time_full = time_display

            decimated_raw = np.asarray(signal_display, dtype=np.float64).copy()
            full_raw = np.asarray(signal_full, dtype=np.float64).copy()
            display_indices = self._compute_display_indices(time_full, time_display)
            if display_indices.size != decimated_raw.size:
                if decimated_raw.size == 0:
                    display_indices = np.array([], dtype=np.int64)
                else:
                    display_indices = np.linspace(
                        0,
                        max(0, full_raw.size - 1),
                        num=decimated_raw.size,
                        dtype=np.int64,
                    )

            decimated_filtered = None
            applied_highpass, applied_lowpass = self._predict_applied_filter_bounds(
                float(sample_rate),
                user_highpass,
                user_lowpass,
            )
            filter_messages = []
            full_filtered = None
            full_filter_deferred = len(full_raw) > large_data_threshold
            if not full_filter_deferred:
                full_filtered, applied_highpass, applied_lowpass, full_messages = apply_robust_filtering(
                    full_raw,
                    float(sample_rate),
                    user_highpass=user_highpass,
                    user_lowpass=user_lowpass,
                )
                decimated_filtered = full_filtered[display_indices] if display_indices.size > 0 else np.array([], dtype=np.float64)
                filter_messages.extend(full_messages)

            prefixed = [f"{channel_name}: {msg}" for msg in filter_messages]
            all_messages.extend(prefixed)
            self.time_history_cache[channel_idx] = {
                "time_decimated": time_display,
                "signal_decimated_raw": decimated_raw,
                "signal_decimated_filtered": decimated_filtered,
                "display_indices": display_indices,
                "time_full": time_full,
                "signal_full_raw": full_raw,
                "signal_full_filtered": full_filtered,
                "full_filter_deferred": full_filter_deferred,
                "sample_rate": float(sample_rate),
                "applied_highpass_hz": float(applied_highpass),
                "applied_lowpass_hz": float(applied_lowpass),
                "filter_messages": prefixed,
            }

        self._cached_filter_messages = all_messages
        if hasattr(self, "applied_filters_label"):
            if self.time_history_cache:
                first = self.time_history_cache[next(iter(self.time_history_cache))]
                self.applied_filters_label.setText(
                    "Applied filters: "
                    f"HP {first['applied_highpass_hz']:.2f} Hz, "
                    f"LP {first['applied_lowpass_hz']:.2f} Hz"
                )
            else:
                self.applied_filters_label.setText("Applied filters: N/A")

        self._set_info_messages(all_messages)

    def _resolve_time_history_signal(self, channel_idx: int):
        """Resolve current time-history data vector from selected mode and cache."""
        cache = self.time_history_cache.get(channel_idx)
        if cache is None:
            return None, None, None, 0, 0, []

        use_full = self.time_resolution_mode == "full"
        use_filtered = self.time_filtering_mode == "filtered"
        info_messages = []
        display_indices = cache.get("display_indices")
        if display_indices is None or len(display_indices) != len(cache.get("signal_decimated_raw", [])):
            full_raw = cache.get("signal_full_raw")
            if full_raw is None:
                display_indices = np.array([], dtype=np.int64)
            else:
                display_indices = np.linspace(
                    0,
                    max(0, len(full_raw) - 1),
                    num=len(cache.get("signal_decimated_raw", [])),
                    dtype=np.int64,
                )
            cache["display_indices"] = display_indices

        if use_filtered and cache["signal_full_filtered"] is None:
            user_highpass = self.low_cutoff_spin.value() if self.enable_filter_checkbox.isChecked() else None
            user_lowpass = self.high_cutoff_spin.value() if self.enable_filter_checkbox.isChecked() else None
            (
                cache["signal_full_filtered"],
                cache["applied_highpass_hz"],
                cache["applied_lowpass_hz"],
                msgs,
            ) = apply_robust_filtering(
                cache["signal_full_raw"],
                cache["sample_rate"],
                user_highpass=user_highpass,
                user_lowpass=user_lowpass,
            )
            cache["signal_decimated_filtered"] = (
                cache["signal_full_filtered"][display_indices]
                if len(display_indices) > 0
                else np.array([], dtype=np.float64)
            )
            if hasattr(self, "applied_filters_label"):
                self.applied_filters_label.setText(
                    "Applied filters: "
                    f"HP {cache['applied_highpass_hz']:.2f} Hz, "
                    f"LP {cache['applied_lowpass_hz']:.2f} Hz"
                )
            if msgs:
                new_msgs = [f"{self.channel_names[channel_idx]}: {msg}" for msg in msgs]
                for msg in new_msgs:
                    if msg not in self._cached_filter_messages:
                        self._cached_filter_messages.append(msg)
                info_messages.extend(new_msgs)
            if not self._full_resolution_warning_shown and len(cache["signal_full_raw"]) > 1_000_000:
                self._full_resolution_warning_shown = True
                info_messages.append(
                    "Full-resolution display contains >1,000,000 points and may render slowly."
                )

        if use_full:
            time_data = cache["time_full"]
            signal_data = cache["signal_full_filtered"] if use_filtered else cache["signal_full_raw"]
            shown_points = len(signal_data)
            total_points = len(cache["signal_full_raw"])
        else:
            time_data = cache["time_decimated"]
            signal_data = cache["signal_decimated_filtered"] if use_filtered else cache["signal_decimated_raw"]
            if signal_data is None:
                signal_data = cache["signal_decimated_raw"]
            shown_points = len(signal_data)
            total_points = len(cache["signal_full_raw"])

        return time_data, signal_data, cache["sample_rate"], shown_points, total_points, info_messages
    
    def _apply_styling(self):
        """Apply aerospace-inspired styling to the window."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1f2e;
            }
            QLabel {
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 2px solid #4a5568;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3d4758;
                border: 2px solid #5a6578;
            }
            QPushButton:pressed {
                background-color: #1d2738;
            }
            QGroupBox {
                color: #e0e0e0;
                border: 2px solid #4a5568;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                border-radius: 3px;
                padding: 5px;
                font-size: 13px;
                min-height: 22px;
            }
            QComboBox::drop-down {
                border: none;
                width: 22px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #e0e0e0;
            }
            QComboBox QAbstractItemView {
                background-color: #2d3748;
                color: #e0e0e0;
                selection-background-color: #3b82f6;
                selection-color: #ffffff;
                border: 1px solid #4a5568;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                width: 20px;
                background-color: #3d4758;
                border: 1px solid #4a5568;
            }
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #4d5768;
            }
            QCheckBox {
                color: #e0e0e0;
                padding: 5px;
            }
            QRadioButton {
                color: #ffffff;
                padding: 2px 5px;
            }
            QRadioButton:disabled {
                color: #9ca3af;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #4a5568;
                border-radius: 3px;
                background-color: #2d3748;
            }
            QCheckBox::indicator:checked {
                background-color: #60a5fa;
                border-color: #60a5fa;
            }
            QScrollArea {
                border: none;
                background-color: #1a1f2e;
            }
            QScrollBar:vertical {
                background: #111827;
                width: 12px;
                margin: 0px;
                border: 1px solid #374151;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #4b5563;
                min-height: 24px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6b7280;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
                border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                background: #111827;
                height: 12px;
                margin: 0px;
                border: 1px solid #374151;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background: #4b5563;
                min-width: 24px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #6b7280;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                background: none;
                border: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
            }
            QWidget#channelWidget {
                background-color: #1a1f2e;
            }
        """)
    
    def _create_ui(self):
        """Create the user interface layout."""
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left panel: Controls
        left_panel = self._create_control_panel()
        main_layout.addWidget(left_panel, stretch=1)
        
        # Right panel: Plots
        right_panel = self._create_plot_panel()
        main_layout.addWidget(right_panel, stretch=3)
    
    def _create_control_panel(self):
        """Create the left control panel with file loading and parameters."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Title
        title = QLabel("PSD Analysis")
        title_font = QFont("Arial", 16, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #60a5fa;")
        layout.addWidget(title)

        self.info_banner_label = QLabel("")
        self.info_banner_label.setVisible(False)
        self.info_banner_label.setWordWrap(True)
        self.info_banner_label.setStyleSheet(
            "color: #bfdbfe; background-color: #1e3a8a; border: 1px solid #3b82f6; "
            "border-radius: 4px; padding: 6px;"
        )
        layout.addWidget(self.info_banner_label)
        
        # File loading group (always visible at top)
        file_group = self._create_file_group()
        layout.addWidget(file_group)
        
        # Create tabbed interface for parameters and options
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #4a5568;
                border-radius: 5px;
                background-color: #1a1f2e;
            }
            QTabBar::tab {
                background-color: #2d3748;
                color: #9ca3af;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #1a1f2e;
                color: #60a5fa;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #3d4758;
            }
        """)
        
        # Tab 1: PSD Parameters
        params_scroll = QScrollArea()
        params_scroll.setWidgetResizable(True)
        params_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        params_tab = QWidget()
        params_tab.setStyleSheet("background-color: #1a1f2e;")
        params_layout = QVBoxLayout(params_tab)
        params_layout.setContentsMargins(0, 0, 0, 0)
        params_layout.setSpacing(4)
        params_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        params_layout.addWidget(self._create_frequency_range_group())
        params_layout.addWidget(self._create_parameter_group())
        params_layout.addStretch()
        params_scroll.setWidget(params_tab)
        tab_widget.addTab(params_scroll, "Parameters")

        # Tab 2: Display & Axes
        display_scroll = QScrollArea()
        display_scroll.setWidgetResizable(True)
        display_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        display_tab = QWidget()
        display_tab.setStyleSheet("background-color: #1a1f2e;")
        display_layout = QVBoxLayout(display_tab)
        display_layout.setContentsMargins(0, 0, 0, 0)
        display_layout.setSpacing(4)
        display_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        display_layout.addWidget(self._create_display_options_group())
        display_layout.addWidget(self._create_axis_limits_group())
        display_layout.addStretch()
        display_scroll.setWidget(display_tab)
        tab_widget.addTab(display_scroll, "Display")

        # Tab 3: Filter
        filter_scroll = QScrollArea()
        filter_scroll.setWidgetResizable(True)
        filter_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        filter_tab = QWidget()
        filter_tab.setStyleSheet("background-color: #1a1f2e;")
        filter_layout = QVBoxLayout(filter_tab)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(4)
        filter_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        filter_layout.addWidget(self._create_filter_group())
        filter_layout.addStretch()
        filter_scroll.setWidget(filter_tab)
        tab_widget.addTab(filter_scroll, "Filter")

        # Tab 4: Comparison
        compare_scroll = QScrollArea()
        compare_scroll.setWidgetResizable(True)
        compare_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        compare_tab = QWidget()
        compare_tab.setStyleSheet("background-color: #1a1f2e;")
        compare_layout = QVBoxLayout(compare_tab)
        compare_layout.setContentsMargins(0, 0, 0, 0)
        compare_layout.setSpacing(4)
        compare_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        compare_layout.addWidget(self._create_comparison_group())
        compare_layout.addStretch()
        compare_scroll.setWidget(compare_tab)
        tab_widget.addTab(compare_scroll, "Compare")

        layout.addWidget(tab_widget)
        
        # Calculate button
        self.calc_button = QPushButton("Calculate PSD")
        self.calc_button.setEnabled(False)
        self.calc_button.clicked.connect(self._calculate_psd)
        self.calc_button.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                font-size: 14px;
                font-weight: bold;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #3b82f6;
            }
            QPushButton:disabled {
                background-color: #1e293b;
                color: #64748b;
            }
        """)
        layout.addWidget(self.calc_button)
        
        # Spectrogram button
        self.spec_button = QPushButton("Calculate Spectrogram")
        self.spec_button.setEnabled(False)
        self.spec_button.clicked.connect(self._open_spectrogram)
        layout.addWidget(self.spec_button)
        
        # Event Manager button
        self.event_button = QPushButton("Manage Events")
        self.event_button.setEnabled(False)
        self.event_button.clicked.connect(self._open_event_manager)
        layout.addWidget(self.event_button)

        # Channel selector button
        self.channel_selector_button = QPushButton("Channels")
        self.channel_selector_button.setEnabled(False)
        self.channel_selector_button.setToolTip("Open channel selection window")
        self.channel_selector_button.clicked.connect(self._toggle_channel_selector)
        layout.addWidget(self.channel_selector_button)
        
        # Clear Events button
        self.clear_events_button = QPushButton("Clear Events")
        self.clear_events_button.setEnabled(False)
        self.clear_events_button.setToolTip("Remove all events and reset to full data")
        self.clear_events_button.clicked.connect(self._clear_events)
        self.clear_events_button.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
            QPushButton:disabled {
                background-color: #4a5568;
                color: #9ca3af;
            }
        """)
        layout.addWidget(self.clear_events_button)

        # Cross-Spectrum button
        self.cross_spectrum_button = QPushButton("Cross-Spectrum Analysis")
        self.cross_spectrum_button.setEnabled(False)
        self.cross_spectrum_button.setToolTip("Analyze coherence and transfer function between two channels")
        self.cross_spectrum_button.clicked.connect(self._open_cross_spectrum)
        layout.addWidget(self.cross_spectrum_button)

        # Generate Report button
        self.report_button = QPushButton("Generate Report")
        self.report_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.report_button.setEnabled(False)
        self.report_button.setToolTip("Generate PowerPoint report with current analysis")
        self.report_button.clicked.connect(self._generate_report)
        if not PPTX_AVAILABLE:
            self.report_button.setToolTip("python-pptx not installed - report generation unavailable")
        layout.addWidget(self.report_button)

        # Statistics button
        self.statistics_button = QPushButton("Statistics Analysis")
        self.statistics_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView))
        self.statistics_button.setEnabled(False)
        self.statistics_button.setToolTip("View probability distribution, running statistics, and standard limits")
        self.statistics_button.clicked.connect(self._open_statistics)
        layout.addWidget(self.statistics_button)

        layout.addStretch()
        
        return panel
    
    def _create_file_group(self):
        """Create the file loading group box."""
        group = QGroupBox("Data File")
        layout = QVBoxLayout()
        
        # File path display
        self.file_label = QLabel("No file loaded")
        self.file_label.setWordWrap(True)
        self.file_label.setStyleSheet("color: #9ca3af; font-style: italic;")
        layout.addWidget(self.file_label)
        
        # Load CSV button
        load_csv_button = QPushButton("Load CSV File")
        load_csv_button.clicked.connect(self._load_file)
        layout.addWidget(load_csv_button)
        
        # Load HDF5 button
        load_hdf5_button = QPushButton("Load HDF5 File")
        load_hdf5_button.clicked.connect(self._load_hdf5_file)
        layout.addWidget(load_hdf5_button)

        # Configuration buttons
        config_button_layout = QHBoxLayout()
        self.load_config_button = QPushButton("Load Configuration")
        self.load_config_button.clicked.connect(self._load_psd_config)
        config_button_layout.addWidget(self.load_config_button)
        self.save_config_button = QPushButton("Save Configuration")
        self.save_config_button.clicked.connect(self._save_psd_config)
        config_button_layout.addWidget(self.save_config_button)
        layout.addLayout(config_button_layout)
        
        # File info labels
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #9ca3af; font-size: 10px;")
        layout.addWidget(self.info_label)
        
        group.setLayout(layout)
        return group

    def _get_psd_config(self):
        """Collect current PSD GUI configuration for save."""
        def _safe_float(text):
            try:
                return float(text)
            except (TypeError, ValueError):
                return None

        events = []
        if self.event_manager is not None:
            for idx, event in enumerate(self.event_manager.events):
                enabled = True
                item = self.event_manager.table.item(idx, 0)
                if item is not None:
                    enabled = item.checkState() == Qt.CheckState.Checked
                events.append({
                    "name": event.name,
                    "start": event.start_time,
                    "end": event.end_time,
                    "enabled": enabled
                })
        else:
            for event in self.events:
                events.append({
                    "name": event.name,
                    "start": event.start_time,
                    "end": event.end_time,
                    "enabled": True
                })

        return {
            "config_version": 2,
            "parameters": {
                "preset_key": self.preset_combo.currentData(),
                "window": self.window_combo.currentText().lower(),
                "df": self.df_spin.value(),
                "overlap": self.overlap_spin.value(),
                "efficient_fft": self.efficient_fft_checkbox.isChecked(),
                "maximax_enabled": self.maximax_checkbox.isChecked(),
                "maximax_window": self.maximax_window_spin.value(),
                "maximax_overlap": self.maximax_overlap_spin.value(),
                "freq_min": self.freq_min_spin.value(),
                "freq_max": self.freq_max_spin.value(),
            },
            "display": {
                "show_crosshair": self.show_crosshair_checkbox.isChecked(),
                "remove_mean": False,  # Legacy config key kept for compatibility; feature removed from PSD GUI.
                "time_resolution_mode": self.time_resolution_mode,
                "time_filtering_mode": self.time_filtering_mode,
                "octave_enabled": self.octave_checkbox.isChecked(),
                "octave_fraction": self.octave_combo.currentData(),
                "x_min": _safe_float(self.x_min_edit.text()),
                "x_max": _safe_float(self.x_max_edit.text()),
                "y_min": _safe_float(self.y_min_edit.text()),
                "y_max": _safe_float(self.y_max_edit.text()),
            },
            "filters": {
                "enabled": self.enable_filter_checkbox.isChecked(),
                "user_highpass_hz": self.low_cutoff_spin.value(),
                "user_lowpass_hz": self.high_cutoff_spin.value(),
                # Legacy compatibility keys
                "filter_type": "bandpass",
                "filter_design": "butterworth",
                "filter_order": 4,
                "cutoff_low": self.low_cutoff_spin.value(),
                "cutoff_high": self.high_cutoff_spin.value(),
            },
            "events": events,
        }

    def _apply_psd_config(self, config: dict):
        """Apply PSD GUI configuration from a dict."""
        errors = []

        def _set_combo(combo, value, label, transform=None):
            if value is None:
                return
            text = transform(value) if transform else str(value)
            idx = combo.findText(text)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            else:
                errors.append(f"{label}: Unknown option '{value}'")

        def _set_spin(spin, value, label):
            if value is None:
                return
            try:
                num = float(value)
            except (TypeError, ValueError):
                errors.append(f"{label}: Invalid value '{value}'")
                return
            if isinstance(spin, QSpinBox):
                num = int(round(num))
            if num < spin.minimum() or num > spin.maximum():
                errors.append(f"{label}: Value {num} out of range")
                return
            spin.setValue(num)

        def _set_checkbox(checkbox, value, label):
            if value is None:
                return
            if not isinstance(value, bool):
                errors.append(f"{label}: Expected boolean value")
                return
            checkbox.setChecked(value)

        params = config.get("parameters", {})
        self.applying_preset = True
        try:
            _set_combo(self.window_combo, params.get("window"), "Window", lambda v: str(v).capitalize())
            _set_spin(self.df_spin, params.get("df"), "df")
            _set_spin(self.overlap_spin, params.get("overlap"), "Overlap")
            _set_checkbox(self.efficient_fft_checkbox, params.get("efficient_fft"), "Efficient FFT")
            _set_checkbox(self.maximax_checkbox, params.get("maximax_enabled"), "Maximax enabled")
            _set_spin(self.maximax_window_spin, params.get("maximax_window"), "Maximax window")
            _set_spin(self.maximax_overlap_spin, params.get("maximax_overlap"), "Maximax overlap")
            _set_spin(self.freq_min_spin, params.get("freq_min"), "Frequency min")
            _set_spin(self.freq_max_spin, params.get("freq_max"), "Frequency max")
        finally:
            self.applying_preset = False

        # Set preset to Custom after loading explicit parameters
        if self.preset_combo.currentData() != "custom":
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(0)
            self.preset_combo.blockSignals(False)

        display = config.get("display", {})
        _set_checkbox(self.show_crosshair_checkbox, display.get("show_crosshair"), "Show crosshair")
        time_resolution_mode = str(display.get("time_resolution_mode", "decimated")).strip().lower()
        if time_resolution_mode == "full":
            self.full_resolution_radio.setChecked(True)
        else:
            self.decimated_radio.setChecked(True)
        time_filtering_mode = str(display.get("time_filtering_mode", "filtered")).strip().lower()
        if time_filtering_mode == "raw":
            self.raw_radio.setChecked(True)
        else:
            self.filtered_radio.setChecked(True)
        _set_checkbox(self.octave_checkbox, display.get("octave_enabled"), "Octave display")
        if display.get("octave_fraction") is not None:
            idx = self.octave_combo.findData(display.get("octave_fraction"))
            if idx >= 0:
                self.octave_combo.setCurrentIndex(idx)
            else:
                errors.append(f"Octave fraction: Unknown value '{display.get('octave_fraction')}'")

        def _set_axis_text(edit, value, label):
            if value is None:
                return
            try:
                num = float(value)
            except (TypeError, ValueError):
                errors.append(f"{label}: Invalid value '{value}'")
                return
            edit.setText(str(num))

        _set_axis_text(self.x_min_edit, display.get("x_min"), "X min")
        _set_axis_text(self.x_max_edit, display.get("x_max"), "X max")
        _set_axis_text(self.y_min_edit, display.get("y_min"), "Y min")
        _set_axis_text(self.y_max_edit, display.get("y_max"), "Y max")

        filters = config.get("filters", {})
        _set_checkbox(self.enable_filter_checkbox, filters.get("enabled"), "Filter enabled")
        _set_spin(
            self.low_cutoff_spin,
            filters.get("user_highpass_hz", filters.get("low_cutoff", filters.get("cutoff_low"))),
            "User highpass",
        )
        _set_spin(
            self.high_cutoff_spin,
            filters.get("user_lowpass_hz", filters.get("high_cutoff", filters.get("cutoff_high"))),
            "User lowpass",
        )

        events = config.get("events", [])
        if isinstance(events, list):
            parsed_events = []
            enabled_flags = []
            min_time_limit = None
            max_time_limit = None
            if self.channel_time_full:
                min_time_limit, max_time_limit = self._get_time_bounds()
            elif self.time_data_full is not None and len(self.time_data_full) > 0:
                min_time_limit = self.time_data_full[0]
                max_time_limit = self.time_data_full[-1]

            for idx, event in enumerate(events, start=1):
                if not isinstance(event, dict):
                    errors.append(f"Event {idx}: Invalid event format")
                    continue
                name = event.get("name") or f"Event {idx}"
                start = event.get("start")
                if start is None:
                    start = event.get("start_time")
                end = event.get("end")
                if end is None:
                    end = event.get("end_time")
                try:
                    start = float(start)
                    end = float(end)
                except (TypeError, ValueError):
                    errors.append(f"{name}: Invalid start/end values")
                    continue
                if min_time_limit is not None and start < min_time_limit:
                    errors.append(f"{name}: Start time is before loaded data range")
                    continue
                if end <= start:
                    errors.append(f"{name}: Start/end values are invalid")
                    continue
                if max_time_limit is not None and end > max_time_limit:
                    errors.append(f"{name}: End time exceeds loaded data duration")
                    continue
                enabled = event.get("enabled", True)
                enabled_flags.append(bool(enabled))
                parsed_events.append(Event(name, start, end))

            if events == []:
                self._on_events_updated([])
            elif parsed_events:
                if max_time_limit is not None:
                    max_time = max_time_limit
                else:
                    max_time = max(e.end_time for e in parsed_events)
                min_time = min_time_limit if min_time_limit is not None else min(e.start_time for e in parsed_events)

                if self.event_manager is None:
                    self.event_manager = EventManagerWindow(max_time=max_time, min_time=min_time)
                    self.event_manager.events_updated.connect(self._on_events_updated)
                    self.event_manager.interactive_mode_changed.connect(self._on_interactive_mode_changed)
                else:
                    self.event_manager.set_time_bounds(min_time=min_time, max_time=max_time)

                self.event_manager.events = parsed_events
                self.event_manager._update_table()

                for i, enabled in enumerate(enabled_flags):
                    item = self.event_manager.table.item(i, 0)
                    if item is not None:
                        item.setCheckState(
                            Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked
                        )

                enabled_events = [e for e, enabled in zip(parsed_events, enabled_flags) if enabled]
                self._on_events_updated(enabled_events)

        if self.signal_data_display is not None:
            self._update_filter_info_display()
            self._build_time_history_cache()
            self._plot_time_history()
            self._apply_axis_limits()

        return errors

    def _save_psd_config(self):
        """Save PSD GUI configuration to JSON file."""
        default_name = "PSD_Config.json"
        if self.current_file:
            default_name = f"PSD_Config_{Path(self.current_file).stem}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PSD Configuration",
            default_name,
            "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return

        try:
            config = self._get_psd_config()
            with open(file_path, "w") as f:
                json.dump(config, f, indent=2)
            show_information(self, "Configuration Saved", f"Configuration saved to:\n{file_path}")
        except Exception as e:
            show_critical(self, "Save Failed", f"Failed to save configuration:\n{e}")

    def _load_psd_config(self):
        """Load PSD GUI configuration from JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load PSD Configuration",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "r") as f:
                config = json.load(f)
            errors = self._apply_psd_config(config)
            if errors:
                show_warning(self, "Configuration Issues", "\n".join(errors))
            show_information(self, "Configuration Loaded", f"Configuration loaded from:\n{file_path}")
        except Exception as e:
            show_critical(self, "Load Failed", f"Failed to load configuration:\n{e}")
    
    def _create_channel_group(self):
        """Deprecated: channel selection is now a pop-out dialog."""
        return None

    def _ensure_channel_selector_dialog(self):
        """Ensure channel selector dialog exists."""
        if self.channel_selector_dialog is None:
            self.channel_selector_dialog = ChannelSelectorDialog(self)
        return self.channel_selector_dialog

    def _position_channel_selector(self):
        """Position channel selector to the right of the main window."""
        dialog = self._ensure_channel_selector_dialog()
        main_geom = self.geometry()
        gap = 12
        width = max(280, int(main_geom.width() * 0.35))
        height = int(main_geom.height() * 0.7)
        x = main_geom.x() + main_geom.width() + gap
        y = main_geom.y() + int(main_geom.height() * 0.1)
        dialog.setGeometry(x, y, width, height)

    def _toggle_channel_selector(self):
        """Show or hide the channel selector dialog."""
        dialog = self._ensure_channel_selector_dialog()
        if dialog.isVisible():
            dialog.hide()
        else:
            self._position_channel_selector()
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
    
    def _create_frequency_range_group(self):
        """Create the frequency range input group box."""
        group = QGroupBox("Frequency Range")
        layout = QGridLayout()
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(3)
        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 1)
        
        # Min frequency
        layout.addWidget(QLabel("Min Freq (Hz):"), 0, 0)
        self.freq_min_spin = QDoubleSpinBox()
        self.freq_min_spin.setRange(0.1, 10000)
        self.freq_min_spin.setValue(20.0)
        self.freq_min_spin.setDecimals(1)
        self.freq_min_spin.valueChanged.connect(self._on_parameter_changed)
        layout.addWidget(self.freq_min_spin, 0, 1)
        
        # Max frequency
        layout.addWidget(QLabel("Max Freq (Hz):"), 1, 0)
        self.freq_max_spin = QDoubleSpinBox()
        self.freq_max_spin.setRange(1, 100000)
        self.freq_max_spin.setValue(2000.0)
        self.freq_max_spin.setDecimals(1)
        self.freq_max_spin.valueChanged.connect(self._on_parameter_changed)
        layout.addWidget(self.freq_max_spin, 1, 1)
        self._apply_compact_parameter_input_sizing([
            self.freq_min_spin,
            self.freq_max_spin,
        ])

        group.setLayout(layout)
        return group
    
    def _create_parameter_group(self):
        """Create the parameter configuration group box."""
        group = QGroupBox("PSD Parameters")
        layout = QGridLayout()
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(3)
        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 1)
        
        row = 0
        
        # Preset selector
        layout.addWidget(QLabel("Preset:"), row, 0)
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumHeight(24)
        self.preset_combo.addItem("Custom", "custom")
        self.preset_combo.addItem("Aerospace Standard (SMC-S-016)", "aerospace_standard")
        self.preset_combo.addItem("High Frequency Resolution", "high_resolution")
        self.preset_combo.addItem("Fast Calculation", "fast_calculation")
        self.preset_combo.addItem("Low Frequency Analysis", "low_frequency")
        self.preset_combo.setToolTip(
            "<b>Parameter Presets</b><br><br>"
            "Quick-select common parameter configurations:<br><br>"
            "<b>Aerospace Standard:</b> SMC-S-016 compliance<br>"
            "<b>High Resolution:</b> Fine frequency detail<br>"
            "<b>Fast Calculation:</b> Quick analysis<br>"
            "<b>Low Frequency:</b> Optimized for < 100 Hz<br>"
            "<b>Custom:</b> Manual parameter selection"
        )
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self.preset_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.preset_combo.setMinimumContentsLength(18)
        layout.addWidget(self.preset_combo, row, 1)
        row += 1
        
        # Window type
        layout.addWidget(QLabel("Window Type:"), row, 0)
        self.window_combo = QComboBox()
        self.window_combo.setMinimumHeight(24)
        window_options = get_window_options()
        for window_name in window_options.keys():
            self.window_combo.addItem(window_name.capitalize())
        self.window_combo.setCurrentText("Hann")
        self.window_combo.currentTextChanged.connect(self._on_parameter_changed)
        self.window_combo.currentTextChanged.connect(self._on_manual_parameter_change)
        layout.addWidget(self.window_combo, row, 1)
        row += 1
        
        # Frequency resolution (df)
        layout.addWidget(QLabel("\u0394f (Hz):"), row, 0)
        self.df_spin = QDoubleSpinBox()
        self.df_spin.setMinimumHeight(24)
        self.df_spin.setRange(0.01, 100)
        self.df_spin.setValue(5.0)
        self.df_spin.setDecimals(2)
        self.df_spin.setSingleStep(0.1)
        self.df_spin.valueChanged.connect(self._update_nperseg_from_df)
        self.df_spin.valueChanged.connect(self._on_parameter_changed)
        self.df_spin.valueChanged.connect(self._validate_df)
        self.df_spin.valueChanged.connect(self._on_manual_parameter_change)
        layout.addWidget(self.df_spin, row, 1)
        row += 1
        
        # Use efficient FFT size checkbox with df display
        fft_layout = QHBoxLayout()
        fft_layout.setContentsMargins(0, 0, 0, 0)
        fft_layout.setSpacing(6)
        self.efficient_fft_checkbox = QCheckBox("Use efficient FFT size")
        self.efficient_fft_checkbox.setChecked(True)
        self.efficient_fft_checkbox.setToolTip("Round segment length to nearest power of 2 for faster FFT computation")
        self.efficient_fft_checkbox.stateChanged.connect(self._update_nperseg_from_df)
        self.efficient_fft_checkbox.stateChanged.connect(self._on_parameter_changed)
        fft_layout.addWidget(self.efficient_fft_checkbox)
        
        # Add df display label next to checkbox
        self.actual_df_label = QLabel("(df = 5.0 Hz)")
        self.actual_df_label.setStyleSheet("color: #9ca3af; font-size: 10pt;")
        self.actual_df_label.setToolTip("Actual frequency resolution after FFT size adjustment")
        fft_layout.addWidget(self.actual_df_label)
        fft_layout.addStretch()
        
        layout.addLayout(fft_layout, row, 0, 1, 2)
        row += 1
        
        # Overlap percentage
        layout.addWidget(QLabel("Overlap (%):" ), row, 0)
        self.overlap_spin = QSpinBox()
        self.overlap_spin.setMinimumHeight(24)
        self.overlap_spin.setRange(0, 90)
        self.overlap_spin.setValue(50)
        self.overlap_spin.setSingleStep(10)
        self.overlap_spin.valueChanged.connect(self._on_parameter_changed)
        self.overlap_spin.valueChanged.connect(self._validate_overlap)
        self.overlap_spin.valueChanged.connect(self._on_manual_parameter_change)
        layout.addWidget(self.overlap_spin, row, 1)
        row += 1
        
        # Maximax PSD checkbox
        self.maximax_checkbox = QCheckBox("Use Maximax PSD")
        self.maximax_checkbox.setChecked(True)  # Default to maximax
        self.maximax_checkbox.setToolTip("Calculate envelope PSD using sliding window maximax method (MPE-style)")
        self.maximax_checkbox.stateChanged.connect(self._on_maximax_toggled)
        self.maximax_checkbox.stateChanged.connect(self._on_parameter_changed)
        layout.addWidget(self.maximax_checkbox, row, 0, 1, 2)
        row += 1
        
        # Maximax window duration
        layout.addWidget(QLabel("Maximax Window (s):" ), row, 0)
        self.maximax_window_spin = QDoubleSpinBox()
        self.maximax_window_spin.setMinimumHeight(24)
        self.maximax_window_spin.setRange(0.1, 10.0)
        self.maximax_window_spin.setValue(1.0)
        self.maximax_window_spin.setDecimals(1)
        self.maximax_window_spin.setSingleStep(0.5)
        self.maximax_window_spin.setToolTip("Duration of each maximax window in seconds")
        self.maximax_window_spin.valueChanged.connect(self._on_parameter_changed)
        self.maximax_window_spin.valueChanged.connect(self._validate_maximax_window)
        layout.addWidget(self.maximax_window_spin, row, 1)
        row += 1
        
        # Maximax overlap percentage
        layout.addWidget(QLabel("Maximax Overlap (%):" ), row, 0)
        self.maximax_overlap_spin = QSpinBox()
        self.maximax_overlap_spin.setMinimumHeight(24)
        self.maximax_overlap_spin.setRange(0, 90)
        self.maximax_overlap_spin.setValue(50)
        self.maximax_overlap_spin.setSingleStep(10)
        self.maximax_overlap_spin.setToolTip("Overlap percentage between maximax windows")
        self.maximax_overlap_spin.valueChanged.connect(self._on_parameter_changed)
        self.maximax_overlap_spin.valueChanged.connect(self._validate_maximax_overlap)
        layout.addWidget(self.maximax_overlap_spin, row, 1)
        row += 1

        group.setStyleSheet("""
            QSpinBox, QDoubleSpinBox, QComboBox {
                padding-top: 2px;
                padding-bottom: 2px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 3px;
            }
        """)
        self._apply_compact_parameter_input_sizing([
            self.preset_combo,
            self.window_combo,
            self.df_spin,
            self.overlap_spin,
            self.maximax_window_spin,
            self.maximax_overlap_spin,
        ])

        group.setLayout(layout)
        return group

    def _apply_compact_parameter_input_sizing(self, controls):
        """Constrain parameter controls to avoid horizontal overflow and excess whitespace."""
        for control in controls:
            if control is None:
                continue
            control.setMinimumWidth(170)
            control.setMaximumWidth(220)
    
    def _create_display_options_group(self):
        """Create display options group."""
        group = QGroupBox("Display Options")
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)
        
        # Show crosshair checkbox
        self.show_crosshair_checkbox = QCheckBox("Show Crosshair")
        self.show_crosshair_checkbox.setChecked(False)
        self.show_crosshair_checkbox.stateChanged.connect(self._toggle_crosshair)
        layout.addWidget(self.show_crosshair_checkbox)

        # Data resolution toggle
        layout.addWidget(QLabel("Data Resolution:"))
        resolution_row = QHBoxLayout()
        self.decimated_radio = QRadioButton("Decimated")
        self.full_resolution_radio = QRadioButton("Full Resolution")
        self.decimated_radio.setChecked(True)
        self.time_resolution_group = QButtonGroup(self)
        self.time_resolution_group.addButton(self.decimated_radio)
        self.time_resolution_group.addButton(self.full_resolution_radio)
        self.decimated_radio.toggled.connect(self._on_time_resolution_changed)
        self.full_resolution_radio.toggled.connect(self._on_time_resolution_changed)
        resolution_row.addWidget(self.decimated_radio)
        resolution_row.addWidget(self.full_resolution_radio)
        resolution_row.addStretch()
        layout.addLayout(resolution_row)

        # Filtering toggle
        layout.addWidget(QLabel("Filtering:"))
        filtering_row = QHBoxLayout()
        self.filtered_radio = QRadioButton("Filtered")
        self.raw_radio = QRadioButton("Raw")
        self.filtered_radio.setChecked(True)
        self.time_filter_group = QButtonGroup(self)
        self.time_filter_group.addButton(self.filtered_radio)
        self.time_filter_group.addButton(self.raw_radio)
        self.filtered_radio.toggled.connect(self._on_time_filtering_changed)
        self.raw_radio.toggled.connect(self._on_time_filtering_changed)
        filtering_row.addWidget(self.filtered_radio)
        filtering_row.addWidget(self.raw_radio)
        filtering_row.addStretch()
        layout.addLayout(filtering_row)

        self.time_points_label = QLabel("Showing: N/A")
        self.time_points_label.setStyleSheet("color: #9ca3af; font-size: 10pt;")
        layout.addWidget(self.time_points_label)

        self.time_stats_label = QLabel("Statistics: N/A")
        self.time_stats_label.setStyleSheet("color: #9ca3af; font-size: 10pt;")
        self.time_stats_label.setWordWrap(True)
        layout.addWidget(self.time_stats_label)

        # Octave band display
        octave_layout = QHBoxLayout()
        self.octave_checkbox = QCheckBox("Octave Band Display")
        self.octave_checkbox.setChecked(False)
        self.octave_checkbox.setToolTip("Convert narrowband PSD to octave bands for visualization")
        self.octave_checkbox.stateChanged.connect(self._on_octave_display_changed)
        octave_layout.addWidget(self.octave_checkbox)
        
        # Octave fraction selector
        self.octave_combo = QComboBox()
        self.octave_combo.addItem("1/3 Octave", 3.0)
        self.octave_combo.addItem("1/6 Octave", 6.0)
        self.octave_combo.addItem("1/12 Octave", 12.0)
        self.octave_combo.addItem("1/24 Octave", 24.0)
        self.octave_combo.addItem("1/36 Octave", 36.0)
        self.octave_combo.setCurrentIndex(0)  # Default to 1/3 octave
        self.octave_combo.setEnabled(False)
        self.octave_combo.currentIndexChanged.connect(self._on_octave_fraction_changed)
        self.octave_combo.setToolTip("Select octave band spacing")
        octave_layout.addWidget(self.octave_combo)
        
        layout.addLayout(octave_layout)
        
        group.setLayout(layout)
        return group
    
    def _create_axis_limits_group(self):
        """Create axis limits control group."""
        group = QGroupBox("Axis Limits")
        layout = QGridLayout()
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(3)

        row = 0
        
        # X-axis limits (Frequency)
        layout.addWidget(QLabel("X-Axis (Hz):"), row, 0, 1, 2)
        row += 1
        
        layout.addWidget(QLabel("Min:"), row, 0)
        self.x_min_edit = QLineEdit()
        self.x_min_edit.setText("10.0")
        self.x_min_edit.setPlaceholderText("e.g., 10 or 1e1")
        self.x_min_edit.setToolTip("Enter frequency in Hz (standard or scientific notation)")
        self.x_min_edit._original_tooltip = self.x_min_edit.toolTip()
        self.x_min_edit.textChanged.connect(self._validate_frequency_range)
        layout.addWidget(self.x_min_edit, row, 1)
        row += 1
        
        layout.addWidget(QLabel("Max:"), row, 0)
        self.x_max_edit = QLineEdit()
        self.x_max_edit.setText("3000.0")
        self.x_max_edit.setPlaceholderText("e.g., 3000 or 3e3")
        self.x_max_edit.setToolTip("Enter frequency in Hz (standard or scientific notation)")
        self.x_max_edit._original_tooltip = self.x_max_edit.toolTip()
        self.x_max_edit.textChanged.connect(self._validate_frequency_range)
        layout.addWidget(self.x_max_edit, row, 1)
        row += 1
        
        # Y-axis limits (PSD)
        layout.addWidget(QLabel("Y-Axis (PSD):"), row, 0, 1, 2)
        row += 1
        
        layout.addWidget(QLabel("Min:"), row, 0)
        self.y_min_edit = QLineEdit()
        self.y_min_edit.setText("1e-7")
        self.y_min_edit.setPlaceholderText("e.g., 1e-7 or 0.0000001")
        self.y_min_edit.setToolTip("Enter PSD value (standard or scientific notation)")
        layout.addWidget(self.y_min_edit, row, 1)
        row += 1
        
        layout.addWidget(QLabel("Max:"), row, 0)
        self.y_max_edit = QLineEdit()
        self.y_max_edit.setText("10.0")
        self.y_max_edit.setPlaceholderText("e.g., 10 or 1e1")
        self.y_max_edit.setToolTip("Enter PSD value (standard or scientific notation)")
        layout.addWidget(self.y_max_edit, row, 1)
        row += 1
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Apply limits button
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._apply_axis_limits)
        button_layout.addWidget(apply_button)
        
        # Auto-fit button
        auto_button = QPushButton("Auto-Fit")
        auto_button.clicked.connect(self._auto_fit_axes)
        button_layout.addWidget(auto_button)
        
        layout.addLayout(button_layout, row, 0, 1, 2)
        
        group.setLayout(layout)
        return group
    
    def _create_filter_group(self):
        """Create baseline + optional override filter controls."""
        group = QGroupBox("Signal Filtering")
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)

        self.default_filter_info_label = QLabel(
            "Automatically calculated from sample rate. These filters are applied by default."
        )
        self.default_filter_info_label.setWordWrap(True)
        self.default_filter_info_label.setToolTip(
            "Automatically calculated from sample rate. These filters are applied by default "
            "based on signal-processing best practices."
        )
        self.default_filter_info_label.setStyleSheet(
            "color: #cbd5e1; font-size: 10pt; padding: 8px; background-color: #1e293b; border-radius: 4px;"
        )
        layout.addWidget(self.default_filter_info_label)

        self.baseline_highpass_label = QLabel("Baseline Highpass: 1.00 Hz (DC/drift removal)")
        self.baseline_lowpass_label = QLabel("Baseline Lowpass: N/A")
        self.baseline_rate_label = QLabel("Sample Rate: N/A -> Nyquist: N/A")
        for label in (self.baseline_highpass_label, self.baseline_lowpass_label, self.baseline_rate_label):
            label.setStyleSheet("color: #cbd5e1;")
            layout.addWidget(label)

        self.enable_filter_checkbox = QCheckBox("Enable Optional Additional Filtering")
        self.enable_filter_checkbox.setChecked(False)
        self.enable_filter_checkbox.stateChanged.connect(self._on_filter_enabled_changed)
        self.enable_filter_checkbox.stateChanged.connect(self._on_parameter_changed)
        layout.addWidget(self.enable_filter_checkbox)

        filter_options_group = QGroupBox("Optional Additional Filtering")
        filter_layout = QGridLayout()
        filter_layout.setContentsMargins(6, 4, 6, 4)
        filter_layout.setHorizontalSpacing(8)
        filter_layout.setVerticalSpacing(3)

        filter_layout.addWidget(QLabel("User Highpass (Hz):"), 0, 0)
        self.low_cutoff_spin = QDoubleSpinBox()
        self.low_cutoff_spin.setRange(0.0, 50000.0)
        self.low_cutoff_spin.setValue(1.0)
        self.low_cutoff_spin.setDecimals(2)
        self.low_cutoff_spin.setSingleStep(0.5)
        self.low_cutoff_spin.valueChanged.connect(self._on_parameter_changed)
        self.low_cutoff_spin.valueChanged.connect(self._on_user_filter_controls_changed)
        self.low_cutoff_spin.setEnabled(False)
        filter_layout.addWidget(self.low_cutoff_spin, 0, 1)

        filter_layout.addWidget(QLabel("User Lowpass (Hz):"), 1, 0)
        self.high_cutoff_spin = QDoubleSpinBox()
        self.high_cutoff_spin.setRange(0.0, 50000.0)
        self.high_cutoff_spin.setValue(2000.0)
        self.high_cutoff_spin.setDecimals(2)
        self.high_cutoff_spin.setSingleStep(1.0)
        self.high_cutoff_spin.valueChanged.connect(self._on_parameter_changed)
        self.high_cutoff_spin.valueChanged.connect(self._on_user_filter_controls_changed)
        self.high_cutoff_spin.setEnabled(False)
        filter_layout.addWidget(self.high_cutoff_spin, 1, 1)

        self.soft_filter_guidance_label = QLabel("Valid range: Highpass >= 1.0 Hz, Lowpass <= 0.45xfs")
        self.soft_filter_guidance_label.setWordWrap(True)
        self.soft_filter_guidance_label.setStyleSheet("color: #9ca3af;")
        filter_layout.addWidget(self.soft_filter_guidance_label, 2, 0, 1, 2)

        self.applied_filters_label = QLabel("Applied filters: N/A")
        self.applied_filters_label.setWordWrap(True)
        self.applied_filters_label.setStyleSheet("color: #9ca3af;")
        filter_layout.addWidget(self.applied_filters_label, 3, 0, 1, 2)

        filter_options_group.setLayout(filter_layout)
        layout.addWidget(filter_options_group)

        layout.addStretch()
        group.setLayout(layout)
        return group
    
    def _on_filter_enabled_changed(self):
        """Handle optional user-filter enable/disable."""
        enabled = self.enable_filter_checkbox.isChecked()
        self.low_cutoff_spin.setEnabled(enabled)
        self.high_cutoff_spin.setEnabled(enabled)
        self._update_filter_info_display()
        if self.channel_names:
            self._build_time_history_cache()
            self._plot_time_history()

    def _on_user_filter_controls_changed(self):
        """Refresh cached time-history variants when user override cutoffs change."""
        self._update_filter_info_display()
        if self.channel_names:
            self._build_time_history_cache()
            self._plot_time_history()
    
    def _on_filter_type_changed(self):
        """Legacy no-op retained for backward compatibility."""
        return
    
    def _apply_filter(self, signal, sample_rate):
        """Legacy helper retained; routes through robust baseline filtering."""
        user_highpass, user_lowpass = self._get_user_filter_inputs()
        filtered, _hp, _lp, _messages = apply_robust_filtering(
            signal,
            sample_rate,
            user_highpass=user_highpass,
            user_lowpass=user_lowpass,
        )
        return filtered

    def _create_comparison_group(self):
        """Create the comparison curves management group box."""
        group = QGroupBox("Reference Curves")
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        # Description
        desc_label = QLabel(
            "Quick-add built-in screening curves or import custom reference PSD curves "
            "from CSV (two columns: frequency, PSD)."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #9ca3af; font-size: 10pt;")
        layout.addWidget(desc_label)

        quick_layout = QVBoxLayout()
        self.quick_curves_layout = quick_layout
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(4)
        quick_layout.addWidget(QLabel("Quick Curves:"))
        self.minimum_screening_checkbox = QCheckBox("Minimum Screening")
        self.minimum_screening_checkbox.stateChanged.connect(self._on_builtin_reference_toggled)
        quick_layout.addWidget(self.minimum_screening_checkbox)
        self.minimum_screening_plus_3db_checkbox = QCheckBox("Minimum Screening + 3 dB")
        self.minimum_screening_plus_3db_checkbox.stateChanged.connect(self._on_builtin_reference_toggled)
        quick_layout.addWidget(self.minimum_screening_plus_3db_checkbox)
        layout.addLayout(quick_layout)

        # Import button
        import_button = QPushButton("Import Reference Curve...")
        import_button.clicked.connect(self._import_comparison_curve)
        layout.addWidget(import_button)

        # List of loaded curves (scroll area)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(170)
        scroll.setMaximumHeight(500)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.comparison_scroll = scroll

        self.comparison_list_widget = QWidget()
        self.comparison_list_widget.setObjectName("comparisonWidget")
        self.comparison_list_layout = QVBoxLayout(self.comparison_list_widget)
        self.comparison_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.comparison_list_widget)
        layout.addWidget(scroll, 1)

        # Clear all button
        clear_button = QPushButton("Clear All Reference Curves")
        clear_button.clicked.connect(self._clear_comparison_curves)
        layout.addWidget(clear_button)

        group.setLayout(layout)
        return group

    def _format_rms_with_unit(self, rms_value: float, unit: str, decimals: int = 2) -> str:
        """Format RMS text consistently for channel and reference legend labels."""
        try:
            value = float(rms_value)
        except (TypeError, ValueError):
            value = 0.0
        unit_text = (unit or "").strip()
        if unit_text:
            return f"{value:.{decimals}f} {unit_text}"
        return f"{value:.{decimals}f}"

    def _next_comparison_curve_color(self):
        color_idx = len(self.comparison_curves) % len(REFERENCE_CURVE_COLOR_PALETTE)
        return REFERENCE_CURVE_COLOR_PALETTE[color_idx]

    def _build_builtin_comparison_curve_data(self, builtin_id: str):
        curve = build_builtin_reference_curve(
            builtin_id,
            enabled=True,
            color=self._next_comparison_curve_color(),
            line_style="dashed",
        )
        frequencies = np.asarray(curve["frequencies"], dtype=np.float64)
        psd = np.asarray(curve["psd"], dtype=np.float64)
        try:
            rms = calculate_rms_from_psd(
                frequencies,
                psd,
                freq_min=self.freq_min_spin.value(),
                freq_max=self.freq_max_spin.value(),
            )
        except Exception:
            rms = 0.0
        return {
            "name": curve["name"],
            "frequencies": frequencies,
            "psd": psd,
            "color": curve["color"],
            "line_style": curve["line_style"],
            "visible": True,
            "enabled": True,
            "source": curve["source"],
            "builtin_id": curve["builtin_id"],
            "file_path": None,
            "rms": rms,
        }

    def _on_builtin_reference_toggled(self, _state: int):
        self._sync_builtin_reference_curves()
        self._update_comparison_list()
        self._update_plot()

    def _sync_builtin_reference_curves(self):
        for builtin_id, checkbox in (
            ("minimum_screening", self.minimum_screening_checkbox),
            ("minimum_screening_plus_3db", self.minimum_screening_plus_3db_checkbox),
        ):
            if checkbox is None:
                continue
            existing_indexes = [
                idx for idx, curve in enumerate(self.comparison_curves)
                if curve.get("source") == "builtin" and curve.get("builtin_id") == builtin_id
            ]
            if checkbox.isChecked():
                if not existing_indexes:
                    self.comparison_curves.append(self._build_builtin_comparison_curve_data(builtin_id))
                elif len(existing_indexes) > 1:
                    for idx in reversed(existing_indexes[1:]):
                        self.comparison_curves.pop(idx)
            else:
                for idx in reversed(existing_indexes):
                    self.comparison_curves.pop(idx)

        try:
            normalized_curves = [self._normalize_comparison_curve(curve) for curve in self.comparison_curves]
            normalized_curves = dedupe_reference_curves(normalized_curves)
        except Exception as exc:
            show_warning(self, "Reference Curve Warning", f"Failed to normalize reference curves: {exc}")
            normalized_curves = []
        self.comparison_curves = [self._curve_dict_from_normalized(curve) for curve in normalized_curves]

    def _curve_line_style_to_qt(self, line_style):
        style = str(line_style).strip().lower()
        if style in {"-", "solid"}:
            return Qt.PenStyle.SolidLine
        if style in {":", "dot", "dotted"}:
            return Qt.PenStyle.DotLine
        if style in {"-.", "dashdot", "dash-dot"}:
            return Qt.PenStyle.DashDotLine
        return Qt.PenStyle.DashLine

    def _normalize_comparison_curve(self, curve):
        normalized = sanitize_reference_curve(
            name=curve.get("name", ""),
            frequencies=curve.get("frequencies", []),
            psd=curve.get("psd", []),
            enabled=curve.get("visible", curve.get("enabled", True)),
            source=curve.get("source", "imported"),
            builtin_id=curve.get("builtin_id"),
            file_path=curve.get("file_path"),
            color=curve.get("color"),
            line_style=curve.get("line_style", "dashed"),
        )
        return normalized

    def _curve_dict_from_normalized(self, normalized_curve):
        frequencies = np.asarray(normalized_curve["frequencies"], dtype=np.float64)
        psd = np.asarray(normalized_curve["psd"], dtype=np.float64)
        try:
            rms = calculate_rms_from_psd(
                frequencies,
                psd,
                freq_min=self.freq_min_spin.value(),
                freq_max=self.freq_max_spin.value(),
            )
        except Exception:
            rms = 0.0
        return {
            "name": normalized_curve["name"],
            "frequencies": frequencies,
            "psd": psd,
            "color": normalized_curve.get("color") or self._next_comparison_curve_color(),
            "line_style": normalized_curve.get("line_style", "dashed"),
            "visible": normalized_curve.get("enabled", True),
            "enabled": normalized_curve.get("enabled", True),
            "source": normalized_curve.get("source", "imported"),
            "builtin_id": normalized_curve.get("builtin_id"),
            "file_path": normalized_curve.get("file_path"),
            "rms": rms,
        }

    def _import_comparison_curve(self):
        """Import a reference PSD curve from a CSV file."""
        from PyQt6.QtWidgets import QFileDialog, QInputDialog

        # Style the file dialog to match dark theme
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("Select Reference Curve CSV")
        file_dialog.setNameFilter("CSV Files (*.csv);;All Files (*)")
        file_dialog.setStyleSheet("""
            QFileDialog {
                background-color: #1a1f2e;
                color: #e0e0e0;
            }
            QWidget {
                background-color: #1a1f2e;
                color: #e0e0e0;
            }
            QLineEdit, QComboBox {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                padding: 5px;
            }
            QPushButton {
                background-color: #2d3748;
                color: #e0e0e0;
                border: 1px solid #4a5568;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #3d4758;
            }
            QTreeView, QListView {
                background-color: #2d3748;
                color: #e0e0e0;
            }
            QHeaderView::section {
                background-color: #2d3748;
                color: #e0e0e0;
            }
        """)

        if not file_dialog.exec():
            return

        file_paths = file_dialog.selectedFiles()
        if not file_paths:
            return
        file_path = file_paths[0]

        try:
            frequencies, psd = load_reference_curve_csv(file_path)

            # Get a name for this curve with styled dialog
            default_name = Path(file_path).stem

            # Create styled input dialog
            input_dialog = QInputDialog(self)
            input_dialog.setWindowTitle("Curve Name")
            input_dialog.setLabelText("Enter a name for this reference curve:")
            input_dialog.setTextValue(default_name)
            input_dialog.setStyleSheet("""
                QInputDialog {
                    background-color: #1a1f2e;
                    color: #e0e0e0;
                }
                QLabel {
                    color: #e0e0e0;
                }
                QLineEdit {
                    background-color: #2d3748;
                    color: #e0e0e0;
                    border: 1px solid #4a5568;
                    padding: 5px;
                    min-width: 300px;
                }
                QPushButton {
                    background-color: #2d3748;
                    color: #e0e0e0;
                    border: 1px solid #4a5568;
                    padding: 5px 15px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #3d4758;
                }
            """)

            ok = input_dialog.exec()
            name = input_dialog.textValue()

            if not ok or not name:
                name = default_name

            normalized_curve = sanitize_reference_curve(
                name=name,
                frequencies=frequencies,
                psd=psd,
                enabled=True,
                source="imported",
                file_path=file_path,
                color=self._next_comparison_curve_color(),
                line_style="dashed",
            )
            self.comparison_curves.append(self._curve_dict_from_normalized(normalized_curve))

            # Update the comparison list UI
            self._update_comparison_list()

            # Update the plot
            self._update_plot()

            show_information(self, "Reference Curve Imported",
                           f"Successfully imported '{name}' with {len(frequencies)} data points.")

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Reference curve import error: {error_details}")
            show_critical(self, "Import Error", f"Failed to import reference curve: {str(e)}")

    def _update_comparison_list(self):
        """Update the comparison curves list UI."""
        # Clear existing widgets
        while self.comparison_list_layout.count():
            item = self.comparison_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add widgets for each curve
        for i, curve in enumerate(self.comparison_curves):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)

            # Checkbox for visibility with RMS value
            rms_value = curve.get('rms', 0.0)
            # Get units from the first channel if available, otherwise default to 'g'
            unit = ''
            if self.channel_units and len(self.channel_units) > 0:
                unit = self.channel_units[0]
            else:
                unit = 'g'  # Default to g if no channels loaded
            rms_text = self._format_rms_with_unit(rms_value, unit)
            label_text = f"{curve['name']} (RMS={rms_text})"
            if curve.get("source") == "builtin":
                label_text = f"{curve['name']} [Built-in] (RMS={rms_text})"
            checkbox = QCheckBox(label_text)
            checkbox.setChecked(curve.get('visible', True))
            checkbox.setStyleSheet(f"color: {curve['color']};")
            checkbox.stateChanged.connect(lambda state, idx=i: self._toggle_comparison_curve(idx, state))
            row_layout.addWidget(checkbox)

            # Remove button for imported curves only
            if curve.get("source") != "builtin":
                remove_btn = QPushButton("X")
                remove_btn.setFixedSize(25, 25)
                remove_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #dc2626;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #b91c1c;
                    }
                """)
                remove_btn.clicked.connect(lambda _, idx=i: self._remove_comparison_curve(idx))
                row_layout.addWidget(remove_btn)

            self.comparison_list_layout.addWidget(row_widget)

    def _toggle_comparison_curve(self, index: int, state: int):
        """Toggle visibility of a comparison curve."""
        if 0 <= index < len(self.comparison_curves):
            visible = (state == Qt.CheckState.Checked.value)
            curve = self.comparison_curves[index]
            if curve.get("source") == "builtin":
                builtin_id = curve.get("builtin_id")
                if builtin_id == "minimum_screening" and self.minimum_screening_checkbox is not None:
                    self.minimum_screening_checkbox.setChecked(visible)
                elif builtin_id == "minimum_screening_plus_3db" and self.minimum_screening_plus_3db_checkbox is not None:
                    self.minimum_screening_plus_3db_checkbox.setChecked(visible)
                return
            curve['visible'] = visible
            curve['enabled'] = visible
            self._update_plot()

    def _remove_comparison_curve(self, index: int):
        """Remove a comparison curve."""
        if 0 <= index < len(self.comparison_curves):
            curve = self.comparison_curves[index]
            if curve.get("source") == "builtin":
                builtin_id = curve.get("builtin_id")
                if builtin_id == "minimum_screening" and self.minimum_screening_checkbox is not None:
                    self.minimum_screening_checkbox.setChecked(False)
                elif builtin_id == "minimum_screening_plus_3db" and self.minimum_screening_plus_3db_checkbox is not None:
                    self.minimum_screening_plus_3db_checkbox.setChecked(False)
            else:
                self.comparison_curves.pop(index)
                self._update_comparison_list()
                self._update_plot()

    def _clear_comparison_curves(self):
        """Clear all comparison curves."""
        self.comparison_curves.clear()
        if self.minimum_screening_checkbox is not None:
            self.minimum_screening_checkbox.blockSignals(True)
            self.minimum_screening_checkbox.setChecked(False)
            self.minimum_screening_checkbox.blockSignals(False)
        if self.minimum_screening_plus_3db_checkbox is not None:
            self.minimum_screening_plus_3db_checkbox.blockSignals(True)
            self.minimum_screening_plus_3db_checkbox.setChecked(False)
            self.minimum_screening_plus_3db_checkbox.blockSignals(False)
        self._update_comparison_list()
        self._update_plot()

    def _open_cross_spectrum(self):
        """Open the Cross-Spectrum Analysis window."""
        if (not self.channel_signal_full and self.signal_data_full is None) or len(self.channel_names) < 2:
            show_warning(self, "Insufficient Data",
                        "At least two channels are required for cross-spectrum analysis.")
            return

        if self._is_multi_rate_loaded():
            show_warning(
                self,
                "Mixed Sample Rates Not Supported",
                "Cross-spectrum currently requires all selected channels to have the same sample rate."
            )
            return

        # Prepare channel data
        channels_data = []
        for i, name in enumerate(self.channel_names):
            _, signal, _ = self._get_channel_full(i)
            if signal is None:
                continue
            unit = self.channel_units[i] if i < len(self.channel_units) else ''
            flight = self.channel_flight_names[i] if i < len(self.channel_flight_names) else ''
            channels_data.append((name, signal, unit, flight))

        # Get current parameters
        window_type = self.window_combo.currentText().lower()
        df = self.df_spin.value()
        overlap = self.overlap_spin.value()
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()

        # Create or show cross-spectrum window
        if self.cross_spectrum_window is None or not self.cross_spectrum_window.isVisible():
            self.cross_spectrum_window = CrossSpectrumWindow(
                channels_data=channels_data,
                sample_rate=self.sample_rate,
                window_type=window_type,
                df=df,
                overlap_percent=overlap,
                freq_min=freq_min,
                freq_max=freq_max,
                parent=self
            )
            self.cross_spectrum_window.show()
        else:
            self.cross_spectrum_window.raise_()
            self.cross_spectrum_window.activateWindow()

    def _open_statistics(self):
        """Open the Statistics Analysis window."""
        if (not self.channel_signal_full and self.signal_data_full is None):
            show_warning(self, "No Data",
                        "Please load data first before opening statistics analysis.")
            return

        if self._is_multi_rate_loaded() and len(self.channel_names) > 1:
            show_warning(
                self,
                "Mixed Sample Rates Not Supported",
                "Statistics window currently supports one shared sample rate across channels."
            )
            return

        filter_settings = self._get_statistics_filter_settings()
        remove_mean = False
        mean_window_seconds = 1.0
        processing_note = build_processing_note(
            filter_settings,
            remove_mean=remove_mean,
            mean_window_seconds=mean_window_seconds,
        )
        processing_flags = {
            "filter_enabled": bool(filter_settings.get("enabled", False)),
            "filter_type": "baseline+user",
            "low_cutoff_hz": filter_settings.get("user_highpass_hz"),
            "high_cutoff_hz": filter_settings.get("user_lowpass_hz"),
            "running_mean_removed": remove_mean,
            "running_mean_window_s": mean_window_seconds,
        }

        # Prepare channel data
        channels_data = []
        for i, name in enumerate(self.channel_names):
            _, signal, _ = self._get_channel_full(i)
            if signal is None:
                continue
            channel_sample_rate = (
                self.channel_sample_rates[i]
                if i < len(self.channel_sample_rates)
                else self.sample_rate
            )
            conditioned_signal = apply_processing_pipeline(
                signal,
                channel_sample_rate,
                filter_settings=filter_settings,
                remove_mean=remove_mean,
                mean_window_seconds=mean_window_seconds,
            )
            unit = self.channel_units[i] if i < len(self.channel_units) else ''
            flight = self.channel_flight_names[i] if i < len(self.channel_flight_names) else ''
            channels_data.append((name, conditioned_signal, unit, flight))

        self._statistics_processing_note = processing_note

        # Create or show statistics window
        if self.statistics_window is None or not self.statistics_window.isVisible():
            self.statistics_window = create_statistics_window(
                channels_data=channels_data,
                sample_rate=self.sample_rate,
                parent=self,
                processing_note=processing_note,
                processing_flags=processing_flags,
            )
            self.statistics_window.show()
        else:
            self.statistics_window.raise_()
            self.statistics_window.activateWindow()

    def _get_statistics_filter_settings(self):
        """Build filter settings payload for shared signal-conditioning utilities."""
        enabled = bool(self.enable_filter_checkbox.isChecked())
        if not enabled:
            return {"enabled": False}
        return {
            "enabled": enabled,
            "user_highpass_hz": self.low_cutoff_spin.value(),
            "user_lowpass_hz": self.high_cutoff_spin.value(),
            # Legacy compatibility keys still consumed by other callers/tests.
            "filter_type": "bandpass",
            "filter_design": "butterworth",
            "filter_order": 4,
            "cutoff_low": self.low_cutoff_spin.value(),
            "cutoff_high": self.high_cutoff_spin.value(),
        }

    def _generate_report(self):
        """Generate a PowerPoint report with the current analysis."""
        if not PPTX_AVAILABLE:
            show_warning(self, "Feature Unavailable",
                        "python-pptx is not installed. Install it with: pip install python-pptx")
            return

        if not self.psd_results:
            show_warning(self, "No Results",
                        "Please calculate PSD first before generating a report.")
            return

        from PyQt6.QtWidgets import QFileDialog

        if os.environ.get("PYTEST_CURRENT_TEST"):
            report_options = PSDReportOptionsDialog.get_default_options()
        else:
            options_dialog = PSDReportOptionsDialog(self)
            if options_dialog.exec() != QDialog.DialogCode.Accepted:
                return
            report_options = options_dialog.get_options()

        default_name = f"PSD_Report_{self.current_file or 'analysis'}.pptx"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Report",
            default_name,
            "PowerPoint Files (*.pptx)"
        )
        if not file_path:
            return

        try:
            title = "PSD Analysis Report"
            if self.flight_name:
                subtitle = f"Flight: {self.flight_name}"
            elif self.current_file:
                subtitle = f"File: {self.current_file}"
            else:
                subtitle = ""

            report = ReportGenerator(
                title=title,
                watermark_text=get_watermark_text(),
                watermark_scope="plot_slides",
            )
            report.add_title_slide(subtitle=subtitle)

            parameters = {
                "Window": self.window_combo.currentText(),
                "df": f"{self.df_spin.value()} Hz",
                "Overlap": f"{self.overlap_spin.value()}%",
                "Method": "Maximax" if self.maximax_checkbox.isChecked() else "Welch",
                "Frequency Range": f"{self.freq_min_spin.value()}-{self.freq_max_spin.value()} Hz",
                "Efficient FFT": "On" if self.efficient_fft_checkbox.isChecked() else "Off",
            }
            if self.maximax_checkbox.isChecked():
                parameters["Maximax Window"] = f"{self.maximax_window_spin.value()} s"
                parameters["Maximax Overlap"] = f"{self.maximax_overlap_spin.value()}%"

            if report_options["include_parameters"]:
                processing_note = build_processing_note(
                    self._get_statistics_filter_settings(),
                    remove_mean=False,
                    mean_window_seconds=1.0,
                )
                report.add_bulleted_sections_slide(
                    title="Processing Configuration",
                    sections=[
                        ("Calculation Parameters", [f"{key}: {value}" for key, value in parameters.items()]),
                        ("Signal Conditioning", [processing_note]),
                    ],
                )

            time_image = export_plot_to_image(self.time_plot_widget)
            psd_image = export_plot_to_image(self.plot_widget)
            spec_image = None
            if report_options["layout"] in {
                "time_psd_spec_one_slide", "all_plots_individual", "psd_spec_side_by_side", "spectrogram_only"
            }:
                spec_image = self._create_report_spectrogram_image(report_options["layout"])

            selected_indices = self._get_selected_channel_indices()
            channel_label = self.channel_names[selected_indices[0]] if selected_indices and self.channel_names else "Selected Channels"
            flight_label = self.flight_name or (self.current_file or "Current Data")
            slide_title = f"{flight_label} | Current View | {channel_label}"

            layout = report_options["layout"]
            if layout == "time_psd_spec_one_slide":
                if time_image and psd_image and spec_image:
                    report.add_three_plot_slide(slide_title, time_image, psd_image, spec_image)
            elif layout == "all_plots_individual":
                report.add_single_plot_slide(time_image, f"Time History | {slide_title}")
                report.add_single_plot_slide(psd_image, f"PSD | {slide_title}")
                if spec_image:
                    report.add_single_plot_slide(spec_image, f"Spectrogram | {slide_title}")
            elif layout == "psd_spec_side_by_side":
                if spec_image:
                    report.add_two_plot_slide(slide_title, psd_image, spec_image)
            elif layout == "psd_only":
                report.add_single_plot_slide(psd_image, slide_title)
            elif layout == "spectrogram_only":
                if spec_image:
                    report.add_single_plot_slide(spec_image, slide_title)
            elif layout == "time_history_only":
                report.add_single_plot_slide(time_image, slide_title)

            if report_options["include_statistics"]:
                stats_payload = self._create_statistics_slide_payload()
                if stats_payload is not None:
                    report.add_statistics_dashboard_slide(
                        slide_title,
                        stats_payload["pdf"],
                        stats_payload["mean"],
                        stats_payload["std"],
                        stats_payload["skew"],
                        stats_payload["kurt"],
                        stats_payload["summary"],
                    )

            if report_options["include_rms_table"] and self.channel_names:
                headers = ["Channel", "RMS"]
                if report_options["include_3sigma_columns"]:
                    headers.append("3-sigma RMS")
                rows = []
                for channel in self.channel_names:
                    rms_value = self.rms_values.get(channel, None)
                    row = [channel, "" if rms_value is None else f"{rms_value:.4f}"]
                    if report_options["include_3sigma_columns"]:
                        row.append("" if rms_value is None else f"{3.0 * rms_value:.4f}")
                    rows.append(row)
                if rows:
                    report.add_rms_table_slide("RMS Summary", headers, rows)

            saved_path = report.save(file_path)
            show_information(self, "Report Generated", f"Report saved to:\n{saved_path}")

        except Exception as e:
            show_critical(self, "Report Error", f"Failed to generate report: {str(e)}")

    def _get_selected_channel_indices(self):
        """Return indices for channels currently selected in the channel checklist."""
        if not self.channel_checkboxes:
            return []
        return [i for i, cb in enumerate(self.channel_checkboxes) if cb.isChecked()]

    def _create_report_spectrogram_image(self, layout: str):
        """Create a spectrogram image for report output from the first selected channel."""
        if (not self.channel_signal_full and self.signal_data_full is None):
            return None
        selected_indices = self._get_selected_channel_indices()
        if not selected_indices:
            return None

        channel_idx = selected_indices[0]
        _, signal, channel_sample_rate = self._get_channel_full(channel_idx)
        if signal is None or len(signal) == 0 or channel_sample_rate is None:
            return None

        freqs, times, sxx = generate_spectrogram(
            signal,
            channel_sample_rate,
            desired_df=float(self.df_spin.value()),
            overlap_percent=float(self.overlap_spin.value()),
            snr_threshold=50.0,
            use_efficient_fft=self.efficient_fft_checkbox.isChecked(),
        )

        import matplotlib.pyplot as plt

        apply_light_matplotlib_theme()
        figsize = (6.1, 5.9) if layout == "psd_spec_side_by_side" else (12.333, 6.0)
        fig, ax = plt.subplots(figsize=figsize)
        sxx_db = 10 * np.log10(sxx + 1e-12)
        im = ax.pcolormesh(times, freqs, sxx_db, shading="auto", cmap="viridis")
        style_axes(ax, "Spectrogram", "Time (s)", "Frequency (Hz)")
        apply_axis_styling(ax, font_size=BASE_FONT_SIZE, include_grid=False)
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label("PSD (dB)")
        style_colorbar(cbar, font_size=BASE_FONT_SIZE)
        fig.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        plt.close(fig)
        return buf.getvalue()

    def _create_statistics_slide_payload(self):
        """Build statistics plot bytes and summary rows for report generation."""
        if (not self.channel_signal_full and self.signal_data_full is None):
            return None
        selected_indices = self._get_selected_channel_indices()
        if not selected_indices:
            return None
        channel_idx = selected_indices[0]
        _, signal, channel_sample_rate = self._get_channel_full(channel_idx)
        if signal is None or len(signal) < 10 or channel_sample_rate is None:
            return None

        filter_settings = self._get_statistics_filter_settings()
        remove_mean = False
        mean_window_seconds = 1.0
        conditioned_signal = apply_processing_pipeline(
            signal,
            channel_sample_rate,
            filter_settings=filter_settings,
            remove_mean=remove_mean,
            mean_window_seconds=mean_window_seconds,
        )
        show_rayleigh = False
        if self.statistics_window is not None and hasattr(self.statistics_window, "rayleigh_checkbox"):
            show_rayleigh = bool(self.statistics_window.rayleigh_checkbox.isChecked())
        processing_note = build_processing_note(
            filter_settings,
            remove_mean=remove_mean,
            mean_window_seconds=mean_window_seconds,
        )

        class _StatsConfig:
            pdf_bins = 50
            running_window_seconds = 1.0
            max_plot_points = 5000
            show_mean = True
            show_std = True
            show_skewness = True
            show_kurtosis = True
            show_normal = True
            show_rayleigh = False
            show_uniform = False
        _StatsConfig.show_rayleigh = bool(show_rayleigh)

        stats = compute_statistics(conditioned_signal, channel_sample_rate, _StatsConfig())
        pdf_fig, _ = plot_pdf(stats["pdf"], _StatsConfig())
        mean_fig, _ = plot_running_stat(stats["running"], "mean", "Running Mean", "Mean")
        std_fig, _ = plot_running_stat(stats["running"], "std", "Running Std", "Std")
        skew_fig, _ = plot_running_stat(stats["running"], "skewness", "Running Skewness", "Skewness")
        kurt_fig, _ = plot_running_stat(stats["running"], "kurtosis", "Running Kurtosis", "Kurtosis")

        import matplotlib.pyplot as plt

        def _fig_to_bytes(fig):
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
            plt.close(fig)
            return buf.getvalue()

        summary = [
            ("Mean", f"{stats['overall']['mean']:.4f}"),
            ("Std", f"{stats['overall']['std']:.4f}"),
            ("Skewness", f"{stats['overall']['skewness']:.4f}"),
            ("Kurtosis", f"{stats['overall']['kurtosis']:.4f}"),
            ("Min", f"{stats['overall']['min']:.4f}"),
            ("Max", f"{stats['overall']['max']:.4f}"),
            ("RMS", f"{stats['overall']['rms']:.4f}"),
            ("Crest Factor", f"{stats['overall']['crest_factor']:.4f}"),
            ("Conditioning", processing_note),
        ]
        return {
            "pdf": _fig_to_bytes(pdf_fig),
            "mean": _fig_to_bytes(mean_fig),
            "std": _fig_to_bytes(std_fig),
            "skew": _fig_to_bytes(skew_fig),
            "kurt": _fig_to_bytes(kurt_fig),
            "summary": summary,
        }

    def _create_plot_panel(self):
        """Create the right plot panel with time history and PSD plots."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Time history plot
        self.time_plot_widget = pg.PlotWidget()
        self.time_plot_widget.setBackground('#1a1f2e')
        apply_context_menu_style(self.time_plot_widget)
        self.time_plot_widget.setLabel('left', 'Amplitude', color='#e0e0e0', size='11pt')
        self.time_plot_widget.setLabel('bottom', 'Time', units='s', color='#e0e0e0', size='11pt')
        self.time_plot_widget.setTitle("Time History", color='#60a5fa', size='12pt')
        self.time_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.time_plot_widget.setMouseEnabled(x=True, y=True)
        
        # Set initial axis limits for professional appearance
        self.time_plot_widget.setXRange(0, 60, padding=0)
        self.time_plot_widget.setYRange(-10, 10, padding=0)
        
        # Add legend for time plot with styled background (initially hidden)
        self.time_legend = self.time_plot_widget.addLegend(offset=(10, 10))
        self.time_legend.setBrush(pg.mkBrush(26, 31, 46, 255))  # Solid GUI background
        self.time_legend.setPen(pg.mkPen(74, 85, 104, 255))  # Subtle border
        self.time_legend.setVisible(False)  # Hide until data is loaded
        
        # Connect click event for interactive event selection
        self.time_plot_widget.scene().sigMouseClicked.connect(self._on_time_plot_clicked)
        
        layout.addWidget(self.time_plot_widget, stretch=1)
        
        # PSD plot with custom axes
        self.plot_widget = pg.PlotWidget(axisItems={
            'left': ScientificAxisItem(orientation='left')
        })
        self.plot_widget.setBackground('#1a1f2e')
        apply_context_menu_style(self.plot_widget)
        self.plot_widget.setLabel('left', 'PSD', units='', color='#e0e0e0', size='12pt')
        self.plot_widget.setLabel('bottom', 'Frequency (Hz)', color='#e0e0e0', size='12pt')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setTitle("Power Spectral Density", color='#60a5fa', size='14pt')
        self.plot_widget.setMouseEnabled(x=True, y=True)
        self.plot_widget.setLogMode(x=True, y=True)
        
        # Set initial axis limits for professional appearance (log scale: 10^1 to 10^3.5 for x, 10^-5 to 10^1 for y)
        self.plot_widget.setXRange(np.log10(10), np.log10(3000), padding=0)
        self.plot_widget.setYRange(np.log10(1e-5), np.log10(10), padding=0)
        
        # Disable auto-range to prevent crosshair from panning
        self.plot_widget.getPlotItem().vb.disableAutoRange()
        
        # Add legend for PSD with styled background (initially hidden)
        self.legend = self.plot_widget.addLegend(offset=(10, 10))
        self.legend.setBrush(pg.mkBrush(26, 31, 46, 255))  # Solid GUI background
        self.legend.setPen(pg.mkPen(74, 85, 104, 255))  # Subtle border
        self.legend.setVisible(False)  # Hide until data is calculated

        # Set initial frequency ticks to powers of 10 (10, 100, 1000)
        self._set_initial_frequency_ticks()

        # Configure axis appearance for full box border
        axis_pen = pg.mkPen(color='#4a5568', width=2)
        self.plot_widget.getPlotItem().getAxis('top').setPen(axis_pen)
        self.plot_widget.getPlotItem().getAxis('right').setPen(axis_pen)
        self.plot_widget.getPlotItem().getAxis('top').setStyle(showValues=False)
        self.plot_widget.getPlotItem().getAxis('right').setStyle(showValues=False)
        self.plot_widget.getPlotItem().showAxis('top')
        self.plot_widget.getPlotItem().showAxis('right')
        
        # Add crosshair for cursor position display
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('#60a5fa', width=1, style=Qt.PenStyle.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('#60a5fa', width=1, style=Qt.PenStyle.DashLine))
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)
        
        # Add label for cursor coordinates
        self.coord_label = pg.TextItem(anchor=(0, 1), color='#e0e0e0')
        self.plot_widget.addItem(self.coord_label, ignoreBounds=True)
        
        # Connect mouse move event
        self.plot_widget.scene().sigMouseMoved.connect(self._on_mouse_moved)
        
        # Hide crosshair initially
        self.vLine.setVisible(False)
        self.hLine.setVisible(False)
        self.coord_label.setVisible(False)
        
        layout.addWidget(self.plot_widget, stretch=2)
        
        return panel
    
    def _toggle_crosshair(self):
        """Toggle crosshair visibility."""
        # Crosshair will only show when checkbox is checked AND mouse is over plot
        pass  # Actual visibility is handled in _on_mouse_moved
    
    def _on_mouse_moved(self, pos):
        """
        Handle mouse movement over the plot to show cursor coordinates.
        
        Args:
            pos: Mouse position in scene coordinates
        """
        # Only show if checkbox is checked
        if not self.show_crosshair_checkbox.isChecked():
            self.vLine.setVisible(False)
            self.hLine.setVisible(False)
            self.coord_label.setVisible(False)
            return
        
        # Check if mouse is within plot area
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            
            # Convert from log scale to linear
            freq = 10 ** mouse_point.x()
            psd = 10 ** mouse_point.y()
            
            # Update crosshair position
            self.vLine.setPos(mouse_point.x())
            self.hLine.setPos(mouse_point.y())
            self.vLine.setVisible(True)
            self.hLine.setVisible(True)
            
            # Update coordinate label
            if self.channel_units and self.channel_units[0]:
                unit = self.channel_units[0]
                label_text = f"f = {freq:.2f} Hz\nPSD = {psd:.3e} {unit}^2/Hz"
            else:
                label_text = f"f = {freq:.2f} Hz\nPSD = {psd:.3e}"
            
            self.coord_label.setText(label_text)
            self.coord_label.setPos(mouse_point.x(), mouse_point.y())
            self.coord_label.setVisible(True)
        else:
            # Hide crosshair when mouse leaves plot area
            self.vLine.setVisible(False)
            self.hLine.setVisible(False)
            self.coord_label.setVisible(False)
    
    def _recalculate_comparison_rms(self):
        """Recalculate RMS values for all comparison curves based on current frequency range."""
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()

        for curve in self.comparison_curves:
            # Recalculate RMS for this curve
            curve_freqs = np.asarray(curve['frequencies'], dtype=np.float64)
            curve_psd = np.asarray(curve['psd'], dtype=np.float64)
            try:
                rms = calculate_rms_from_psd(
                    curve_freqs,
                    curve_psd,
                    freq_min=freq_min,
                    freq_max=freq_max
                )
            except Exception:
                rms = 0.0
            curve['rms'] = rms

        # Update the UI to show new RMS values
        self._update_comparison_list()

    def _on_parameter_changed(self):
        """Handle parameter changes - clear PSD results to force recalculation."""
        # Clear PSD results
        self.frequencies = {}
        self.psd_results = {}
        self.rms_values = {}

        # Recalculate RMS for comparison curves (frequency range may have changed)
        if self.comparison_curves:
            self._recalculate_comparison_rms()

        # Clear the PSD plot but keep time history
        self._clear_psd_plot()

    def _get_active_events_for_calculation(self):
        """Resolve active events, preferring Event Manager checkbox state."""
        if self.event_manager is not None and hasattr(self.event_manager, "get_enabled_events"):
            enabled_events = list(self.event_manager.get_enabled_events())
            self.events = enabled_events
            return enabled_events
        return list(self.events)

    def _compute_channel_psd(self, signal, channel_sample_rate):
        """Compute PSD for one channel signal slice using robust baseline filtering."""
        window = self.window_combo.currentText().lower()
        df = self.df_spin.value()
        use_efficient_fft = self.efficient_fft_checkbox.isChecked()

        processed_signal = np.asarray(signal, dtype=np.float64).copy()
        user_highpass, user_lowpass = self._get_user_filter_inputs()
        processed_signal, applied_highpass, applied_lowpass, info_messages = apply_robust_filtering(
            processed_signal,
            channel_sample_rate,
            user_highpass=user_highpass,
            user_lowpass=user_lowpass,
        )

        if self.maximax_checkbox.isChecked():
            frequencies, psd = calculate_psd_maximax(
                processed_signal,
                channel_sample_rate,
                df=df,
                maximax_window=self.maximax_window_spin.value(),
                overlap_percent=self.maximax_overlap_spin.value(),
                window=window,
                use_efficient_fft=use_efficient_fft,
            )
        else:
            nperseg = int(channel_sample_rate / df)
            noverlap = int(nperseg * self.overlap_spin.value() / 100.0)
            frequencies, psd = calculate_psd_welch(
                processed_signal,
                channel_sample_rate,
                df=df,
                noverlap=noverlap,
                window=window,
                use_efficient_fft=use_efficient_fft,
            )

        return frequencies, psd, applied_highpass, applied_lowpass, info_messages
    
    def _validate_overlap(self):
        """Validate overlap percentage in real-time."""
        overlap = self.overlap_spin.value()
        result = self.validator.validate_overlap(overlap)
        self.validator.apply_validation_style(self.overlap_spin, result)
    
    def _validate_maximax_overlap(self):
        """Validate maximax overlap percentage in real-time."""
        overlap = self.maximax_overlap_spin.value()
        result = self.validator.validate_overlap(overlap)
        self.validator.apply_validation_style(self.maximax_overlap_spin, result)
    
    def _validate_df(self):
        """Validate frequency resolution in real-time."""
        df = self.df_spin.value()
        result = self.validator.validate_frequency_resolution(df)
        self.validator.apply_validation_style(self.df_spin, result)
    
    def _validate_maximax_window(self):
        """Validate maximax window duration in real-time."""
        window_duration = self.maximax_window_spin.value()
        data_duration = None
        if self.channel_time_full:
            time_min, time_max = self._get_time_bounds()
            data_duration = max(0.0, time_max - time_min)
        elif self.time_data_full is not None and self.sample_rate is not None:
            data_duration = len(self.time_data_full) / self.sample_rate
        result = self.validator.validate_maximax_window(window_duration, data_duration)
        self.validator.apply_validation_style(self.maximax_window_spin, result)
    
    def _validate_frequency_range(self):
        """Validate frequency range in real-time."""
        try:
            min_freq = float(self.x_min_edit.text())
            max_freq = float(self.x_max_edit.text())
            result = self.validator.validate_frequency_range(min_freq, max_freq)
            self.validator.apply_validation_style(self.x_min_edit, result)
            self.validator.apply_validation_style(self.x_max_edit, result)
        except ValueError:
            # Invalid number format
            from spectral_edge.gui.input_validator import ValidationResult
            result = ValidationResult(False, "Invalid number format")
            self.validator.apply_validation_style(self.x_min_edit, result)
            self.validator.apply_validation_style(self.x_max_edit, result)
    
    def _on_preset_changed(self):
        """Handle preset selection change."""
        if self.applying_preset:
            return  # Prevent recursive calls
        
        preset_key = self.preset_combo.currentData()
        if preset_key == "custom":
            return  # Custom mode - no action needed
        
        # Get the preset
        preset = self.preset_manager.get_preset(preset_key)
        if preset is None:
            return
        
        # Apply the preset
        self.applying_preset = True
        try:
            apply_preset_to_window(self, preset)
            print(f"Applied preset: {preset.name}")
        finally:
            self.applying_preset = False
    
    def _on_manual_parameter_change(self):
        """Handle manual parameter changes - switch to Custom preset."""
        if self.applying_preset:
            return  # Don't switch to custom when applying a preset
        
        # Switch to Custom if not already selected
        if self.preset_combo.currentData() != "custom":
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(0)  # Custom is first item
            self.preset_combo.blockSignals(False)
    
    def _clear_psd_plot(self):
        """Clear only the PSD plot."""
        self.plot_widget.clear()
        
        # Re-add crosshair and label
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)
        self.plot_widget.addItem(self.coord_label, ignoreBounds=True)
        
        # Re-add legend with styling
        self.legend = self.plot_widget.addLegend(offset=(10, 10))
        self.legend.setBrush(pg.mkBrush(26, 31, 46, 255))  # Solid GUI background
        self.legend.setPen(pg.mkPen(74, 85, 104, 255))
    
    def _update_nperseg_from_df(self):
        """
        Update actual df label based on desired frequency resolution and FFT size option.
        
        The relationship is: df = sample_rate / nperseg
        Therefore: nperseg = sample_rate / df
        
        If "Use efficient FFT size" is checked, round to the nearest power of 2.
        This updates the displayed actual df value that will be achieved.
        """
        if self.sample_rate is None:
            return
        
        df = self.df_spin.value()
        nperseg = int(self.sample_rate / df)
        
        if self.efficient_fft_checkbox.isChecked():
            # Round to nearest power of 2 (preferring larger for better resolution)
            nperseg = 2 ** int(np.ceil(np.log2(nperseg)))
        
        # Update actual df label
        actual_df = self.sample_rate / nperseg
        self.actual_df_label.setText(f"(df = {actual_df:.3f} Hz)")
        self.actual_df_label.setToolTip(f"Actual frequency resolution: {actual_df:.3f} Hz (nperseg = {nperseg})")
    
    def _load_file(self):
        """Handle file loading button click."""
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select CSV Data File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Load the data
            time_data, signal_data, self.channel_names, self.sample_rate = \
                load_csv_data(file_path)
            
            # For CSV files, store same data for both full and display
            # (CSV files are typically small enough that no decimation is needed)
            self.time_data_full = time_data
            self.signal_data_full = signal_data
            self.time_data_display = time_data
            self.signal_data_display = signal_data

            # Build per-channel storage for compatibility with mixed-rate paths
            if signal_data.ndim == 1:
                signal_columns = [signal_data]
            else:
                signal_columns = [signal_data[:, i] for i in range(signal_data.shape[1])]

            self.channel_signal_full = [sig.copy() for sig in signal_columns]
            self.channel_signal_display = [sig.copy() for sig in signal_columns]
            self.channel_time_full = [time_data for _ in signal_columns]
            self.channel_time_display = [time_data for _ in signal_columns]
            self.channel_sample_rates = [self.sample_rate for _ in signal_columns]
            
            self.current_file = Path(file_path).name
            self.flight_name = ""  # CSV data has no flight name
            self.channel_flight_names = ["" for _ in signal_columns]  # CSV data has no flight names
            
            # Extract units from channel names (e.g., "Accelerometer_X (g)" -> "g")
            self.channel_units = []
            for name in self.channel_names:
                if '(' in name and ')' in name:
                    unit = name[name.find('(')+1:name.find(')')]
                    self.channel_units.append(unit)
                else:
                    self.channel_units.append('')
            
            # Update UI
            self.file_label.setText(f"Loaded: {self.current_file}")
            self.file_label.setStyleSheet("color: #10b981;")
            
            # Display file info
            num_channels = len(self.channel_names)
            duration = self.time_data_full[-1] - self.time_data_full[0]  # Use actual time span
            info_text = (f"Channels: {num_channels}\n"
                        f"Sample Rate: {self.sample_rate:.1f} Hz\n"
                        f"Duration: {duration:.2f} s\n"
                        f"Samples: {len(self.time_data_full)} (Full resolution)")
            self.info_label.setText(info_text)
            
            # Update nperseg calculation
            self._update_nperseg_from_df()
            
            # Create channel selection checkboxes
            self._create_channel_checkboxes()

            # Keep event manager bounds synchronized with newly loaded data.
            if self.event_manager is not None:
                time_min, time_max = self._get_time_bounds()
                self.event_manager.set_time_bounds(min_time=time_min, max_time=time_max)
            
            # Enable calculate buttons
            self.calc_button.setEnabled(True)
            self.spec_button.setEnabled(True)
            self.event_button.setEnabled(True)
            self.cross_spectrum_button.setEnabled(len(self.channel_names) >= 2)
            self.report_button.setEnabled(PPTX_AVAILABLE)
            self.statistics_button.setEnabled(True)

            # Clear previous results
            self.frequencies = {}
            self.psd_results = {}
            self.rms_values = {}

            # Reset and rebuild adaptive time-history cache.
            self._reset_time_history_defaults()
            self._update_filter_info_display()
            self._build_time_history_cache()
            self._plot_time_history()
            
        except (DataLoadError, FileNotFoundError) as e:
            show_critical(self, "Error Loading File", str(e))
        except Exception as e:
            show_critical(self, "Unexpected Error", f"An error occurred: {e}")
    
    def _create_channel_checkboxes(self):
        """Create checkboxes for channel selection."""
        # Clear existing checkboxes
        for checkbox in self.channel_checkboxes:
            checkbox.deleteLater()
        self.channel_checkboxes.clear()

        dialog = self._ensure_channel_selector_dialog()
        if dialog.channel_layout is None:
            return
        # Clear existing widgets in dialog layout
        while dialog.channel_layout.count():
            item = dialog.channel_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        
        # Create new checkboxes
        multi_rate = False
        if self.channel_sample_rates:
            multi_rate = len(set(self.channel_sample_rates)) > 1

        for i, channel_name in enumerate(self.channel_names):
            unit = self.channel_units[i] if i < len(self.channel_units) else ""
            display_name = channel_name
            if unit:
                display_name = f"{display_name} ({unit})"
            if multi_rate and i < len(self.channel_sample_rates):
                sr = self.channel_sample_rates[i]
                if unit:
                    display_name = f"{channel_name} ({unit}, {sr:.0f} Hz)"
                else:
                    display_name = f"{channel_name} ({sr:.0f} Hz)"

            checkbox = QCheckBox(display_name)
            checkbox.setChecked(True)  # All channels selected by default
            checkbox.stateChanged.connect(self._on_channel_selection_changed)
            dialog.channel_layout.addWidget(checkbox)
            self.channel_checkboxes.append(checkbox)
        
        # Enable channel selector button
        if self.channel_selector_button is not None:
            self.channel_selector_button.setEnabled(True)
    
    def _on_channel_selection_changed(self):
        """Handle channel selection changes."""
        # Update both time history and PSD plots
        self._plot_time_history()
        self._update_plot()

    def _on_time_resolution_changed(self):
        """Handle decimated/full-resolution toggle changes."""
        new_mode = "full" if self.full_resolution_radio.isChecked() else "decimated"
        if self.time_resolution_mode == new_mode:
            return
        self.time_resolution_mode = new_mode
        if new_mode == "full" and not self._full_resolution_warning_shown:
            for cache in self.time_history_cache.values():
                if len(cache.get("signal_full_raw", [])) > 1_000_000:
                    self._full_resolution_warning_shown = True
                    self._set_info_messages(
                        ["Full-resolution display contains >1,000,000 points and may render slowly."]
                    )
                    break
        self._plot_time_history()

    def _on_time_filtering_changed(self):
        """Handle filtered/raw time-history toggle changes."""
        new_mode = "raw" if self.raw_radio.isChecked() else "filtered"
        if self.time_filtering_mode == new_mode:
            return
        self.time_filtering_mode = new_mode
        self._plot_time_history()
    
    def _plot_time_history(self):
        """Plot time history from the 4-state cache (decimated/full x filtered/raw)."""
        if not self.channel_signal_display and self.signal_data_display is None:
            return

        if not self.time_history_cache and self.channel_names:
            self._build_time_history_cache()

        # Preserve current zoom/pan when toggling display modes.
        view_box = self.time_plot_widget.getPlotItem().vb
        previous_x, previous_y = view_box.viewRange()
        had_previous_data = bool(self.time_plot_widget.listDataItems())

        self.time_plot_widget.clear()
        self.time_legend.clear()
        self.time_legend = self.time_plot_widget.addLegend(offset=(10, 10))
        self.time_legend.setBrush(pg.mkBrush(26, 31, 46, 255))
        self.time_legend.setPen(pg.mkPen(74, 85, 104, 255))
        self.time_legend.setVisible(True)

        colors = ['#60a5fa', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
        plot_count = 0
        shown_points = 0
        total_points = 0
        info_messages = list(self._cached_filter_messages)
        primary_signal = None
        primary_channel_name = None

        for i, checkbox in enumerate(self.channel_checkboxes):
            if not checkbox.isChecked():
                continue

            channel_name = self.channel_names[i]
            flight_name = self.channel_flight_names[i] if i < len(self.channel_flight_names) else None
            time_data, signal_data, _sample_rate, shown, total, messages = self._resolve_time_history_signal(i)
            if signal_data is None or time_data is None or len(signal_data) == 0:
                continue

            shown_points = max(shown_points, int(shown))
            total_points = max(total_points, int(total))
            info_messages.extend(messages)

            if primary_signal is None:
                primary_signal = np.asarray(signal_data, dtype=np.float64)
                primary_channel_name = channel_name

            color = colors[plot_count % len(colors)]
            pen = pg.mkPen(color=color, width=1.5)
            if flight_name:
                clean_flight_name = flight_name.replace('flight_', '')
                legend_label = f"{clean_flight_name} - {channel_name}"
            else:
                legend_label = channel_name

            view_suffix = "Filtered" if self.time_filtering_mode == "filtered" else "Raw"
            legend_label = f"{legend_label} ({view_suffix})"

            self.time_plot_widget.plot(time_data, signal_data, pen=pen, name=legend_label)
            plot_count += 1

        resolution_label = "Full Resolution" if self.time_resolution_mode == "full" else "Decimated"
        filtering_label = "Filtered" if self.time_filtering_mode == "filtered" else "Raw"
        self.time_plot_widget.setTitle(
            f"Time History ({resolution_label}, {filtering_label})",
            color='#60a5fa',
            size='12pt',
        )

        if self.channel_units and self.channel_units[0]:
            unit = self.channel_units[0]
            self.time_plot_widget.setLabel('left', f'Amplitude ({unit})', color='#e0e0e0', size='11pt')
        else:
            self.time_plot_widget.setLabel('left', 'Amplitude', color='#e0e0e0', size='11pt')

        if plot_count > 0 and primary_signal is not None:
            rms = float(np.sqrt(np.mean(np.square(primary_signal))))
            p2p = float(np.ptp(primary_signal))
            vmin = float(np.min(primary_signal))
            vmax = float(np.max(primary_signal))
            self.time_points_label.setText(f"Showing {shown_points:,} of {total_points:,} points")
            self.time_stats_label.setText(
                f"Statistics ({primary_channel_name}): RMS={rms:.4g}, P2P={p2p:.4g}, Min={vmin:.4g}, Max={vmax:.4g}"
            )
            self.time_legend.setVisible(True)
        else:
            self.time_points_label.setText("Showing: N/A")
            self.time_stats_label.setText("Statistics: N/A")
            self.time_legend.setVisible(False)

        self._set_info_messages(info_messages)

        if had_previous_data and plot_count > 0:
            try:
                self.time_plot_widget.setXRange(previous_x[0], previous_x[1], padding=0)
                self.time_plot_widget.setYRange(previous_y[0], previous_y[1], padding=0)
            except Exception:
                self.time_plot_widget.enableAutoRange()
        elif plot_count > 0:
            self.time_plot_widget.enableAutoRange()

        # Re-draw event regions after plot reset.
        self._update_event_regions()
    
    def _calculate_psd(self):
        """Calculate PSD with current parameters for all channels using FULL RESOLUTION data."""
        if not self.channel_signal_full and self.signal_data_full is None:
            show_warning(
                self,
                "No Data Loaded",
                "Please load an HDF5 file and select a channel before calculating PSD."
            )
            return

        try:
            df = self.df_spin.value()
            overlap_percent = self.overlap_spin.value()

            # Validate all parameters before calculation
            data_duration = None
            if self.channel_time_full:
                time_min, time_max = self._get_time_bounds()
                data_duration = max(0.0, time_max - time_min)
            elif self.time_data_full is not None and self.sample_rate:
                data_duration = len(self.time_data_full) / self.sample_rate
            params = {
                'overlap': overlap_percent,
                'df': df,
                'maximax_window': self.maximax_window_spin.value() if self.maximax_checkbox.isChecked() else None,
                'data_duration': data_duration
            }

            all_valid, errors = self.validator.validate_all_parameters(params)
            if not all_valid:
                error_msg = "Cannot calculate PSD due to invalid parameters:\n\n"
                error_msg += "\n".join(f"• {err}" for err in errors)
                error_msg += "\n\nPlease correct the highlighted parameters and try again."
                show_warning(self, "Invalid Parameters", error_msg)
                return

            active_events = self._get_active_events_for_calculation()
            if (
                self.event_manager is not None
                and len(getattr(self.event_manager, "events", [])) > 0
                and len(active_events) == 0
            ):
                show_warning(
                    self,
                    "No Events Enabled",
                    "Event Manager has no enabled events. Enable at least one event or clear Event Manager events.",
                )
                return
            if active_events:
                self._update_event_regions()
                self._calculate_event_psds(events=active_events)
                return

            freq_min = self.freq_min_spin.value()
            freq_max = self.freq_max_spin.value()

            # Determine number of channels from selected dataset
            num_channels = len(self.channel_names) if self.channel_names else 0
            if num_channels == 0 and self.signal_data_full is not None:
                num_channels = 1 if self.signal_data_full.ndim == 1 else self.signal_data_full.shape[1]

            self.frequencies = {}
            self.psd_results = {}
            self.rms_values = {}
            skipped_channels = []
            filter_info_messages = []
            first_applied = None

            progress = QProgressDialog("Calculating PSDs...", "Cancel", 0, num_channels, self)
            progress.setWindowTitle("PSD Analysis")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(500)
            progress.setValue(0)
            progress.setStyleSheet("""
                QProgressDialog {
                    background-color: #ffffff;
                }
                QProgressDialog QLabel {
                    color: #000000;
                }
                QProgressDialog QPushButton {
                    color: #000000;
                }
            """)

            try:
                for channel_idx in range(num_channels):
                    if progress.wasCanceled():
                        self.frequencies = {}
                        self.psd_results = {}
                        self.rms_values = {}
                        self._clear_psd_plot()
                        show_warning(self, "Calculation Canceled", "PSD calculation was canceled.")
                        return

                    channel_name = self.channel_names[channel_idx]
                    progress.setLabelText(f"Calculating: {channel_name} ({channel_idx + 1}/{num_channels})")
                    progress.setValue(channel_idx)
                    QApplication.processEvents()

                    _, signal_full, channel_sample_rate = self._get_channel_full(channel_idx)
                    if signal_full is None or channel_sample_rate is None or len(signal_full) == 0:
                        continue

                    try:
                        frequencies, psd, applied_hp, applied_lp, info_messages = self._compute_channel_psd(
                            signal_full,
                            channel_sample_rate,
                        )
                    except Exception as exc:
                        skipped_channels.append(f"{channel_name}: {exc}")
                        continue

                    self.frequencies[channel_name] = frequencies
                    self.psd_results[channel_name] = psd
                    if first_applied is None:
                        first_applied = (applied_hp, applied_lp)
                    filter_info_messages.extend(f"{channel_name}: {msg}" for msg in info_messages)

                    rms = calculate_rms_from_psd(
                        frequencies,
                        psd,
                        freq_min=freq_min,
                        freq_max=freq_max
                    )
                    self.rms_values[channel_name] = rms
            finally:
                progress.setValue(num_channels)
                progress.close()

            if skipped_channels:
                skipped_text = "\n".join(f"• {msg}" for msg in skipped_channels[:12])
                if len(skipped_channels) > 12:
                    skipped_text += f"\n• ... and {len(skipped_channels) - 12} more"
                show_warning(
                    self,
                    "PSD Calculation Warnings",
                    "Some channels were skipped during PSD calculation:\n\n"
                    f"{skipped_text}",
                )

            if first_applied is not None and hasattr(self, "applied_filters_label"):
                self.applied_filters_label.setText(
                    f"Applied filters: HP {first_applied[0]:.2f} Hz, LP {first_applied[1]:.2f} Hz"
                )
            self._set_info_messages(filter_info_messages or self._cached_filter_messages)

            if not self.psd_results:
                self._clear_psd_plot()
                show_warning(self, "No PSD Results", "No valid PSD results were produced for the selected channels.")
                return

            self._update_plot()

        except Exception as e:
            show_critical(self, "Calculation Error", f"Failed to calculate PSD: {e}\n\nPlease try adjusting the frequency resolution or frequency range.")

    def _set_initial_frequency_ticks(self):
        """Set initial frequency axis ticks to powers of 10 for the default range (10-3000 Hz)."""
        # Default range: 10 to 3000 Hz
        tick_values = []
        tick_labels = []

        for power in range(1, 4):  # 10^1, 10^2, 10^3
            freq = 10 ** power
            tick_values.append(np.log10(freq))
            tick_labels.append(str(int(freq)))

        # Set the ticks on the bottom axis
        bottom_axis = self.plot_widget.getPlotItem().getAxis('bottom')
        bottom_axis.setTicks([[(val, label) for val, label in zip(tick_values, tick_labels)]])

    def _set_frequency_ticks(self):
        """Set frequency axis ticks to only show powers of 10."""
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        
        # Generate powers of 10 within the frequency range
        min_power = int(np.floor(np.log10(freq_min)))
        max_power = int(np.ceil(np.log10(freq_max)))
        
        # Create tick values (in log space)
        tick_values = []
        tick_labels = []
        
        for power in range(min_power, max_power + 1):
            freq = 10 ** power
            if freq >= freq_min and freq <= freq_max:
                tick_values.append(np.log10(freq))
                tick_labels.append(str(int(freq)))
        
        # Set the ticks on the bottom axis
        bottom_axis = self.plot_widget.getPlotItem().getAxis('bottom')
        bottom_axis.setTicks([[(val, label) for val, label in zip(tick_values, tick_labels)]])
    
    def _update_plot(self):
        """Update the PSD plot with selected channels."""
        if not self.frequencies or not self.psd_results:
            return
        
        # Clear previous plot
        self._clear_psd_plot()
        
        # Get frequency range for plotting
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        
        # Note: With multi-rate channels, each channel has its own frequency array
        # We'll apply freq_mask per channel in the loop below
        
        # Define colors for different channels
        colors = ['#60a5fa', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
        
        # Check if octave band display is enabled
        use_octave = self.octave_checkbox.isChecked()
        octave_fraction = self.octave_combo.currentData() if use_octave else None
        
        # Plot each selected channel
        plot_count = 0
        for i, checkbox in enumerate(self.channel_checkboxes):
            if checkbox.isChecked():
                channel_name = self.channel_names[i]
                
                # Check if PSD exists for this channel
                if channel_name not in self.psd_results:
                    continue
                
                # Get frequency array for this channel
                frequencies = self.frequencies[channel_name]
                
                # Apply frequency mask for this channel's frequency array
                # Clip to available frequency range (don't error if user sets range beyond data)
                actual_freq_min = max(freq_min, frequencies[0])
                actual_freq_max = min(freq_max, frequencies[-1])
                freq_mask = (frequencies >= actual_freq_min) & (frequencies <= actual_freq_max)
                
                if not np.any(freq_mask):
                    continue  # Skip this channel if no data in range
                
                frequencies_plot = frequencies[freq_mask]
                psd = self.psd_results[channel_name][freq_mask]
                rms = self.rms_values[channel_name]
                unit = self.channel_units[i] if i < len(self.channel_units) else ''
                # Get individual flight name for this channel
                flight_name = self.channel_flight_names[i] if i < len(self.channel_flight_names) else None

                if flight_name:
                    # Remove 'flight_' prefix for cleaner display
                    clean_flight_name = flight_name.replace('flight_', '')
                    legend_prefix = f"{clean_flight_name} - {channel_name}"
                else:
                    legend_prefix = channel_name
                rms_text = self._format_rms_with_unit(rms, unit)
                base_legend_label = f"{legend_prefix}: RMS={rms_text}"

                frequencies_to_plot = frequencies_plot
                psd_to_plot = psd
                legend_label = base_legend_label
                channel_use_octave_plot = False

                # Convert to octave bands if requested
                if use_octave and octave_fraction is not None:
                    try:
                        frequencies_plot_oct, psd_oct = convert_psd_to_octave_bands(
                            frequencies,  # Full frequency array
                            self.psd_results[channel_name],  # Full PSD array
                            octave_fraction=octave_fraction,
                            freq_min=actual_freq_min,
                            freq_max=actual_freq_max
                        )
                        octave_name = self.octave_combo.currentText()
                        frequencies_to_plot = frequencies_plot_oct
                        psd_to_plot = psd_oct
                        legend_label = f"{legend_prefix} ({octave_name}): RMS={rms_text}"
                        channel_use_octave_plot = True
                    except Exception as e:
                        show_warning(
                            self,
                            "Octave Conversion Error",
                            f"Failed to convert to octave bands: {str(e)}\nShowing narrowband data."
                        )

                # Enforce log-safe data for plotting
                plot_mask = (
                    np.isfinite(frequencies_to_plot)
                    & np.isfinite(psd_to_plot)
                    & (frequencies_to_plot > 0)
                    & (psd_to_plot > 0)
                )

                if not np.any(plot_mask):
                    # Fallback to narrowband data for this channel if octave output is not plottable
                    fallback_mask = (
                        np.isfinite(frequencies_plot)
                        & np.isfinite(psd)
                        & (frequencies_plot > 0)
                        & (psd > 0)
                    )
                    if not np.any(fallback_mask):
                        continue

                    frequencies_to_plot = frequencies_plot
                    psd_to_plot = psd
                    legend_label = base_legend_label
                    channel_use_octave_plot = False
                    plot_mask = fallback_mask

                frequencies_to_plot = frequencies_to_plot[plot_mask]
                psd_to_plot = psd_to_plot[plot_mask]
                
                # Plot the PSD
                color = colors[plot_count % len(colors)]
                pen = pg.mkPen(color=color, width=2)
                
                # Use bar plot for octave bands, line plot for narrowband
                if channel_use_octave_plot:
                    # Use combined markers and lines for octave bands
                    # This ensures connectivity even with sparse data points
                    self.plot_widget.plot(
                        frequencies_to_plot,
                        psd_to_plot,
                        pen=pg.mkPen(color=color, width=1.5),  # Solid line connecting points
                        symbol='o',
                        symbolSize=8,
                        symbolBrush=color,
                        symbolPen=pg.mkPen(color=color, width=1),
                        name=legend_label
                    )
                else:
                    self.plot_widget.plot(
                        frequencies_to_plot, 
                        psd_to_plot, 
                        pen=pen,
                        name=legend_label
                    )
                
                plot_count += 1
        
        # Plot comparison curves (reference/spec limit curves)
        for curve in self.comparison_curves:
            if not curve.get('visible', True):
                continue

            # Plot full valid comparison curve (do not trim to PSD parameter range)
            curve_freqs = np.asarray(curve['frequencies'], dtype=np.float64)
            curve_psd = np.asarray(curve['psd'], dtype=np.float64)
            curve_mask = (
                np.isfinite(curve_freqs)
                & np.isfinite(curve_psd)
                & (curve_freqs > 0)
                & (curve_psd > 0)
            )
            if not np.any(curve_mask):
                continue

            curve_freqs_plot = curve_freqs[curve_mask]
            curve_psd_plot = curve_psd[curve_mask]

            # Plot with dashed line style
            pen = pg.mkPen(
                color=curve['color'],
                width=2,
                style=self._curve_line_style_to_qt(curve.get('line_style', 'dashed'))
            )

            # Get RMS value and units for legend
            rms_value = curve.get('rms', 0.0)
            unit = ''
            if self.channel_units and len(self.channel_units) > 0:
                unit = self.channel_units[0]
            else:
                unit = 'g'  # Default to g if no channels loaded
            rms_text = self._format_rms_with_unit(rms_value, unit)

            self.plot_widget.plot(
                curve_freqs_plot,
                curve_psd_plot,
                pen=pen,
                name=f"Ref: {curve['name']}: RMS={rms_text}"
            )
            plot_count += 1

        # Show legend when data is present
        if plot_count > 0:
            self.legend.setVisible(True)

        # Update Y-axis label with units
        if self.channel_units and self.channel_units[0]:
            unit = self.channel_units[0]
            self.plot_widget.setLabel('left', f'PSD ({unit}^2/Hz)', color='#e0e0e0', size='12pt')
        else:
            self.plot_widget.setLabel('left', 'PSD (units^2/Hz)', color='#e0e0e0', size='12pt')
        
        # Enable autorange for PSD plot after data is calculated
        if plot_count > 0:
            self.plot_widget.enableAutoRange()
        
        # Apply axis limits from controls
        self._apply_axis_limits()
    
    def _open_spectrogram(self):
        """Open spectrogram window for selected channels (up to 4) using FULL RESOLUTION data."""
        if (not self.channel_signal_full and self.signal_data_full is None):
            return
        
        # Find all selected channels
        selected_channels = []
        for i, checkbox in enumerate(self.channel_checkboxes):
            if checkbox.isChecked():
                selected_channels.append(i)
        
        if len(selected_channels) == 0:
            show_warning(self, "No Channel Selected", "Please select at least one channel to generate spectrogram.")
            return
        
        # Warn if more than 4 channels selected
        if len(selected_channels) > 4:
            show_warning(
                self, 
                "Too Many Channels", 
                f"You have selected {len(selected_channels)} channels. "
                "Only the first 4 will be displayed in the spectrogram window."
            )
            selected_channels = selected_channels[:4]
        
        # Prepare data for selected channels
        channels_data = []
        channel_sample_rates_list = []  # Store sample rate for each selected channel
        time_data_for_window = None
        for idx in selected_channels:
            channel_name = self.channel_names[idx]
            # Use FULL resolution data for spectrogram calculations
            time_full, signal, channel_sr = self._get_channel_full(idx)
            if signal is None or time_full is None:
                continue
            unit = self.channel_units[idx] if idx < len(self.channel_units) else ''
            # Get flight name for this specific channel (empty for CSV)
            flight_name = self.channel_flight_names[idx] if idx < len(self.channel_flight_names) else ''
            channels_data.append((channel_name, signal, unit, flight_name))
            channel_sample_rates_list.append(channel_sr)
            if time_data_for_window is None:
                time_data_for_window = time_full

        if not channels_data or time_data_for_window is None:
            show_warning(self, "No Data", "Could not prepare channel data for spectrogram.")
            return
        
        # Get current PSD parameters to pass to spectrogram
        window = self.window_combo.currentText().lower()
        df = self.df_spin.value()
        overlap_percent = self.overlap_spin.value()
        efficient_fft = self.efficient_fft_checkbox.isChecked()
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        filter_settings = self._get_statistics_filter_settings()
        remove_mean = False
        mean_window_seconds = 1.0
        
        # Create unique key for this channel combination
        channels_key = "_".join([name for name, _, _, _ in channels_data])
        
        # Create or show spectrogram window
        if channels_key in self.spectrogram_windows:
            window_obj = self.spectrogram_windows[channels_key]
            if hasattr(window_obj, "update_conditioning_defaults"):
                window_obj.update_conditioning_defaults(
                    filter_settings=filter_settings,
                    remove_mean=remove_mean,
                    mean_window_seconds=mean_window_seconds,
                    recalculate=True,
                )
            window_obj.show()
            window_obj.raise_()
            window_obj.activateWindow()
        else:
            window_obj = SpectrogramWindow(
                time_data_for_window,
                channels_data,  # Pass list of (name, signal, unit, flight_name) tuples
                channel_sample_rates_list,  # Pass list of sample rates (one per channel)
                window_type=window,
                df=df,
                overlap_percent=overlap_percent,
                efficient_fft=efficient_fft,
                freq_min=freq_min,
                freq_max=freq_max,
                filter_settings=filter_settings,
                remove_mean=remove_mean,
                mean_window_seconds=mean_window_seconds,
            )
            window_obj.show()
            self.spectrogram_windows[channels_key] = window_obj
    
    def _open_event_manager(self):
        """Open the Event Manager window."""
        if not self.channel_time_full and self.time_data_full is None:
            return

        min_time, max_time = self._get_time_bounds()
        if max_time <= min_time:
            return
        
        # Create event manager if it doesn't exist
        if self.event_manager is None:
            self.event_manager = EventManagerWindow(max_time=max_time, min_time=min_time)
            
            # Connect signals
            self.event_manager.events_updated.connect(self._on_events_updated)
            self.event_manager.interactive_mode_changed.connect(self._on_interactive_mode_changed)
        else:
            self.event_manager.set_time_bounds(min_time=min_time, max_time=max_time)
        
        # Show the window
        self.event_manager.show()
        self.event_manager.raise_()
        self.event_manager.activateWindow()
    
    def _on_events_updated(self, events):
        """
        Handle events updated from Event Manager.
        
        Args:
            events: List of Event objects
        """
        self.events = events
        
        # Enable/disable clear events button based on whether events exist
        # Don't count the "Full" event as it's always present
        non_full_events = [e for e in events if e.name != "Full"]
        self.clear_events_button.setEnabled(len(non_full_events) > 0)
        
        # Update visualization
        self._update_event_regions()
        
        # Calculate PSDs for all events
        self._calculate_event_psds(events=events)
    
    def _on_interactive_mode_changed(self, enabled):
        """
        Handle interactive selection mode toggle.
        
        Args:
            enabled: True if interactive mode is enabled
        """
        self.interactive_selection_mode = enabled
        
        # Reset selection state
        self.selection_start = None
        if self.temp_selection_line is not None:
            self.time_plot_widget.removeItem(self.temp_selection_line)
            self.temp_selection_line = None
    
    def _on_time_plot_clicked(self, event):
        """
        Handle click on time history plot for interactive event selection.
        
        Args:
            event: Mouse click event
        """
        if not self.interactive_selection_mode:
            return
        
        # Check if click is within plot area
        if not self.time_plot_widget.sceneBoundingRect().contains(event.scenePos()):
            return
        
        # Get time value at click position
        mouse_point = self.time_plot_widget.plotItem.vb.mapSceneToView(event.scenePos())
        time_value = mouse_point.x()
        
        # Clamp to valid range
        min_time, max_time = self._get_time_bounds()
        time_value = max(min_time, min(time_value, max_time))
        
        if self.selection_start is None:
            # First click - set start time
            self.selection_start = time_value
            
            # Add temporary vertical line
            self.temp_selection_line = pg.InfiniteLine(
                pos=time_value,
                angle=90,
                pen=pg.mkPen('#60a5fa', width=2, style=Qt.PenStyle.DashLine),
                label='Start'
            )
            self.time_plot_widget.addItem(self.temp_selection_line)
        
        else:
            # Second click - set end time and create event
            end_time = time_value
            
            # Remove temporary line
            if self.temp_selection_line is not None:
                self.time_plot_widget.removeItem(self.temp_selection_line)
                self.temp_selection_line = None
            
            # Ensure start < end
            if self.selection_start > end_time:
                self.selection_start, end_time = end_time, self.selection_start
            
            # Add event to Event Manager
            if self.event_manager is not None:
                self.event_manager.add_event_from_selection(self.selection_start, end_time)
            
            # Reset selection
            self.selection_start = None
    
    def _update_event_regions(self):
        """Update visual representation of events on time history plot."""
        # Remove existing regions
        for region in self.event_regions:
            self.time_plot_widget.removeItem(region)
        self.event_regions.clear()
        
        # Add new regions
        colors = [
            (96, 165, 250, 50),   # Blue
            (16, 185, 129, 50),   # Green
            (245, 158, 11, 50),   # Orange
            (239, 68, 68, 50),    # Red
            (139, 92, 246, 50),   # Purple
            (236, 72, 153, 50),   # Pink
        ]
        
        for i, event in enumerate(self.events):
            # Skip "Full" event
            if event.name == "Full":
                continue
            
            color = colors[i % len(colors)]
            
            # Create shaded region
            region = pg.LinearRegionItem(
                values=[event.start_time, event.end_time],
                brush=pg.mkBrush(*color),
                pen=pg.mkPen(color[:3] + (150,), width=2),
                movable=False
            )
            
            self.time_plot_widget.addItem(region)
            self.event_regions.append(region)
    
    def _calculate_event_psds(self, events=None):
        """Calculate PSDs for active events using full-resolution channel data."""
        if (not self.channel_signal_full and self.signal_data_full is None):
            return

        active_events = list(events) if events is not None else self._get_active_events_for_calculation()
        self.events = active_events
        if not active_events:
            self.frequencies = {}
            self.psd_results = {}
            self.rms_values = {}
            self._clear_psd_plot()
            return

        try:
            freq_min = self.freq_min_spin.value()
            freq_max = self.freq_max_spin.value()

            num_channels = len(self.channel_names) if self.channel_names else 0
            if num_channels == 0:
                return

            self.frequencies = {}
            self.psd_results = {}
            self.rms_values = {}
            skipped_entries = []
            filter_info_messages = []

            for event in active_events:
                for channel_idx in range(num_channels):
                    channel_name = self.channel_names[channel_idx]
                    time_full, signal_full, channel_sample_rate = self._get_channel_full(channel_idx)
                    if time_full is None or signal_full is None or len(signal_full) == 0:
                        continue
                    if channel_sample_rate is None or channel_sample_rate <= 0:
                        continue

                    start_idx = int(np.searchsorted(time_full, event.start_time, side='left'))
                    end_idx = int(np.searchsorted(time_full, event.end_time, side='right'))
                    start_idx = max(0, min(start_idx, len(signal_full)))
                    end_idx = max(start_idx, min(end_idx, len(signal_full)))
                    if end_idx - start_idx < 2:
                        skipped_entries.append(f"{event.name} / {channel_name}: insufficient samples")
                        continue

                    signal_segment = signal_full[start_idx:end_idx]

                    try:
                        frequencies, psd, _hp, _lp, info_messages = self._compute_channel_psd(
                            signal_segment,
                            channel_sample_rate,
                        )
                    except Exception as exc:
                        skipped_entries.append(f"{event.name} / {channel_name}: {exc}")
                        continue

                    self.frequencies[channel_name] = frequencies
                    key = f"{event.name}_{channel_name}"
                    self.psd_results[key] = psd
                    self.rms_values[key] = calculate_rms_from_psd(
                        frequencies,
                        psd,
                        freq_min=freq_min,
                        freq_max=freq_max,
                    )
                    filter_info_messages.extend(
                        f"{event.name} / {channel_name}: {msg}" for msg in info_messages
                    )

            if skipped_entries:
                skipped_text = "\n".join(f"• {msg}" for msg in skipped_entries[:12])
                if len(skipped_entries) > 12:
                    skipped_text += f"\n• ... and {len(skipped_entries) - 12} more"
                show_warning(
                    self,
                    "Event PSD Warnings",
                    "Some event/channel PSD calculations were skipped:\n\n"
                    f"{skipped_text}",
                )

            self._set_info_messages(filter_info_messages or self._cached_filter_messages)

            if not self.psd_results:
                self._clear_psd_plot()
                show_warning(
                    self,
                    "No Event PSD Results",
                    "No valid PSD results were produced for the enabled events.",
                )
                return

            self._update_plot_with_events()

        except Exception as e:
            show_critical(self, "Calculation Error", f"Failed to calculate event PSDs: {e}")

    def _update_plot_with_events(self):
        """Update the PSD plot with event-based PSDs."""
        if not self.frequencies or not self.psd_results:
            return
        
        # Clear previous plot
        self._clear_psd_plot()
        
        # Get frequency range for plotting
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        
        # Define colors for different events
        colors = ['#60a5fa', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
        
        # Plot PSDs for each event and selected channel
        plot_count = 0
        for event in self.events:
            for i, checkbox in enumerate(self.channel_checkboxes):
                if checkbox.isChecked():
                    channel_name = self.channel_names[i]
                    key = f"{event.name}_{channel_name}"
                    
                    # Check if PSD exists for this event + channel
                    if key not in self.psd_results:
                        continue
                    
                    # Get frequency array for this channel
                    frequencies = self.frequencies[channel_name]
                    
                    # Apply frequency mask for this channel's frequency array
                    freq_mask = (frequencies >= freq_min) & (frequencies <= freq_max)
                    
                    if not np.any(freq_mask):
                        continue
                    
                    frequencies_plot = frequencies[freq_mask]
                    psd = self.psd_results[key][freq_mask]
                    rms = self.rms_values[key]
                    unit = self.channel_units[i] if i < len(self.channel_units) else ''
                    
                    # Create legend label with event name, channel, and RMS
                    if len(self.events) > 1:
                        # Show event name when multiple events
                        if unit:
                            legend_label = f"{event.name} - {channel_name}: RMS={rms:.2f} {unit}"
                        else:
                            legend_label = f"{event.name} - {channel_name}: RMS={rms:.2f}"
                    else:
                        # Just channel name for single event
                        if unit:
                            legend_label = f"{channel_name}: RMS={rms:.2f} {unit}"
                        else:
                            legend_label = f"{channel_name}: RMS={rms:.2f}"
                    
                    # Plot the PSD
                    color = colors[plot_count % len(colors)]
                    
                    # Use dashed line for "Full" event
                    if event.name == "Full":
                        pen = pg.mkPen(color=color, width=2, style=Qt.PenStyle.DashLine)
                    else:
                        pen = pg.mkPen(color=color, width=2)
                    
                    self.plot_widget.plot(
                        frequencies_plot, 
                        psd, 
                        pen=pen,
                        name=legend_label
                    )
                    
                    plot_count += 1
        
        # Update Y-axis label with units
        if self.channel_units and self.channel_units[0]:
            unit = self.channel_units[0]
            self.plot_widget.setLabel('left', f'PSD ({unit}^2/Hz)', color='#e0e0e0', size='12pt')
        else:
            self.plot_widget.setLabel('left', 'PSD (units^2/Hz)', color='#e0e0e0', size='12pt')
        
        # Set X-axis range
        self.plot_widget.setXRange(np.log10(freq_min), np.log10(freq_max))
        
        # Set custom frequency ticks
        self._set_frequency_ticks()
        
        # Disable auto-range
        self.plot_widget.getPlotItem().vb.enableAutoRange(enable=False)
    
    def _apply_axis_limits(self):
        """Apply user-specified axis limits to the PSD plot."""
        # Get limits from text fields and parse
        try:
            x_min = float(self.x_min_edit.text())
            x_max = float(self.x_max_edit.text())
            y_min = float(self.y_min_edit.text())
            y_max = float(self.y_max_edit.text())
        except ValueError as e:
            show_warning(self, "Invalid Input", 
                        f"Please enter valid numbers (standard or scientific notation).\nError: {e}")
            return
        
        # Validate limits
        if x_min >= x_max:
            show_warning(self, "Invalid Limits", "X-axis minimum must be less than maximum.")
            return
        
        if y_min >= y_max:
            show_warning(self, "Invalid Limits", "Y-axis minimum must be less than maximum.")
            return
        
        # Validate positive values for log scale
        if x_min <= 0 or x_max <= 0:
            show_warning(self, "Invalid Limits", "X-axis limits must be positive for log scale.")
            return
        
        if y_min <= 0 or y_max <= 0:
            show_warning(self, "Invalid Limits", "Y-axis limits must be positive for log scale.")
            return
        
        # Set X-axis range (log scale)
        try:
            log_x_min = np.log10(x_min)
            log_x_max = np.log10(x_max)
            if np.isfinite(log_x_min) and np.isfinite(log_x_max):
                self.plot_widget.setXRange(log_x_min, log_x_max)
            else:
                show_warning(self, "Invalid Range", "X-axis range resulted in invalid log values.")
                return
        except Exception as e:
            show_warning(self, "Error", f"Failed to set X-axis range: {e}")
            return
        
        # Set Y-axis range (log scale)
        try:
            log_y_min = np.log10(y_min)
            log_y_max = np.log10(y_max)
            if np.isfinite(log_y_min) and np.isfinite(log_y_max):
                self.plot_widget.setYRange(log_y_min, log_y_max)
            else:
                show_warning(self, "Invalid Range", "Y-axis range resulted in invalid log values.")
                return
        except Exception as e:
            show_warning(self, "Error", f"Failed to set Y-axis range: {e}")
            return
        
        # Update frequency ticks
        self._set_frequency_ticks()
        
        # Disable auto-range to maintain user-specified limits
        self.plot_widget.getPlotItem().vb.enableAutoRange(enable=False)
    
    def _auto_fit_axes(self):
        """Auto-fit axes based on current data."""
        if not self.frequencies or not self.psd_results:
            show_information(self, "No Data", "Please calculate PSD first before using auto-fit.")
            return
        
        # Get frequency range from data
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        
        # Find min/max PSD values across all selected channels
        psd_min = np.inf
        psd_max = -np.inf
        
        for i, checkbox in enumerate(self.channel_checkboxes):
            if checkbox.isChecked():
                channel_name = self.channel_names[i]
                
                if channel_name in self.psd_results:
                    # Get frequency array for this channel
                    frequencies = self.frequencies[channel_name]
                    
                    # Apply frequency mask for this channel
                    freq_mask = (frequencies >= freq_min) & (frequencies <= freq_max)
                    
                    if not np.any(freq_mask):
                        continue
                    
                    psd = self.psd_results[channel_name][freq_mask]
                    
                    # Filter out zeros and negative values for log scale
                    psd_positive = psd[psd > 0]
                    
                    if len(psd_positive) > 0:
                        psd_min = min(psd_min, np.min(psd_positive))
                        psd_max = max(psd_max, np.max(psd_positive))
        
        # If we found valid data, update limits
        if psd_min != np.inf and psd_max != -np.inf:
            # Add some margin (10% on log scale)
            log_range = np.log10(psd_max) - np.log10(psd_min)
            margin = log_range * 0.1
            
            y_min_auto = 10 ** (np.log10(psd_min) - margin)
            y_max_auto = 10 ** (np.log10(psd_max) + margin)
            
            # Update text fields
            self.y_min_edit.setText(f"{y_min_auto:.2e}")
            self.y_max_edit.setText(f"{y_max_auto:.2e}")
            
            # Apply the new limits
            self._apply_axis_limits()
        else:
            show_warning(self, "No Valid Data", "No positive PSD values found for auto-fit.")
    
    def _load_hdf5_file(self):
        """Load HDF5 file and open flight navigator."""
        try:
            # Open file dialog
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load HDF5 File",
                str(Path.home()),
                "HDF5 Files (*.hdf5 *.h5);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # Close existing loader if any
            if self.hdf5_loader is not None:
                self.hdf5_loader.close()
            
            # Create new loader
            self.hdf5_loader = HDF5FlightDataLoader(file_path)
            
            # Open flight navigator
            self.flight_navigator = FlightNavigator(self.hdf5_loader, self)
            self.flight_navigator.data_selected.connect(self._on_hdf5_data_selected)
            self.flight_navigator.show()
            
        except FileNotFoundError:
            show_critical(
                self, 
                "File Not Found", 
                "The selected HDF5 file could not be found.\n\n"
                "Please verify the file path and try again."
            )
        except PermissionError:
            show_critical(
                self, 
                "Permission Denied", 
                "Unable to access the HDF5 file due to insufficient permissions.\n\n"
                "Please check file permissions and try again."
            )
        except OSError as e:
            if "corrupted" in str(e).lower() or "invalid" in str(e).lower():
                show_critical(
                    self, 
                    "Corrupted File", 
                    "The HDF5 file appears to be corrupted or invalid.\n\n"
                    f"Error details: {e}\n\n"
                    "Try using a different file or re-exporting the data."
                )
            else:
                show_critical(
                    self, 
                    "File System Error", 
                    f"An error occurred while accessing the file:\n\n{e}\n\n"
                    "This may be due to insufficient disk space or file system issues."
                )
        except MemoryError:
            show_critical(
                self, 
                "Insufficient Memory", 
                "Not enough memory to load this HDF5 file.\n\n"
                "Try closing other applications or selecting fewer channels."
            )
        except Exception as e:
            show_critical(
                self, 
                "Load Error", 
                f"Failed to load HDF5 file:\n\n{e}\n\n"
                "If this problem persists, please verify the file format is correct."
            )
    
    def _on_hdf5_data_selected(self, selected_items):
        """
        Handle data selection from flight navigator.
        
        Parameters:
        -----------
        selected_items : list of tuples
            List of (flight_key, channel_key, channel_info) tuples
        """
        try:
            print("\n=== HDF5 DATA LOADING DEBUG ===")
            print(f"Selected items: {len(selected_items)}")
            
            if not selected_items:
                print("No items selected")
                return
            
            # Load all selected channels
            print(f"Loading {len(selected_items)} channel(s)...")
            
            all_time_full = []
            all_time_display = []
            all_signals_full = []
            all_signals_display = []
            all_channel_names = []
            all_channel_units = []
            all_sample_rates = []  # Store sample rate for each channel
            sample_rate = None  # Reference sample rate (will be max of all)
            decimation_factor = 1
            flight_info = []
            
            # First pass: collect all data and find max sample rate
            channel_data_list = []
            for idx, (flight_key, channel_key, channel_info) in enumerate(selected_items):
                print(f"\nChannel {idx+1}/{len(selected_items)}:")
                print(f"  Flight key: {flight_key}")
                print(f"  Channel key: {channel_key}")
                print(f"  Sample rate: {channel_info.sample_rate} Hz")
                
                # Load data - returns dict with both full and decimated data
                result = self.hdf5_loader.load_channel_data(flight_key, channel_key, decimate_for_display=True)
                print(f"  Full data: time shape={result['time_full'].shape}, signal shape={result['data_full'].shape}")
                print(f"  Display data: time shape={result['time_display'].shape}, signal shape={result['data_display'].shape}")
                print(f"  Decimation factor: {result.get('decimation_factor', 1)}")
                
                channel_data_list.append({
                    'result': result,
                    'channel_key': channel_key,
                    'flight_key': flight_key,
                    'units': channel_info.units
                })
                
                # Track max sample rate
                if sample_rate is None or result['sample_rate'] > sample_rate:
                    sample_rate = result['sample_rate']
                decimation_factor = max(decimation_factor, result.get('decimation_factor', 1))
            
            print(f"\nReference sample rate (max): {sample_rate} Hz")
            
            # Second pass: collect per-channel data (no padding/resampling)
            for idx, ch_data in enumerate(channel_data_list):
                result = ch_data['result']

                # Check if sample rates differ
                if result['sample_rate'] != sample_rate:
                    print(f"  Channel {idx+1}: Different sample rate {result['sample_rate']} Hz (reference: {sample_rate} Hz)")
                    print(f"    Multi-rate support: Each channel will use its own sample rate for PSD calculation")

                all_time_full.append(result['time_full'])
                all_time_display.append(result['time_display'])
                all_signals_full.append(result['data_full'])
                all_signals_display.append(result['data_display'])
                all_channel_names.append(ch_data['channel_key'])
                all_channel_units.append(ch_data['units'])
                all_sample_rates.append(result['sample_rate'])  # Store each channel's sample rate
                flight_info.append(ch_data['flight_key'])

            # Store canonical per-channel data for all mixed-rate operations
            self.channel_time_full = all_time_full
            self.channel_time_display = all_time_display
            self.channel_signal_full = all_signals_full
            self.channel_signal_display = all_signals_display

            # Keep legacy references for compatibility with older code paths.
            self.time_data_full = all_time_full[0] if all_time_full else None
            self.time_data_display = all_time_display[0] if all_time_display else None
            if len(all_signals_full) == 1:
                self.signal_data_full = all_signals_full[0].reshape(-1, 1)
                self.signal_data_display = all_signals_display[0].reshape(-1, 1)
            else:
                same_full_length = len(set(len(sig) for sig in all_signals_full)) == 1
                same_display_length = len(set(len(sig) for sig in all_signals_display)) == 1
                same_full_time = all(np.array_equal(t, all_time_full[0]) for t in all_time_full[1:]) if len(all_time_full) > 1 else True
                same_display_time = all(np.array_equal(t, all_time_display[0]) for t in all_time_display[1:]) if len(all_time_display) > 1 else True
                if same_full_length and same_full_time:
                    self.signal_data_full = np.column_stack(all_signals_full)
                else:
                    self.signal_data_full = all_signals_full[0].reshape(-1, 1)
                if same_display_length and same_display_time:
                    self.signal_data_display = np.column_stack(all_signals_display)
                else:
                    self.signal_data_display = all_signals_display[0].reshape(-1, 1)

            self.sample_rate = sample_rate  # Reference sample rate (max)
            self.channel_names = all_channel_names
            self.channel_units = all_channel_units
            self.channel_sample_rates = all_sample_rates  # Store each channel's sample rate
            self.channel_flight_names = flight_info  # Store flight name for each channel
            
            # Update validator with Nyquist frequency
            if self.sample_rate is not None:
                nyquist_freq = self.sample_rate / 2
                self.validator.set_nyquist_frequency(nyquist_freq)
                print(f"Validator: Nyquist frequency set to {nyquist_freq} Hz")
            
            # Create file label and set flight name
            if len(set(flight_info)) == 1:
                self.current_file = f"{flight_info[0]} ({len(selected_items)} channels)"
                self.flight_name = flight_info[0]  # Single flight name
            else:
                self.current_file = f"Multiple flights ({len(selected_items)} channels)"
                self.flight_name = "Multiple flights"  # Multiple flights
            
            print(f"\nLoaded channels: {len(self.channel_names)}")
            for idx, (name, sr, sig, t) in enumerate(zip(self.channel_names, self.channel_sample_rates, self.channel_signal_full, self.channel_time_full), start=1):
                print(f"  [{idx}] {name}: sr={sr}, samples={len(sig)}, t=[{float(t[0]):.3f}, {float(t[-1]):.3f}]")
            
            # Calculate global duration from per-channel time bounds
            time_min, time_max = self._get_time_bounds()
            duration = max(0.0, time_max - time_min)
            
            # Update UI
            self.file_label.setText(f"Loaded: {self.current_file}")
            if decimation_factor > 1:
                self.info_label.setText(
                    f"Reference SR: {self.sample_rate:.0f} Hz | "
                    f"Duration: {duration:.2f} s | "
                    f"Channels: {len(self.channel_names)} | "
                    f"Decimated {decimation_factor}x for display"
                )
            else:
                self.info_label.setText(
                    f"Reference SR: {self.sample_rate:.0f} Hz | "
                    f"Duration: {duration:.2f} s | "
                    f"Channels: {len(self.channel_names)} (Full resolution)"
                )
            
            # Create channel selection checkboxes
            self._create_channel_checkboxes()
            
            # Enable buttons
            self.calc_button.setEnabled(True)
            self.spec_button.setEnabled(True)
            self.event_button.setEnabled(True)
            self.channel_selector_button.setEnabled(True)
            self.cross_spectrum_button.setEnabled(len(self.channel_names) >= 2)
            self.report_button.setEnabled(PPTX_AVAILABLE)
            self.statistics_button.setEnabled(True)

            # Clear previous results
            self.frequencies = {}
            self.psd_results = {}
            self.rms_values = {}
            self._clear_psd_plot()
            
            # Reset and rebuild adaptive time-history cache.
            self._reset_time_history_defaults()
            self._update_filter_info_display()
            self._build_time_history_cache()
            self._plot_time_history()
            
            # Update nperseg display
            self._update_nperseg_from_df()
            
            # Create message based on decimation
            if decimation_factor > 1:
                message = (
                    f"Successfully loaded {len(self.channel_names)} channel(s)\n"
                    f"Channels: {', '.join(self.channel_names)}\n"
                    f"Reference Sample Rate: {self.sample_rate:.0f} Hz\n"
                    f"Duration: {duration:.2f} seconds\n"
                    f"Time Range: {time_min:.3f} to {time_max:.3f} s\n\n"
                    f"Note: Data decimated {decimation_factor}x for display.\n"
                    f"Full resolution will be used for PSD calculations."
                )
            else:
                message = (
                    f"Successfully loaded {len(self.channel_names)} channel(s)\n"
                    f"Channels: {', '.join(self.channel_names)}\n"
                    f"Reference Sample Rate: {self.sample_rate:.0f} Hz\n"
                    f"Duration: {duration:.2f} seconds\n"
                    f"Time Range: {time_min:.3f} to {time_max:.3f} s"
                )
            
            show_information(self, "Data Loaded", message)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"\n=== ERROR IN HDF5 LOADING ===")
            print(error_details)
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            show_critical(self, "Load Error", f"Failed to load HDF5 data: {e}\n\nSee console for full traceback.")
    
    def _on_maximax_toggled(self):
        """Handle maximax checkbox toggle."""
        is_maximax = self.maximax_checkbox.isChecked()
        
        # Enable/disable maximax-specific controls
        self.maximax_window_spin.setEnabled(is_maximax)
        self.maximax_overlap_spin.setEnabled(is_maximax)
        
        # Update tooltip on calculate button
        if is_maximax:
            self.calc_button.setToolTip(
                "Calculate Maximax PSD (envelope of sliding window PSDs)"
            )
        else:
            self.calc_button.setToolTip(
                "Calculate averaged PSD using Welch's method"
            )

    
    def _on_octave_display_changed(self):
        """Handle octave band display checkbox state change."""
        is_enabled = self.octave_checkbox.isChecked()
        self.octave_combo.setEnabled(is_enabled)
        
        # Re-plot if we have data
        if self.frequencies and self.psd_results:
            self._update_plot()
    
    def _on_octave_fraction_changed(self):
        """Handle octave fraction selection change."""
        # Re-plot if we have data and octave display is enabled
        if self.octave_checkbox.isChecked() and self.frequencies and self.psd_results:
            self._update_plot()

    def _clear_events(self):
        """Clear all events and reset plots to full data."""
        # Clear events list (keep only "Full" event if it exists)
        self.events = [e for e in self.events if e.name == "Full"]
        
        # Clear event regions from time plot
        for region in self.event_regions:
            self.time_plot_widget.removeItem(region)
        self.event_regions.clear()
        
        # Disable clear events button
        self.clear_events_button.setEnabled(False)
        
        # Update event manager if it exists
        if self.event_manager is not None:
            self.event_manager.clear_all_events()
        
        # Reset interactive selection mode
        self.interactive_selection_mode = False
        self.selection_start = None
        if self.temp_selection_line is not None:
            self.time_plot_widget.removeItem(self.temp_selection_line)
            self.temp_selection_line = None
        
        # Clear event-based PSD results
        self.psd_results = {}
        self.rms_values = {}
        self.frequencies = {}
        
        # Clear PSD plot
        self._clear_psd_plot()
        
        # Show information message
        show_information(self, "Events Cleared", "All events have been removed. Click 'Calculate PSD' to recalculate with full data.")


