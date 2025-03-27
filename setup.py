#!/usr/bin/env python3
"""
Setup script to create required directories for the application.
Run this script once after cloning the repository.
"""

import os

# List of directories to create
DIRECTORIES = [
    'static',
    'templates',
]

def setup():
    """Create necessary directories for the application."""
    for directory in DIRECTORIES:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Created directory: {directory}")
        else:
            print(f"Directory already exists: {directory}")

if __name__ == "__main__":
    setup()
    print("Setup complete. You can now run the application.") 