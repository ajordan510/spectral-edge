"""
Batch Processor Worker Thread

This module provides a QThread-based worker for running batch processing
in the background without blocking the GUI.

Author: SpectralEdge Development Team
Date: 2026-02-02
"""

import logging
import time
from typing import Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal

from spectral_edge.batch.config import BatchConfig
from spectral_edge.batch.processor import BatchProcessor

logger = logging.getLogger(__name__)


class BatchWorker(QThread):
    """
    Worker thread for executing batch PSD processing.
    
    Runs the batch processor in a separate thread to prevent GUI freezing.
    Emits signals to update progress and report completion/errors.
    
    Signals:
    --------
    progress_updated : pyqtSignal(int, str)
        Emitted when progress changes. Args: (percent_complete, status_message)
    processing_complete : pyqtSignal(dict)
        Emitted when processing completes successfully. Args: (results_dict,)
    processing_failed : pyqtSignal(str)
        Emitted when processing fails. Args: (error_message,)
    log_message : pyqtSignal(str)
        Emitted for log messages during processing. Args: (message,)
    """
    
    progress_updated = pyqtSignal(int, str)
    processing_complete = pyqtSignal(dict)
    processing_failed = pyqtSignal(str)
    log_message = pyqtSignal(str)
    
    def __init__(self, config: BatchConfig):
        """
        Initialize the batch worker.
        
        Parameters:
        -----------
        config : BatchConfig
            Batch configuration object
        """
        super().__init__()
        self.config = config
        self.processor = None
        self._is_cancelled = False
    
    def run(self):
        """
        Execute the batch processing.
        
        This method runs in a separate thread and should not be called directly.
        Use start() instead.
        """
        try:
            self.log_message.emit("Initializing batch processor...")
            self.progress_updated.emit(0, "Initializing...")
            
            # Create processor with progress callback
            def progress_handler(progress_info):
                self.progress_updated.emit(
                    int(progress_info.percent_complete),
                    str(progress_info)
                )
                self.log_message.emit(str(progress_info))
            
            self.processor = BatchProcessor(self.config, progress_callback=progress_handler)
            
            # Run batch processing
            self.log_message.emit("Starting batch processing...")
            self.progress_updated.emit(5, "Loading data...")

            # Run batch processing with timing
            processing_start = time.perf_counter()
            result = self.processor.process()
            processing_time = time.perf_counter() - processing_start

            if self._is_cancelled:
                self.log_message.emit("Batch processing cancelled by user")
                self.processing_failed.emit("Processing cancelled by user")
                return

            # Check for fatal errors
            if result.errors:
                error_summary = f"{len(result.errors)} error(s) occurred during processing"
                self.log_message.emit(error_summary)
                self.processing_failed.emit(error_summary)
                return

            self.progress_updated.emit(50, "Generating outputs...")
            self.log_message.emit(f"Processing complete in {processing_time:.2f}s, generating outputs...")
            
            # Generate outputs
            from spectral_edge.batch.excel_output import export_to_excel
            from spectral_edge.batch.hdf5_output import write_psds_to_hdf5
            from spectral_edge.batch.powerpoint_output import generate_powerpoint_report
            
            output_config = self.config.output_config
            
            try:
                output_times = {}

                # Check cancellation before Excel output
                if self._is_cancelled:
                    self.log_message.emit("Cancelled before output generation")
                    self.processing_failed.emit("Processing cancelled by user")
                    return

                if output_config.excel_enabled:
                    self.progress_updated.emit(55, "Generating Excel output...")
                    self.log_message.emit("Generating Excel output...")
                    excel_start = time.perf_counter()
                    excel_path = export_to_excel(result, output_config.output_directory)
                    excel_time = time.perf_counter() - excel_start
                    output_times['excel'] = excel_time
                    self.log_message.emit(f"Excel saved: {excel_path} ({excel_time:.2f}s)")

                # Check cancellation before CSV output
                if self._is_cancelled:
                    self.log_message.emit("Cancelled during output generation")
                    self.processing_failed.emit("Processing cancelled by user")
                    return

                if output_config.csv_enabled:
                    self.progress_updated.emit(65, "Generating CSV outputs...")
                    self.log_message.emit("Generating CSV outputs...")
                    csv_start = time.perf_counter()
                    # CSV is generated by excel_output module
                    csv_time = time.perf_counter() - csv_start
                    output_times['csv'] = csv_time
                    self.log_message.emit(f"CSV files saved ({csv_time:.2f}s)")

                # Check cancellation before PowerPoint output
                if self._is_cancelled:
                    self.log_message.emit("Cancelled during output generation")
                    self.processing_failed.emit("Processing cancelled by user")
                    return

                if output_config.powerpoint_enabled:
                    self.progress_updated.emit(75, "Generating PowerPoint report...")
                    self.log_message.emit("Generating PowerPoint report...")
                    ppt_start = time.perf_counter()
                    ppt_path = generate_powerpoint_report(
                        result,
                        output_config.output_directory,
                        self.config
                    )
                    ppt_time = time.perf_counter() - ppt_start
                    output_times['powerpoint'] = ppt_time
                    self.log_message.emit(f"PowerPoint saved: {ppt_path} ({ppt_time:.2f}s)")

                # Check cancellation before HDF5 output
                if self._is_cancelled:
                    self.log_message.emit("Cancelled during output generation")
                    self.processing_failed.emit("Processing cancelled by user")
                    return

                if output_config.hdf5_enabled and self.config.data_source.source_type == 'hdf5':
                    self.progress_updated.emit(90, "Writing PSDs to HDF5...")
                    self.log_message.emit("Writing PSDs back to HDF5...")
                    hdf5_start = time.perf_counter()
                    write_psds_to_hdf5(result, self.config.data_source.hdf5_file)
                    hdf5_time = time.perf_counter() - hdf5_start
                    output_times['hdf5'] = hdf5_time
                    self.log_message.emit(f"HDF5 write complete ({hdf5_time:.2f}s)")

                # Log output timing summary
                if output_times:
                    total_output_time = sum(output_times.values())
                    timing_summary = ", ".join([f"{k}: {v:.2f}s" for k, v in output_times.items()])
                    self.log_message.emit(f"Output generation complete: {timing_summary} (total: {total_output_time:.2f}s)")  
            except Exception as e:
                error_msg = f"Error generating outputs: {str(e)}"
                self.log_message.emit(error_msg)
                self.processing_failed.emit(error_msg)
                return
            
            self.progress_updated.emit(100, "Complete!")
            self.log_message.emit("Batch processing completed successfully")
            
            # Convert result to dict for signal emission
            results_dict = {
                'channel_count': len(result.channel_results),
                'event_count': len(self.config.events) if not self.config.process_full_duration else 1,
                'warnings': len(result.warnings),
                'output_directory': output_config.output_directory
            }
            self.processing_complete.emit(results_dict)
            
        except Exception as e:
            error_msg = f"Batch processing failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.log_message.emit(error_msg)
            self.processing_failed.emit(error_msg)
    
    def cancel(self):
        """
        Request cancellation of the batch processing.
        
        Note: The cancellation is cooperative and may not take effect immediately.
        """
        self._is_cancelled = True
        self.log_message.emit("Cancellation requested...")
        
        if self.processor:
            self.processor.cancel_requested = True
