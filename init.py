#!/usr/bin/env python3
"""
Initialization script to run when the application starts.
Creates necessary directories and checks environment variables.
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

def init_app():
    """Initialize the application."""
    # Create necessary directories
    directories = ['static', 'templates']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")
    
    # Check environment variables
    required_vars = [
        "TASTYTRADE_USERNAME",
        "TASTYTRADE_PASSWORD",
        "TASTYTRADE_ACCOUNT_ID"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.warning("The application may not function correctly without these variables.")
    else:
        logger.info("All required environment variables are set.")
    
    logger.info("Application initialization complete.")
    
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    init_app() 