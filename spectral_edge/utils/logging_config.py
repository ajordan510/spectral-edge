"""
Logging Configuration for SpectralEdge

This module provides centralized logging configuration that writes logs
to both console and timestamped log files in the logs/ directory.

Author: SpectralEdge Development Team
Date: 2026-02-03
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_dir: str = None) -> str:
    """
    Configure logging for the SpectralEdge application.

    Sets up logging to both console and a timestamped log file.
    Log files are stored in the logs/ directory at the project root.

    Parameters:
    -----------
    log_level : str
        Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        Default is INFO.
    log_dir : str, optional
        Custom log directory. If not provided, uses logs/ in project root.

    Returns:
    --------
    str
        Path to the current log file.
    """
    # Determine log directory
    if log_dir is None:
        # Get project root (parent of spectral_edge package)
        project_root = Path(__file__).parent.parent.parent
        log_dir = project_root / "logs"
    else:
        log_dir = Path(log_dir)

    # Create logs directory if it doesn't exist
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create timestamped log filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"spectral_edge_{timestamp}.log"
    log_path = log_dir / log_filename

    # Also create a "latest.log" symlink/copy for easy access
    latest_log_path = log_dir / "latest.log"

    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(levelname)-8s | %(name)-30s | %(message)s'
    )

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all, let handlers filter

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler (respects log_level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (always captures DEBUG level)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)  # Capture everything to file
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)

    # Create/update latest.log (on Windows, we copy; on Unix, we symlink)
    try:
        if latest_log_path.exists() or latest_log_path.is_symlink():
            latest_log_path.unlink()

        # Try to create symlink (works on Unix and Windows with dev mode)
        try:
            latest_log_path.symlink_to(log_path.name)
        except (OSError, NotImplementedError):
            # Fall back to just noting the latest file
            pass
    except Exception:
        pass  # Don't fail logging setup due to symlink issues

    # Log initial message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Log file: {log_path}")
    logger.info(f"Console log level: {log_level}, File log level: DEBUG")

    return str(log_path)


def get_batch_logger() -> logging.Logger:
    """
    Get a logger specifically for batch processing operations.

    Returns:
    --------
    logging.Logger
        Logger configured for batch processing.
    """
    return logging.getLogger("spectral_edge.batch")


def get_gui_logger() -> logging.Logger:
    """
    Get a logger specifically for GUI operations.

    Returns:
    --------
    logging.Logger
        Logger configured for GUI operations.
    """
    return logging.getLogger("spectral_edge.gui")


class BatchProcessingLogContext:
    """
    Context manager for batch processing that creates a dedicated log section.

    Usage:
    ------
    with BatchProcessingLogContext("Processing Flight A"):
        # ... processing code ...
    """

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.logger = logging.getLogger("spectral_edge.batch")
        self.start_time = None

    def __enter__(self):
        import time
        self.start_time = time.perf_counter()
        self.logger.info("=" * 60)
        self.logger.info(f"STARTING: {self.operation_name}")
        self.logger.info("=" * 60)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        elapsed = time.perf_counter() - self.start_time

        if exc_type is not None:
            self.logger.error(f"FAILED: {self.operation_name} ({elapsed:.2f}s)")
            self.logger.error(f"Error: {exc_val}")
        else:
            self.logger.info(f"COMPLETED: {self.operation_name} ({elapsed:.2f}s)")

        self.logger.info("-" * 60)
        return False  # Don't suppress exceptions
