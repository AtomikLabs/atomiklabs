#!/bin/bash
set -e

# Install poetry if not already installed
if ! command -v poetry &> /dev/null; then
    echo "Installing poetry..."
    pip install poetry
fi

# Install dependencies
echo "Installing project dependencies..."
poetry install

# Create pre-commit hooks
echo "Setting up pre-commit hooks..."
if ! command -v pre-commit &> /dev/null; then
    pip install pre-commit
fi

if [ -f .pre-commit-config.yaml ]; then
    pre-commit install
fi

echo "Development environment setup complete!"
echo "To activate the poetry environment, run: poetry shell" 