"""
Main entry point for SpectralEdge application.

This module provides the main function that launches the SpectralEdge
GUI application. It initializes the PyQt6 application and displays
the landing page.

Author: SpectralEdge Development Team
"""

import sys
from spectral_edge.utils.dependency_checker import check_dependencies_or_exit

# Check dependencies before importing GUI components
check_dependencies_or_exit()

from PyQt6.QtWidgets import QApplication
from spectral_edge.gui.landing_page import LandingPage
from spectral_edge.gui.global_styles import apply_global_stylesheet
from spectral_edge.utils.logging_config import setup_logging


def main():
    """
    Main function to launch the SpectralEdge application.

    This function creates a QApplication instance, initializes the
    landing page window, and starts the application event loop.

    Returns:
        int: Exit code from the application.
    """
    # Initialize logging - logs go to logs/ folder with timestamp
    log_file = setup_logging(log_level="INFO")
    print(f"Log file: {log_file}")

    # Create the Qt application
    # sys.argv allows passing command-line arguments to the application
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName("SpectralEdge")
    app.setOrganizationName("SpectralEdge Team")
    app.setApplicationVersion("0.1.0")
    
    # Apply global stylesheet (dark theme with readable dialogs)
    apply_global_stylesheet(app)

    # Create and show the landing page window
    window = LandingPage()
    window.show()

    # Start the application event loop
    # This will run until the user closes the application
    return app.exec()


if __name__ == "__main__":
    # If this file is run directly (not imported), launch the application
    sys.exit(main())
