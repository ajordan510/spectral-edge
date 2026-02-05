"""
Dependency Checker for SpectralEdge Application

This module checks that all required Python packages are installed
before launching the application. It provides helpful error messages
if dependencies are missing.

Author: SpectralEdge Development Team
"""

import sys
import importlib.util
from pathlib import Path


# Required packages with their import names and display names
REQUIRED_PACKAGES = [
    ('PyQt6', 'PyQt6', 'PyQt6 GUI framework'),
    ('pyqtgraph', 'pyqtgraph', 'PyQtGraph plotting library'),
    ('numpy', 'numpy', 'NumPy numerical computing'),
    ('scipy', 'scipy', 'SciPy scientific computing'),
    ('matplotlib', 'matplotlib', 'Matplotlib plotting library'),
    ('h5py', 'h5py', 'HDF5 file format support'),
    ('pptx', 'python-pptx', 'PowerPoint generation'),
    ('pandas', 'pandas', 'Pandas data analysis'),
    ('openpyxl', 'openpyxl', 'Excel file generation'),
]


def check_package_installed(import_name: str) -> bool:
    """
    Check if a package is installed.
    
    Args:
        import_name: The name used to import the package
        
    Returns:
        True if package is installed, False otherwise
    """
    spec = importlib.util.find_spec(import_name)
    return spec is not None


def check_all_dependencies() -> tuple[bool, list[str]]:
    """
    Check all required dependencies.
    
    Returns:
        Tuple of (all_installed, missing_packages)
        - all_installed: True if all packages are installed
        - missing_packages: List of missing package names (pip install names)
    """
    missing = []
    
    for import_name, pip_name, description in REQUIRED_PACKAGES:
        if not check_package_installed(import_name):
            missing.append(pip_name)
    
    return len(missing) == 0, missing


def print_missing_dependencies_error(missing_packages: list[str]):
    """
    Print a helpful error message about missing dependencies.
    
    Args:
        missing_packages: List of missing package names
    """
    print("\n" + "="*70)
    print("ERROR: Missing Required Dependencies")
    print("="*70)
    print("\nThe following required packages are not installed:\n")
    
    for package in missing_packages:
        print(f"  • {package}")
    
    print("\n" + "-"*70)
    print("To install all missing dependencies, run:")
    print("-"*70)
    print(f"\n  pip install {' '.join(missing_packages)}")
    print("\nOr install all requirements from the requirements file:")
    print("\n  pip install -r requirements.txt")
    print("\n" + "="*70 + "\n")


def check_dependencies_or_exit():
    """
    Check all dependencies and exit with error message if any are missing.
    
    This function should be called at the start of the application.
    If dependencies are missing, it will print an error message and exit.
    """
    all_installed, missing = check_all_dependencies()
    
    if not all_installed:
        print_missing_dependencies_error(missing)
        sys.exit(1)
    
    # All dependencies installed
    return True


if __name__ == "__main__":
    # Allow running this module directly to check dependencies
    all_installed, missing = check_all_dependencies()
    
    if all_installed:
        print("✅ All required dependencies are installed!")
        sys.exit(0)
    else:
        print_missing_dependencies_error(missing)
        sys.exit(1)
