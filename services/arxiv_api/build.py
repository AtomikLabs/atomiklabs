#!/usr/bin/env python3
"""
Build script for packaging the Lambda function
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

def build_lambda_package():
    """Build the Lambda deployment package"""
    # Define paths
    project_root = Path(__file__).parent
    src_dir = project_root / "src"
    build_dir = project_root / "dist" / "lambda"
    zip_file = project_root / ".." / ".." / "infra" / "build" / "arxiv_api.zip"
    
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
    
    # Create the zip file
    print(f"Creating zip file: {zip_file}")
    os.makedirs(os.path.dirname(zip_file), exist_ok=True)
    
    # Create the zip file
    shutil.make_archive(
        str(zip_file).replace(".zip", ""),  # Base name without extension
        "zip",
        str(build_dir)
    )
    
    print(f"Lambda package created at {zip_file}")
    return 0

if __name__ == "__main__":
    sys.exit(build_lambda_package()) 