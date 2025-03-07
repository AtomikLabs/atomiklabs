#!/usr/bin/env python3
"""
Build script for packaging the ArXiv processor ECS task
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

def build_ecs_package():
    """Build the ECS deployment package"""
    try:
        # Define paths
        project_root = Path(__file__).parent
        src_dir = project_root / "src"
        build_dir = project_root / "dist" / "ecs"
        
        # Create build directory
        build_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy source files
        print("Copying source files...")
        for file in src_dir.glob("**/*.py"):
            rel_path = file.relative_to(src_dir)
            dest_path = build_dir / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, dest_path)
        
        # Install dependencies
        print("Installing dependencies...")
        subprocess.run(
            [
                "pip", "install", 
                "--target", str(build_dir),
                "--no-deps",
                "-r", str(project_root / "requirements.txt")
            ],
            check=True
        )
        
        print("ECS package built successfully")
        return 0  # Success
    except Exception as e:
        print(f"Error building ECS package: {e}")
        return 1  # Error

if __name__ == "__main__":
    sys.exit(build_ecs_package()) 