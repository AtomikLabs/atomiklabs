#!/usr/bin/env python3
"""
Export Poetry dependencies to requirements.txt
"""
import subprocess
import sys
from pathlib import Path

def export_requirements():
    """Export Poetry dependencies to requirements.txt"""
    project_root = Path(__file__).parent
    requirements_file = project_root / "requirements.txt"
    
    print(f"Exporting Poetry dependencies to {requirements_file}")
    
    # Export dependencies using Poetry
    try:
        subprocess.run(
            [
                "poetry", "export", 
                "--format", "requirements.txt",
                "--output", str(requirements_file),
                "--without-hashes"
            ],
            check=True
        )
        print("Requirements exported successfully")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error exporting requirements: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(export_requirements()) 