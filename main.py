from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
import pytz
import json
import os
from typing import List, Dict
import logging
from trading_logic import handle_trading_signal, api_logger
from health import get_health_status
from init import init_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize the application
init_app()

# API Version
API_VERSION = "1.1.0"

# Create FastAPI app 
app = FastAPI(title="TastyTrade Webhook Service")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global variables
last_trade_time = None
TRADE_COOLDOWN_HOURS = 12

@app.get("/version")
async def version():
    """Return the API version."""
    return {"version": API_VERSION}

@app.post("/webhook")
async def webhook(request: Request):
    global last_trade_time
    try:
        # Get request body
        body = await request.json()
        signal = body.get("signal")
        
        # Log incoming webhook
        api_logger.log_request("webhook", "POST", body)
        
        if signal not in ["long", "short"]:
            response = {"status": "error", "message": "Invalid signal"}
            api_logger.log_response("webhook", "POST", response)
            return response
            
        # Check if we're in cooldown period
        if last_trade_time:
            time_since_last_trade = (datetime.now(pytz.UTC) - last_trade_time).total_seconds() / 3600
            if time_since_last_trade < TRADE_COOLDOWN_HOURS:
                response = {"status": "cooldown", "message": "Trading is in cooldown period"}
                api_logger.log_response("webhook", "POST", response)
                return response
        
        # Handle trading signal
        result = await handle_trading_signal(signal)
        
        # Update last trade time if successful
        if result.get("status") == "success":
            last_trade_time = datetime.now(pytz.UTC)
        
        api_logger.log_response("webhook", "POST", result)
        return result
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        response = {"status": "error", "message": str(e)}
        api_logger.log_response("webhook", "POST", response)
        return response

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    logs = api_logger.get_logs()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "logs": logs}
    )

@app.get("/api/logs")
async def get_logs():
    """Get all API logs."""
    return api_logger.get_logs()

@app.get("/api/tastytrade-logs")
async def get_tastytrade_logs():
    """Get only TastyTrade API logs."""
    all_logs = api_logger.get_logs()
    tastytrade_logs = [log for log in all_logs if log.get("type") == "tastytrade_api"]
    return tastytrade_logs

@app.get("/api/test")
async def test_endpoint():
    """Simple test endpoint to verify API routing."""
    return {"status": "ok", "message": "API is working"}

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    status = await get_health_status()
    return status 