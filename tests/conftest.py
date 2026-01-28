"""
Pytest configuration and fixtures for SpectralEdge tests.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.test_data_contracts import ContractValidator


@pytest.fixture
def validator():
    """Provide a ContractValidator instance for tests."""
    return ContractValidator()
