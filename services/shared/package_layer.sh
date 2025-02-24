#!/bin/bash
set -e

# Create layer directory structure
mkdir -p layer/python
cd layer/python

# Install package
pip install --target . ../../

# Clean up
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Create zip
cd ..
zip -r ../layer.zip python/

# Clean up
cd ..
rm -rf layer/
