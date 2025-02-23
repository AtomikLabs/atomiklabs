import os
import sys
import pytest

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure pytest
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    ) 