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

from build import build_lambda_package


@patch("build.subprocess.run")
@patch("build.os.makedirs")
@patch("build.shutil.copy2")
@patch("build.shutil.make_archive")
@patch("build.Path.glob")
@patch("build.Path.mkdir")
def test_build_lambda_package(mock_mkdir, mock_glob, mock_make_archive, 
                             mock_copy2, mock_makedirs, mock_subprocess_run):
    """Test the build_lambda_package function"""
    # Setup mocks
    mock_glob.return_value = [
        Path("/home/atomik/src/atomiklabs/services/arxiv_api/src/file1.py"),
        Path("/home/atomik/src/atomiklabs/services/arxiv_api/src/subdir/file2.py")
    ]
    
    # Call the function
    result = build_lambda_package()
    
    # Verify the result
    assert result == 0
    
    # Verify mkdir was called to create build directory
    mock_mkdir.assert_called()
    
    # Verify copy2 was called to copy the source files
    assert mock_copy2.call_count == 2
    
    # Verify subprocess.run was called to install dependencies
    mock_subprocess_run.assert_called_once()
    
    # Verify os.makedirs was called to create the zip directory
    mock_makedirs.assert_called_once()
    
    # Verify shutil.make_archive was called to create the zip file
    mock_make_archive.assert_called_once()


@patch("build.subprocess.run")
@patch("build.os.makedirs")
@patch("build.shutil.copy2")
@patch("build.shutil.make_archive")
@patch("build.Path.glob")
@patch("build.Path.mkdir")
def test_build_lambda_package_empty_source(mock_mkdir, mock_glob, mock_make_archive, 
                                          mock_copy2, mock_makedirs, mock_subprocess_run):
    """Test the build_lambda_package function with empty source directory"""
    # Setup mocks
    mock_glob.return_value = []
    
    # Call the function
    result = build_lambda_package()
    
    # Verify the result
    assert result == 0
    
    # Verify copy2 was not called since there are no source files
    mock_copy2.assert_not_called()
    
    # Verify the rest of the function continued to execute
    mock_subprocess_run.assert_called_once()
    mock_makedirs.assert_called_once()
    mock_make_archive.assert_called_once()


@patch("build.subprocess.run", side_effect=Exception("Test error"))
@patch("build.os.makedirs")
@patch("build.shutil.copy2")
@patch("build.Path.glob")
@patch("build.Path.mkdir")
def test_build_lambda_package_error(mock_mkdir, mock_glob, mock_copy2, 
                                   mock_makedirs, mock_subprocess_run):
    """Test the build_lambda_package function when an error occurs"""
    # Setup mocks
    mock_glob.return_value = [Path("/home/atomik/src/atomiklabs/services/arxiv_api/src/file1.py")]
    
    # Call the function and expect it to handle the error
    result = build_lambda_package()
    
    # Verify the result indicates an error
    assert result == 1  # Function should return 1 on error
    
    # Verify mkdir was called
    mock_mkdir.assert_called()
    
    # Verify copy2 was called
    mock_copy2.assert_called_once()
    
    # Verify subprocess.run was called and raised the exception
    mock_subprocess_run.assert_called_once() 