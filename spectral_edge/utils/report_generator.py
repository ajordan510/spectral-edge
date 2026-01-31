"""
Report Generator Module for SpectralEdge.

This module provides functionality to generate PowerPoint reports containing
PSD analysis results, including plots, parameters, and summary tables.

Author: SpectralEdge Development Team
"""

import io
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.enum.shapes import MSO_SHAPE
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

import numpy as np


class ReportGenerator:
    """
    Generate PowerPoint reports for PSD analysis results.

    This class provides methods to create professional reports containing:
    - PSD plots (captured as images)
    - Analysis parameters
    - RMS values and summary tables
    - Spectrogram images (optional)

    Attributes
    ----------
    presentation : Presentation
        The python-pptx Presentation object being built.
    title : str
        Report title.

    Examples
    --------
    >>> generator = ReportGenerator(title="Vibration Analysis Report")
    >>> generator.add_title_slide(subtitle="Flight Test 001")
    >>> generator.add_psd_plot(image_bytes, "Channel 1 PSD", {"df": 1.0, "window": "hann"})
    >>> generator.add_summary_table(channels, rms_values)
    >>> generator.save("report.pptx")
    """

    def __init__(self, title: str = "PSD Analysis Report", template_path: Optional[str] = None):
        """
        Initialize the report generator.

        Parameters
        ----------
        title : str, optional
            Report title. Default is "PSD Analysis Report".
        template_path : str, optional
            Path to a PowerPoint template file. If None, uses default blank template.
        """
        if not PPTX_AVAILABLE:
            raise ImportError(
                "python-pptx is required for report generation. "
                "Install it with: pip install python-pptx"
            )

        self.title = title

        if template_path and Path(template_path).exists():
            self.presentation = Presentation(template_path)
        else:
            self.presentation = Presentation()
            # Set default slide dimensions (16:9 widescreen)
            self.presentation.slide_width = Inches(13.333)
            self.presentation.slide_height = Inches(7.5)

        self._slide_count = 0

    def add_title_slide(
        self,
        subtitle: str = "",
        author: str = "",
        date: Optional[str] = None
    ) -> None:
        """
        Add a title slide to the report.

        Parameters
        ----------
        subtitle : str, optional
            Subtitle text (e.g., flight name, test ID).
        author : str, optional
            Author name.
        date : str, optional
            Date string. If None, uses current date.
        """
        # Use blank layout and add shapes manually for more control
        slide_layout = self.presentation.slide_layouts[6]  # Blank layout
        slide = self.presentation.slides.add_slide(slide_layout)

        # Add title
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(2.5), Inches(12.333), Inches(1.5)
        )
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = self.title
        title_para.font.size = Pt(44)
        title_para.font.bold = True
        title_para.font.color.rgb = RGBColor(0x1a, 0x1f, 0x2e)  # Dark blue
        title_para.alignment = PP_ALIGN.CENTER

        # Add subtitle if provided
        if subtitle:
            subtitle_box = slide.shapes.add_textbox(
                Inches(0.5), Inches(4.0), Inches(12.333), Inches(0.75)
            )
            subtitle_frame = subtitle_box.text_frame
            subtitle_para = subtitle_frame.paragraphs[0]
            subtitle_para.text = subtitle
            subtitle_para.font.size = Pt(28)
            subtitle_para.font.color.rgb = RGBColor(0x4a, 0x55, 0x68)  # Gray
            subtitle_para.alignment = PP_ALIGN.CENTER

        # Add date
        if date is None:
            date = datetime.now().strftime("%B %d, %Y")

        date_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(5.5), Inches(12.333), Inches(0.5)
        )
        date_frame = date_box.text_frame
        date_para = date_frame.paragraphs[0]
        date_para.text = date
        date_para.font.size = Pt(18)
        date_para.font.color.rgb = RGBColor(0x6b, 0x72, 0x80)  # Light gray
        date_para.alignment = PP_ALIGN.CENTER

        # Add author if provided
        if author:
            author_box = slide.shapes.add_textbox(
                Inches(0.5), Inches(6.0), Inches(12.333), Inches(0.5)
            )
            author_frame = author_box.text_frame
            author_para = author_frame.paragraphs[0]
            author_para.text = author
            author_para.font.size = Pt(16)
            author_para.font.color.rgb = RGBColor(0x6b, 0x72, 0x80)
            author_para.alignment = PP_ALIGN.CENTER

        self._slide_count += 1

    def add_psd_plot(
        self,
        image_bytes: bytes,
        title: str = "PSD Analysis",
        parameters: Optional[Dict[str, Any]] = None,
        rms_values: Optional[Dict[str, float]] = None,
        units: str = ""
    ) -> None:
        """
        Add a slide with a PSD plot image and optional parameters.

        Parameters
        ----------
        image_bytes : bytes
            PNG image data of the PSD plot.
        title : str, optional
            Slide title.
        parameters : dict, optional
            Dictionary of analysis parameters to display.
            Example: {"df": 1.0, "window": "hann", "method": "Maximax"}
        rms_values : dict, optional
            Dictionary of channel names to RMS values.
            Example: {"Channel 1": 2.45, "Channel 2": 1.89}
        units : str, optional
            Units for RMS values (e.g., "g", "m/s²").
        """
        slide_layout = self.presentation.slide_layouts[6]  # Blank layout
        slide = self.presentation.slides.add_slide(slide_layout)

        # Add title
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.6)
        )
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = title
        title_para.font.size = Pt(28)
        title_para.font.bold = True
        title_para.font.color.rgb = RGBColor(0x1a, 0x1f, 0x2e)

        # Add the plot image
        image_stream = io.BytesIO(image_bytes)

        # Calculate image position (centered, with room for parameters)
        if parameters or rms_values:
            # Image on left, parameters on right
            img_left = Inches(0.3)
            img_top = Inches(1.0)
            img_width = Inches(9.0)
            img_height = Inches(5.5)
        else:
            # Image centered and larger
            img_left = Inches(1.0)
            img_top = Inches(1.0)
            img_width = Inches(11.0)
            img_height = Inches(6.0)

        slide.shapes.add_picture(
            image_stream, img_left, img_top, img_width, img_height
        )

        # Add parameters box if provided
        if parameters or rms_values:
            param_box = slide.shapes.add_textbox(
                Inches(9.5), Inches(1.0), Inches(3.5), Inches(5.5)
            )
            param_frame = param_box.text_frame
            param_frame.word_wrap = True

            # Add parameters header
            if parameters:
                para = param_frame.paragraphs[0]
                para.text = "Parameters"
                para.font.size = Pt(14)
                para.font.bold = True
                para.font.color.rgb = RGBColor(0x1a, 0x1f, 0x2e)

                # Add each parameter
                for key, value in parameters.items():
                    para = param_frame.add_paragraph()
                    para.text = f"{key}: {value}"
                    para.font.size = Pt(11)
                    para.font.color.rgb = RGBColor(0x4a, 0x55, 0x68)

                # Add spacing
                para = param_frame.add_paragraph()
                para.text = ""

            # Add RMS values if provided
            if rms_values:
                para = param_frame.add_paragraph() if parameters else param_frame.paragraphs[0]
                para.text = "RMS Values"
                para.font.size = Pt(14)
                para.font.bold = True
                para.font.color.rgb = RGBColor(0x1a, 0x1f, 0x2e)

                for channel, rms in rms_values.items():
                    para = param_frame.add_paragraph()
                    if units:
                        para.text = f"{channel}: {rms:.4f} {units}"
                    else:
                        para.text = f"{channel}: {rms:.4f}"
                    para.font.size = Pt(11)
                    para.font.color.rgb = RGBColor(0x4a, 0x55, 0x68)

        self._slide_count += 1

    def add_spectrogram(
        self,
        image_bytes: bytes,
        title: str = "Spectrogram",
        channel_name: str = "",
        parameters: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a slide with a spectrogram image.

        Parameters
        ----------
        image_bytes : bytes
            PNG image data of the spectrogram.
        title : str, optional
            Slide title.
        channel_name : str, optional
            Name of the channel being displayed.
        parameters : dict, optional
            Dictionary of spectrogram parameters.
        """
        slide_layout = self.presentation.slide_layouts[6]  # Blank layout
        slide = self.presentation.slides.add_slide(slide_layout)

        # Add title
        full_title = f"{title}: {channel_name}" if channel_name else title
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.6)
        )
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = full_title
        title_para.font.size = Pt(28)
        title_para.font.bold = True
        title_para.font.color.rgb = RGBColor(0x1a, 0x1f, 0x2e)

        # Add the spectrogram image (full width)
        image_stream = io.BytesIO(image_bytes)
        slide.shapes.add_picture(
            image_stream, Inches(0.5), Inches(1.0), Inches(12.333), Inches(6.0)
        )

        self._slide_count += 1

    def add_summary_table(
        self,
        channels: List[str],
        rms_values: Dict[str, float],
        units: str = "",
        additional_metrics: Optional[Dict[str, Dict[str, float]]] = None,
        title: str = "Analysis Summary"
    ) -> None:
        """
        Add a summary table slide with RMS values for all channels.

        Parameters
        ----------
        channels : list of str
            List of channel names.
        rms_values : dict
            Dictionary mapping channel names to RMS values.
        units : str, optional
            Units for RMS values.
        additional_metrics : dict, optional
            Additional metrics to include. Format: {"Metric Name": {"Channel": value}}
        title : str, optional
            Slide title.
        """
        slide_layout = self.presentation.slide_layouts[6]  # Blank layout
        slide = self.presentation.slides.add_slide(slide_layout)

        # Add title
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.6)
        )
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = title
        title_para.font.size = Pt(28)
        title_para.font.bold = True
        title_para.font.color.rgb = RGBColor(0x1a, 0x1f, 0x2e)

        # Determine table dimensions
        num_cols = 2  # Channel, RMS
        if additional_metrics:
            num_cols += len(additional_metrics)
        num_rows = len(channels) + 1  # Header + data rows

        # Create table
        table_width = Inches(10)
        table_height = Inches(0.4 * num_rows)
        table_left = Inches(1.5)
        table_top = Inches(1.5)

        table = slide.shapes.add_table(
            num_rows, num_cols, table_left, table_top, table_width, table_height
        ).table

        # Style the table
        # Header row
        headers = ["Channel", f"RMS ({units})" if units else "RMS"]
        if additional_metrics:
            headers.extend(additional_metrics.keys())

        for col, header in enumerate(headers):
            cell = table.cell(0, col)
            cell.text = header
            cell.text_frame.paragraphs[0].font.bold = True
            cell.text_frame.paragraphs[0].font.size = Pt(12)
            cell.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

        # Data rows
        for row, channel in enumerate(channels, start=1):
            # Channel name
            table.cell(row, 0).text = channel
            table.cell(row, 0).text_frame.paragraphs[0].font.size = Pt(11)

            # RMS value
            rms = rms_values.get(channel, 0.0)
            table.cell(row, 1).text = f"{rms:.4f}"
            table.cell(row, 1).text_frame.paragraphs[0].font.size = Pt(11)
            table.cell(row, 1).text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

            # Additional metrics
            if additional_metrics:
                for col, metric_name in enumerate(additional_metrics.keys(), start=2):
                    value = additional_metrics[metric_name].get(channel, 0.0)
                    table.cell(row, col).text = f"{value:.4f}"
                    table.cell(row, col).text_frame.paragraphs[0].font.size = Pt(11)
                    table.cell(row, col).text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

        self._slide_count += 1

    def add_comparison_plot(
        self,
        image_bytes: bytes,
        title: str = "PSD Comparison",
        description: str = ""
    ) -> None:
        """
        Add a slide with a PSD comparison plot.

        Parameters
        ----------
        image_bytes : bytes
            PNG image data of the comparison plot.
        title : str, optional
            Slide title.
        description : str, optional
            Description text to display below the plot.
        """
        slide_layout = self.presentation.slide_layouts[6]  # Blank layout
        slide = self.presentation.slides.add_slide(slide_layout)

        # Add title
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.6)
        )
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = title
        title_para.font.size = Pt(28)
        title_para.font.bold = True
        title_para.font.color.rgb = RGBColor(0x1a, 0x1f, 0x2e)

        # Add the plot image
        image_stream = io.BytesIO(image_bytes)
        slide.shapes.add_picture(
            image_stream, Inches(0.5), Inches(1.0), Inches(12.333), Inches(5.5)
        )

        # Add description if provided
        if description:
            desc_box = slide.shapes.add_textbox(
                Inches(0.5), Inches(6.6), Inches(12.333), Inches(0.5)
            )
            desc_frame = desc_box.text_frame
            desc_para = desc_frame.paragraphs[0]
            desc_para.text = description
            desc_para.font.size = Pt(12)
            desc_para.font.color.rgb = RGBColor(0x4a, 0x55, 0x68)
            desc_para.alignment = PP_ALIGN.CENTER

        self._slide_count += 1

    def add_text_slide(
        self,
        title: str,
        content: str,
        bullet_points: Optional[List[str]] = None
    ) -> None:
        """
        Add a text-only slide with optional bullet points.

        Parameters
        ----------
        title : str
            Slide title.
        content : str
            Main text content.
        bullet_points : list of str, optional
            List of bullet points to add.
        """
        slide_layout = self.presentation.slide_layouts[6]  # Blank layout
        slide = self.presentation.slides.add_slide(slide_layout)

        # Add title
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.6)
        )
        title_frame = title_box.text_frame
        title_para = title_frame.paragraphs[0]
        title_para.text = title
        title_para.font.size = Pt(28)
        title_para.font.bold = True
        title_para.font.color.rgb = RGBColor(0x1a, 0x1f, 0x2e)

        # Add content
        content_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(1.2), Inches(12.333), Inches(5.5)
        )
        content_frame = content_box.text_frame
        content_frame.word_wrap = True

        # Main content
        para = content_frame.paragraphs[0]
        para.text = content
        para.font.size = Pt(14)
        para.font.color.rgb = RGBColor(0x4a, 0x55, 0x68)

        # Bullet points
        if bullet_points:
            for point in bullet_points:
                para = content_frame.add_paragraph()
                para.text = f"• {point}"
                para.font.size = Pt(12)
                para.font.color.rgb = RGBColor(0x4a, 0x55, 0x68)
                para.level = 0

        self._slide_count += 1

    def save(self, output_path: str) -> str:
        """
        Save the report to a PowerPoint file.

        Parameters
        ----------
        output_path : str
            Path where the PowerPoint file will be saved.

        Returns
        -------
        str
            The path where the file was saved.
        """
        # Ensure .pptx extension
        if not output_path.lower().endswith('.pptx'):
            output_path += '.pptx'

        self.presentation.save(output_path)
        return output_path

    def save_to_bytes(self) -> bytes:
        """
        Save the report to bytes (for in-memory handling).

        Returns
        -------
        bytes
            The PowerPoint file as bytes.
        """
        output = io.BytesIO()
        self.presentation.save(output)
        output.seek(0)
        return output.read()

    @property
    def slide_count(self) -> int:
        """Return the number of slides in the presentation."""
        return self._slide_count


def export_plot_to_image(plot_widget, width: int = 1200, height: int = 800) -> bytes:
    """
    Export a PyQtGraph plot widget to PNG image bytes.

    Parameters
    ----------
    plot_widget : pg.PlotWidget
        The PyQtGraph plot widget to export.
    width : int, optional
        Image width in pixels. Default is 1200.
    height : int, optional
        Image height in pixels. Default is 800.

    Returns
    -------
    bytes
        PNG image data.
    """
    try:
        from pyqtgraph.exporters import ImageExporter

        # Create exporter
        exporter = ImageExporter(plot_widget.plotItem)
        exporter.parameters()['width'] = width
        exporter.parameters()['height'] = height

        # Export to bytes
        output = io.BytesIO()
        exporter.export(output)
        output.seek(0)
        return output.read()

    except Exception as e:
        raise RuntimeError(f"Failed to export plot: {e}")
