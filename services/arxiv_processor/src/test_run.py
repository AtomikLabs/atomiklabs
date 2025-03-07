#!/usr/bin/env python3
"""
Test script for the ArXiv processor

This script runs the processor with a limited configuration for testing purposes.
"""

import logging
import os
import sys
from datetime import datetime

# Set up environment variables for testing
os.environ['ARXIV_CATEGORIES'] = 'cs.AI,cs.CL'
os.environ['ARXIV_SETS'] = 'cs'
os.environ['DAYS_LOOKBACK'] = '1'
os.environ['BATCH_SIZE'] = '2'
os.environ['API_ENDPOINT'] = 'http://localhost:8080'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Import after setting environment variables
from main import main

if __name__ == "__main__":
    print(f"Starting test run at {datetime.now().isoformat()}")
    try:
        main()
        print(f"Test run completed successfully at {datetime.now().isoformat()}")
    except Exception as e:
        print(f"Test run failed: {e}")
        sys.exit(1) 