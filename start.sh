#!/bin/bash
# Startup script for the TastyTrade Webhook Service

# Run initialization script
python init.py

# Start the FastAPI application
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} 