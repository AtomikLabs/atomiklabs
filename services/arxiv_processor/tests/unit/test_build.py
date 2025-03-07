#!/usr/bin/env python3
"""
Unit tests for build.py
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest

# Add project root to sys.path so we can import build.py
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from build import build_ecs_package


@patch("build.subprocess.run")
@patch("build.Path.mkdir")
@patch("build.shutil.copy2")
@patch("build.Path.glob")
def test_build_ecs_package(mock_glob, mock_copy2, mock_mkdir, mock_subprocess_run):
    """Test the build_ecs_package function"""
    # Setup mocks
    mock_glob.return_value = [
        Path("/home/atomik/src/atomiklabs/services/arxiv_processor/src/file1.py"),
        Path("/home/atomik/src/atomiklabs/services/arxiv_processor/src/subdir/file2.py")
    ]
    
    # Call the function
    result = build_ecs_package()
    
    # Verify the result
    assert result == 0
    
    # Verify mkdir was called to create build directory
    mock_mkdir.assert_called()
    
    # Verify copy2 was called to copy the source files
    assert mock_copy2.call_count == 2
    
    # Verify subprocess.run was called to install dependencies
    mock_subprocess_run.assert_called_once()


@patch("build.subprocess.run")
@patch("build.Path.glob")
def test_build_ecs_package_error(mock_glob, mock_subprocess_run):
    """Test error handling in build_ecs_package"""
    # Setup mocks to raise an exception
    mock_glob.side_effect = Exception("Test error")
    
    # Call the function
    result = build_ecs_package()
    
    # Verify the result is an error
    assert result == 1
    
    # Verify subprocess.run was not called
    mock_subprocess_run.assert_not_called() 