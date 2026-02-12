"""
PowerPoint Output Module for Batch Processing

Generates PowerPoint presentations from batch processing results with
flexible layout options and consistent light-theme plotting.
"""

import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, List, Optional

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from spectral_edge.utils.report_generator import ReportGenerator
from spectral_edge.utils.plot_theme import (
    apply_light_matplotlib_theme,
    style_axes,
    style_colorbar,
    apply_axis_styling,
    BASE_FONT_SIZE,
    LINE_COLOR,
    get_watermark_text,
)
from spectral_edge.batch.output_psd import apply_frequency_spacing
from spectral_edge.batch.spectrogram_generator import generate_spectrogram
from spectral_edge.batch.statistics import compute_statistics, plot_pdf, plot_running_stat
from spectral_edge.utils.hdf5_loader import HDF5FlightDataLoader
from spectral_edge.batch.csv_loader import load_csv_files
from spectral_edge.utils.signal_conditioning import apply_processing_pipeline, build_processing_note
from spectral_edge.utils.reference_curves import prepare_reference_curves_for_plot, REFERENCE_CURVE_COLOR_PALETTE

logger = logging.getLogger(__name__)


def _sanitize_filename_component(value: Optional[str]) -> str:
    """Return a filesystem-safe filename component."""
    text = (value or "").strip()
    if not text:
        return ""
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in text)
    return safe.strip("_")


def _build_batch_filter_settings(config: "BatchConfig") -> Dict[str, object]:
    """Convert batch filter config into shared conditioning settings."""
    fc = config.filter_config
    user_highpass = getattr(fc, "user_highpass_hz", None)
    user_lowpass = getattr(fc, "user_lowpass_hz", None)
    filter_type = str(getattr(fc, "filter_type", "bandpass")).strip().lower()
    if user_highpass is None and filter_type in {"highpass", "bandpass"}:
        user_highpass = getattr(fc, "cutoff_low", None)
    if user_lowpass is None and filter_type in {"lowpass", "bandpass"}:
        user_lowpass = getattr(fc, "cutoff_high", None)
    return {
        "enabled": bool(getattr(fc, "enabled", False)),
        "user_highpass_hz": user_highpass,
        "user_lowpass_hz": user_lowpass,
    }


def generate_powerpoint_report(
    results,  # BatchProcessingResult object
    output_path: str,
    config: 'BatchConfig',
    title: str = "Batch PSD Processing Report"
) -> str:
    """
    Generate a PowerPoint presentation from batch processing results.
    """
    try:
        report_gen = ReportGenerator(
            title=title,
            watermark_text=get_watermark_text(),
            watermark_scope="plot_slides",
        )
        report_gen.add_title_slide(
            subtitle=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        if config.powerpoint_config.include_parameters:
            _add_config_slide(report_gen, config, results)

        layout = config.powerpoint_config.layout
        include_time = _layout_includes_time(layout)
        include_psd = _layout_includes_psd(layout)
        include_spec = _layout_includes_spectrogram(layout)
        include_stats = config.powerpoint_config.include_statistics
        conditioning_filter_settings = _build_batch_filter_settings(config)
        conditioning_note = build_processing_note(
            conditioning_filter_settings,
            remove_mean=False,
            mean_window_seconds=1.0,
        )

        events = _get_event_definitions(config)

        time_history_cache = {}
        if include_time or include_stats or include_spec:
            time_history_cache = _load_time_history_cache(results, config, events)

        for event_name, start_time, end_time in events:
            for (flight_key, channel_key), event_dict in results.channel_results.items():
                if event_name not in event_dict:
                    continue

                event_result = event_dict[event_name]
                metadata = event_result.get('metadata', {})
                units = metadata.get('units', '')
                sample_rate = metadata.get('sample_rate', None)

                channel_label = f"{flight_key}/{channel_key}"
                slide_title = f"{flight_key} | {event_name} | {channel_key}"

                time_data = None
                signal_data = None
                time_full_slice = None
                signal_full_slice = None
                conditioned_signal_full_slice = None
                if (flight_key, channel_key) in time_history_cache:
                    time_full, signal_full, units_loaded, sample_rate_loaded = time_history_cache[(flight_key, channel_key)]
                    if not units:
                        units = units_loaded
                    if sample_rate is None:
                        sample_rate = sample_rate_loaded
                    time_full_slice, signal_full_slice = _slice_event_signal(
                        time_full, signal_full, start_time, end_time
                    )
                    if sample_rate is None and time_full_slice is not None and len(time_full_slice) > 1:
                        sample_rate = float(1.0 / np.median(np.diff(time_full_slice)))
                    if signal_full_slice is not None and sample_rate and len(signal_full_slice) > 0:
                        conditioned_signal_full_slice = apply_processing_pipeline(
                            signal_full_slice,
                            sample_rate,
                            filter_settings=conditioning_filter_settings,
                            remove_mean=False,
                            mean_window_seconds=1.0,
                        )
                    else:
                        conditioned_signal_full_slice = signal_full_slice
                    time_data, signal_data = _decimate_time_series(time_full_slice, conditioned_signal_full_slice)

                if sample_rate is None and time_full_slice is not None and len(time_full_slice) > 1:
                    sample_rate = float(1.0 / np.median(np.diff(time_full_slice)))

                plot_channel_title = f"{flight_key}, {event_name} - {channel_key}"
                # PSD plot
                psd_image = None
                if include_psd:
                    psd_role = _get_slot_role(layout, "psd")
                    psd_image = _create_psd_plot(
                        event_result,
                        config,
                        units,
                        plot_title=f"PSD: {plot_channel_title}",
                        layout=layout,
                        slot_role=psd_role,
                    )

                # Time history plot
                time_image = None
                if include_time and time_data is not None and signal_data is not None and len(time_data) > 0:
                    time_role = _get_slot_role(layout, "time")
                    time_image = _create_time_history_plot(
                        time_data,
                        signal_data,
                        units,
                        plot_title=f"Time History: {plot_channel_title}",
                        layout=layout,
                        slot_role=time_role,
                    )

                # Spectrogram plot
                spec_image = None
                if include_spec:
                    spectrogram_data = event_result.get('spectrogram')
                    if spectrogram_data is None and time_full_slice is not None and conditioned_signal_full_slice is not None and sample_rate and len(time_full_slice) > 0:
                        try:
                            spec_freqs, spec_times, Sxx = generate_spectrogram(
                                conditioned_signal_full_slice,
                                sample_rate,
                                desired_df=config.spectrogram_config.desired_df,
                                overlap_percent=config.spectrogram_config.overlap_percent,
                                snr_threshold=config.spectrogram_config.snr_threshold,
                                use_efficient_fft=True
                            )
                            spectrogram_data = {
                                'frequencies': spec_freqs,
                                'times': spec_times,
                                'Sxx': Sxx
                            }
                        except Exception as exc:
                            logger.warning(f"Spectrogram generation failed for {channel_label}/{event_name}: {exc}")

                    if spectrogram_data is not None:
                        spec_role = _get_slot_role(layout, "spectrogram")
                        spec_image = _create_spectrogram_plot(
                            spectrogram_data,
                            config,
                            plot_title=f"Spectrogram: {plot_channel_title}",
                            layout=layout,
                            slot_role=spec_role,
                        )

                # Slide generation
                if layout == "time_psd_spec_one_slide":
                    if time_image and psd_image and spec_image:
                        left_params, right_params = _build_plot_parameter_boxes(
                            config,
                            event_name,
                            start_time,
                            end_time,
                            sample_rate,
                            units,
                            event_result=event_result,
                        )
                        report_gen.add_three_plot_slide(
                            slide_title,
                            time_image,
                            psd_image,
                            spec_image,
                            left_params_text=left_params,
                            right_params_text=right_params
                        )
                elif layout == "all_plots_individual":
                    if time_image:
                        report_gen.add_single_plot_slide(time_image, f"Time History | {slide_title}")
                    if psd_image:
                        report_gen.add_single_plot_slide(psd_image, f"PSD | {slide_title}")
                    if spec_image:
                        report_gen.add_single_plot_slide(spec_image, f"Spectrogram | {slide_title}")
                elif layout == "psd_spec_side_by_side":
                    if psd_image and spec_image:
                        report_gen.add_two_plot_slide(slide_title, psd_image, spec_image)
                elif layout == "psd_only":
                    if psd_image:
                        report_gen.add_single_plot_slide(psd_image, slide_title)
                elif layout == "spectrogram_only":
                    if spec_image:
                        report_gen.add_single_plot_slide(spec_image, slide_title)
                elif layout == "time_history_only":
                    if time_image:
                        report_gen.add_single_plot_slide(time_image, slide_title)

                # Statistics slide
                if include_stats and time_full_slice is not None and conditioned_signal_full_slice is not None and len(time_full_slice) > 0:
                    stats = compute_statistics(conditioned_signal_full_slice, sample_rate, config.statistics_config)
                    pdf_fig, _ = plot_pdf(stats['pdf'], config.statistics_config)
                    pdf_bytes = _fig_to_bytes(pdf_fig)

                    running_mean_fig, _ = plot_running_stat(stats['running'], "mean", "Running Mean", "Mean")
                    running_std_fig, _ = plot_running_stat(stats['running'], "std", "Running Std", "Std")
                    running_skew_fig, _ = plot_running_stat(stats['running'], "skewness", "Running Skewness", "Skewness")
                    running_kurt_fig, _ = plot_running_stat(stats['running'], "kurtosis", "Running Kurtosis", "Kurtosis")

                    mean_bytes = _fig_to_bytes(running_mean_fig)
                    std_bytes = _fig_to_bytes(running_std_fig)
                    skew_bytes = _fig_to_bytes(running_skew_fig)
                    kurt_bytes = _fig_to_bytes(running_kurt_fig)

                    summary = _format_stats_summary_dict(stats['overall'], units)
                    summary.append(("Conditioning", conditioning_note))
                    report_gen.add_statistics_dashboard_slide(
                        slide_title,
                        pdf_bytes,
                        mean_bytes,
                        std_bytes,
                        skew_bytes,
                        kurt_bytes,
                        summary
                    )

        if config.powerpoint_config.include_rms_table:
            _add_rms_summary_slides(report_gen, results, config)

        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        prefix = _sanitize_filename_component(getattr(config.output_config, "filename_prefix", ""))
        report_name = "batch_psd_report.pptx" if not prefix else f"{prefix}_batch_psd_report.pptx"
        ppt_file = output_dir / report_name
        report_gen.save(str(ppt_file))
        logger.info(f"PowerPoint report saved: {ppt_file}")
        return str(ppt_file)

    except Exception as e:
        logger.error(f"Failed to generate PowerPoint report: {str(e)}")
        raise


def _add_config_slide(report_gen: ReportGenerator, config: 'BatchConfig', results) -> None:
    source_files = [Path(p).name for p in config.source_files]
    num_channels = len(results.channel_results) if results else len(config.selected_channels)
    event_defs = _get_event_definitions(config)
    if event_defs:
        event_names = [e[0] for e in event_defs]
        if "full_duration" in event_names and len(event_names) > 1:
            events_desc = f"Full duration + {len(event_names) - 1} event(s)"
        elif "full_duration" in event_names:
            events_desc = "Full duration"
        else:
            events_desc = f"{len(event_names)} event(s)"
    else:
        events_desc = "None"

    if config.filter_config.enabled:
        filter_desc = (
            f"User overrides (HP={getattr(config.filter_config, 'user_highpass_hz', None)}, "
            f"LP={getattr(config.filter_config, 'user_lowpass_hz', None)})"
        )
    else:
        filter_desc = "Baseline only (HP 1.0 Hz, LP 0.45xFs)"

    sections = [
        (
            "Ground Rules & Assumptions",
            [
                f"PSD method: {config.psd_config.method} with {config.psd_config.window} window",
                f"Overlap: {config.psd_config.overlap_percent}% and df {config.psd_config.desired_df} Hz",
                f"Frequency spacing displayed as {config.psd_config.frequency_spacing}",
                "Running mean removal: Disabled (baseline HP 1.0 Hz applied)",
                f"Filtering: {filter_desc}",
            ],
        ),
        (
            "Source Data",
            [
                f"Source type: {config.source_type.upper()}",
                f"Source files: {', '.join(source_files)}",
                f"Channels processed: {num_channels}",
                f"Events: {events_desc}",
            ],
        ),
        (
            "Processing Parameters",
            [
                f"Frequency range: {config.psd_config.freq_min} to {config.psd_config.freq_max} Hz",
                f"Efficient FFT: {'On' if config.psd_config.use_efficient_fft else 'Off'}",
                f"Spectrograms: {'Enabled' if config.spectrogram_config.enabled else 'Disabled'}",
                f"Statistics: {'Enabled' if config.powerpoint_config.include_statistics else 'Disabled'}",
            ],
        ),
    ]

    report_gen.add_bulleted_sections_slide(
        title="Processing Configuration",
        sections=sections
    )


def _layout_includes_time(layout: str) -> bool:
    return layout in {
        "time_psd_spec_one_slide",
        "all_plots_individual",
        "time_history_only"
    }


def _layout_includes_psd(layout: str) -> bool:
    return layout in {
        "time_psd_spec_one_slide",
        "all_plots_individual",
        "psd_spec_side_by_side",
        "psd_only"
    }


def _layout_includes_spectrogram(layout: str) -> bool:
    return layout in {
        "time_psd_spec_one_slide",
        "all_plots_individual",
        "psd_spec_side_by_side",
        "spectrogram_only"
    }


def _get_slot_role(layout: str, plot_kind: str) -> str:
    """
    Return slot role used by the report layout for a given plot kind.

    Roles map to report placeholder geometry:
    - single: 12.333 x 6.0
    - two_col: 6.1 x 5.9
    - three_top: 12.333 x 1.92
    - three_bottom: 6.1 x 4.03
    """
    if layout == "time_psd_spec_one_slide":
        if plot_kind == "time":
            return "three_top"
        return "three_bottom"
    if layout == "psd_spec_side_by_side":
        return "two_col"
    return "single"


def _get_plot_figsize(layout: str, plot_kind: str, slot_role: str = "single") -> Tuple[float, float]:
    """Return matplotlib figure size matched to the target PowerPoint slot ratio."""
    slot_sizes = {
        "single": (12.333, 6.0),
        "two_col": (6.1, 5.9),
        "three_top": (12.333, 1.92),
        "three_bottom": (6.1, 4.03),
    }
    return slot_sizes.get(slot_role, slot_sizes["single"])


def _build_plot_parameter_boxes(
    config: 'BatchConfig',
    event_name: str,
    start_time: Optional[float],
    end_time: Optional[float],
    sample_rate: Optional[float],
    units: str,
    event_result: Optional[Dict] = None,
) -> Tuple[str, str]:
    """Build PSD and spectrogram parameter strings (max 3 lines each)."""
    spacing = config.psd_config.frequency_spacing
    df = config.psd_config.desired_df
    fs_text = f"Fs={sample_rate:.1f} Hz" if sample_rate else "Fs=NA"

    if start_time is None or end_time is None:
        event_text = event_name
        time_range = "full duration"
    else:
        event_text = event_name
        time_range = f"{start_time:.2f}-{end_time:.2f}s"

    metadata = (event_result or {}).get("metadata", {}) if event_result else {}
    applied_hp = metadata.get("applied_highpass_hz")
    applied_lp = metadata.get("applied_lowpass_hz")
    if applied_hp is not None and applied_lp is not None:
        filt_desc = f"Baseline+user (HP {float(applied_hp):g} Hz, LP {float(applied_lp):g} Hz)"
    elif config.filter_config.enabled:
        hp = getattr(config.filter_config, "user_highpass_hz", None)
        lp = getattr(config.filter_config, "user_lowpass_hz", None)
        if hp is None:
            hp = getattr(config.filter_config, "cutoff_low", None)
        if lp is None:
            lp = getattr(config.filter_config, "cutoff_high", None)
        hp_text = "baseline" if hp is None else f"{float(hp):g}"
        lp_text = "baseline" if lp is None else f"{float(lp):g}"
        filt_desc = f"Baseline+user (HP {hp_text} Hz, LP {lp_text} Hz)"
    else:
        filt_desc = "Baseline (HP 1.0 Hz, LP 0.45xFs)"

    method = config.psd_config.method
    actual_df = metadata.get("actual_df_hz")
    method_desc = (
        f"{method.capitalize()} | window={config.psd_config.window} | "
        f"overlap={config.psd_config.overlap_percent}%"
    )
    df_text = (
        f"df={df} Hz (actual {float(actual_df):.3f} Hz)"
        if actual_df is not None else
        f"df={df} Hz"
    )

    psd_lines = [
        f"{df_text} | spacing={spacing} | {fs_text}",
        f"Event={event_text} ({time_range}) | Filter={filt_desc}",
        f"Method={method_desc}",
    ]

    spec_lines = [
        f"df={config.spectrogram_config.desired_df} Hz | overlap={config.spectrogram_config.overlap_percent}% | SNR={config.spectrogram_config.snr_threshold} dB",
        f"Event={event_text} ({time_range}) | {fs_text}",
        f"Colormap={config.spectrogram_config.colormap}",
    ]

    return "\n".join(psd_lines[:3]), "\n".join(spec_lines[:3])


def _get_event_definitions(config: 'BatchConfig') -> List[Tuple[str, Optional[float], Optional[float]]]:
    events = [(evt.name, evt.start_time, evt.end_time) for evt in config.events]
    if config.process_full_duration:
        return [("full_duration", None, None)] + events
    return events


def _event_bounds(events: List[Tuple[str, Optional[float], Optional[float]]]) -> Tuple[Optional[float], Optional[float]]:
    starts = [s for _, s, _ in events if s is not None]
    ends = [e for _, _, e in events if e is not None]
    if not starts or not ends:
        return None, None
    return min(starts), max(ends)


def _build_flight_to_file_map(source_files: List[str]) -> Dict[str, str]:
    mapping = {}
    for file_path in source_files:
        try:
            loader = HDF5FlightDataLoader(file_path)
            for flight_key in loader.flights.keys():
                mapping[flight_key] = file_path
            loader.close()
        except Exception as exc:
            logger.warning(f"Failed to read HDF5 metadata from {file_path}: {exc}")
    return mapping


def _load_time_history_cache(results, config: 'BatchConfig', events):
    cache = {}
    event_min, event_max = _event_bounds(events)

    if config.source_type == "hdf5":
        flight_map = _build_flight_to_file_map(config.source_files)
        loader_cache = {}

        def _get_loader(path):
            if path not in loader_cache:
                loader_cache[path] = HDF5FlightDataLoader(path)
            return loader_cache[path]

        for flight_key, channel_key in results.channel_results.keys():
            file_path = flight_map.get(flight_key)
            if not file_path:
                continue
            try:
                loader = _get_loader(file_path)
                data = loader.load_channel_data(
                    flight_key,
                    channel_key,
                    start_time=event_min,
                    end_time=event_max,
                    decimate_for_display=False
                )
                channel_info = loader.get_channel_info(flight_key, channel_key)
                units = channel_info.units if channel_info else ""
                cache[(flight_key, channel_key)] = (
                    data['time_full'],
                    data['data_full'],
                    units,
                    data.get('sample_rate', None)
                )
            except Exception as exc:
                logger.warning(f"Failed to load time history for {flight_key}/{channel_key}: {exc}")

        for loader in loader_cache.values():
            try:
                loader.close()
            except Exception:
                pass
    else:
        csv_data = load_csv_files(config.source_files)
        for file_path, channels in csv_data.items():
            flight_key = Path(file_path).stem
            for channel_key, (time_array, signal_array, sample_rate, units) in channels.items():
                if (flight_key, channel_key) in results.channel_results:
                    cache[(flight_key, channel_key)] = (time_array, signal_array, units, sample_rate)

    return cache


def _slice_event_signal(time_array, signal_array, start_time, end_time):
    if start_time is None or end_time is None:
        return time_array, signal_array
    if time_array.size == 0:
        return time_array, signal_array

    start = max(start_time, float(time_array[0]))
    end = min(end_time, float(time_array[-1]))
    if start >= end:
        return np.array([]), np.array([])

    mask = (time_array >= start) & (time_array <= end)
    return time_array[mask], signal_array[mask]


def _decimate_time_series(time_array, signal_array, max_points: int = 10000):
    if time_array is None or signal_array is None:
        return time_array, signal_array
    if len(time_array) <= max_points:
        return time_array, signal_array
    step = max(1, len(time_array) // max_points)
    return time_array[::step], signal_array[::step]


def _fig_to_bytes(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    buf.seek(0)
    data = buf.read()
    plt.close(fig)
    return data


def _create_time_history_plot(
    time_array,
    signal_array,
    units: str,
    plot_title: str,
    layout: str,
    slot_role: str = "single",
) -> bytes:
    apply_light_matplotlib_theme()
    fig, ax = plt.subplots(figsize=_get_plot_figsize(layout, "time", slot_role))
    ax.plot(time_array, signal_array, linewidth=0.9, color=LINE_COLOR)
    ylabel = f"Amplitude ({units})" if units else "Amplitude"
    style_axes(ax, plot_title, "Time (s)", ylabel)
    apply_axis_styling(ax, font_size=BASE_FONT_SIZE, include_grid=True)
    fig.tight_layout()
    return _fig_to_bytes(fig)


def _create_psd_plot(
    event_result: Dict,
    config: 'BatchConfig',
    units: str,
    plot_title: str,
    layout: str,
    slot_role: str = "single",
) -> bytes:
    frequencies = event_result['frequencies']
    psd_values = event_result['psd']
    frequencies, psd_values = apply_frequency_spacing(frequencies, psd_values, config.psd_config)
    if len(frequencies) == 0 or len(psd_values) == 0:
        frequencies = np.array([max(0.1, float(config.psd_config.freq_min))], dtype=float)
        psd_values = np.array([1e-12], dtype=float)

    apply_light_matplotlib_theme()
    fig, ax = plt.subplots(figsize=_get_plot_figsize(layout, "psd", slot_role))
    ax.loglog(frequencies, psd_values, linewidth=1.0, color=LINE_COLOR, label="PSD")

    reference_curve_entries = []
    if hasattr(config, "powerpoint_config"):
        reference_curve_entries = getattr(config.powerpoint_config, "reference_curves", []) or []
    reference_curves = []
    if len(frequencies) > 1:
        reference_curves = prepare_reference_curves_for_plot(
            reference_curve_entries,
            freq_min=float(np.min(frequencies)),
            freq_max=float(np.max(frequencies)),
            clip_to_range=False,
            logger=logger,
        )

    for idx, curve in enumerate(reference_curves):
        curve_color = curve.get("color") or REFERENCE_CURVE_COLOR_PALETTE[idx % len(REFERENCE_CURVE_COLOR_PALETTE)]
        ax.loglog(
            curve["frequencies"],
            curve["psd"],
            linewidth=1.2,
            linestyle=curve.get("line_style", "--"),
            color=curve_color,
            label=f"Ref: {curve['name']}",
        )

    ylabel = f"PSD ({units}^2/Hz)" if units else "PSD"
    style_axes(ax, plot_title, "Frequency (Hz)", ylabel)
    apply_axis_styling(ax, font_size=BASE_FONT_SIZE, include_grid=config.display_config.psd_show_grid)
    if not config.display_config.psd_show_grid:
        ax.grid(False)
    if config.display_config.psd_show_legend and reference_curves:
        ax.legend(fontsize=max(6.5, BASE_FONT_SIZE - 1.0), loc="best")

    if not config.display_config.psd_auto_scale:
        if config.display_config.psd_x_axis_min and config.display_config.psd_x_axis_max:
            ax.set_xlim(config.display_config.psd_x_axis_min, config.display_config.psd_x_axis_max)
        if config.display_config.psd_y_axis_min and config.display_config.psd_y_axis_max:
            ax.set_ylim(config.display_config.psd_y_axis_min, config.display_config.psd_y_axis_max)

    fig.tight_layout()
    return _fig_to_bytes(fig)


def _create_spectrogram_plot(
    spectrogram_data: Dict,
    config: 'BatchConfig',
    plot_title: str,
    layout: str,
    slot_role: str = "single",
) -> Optional[bytes]:
    apply_light_matplotlib_theme()
    fig, ax = plt.subplots(figsize=_get_plot_figsize(layout, "spectrogram", slot_role))

    frequencies = spectrogram_data['frequencies']
    times = spectrogram_data['times']
    Sxx = spectrogram_data['Sxx']

    Sxx_db = 10 * np.log10(Sxx + 1e-12)

    if Sxx_db.shape == (len(frequencies), len(times)):
        plot_data = Sxx_db
    elif Sxx_db.shape == (len(times), len(frequencies)):
        plot_data = Sxx_db.T
    else:
        logger.warning(
            f"Spectrogram shape mismatch: Sxx {Sxx_db.shape}, "
            f"freq {len(frequencies)}, time {len(times)}"
        )
        plt.close(fig)
        return None

    im = ax.pcolormesh(
        times,
        frequencies,
        plot_data,
        shading='auto',
        cmap=config.spectrogram_config.colormap
    )

    style_axes(ax, plot_title, "Time (s)", "Frequency (Hz)")
    apply_axis_styling(ax, font_size=BASE_FONT_SIZE, include_grid=False)
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label("PSD (dB)")
    style_colorbar(cbar, font_size=BASE_FONT_SIZE)

    if not config.display_config.spectrogram_auto_scale:
        if config.display_config.spectrogram_time_min is not None and config.display_config.spectrogram_time_max is not None:
            ax.set_xlim(config.display_config.spectrogram_time_min, config.display_config.spectrogram_time_max)
        if config.display_config.spectrogram_freq_min is not None and config.display_config.spectrogram_freq_max is not None:
            ax.set_ylim(config.display_config.spectrogram_freq_min, config.display_config.spectrogram_freq_max)

    fig.tight_layout()
    return _fig_to_bytes(fig)


def _format_stats_summary(overall_stats: Dict, units: str) -> str:
    unit_suffix = f" {units}" if units else ""
    lines = [
        f"Mean: {overall_stats['mean']:.4f}{unit_suffix}",
        f"Std: {overall_stats['std']:.4f}{unit_suffix}",
        f"Skewness: {overall_stats['skewness']:.4f}",
        f"Kurtosis: {overall_stats['kurtosis']:.4f}",
        f"Min: {overall_stats['min']:.4f}{unit_suffix}",
        f"Max: {overall_stats['max']:.4f}{unit_suffix}",
        f"RMS: {overall_stats['rms']:.4f}{unit_suffix}",
        f"Crest Factor: {overall_stats['crest_factor']:.4f}",
    ]
    return "\n".join(lines)


def _format_stats_summary_dict(overall_stats: Dict, units: str) -> List[Tuple[str, str]]:
    unit_suffix = f" {units}" if units else ""
    return [
        ("Mean", f"{overall_stats['mean']:.4f}{unit_suffix}"),
        ("Std", f"{overall_stats['std']:.4f}{unit_suffix}"),
        ("Skewness", f"{overall_stats['skewness']:.4f}"),
        ("Kurtosis", f"{overall_stats['kurtosis']:.4f}"),
        ("Min", f"{overall_stats['min']:.4f}{unit_suffix}"),
        ("Max", f"{overall_stats['max']:.4f}{unit_suffix}"),
        ("RMS", f"{overall_stats['rms']:.4f}{unit_suffix}"),
        ("Crest Factor", f"{overall_stats['crest_factor']:.4f}"),
    ]


def _add_rms_summary_slides(report_gen: ReportGenerator, results, config: 'BatchConfig') -> None:
    if not results.channel_results:
        return

    include_3sigma = config.powerpoint_config.include_3sigma_columns
    headers = ["Flight", "Channel", "Units", "Event", "RMS"]
    if include_3sigma:
        headers.append("3-Sigma RMS")

    rows = []
    for (flight_key, channel_key), event_dict in results.channel_results.items():
        for event_name, event_result in event_dict.items():
            metadata = event_result.get('metadata', {})
            rms_value = event_result.get('metadata', {}).get('rms')
            row = [
                flight_key,
                channel_key,
                metadata.get("units", ""),
                event_name,
                "" if rms_value is None else f"{rms_value:.4f}",
            ]
            if include_3sigma:
                row.append("" if rms_value is None else f"{3.0 * rms_value:.4f}")
            rows.append(row)

    rows.sort(key=lambda r: (r[0], r[1], r[3]))
    chunk_size = 20
    total_pages = max(1, int(np.ceil(len(rows) / chunk_size)))
    for page_idx in range(total_pages):
        start = page_idx * chunk_size
        end = start + chunk_size
        page_rows = rows[start:end]
        title = "RMS Summary" if total_pages == 1 else f"RMS Summary ({page_idx + 1}/{total_pages})"
        report_gen.add_rms_table_slide(title, headers, page_rows)
