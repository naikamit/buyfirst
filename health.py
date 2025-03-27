"""
Health check module for the application.
Used to verify that the service is running correctly.
"""

import os
from datetime import datetime
import pytz
from tastytrade_sdk import Tastytrade

async def check_tastytrade_api():
    """Check if the TastyTrade API is accessible."""
    try:
        # Check if credentials are set
        if not os.getenv("TASTYTRADE_USERNAME") or not os.getenv("TASTYTRADE_PASSWORD"):
            return {
                "status": "warning",
                "message": "TastyTrade credentials not set. Operating in demo mode."
            }
            
        # Initialize TastyTrade client
        tasty = Tastytrade()
        try:
            tasty.login(
                login=os.getenv("TASTYTRADE_USERNAME"),
                password=os.getenv("TASTYTRADE_PASSWORD")
            )
            
            # Attempt to get accounts (this will verify authentication)
            accounts = tasty.api.get('/accounts')
            
            return {
                "status": "ok",
                "message": f"Successfully connected to TastyTrade API. Found {len(accounts.get('items', []))} accounts."
            }
        except Exception as e:
            return {
                "status": "warning",
                "message": f"Error connecting to TastyTrade API: {str(e)}. Operating in demo mode."
            }
    except Exception as e:
        return {
            "status": "warning",
            "message": f"Error in TastyTrade API check: {str(e)}. Operating in demo mode."
        }

async def get_health_status():
    """Get complete health status of the application."""
    # Get current time in IST
    utc_now = datetime.now(pytz.UTC)
    ist = pytz.timezone('Asia/Kolkata')
    ist_time = utc_now.astimezone(ist).strftime('%Y-%m-%d %H:%M:%S %Z')
    
    # Check TastyTrade API
    tastytrade_status = await check_tastytrade_api()
    
    # Determine overall status - app can be healthy even if TastyTrade API is in warning state
    # since we have fallback demo mode
    overall_status = "healthy"
    if tastytrade_status["status"] == "error":
        overall_status = "warning"
    
    return {
        "status": overall_status,
        "timestamp": ist_time,
        "services": {
            "tastytrade_api": tastytrade_status
        },
        "environment": {
            "tastytrade_username_set": os.getenv("TASTYTRADE_USERNAME") is not None,
            "tastytrade_password_set": os.getenv("TASTYTRADE_PASSWORD") is not None,
            "tastytrade_account_id_set": os.getenv("TASTYTRADE_ACCOUNT_ID") is not None
        }
    } 