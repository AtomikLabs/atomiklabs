#!/usr/bin/env python3
"""
Export requirements from Poetry

This script handles exporting requirements from Poetry to a requirements.txt file,
with special handling for different Poetry versions.
"""

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("export-requirements")

# Hardcoded requirements as a fallback
# These must match the dependencies in pyproject.toml
FALLBACK_REQUIREMENTS = """
boto3>=1.37.6,<2.0.0
requests>=2.31.0,<3.0.0
defusedxml>=0.7.1,<1.0.0
pydantic>=2.10.6,<3.0.0
"""

def get_poetry_version() -> Tuple[int, int, int]:
    """Get the installed Poetry version as a tuple of (major, minor, patch)"""
    try:
        result = subprocess.run(
            ["poetry", "--version"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        version_str = re.search(r"(\d+\.\d+\.\d+)", result.stdout)
        if version_str:
            version_parts = version_str.group(1).split(".")
            return (int(version_parts[0]), int(version_parts[1]), int(version_parts[2]))
        return (0, 0, 0)
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("Could not determine Poetry version")
        return (0, 0, 0)


def check_export_plugin() -> bool:
    """Check if the export plugin is installed"""
    try:
        result = subprocess.run(
            ["poetry", "plugin", "list"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        return "export" in result.stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def install_export_plugin() -> bool:
    """Install the export plugin"""
    try:
        logger.info("Installing poetry-plugin-export...")
        result = subprocess.run(
            ["poetry", "plugin", "add", "poetry-plugin-export"],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("Failed to install poetry-plugin-export")
        return False


def export_with_plugin() -> Optional[str]:
    """Export requirements using the Poetry export plugin"""
    try:
        logger.info("Exporting requirements using the export plugin...")
        result = subprocess.run(
            ["poetry", "export", "--format", "requirements.txt", "--without", "dev", "--without-hashes"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return result.stdout
        logger.error(f"Export failed: {result.stderr}")
        return None
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("Failed to run poetry export")
        return None


def export_with_command() -> Optional[str]:
    """Export requirements using the Poetry export command (v1.x)"""
    try:
        logger.info("Exporting requirements using Poetry 1.x export command...")
        result = subprocess.run(
            ["poetry", "export", "--format", "requirements.txt", "--without-hashes", "--dev"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return result.stdout
        logger.error(f"Export failed: {result.stderr}")
        return None
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("Failed to run poetry export")
        return None


def write_requirements(requirements: str) -> bool:
    """Write requirements to a file"""
    try:
        with open("requirements.txt", "w") as f:
            f.write(requirements)
        logger.info("Requirements written to requirements.txt")
        return True
    except Exception as e:
        logger.error(f"Failed to write requirements.txt: {str(e)}")
        return False


def main() -> int:
    """Main function"""
    logger.info("Starting requirements export")
    
    # Get Poetry version
    major, minor, patch = get_poetry_version()
    logger.info(f"Poetry version: {major}.{minor}.{patch}")
    
    requirements = None
    
    # Version-specific export strategies
    if major >= 2:
        # Poetry 2.x requires the export plugin
        if not check_export_plugin():
            logger.info("Export plugin not installed")
            if not install_export_plugin():
                logger.warning("Failed to install export plugin, using fallback requirements")
                requirements = FALLBACK_REQUIREMENTS
        
        if requirements is None:  # Only try export if we don't have fallback already
            requirements = export_with_plugin()
    
    elif major == 1:
        # Poetry 1.x has built-in export command
        requirements = export_with_command()
    
    # If all strategies failed, use fallback
    if requirements is None:
        logger.warning("All export strategies failed, using fallback requirements")
        requirements = FALLBACK_REQUIREMENTS
    
    # Write requirements
    if not write_requirements(requirements):
        logger.error("Failed to write requirements.txt")
        return 1
    
    logger.info("Requirements export completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 