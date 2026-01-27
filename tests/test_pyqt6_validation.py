"""
PyQt6 Attribute Validation Test

This script validates that all PyQt6 attributes used in the SpectralEdge
application are correct and available. It catches runtime errors that
simple import tests would miss.

Run this test before pushing any GUI changes.

Author: SpectralEdge Development Team
Date: 2026-01-27
"""

import sys
import re
from pathlib import Path


def extract_qt_attributes(file_path: str) -> list:
    """
    Extract all Qt.* attribute references from a Python file.
    
    Parameters:
    -----------
    file_path : str
        Path to the Python file to analyze
    
    Returns:
    --------
    list of tuples
        List of (line_number, attribute_string) tuples
    """
    attributes = []
    
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            # Find Qt.Something.Something patterns
            matches = re.findall(r'Qt\.(\w+)\.(\w+)', line)
            for match in matches:
                attr_str = f"Qt.{match[0]}.{match[1]}"
                attributes.append((line_num, attr_str))
            
            # Find QMessageBox.Something.Something patterns
            matches = re.findall(r'QMessageBox\.(\w+)\.(\w+)', line)
            for match in matches:
                attr_str = f"QMessageBox.{match[0]}.{match[1]}"
                attributes.append((line_num, attr_str))
    
    return attributes


def validate_attribute(attr_str: str) -> tuple:
    """
    Validate that a Qt attribute exists.
    
    Parameters:
    -----------
    attr_str : str
        Attribute string like "Qt.ItemFlag.ItemIsAutoTristate"
    
    Returns:
    --------
    tuple
        (is_valid: bool, error_message: str or None)
    """
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QMessageBox
    
    try:
        parts = attr_str.split('.')
        if parts[0] == 'Qt':
            obj = Qt
            for part in parts[1:]:
                obj = getattr(obj, part)
        elif parts[0] == 'QMessageBox':
            obj = QMessageBox
            for part in parts[1:]:
                obj = getattr(obj, part)
        else:
            return (False, f"Unknown base: {parts[0]}")
        
        return (True, None)
    except AttributeError as e:
        return (False, str(e))


def validate_file(file_path: str) -> list:
    """
    Validate all Qt attributes in a file.
    
    Parameters:
    -----------
    file_path : str
        Path to the Python file to validate
    
    Returns:
    --------
    list of tuples
        List of (line_number, attribute, error) for invalid attributes
    """
    errors = []
    attributes = extract_qt_attributes(file_path)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_attrs = []
    for line_num, attr in attributes:
        if attr not in seen:
            seen.add(attr)
            unique_attrs.append((line_num, attr))
    
    for line_num, attr in unique_attrs:
        is_valid, error = validate_attribute(attr)
        if not is_valid:
            errors.append((line_num, attr, error))
    
    return errors


def main():
    """Run validation on all GUI files."""
    print("=" * 60)
    print("PyQt6 Attribute Validation Test")
    print("=" * 60)
    
    # Find all Python files in gui and utils directories
    base_path = Path(__file__).parent.parent / "spectral_edge"
    gui_path = base_path / "gui"
    utils_path = base_path / "utils"
    
    all_files = []
    if gui_path.exists():
        all_files.extend(gui_path.glob("*.py"))
    if utils_path.exists():
        all_files.extend(utils_path.glob("*.py"))
    
    total_errors = 0
    
    for file_path in sorted(all_files):
        if file_path.name.startswith("__"):
            continue
        
        print(f"\nValidating: {file_path.name}")
        errors = validate_file(str(file_path))
        
        if errors:
            total_errors += len(errors)
            for line_num, attr, error in errors:
                print(f"  ❌ Line {line_num}: {attr}")
                print(f"     Error: {error}")
        else:
            print(f"  ✓ All attributes valid")
    
    print("\n" + "=" * 60)
    if total_errors == 0:
        print("✅ ALL VALIDATIONS PASSED")
        return 0
    else:
        print(f"❌ FOUND {total_errors} INVALID ATTRIBUTES")
        return 1


if __name__ == "__main__":
    sys.exit(main())
