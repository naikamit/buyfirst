import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from tastytrade_sdk import TastytradeSession
from api_logger import APILogger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize API logger
api_logger = APILogger()

# Global TastyTrade client
tasty = None

async def safe_api_call(endpoint, method, api_call, *args, **kwargs):
    """Safely make API calls with logging."""
    try:
        # Log the request
        request_data = {
            "args": str(args),
            "kwargs": str(kwargs)
        }
        api_logger.log_tastytrade_api(endpoint, method, request_data=request_data)
        
        # Make the API call
        response = api_call(*args, **kwargs)
        
        # Log the successful response
        response_data = None
        if hasattr(response, '__dict__'):
            try:
                response_data = {k: str(v) for k, v in response.__dict__.items() 
                                if not k.startswith('_') and not callable(v)}
            except:
                response_data = {"raw_response": str(response)}
        else:
            response_data = {"raw_response": str(response)}
            
        api_logger.log_tastytrade_api(endpoint, method, 
                                    request_data=request_data,
                                    response_data=response_data)
        return response
    except Exception as e:
        # Get detailed error information
        error_type = type(e).__name__
        error_module = type(e).__module__
        error_message = str(e)
        
        # Create detailed error info
        error_details = (
            f"Error Type: {error_type}\n"
            f"Error Module: {error_module}\n"
            f"Error Message: {error_message}\n"
            f"Args: {str(args)}\n"
            f"Kwargs: {str(kwargs)}"
        )
        
        # Log the error
        api_logger.log_tastytrade_api(endpoint, method, 
                                    request_data=request_data,
                                    error=error_details)
        # Re-raise the exception
        raise

async def initialize_tastytrade() -> bool:
    """Initialize TastyTrade client."""
    global tasty
    
    username = os.getenv("TASTYTRADE_USERNAME")
    password = os.getenv("TASTYTRADE_PASSWORD")
    
    if not username or not password:
        logger.error("TastyTrade credentials not set. Set TASTYTRADE_USERNAME and TASTYTRADE_PASSWORD environment variables.")
        raise ValueError("TastyTrade credentials not set")
        
    try:
        # Initialize API
        tasty = TastytradeSession(username, password, remember=True)
        
        # Log in
        tasty.login()
        logger.info("Successfully logged into TastyTrade")
        
        # Test API with a simple call
        try:
            await safe_api_call("/accounts", "GET", tasty.api.get, "/accounts")
            logger.info("TastyTrade API test successful")
            return True
        except Exception as e:
            logger.error(f"TastyTrade API test failed: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f"Failed to initialize TastyTrade: {str(e)}")
        raise

async def get_account_info() -> Dict:
    """Get account information."""
    await initialize_tastytrade()
    
    # Get accounts and use the first one or the specified account ID
    accounts_response = await safe_api_call("/accounts", "GET", tasty.api.get, "/accounts")
    accounts = accounts_response.get('items', [])
    if not accounts:
        raise ValueError("No accounts found")
    
    account_id = os.getenv("TASTYTRADE_ACCOUNT_ID")
    if not account_id:
        account_id = accounts[0]['account']['account-number']
        logger.info(f"Using first account: {account_id}")
    
    # Get positions
    positions_response = await safe_api_call(
        f"/accounts/{account_id}/positions", 
        "GET", 
        tasty.api.get, 
        f"/accounts/{account_id}/positions"
    )
    positions = positions_response.get('items', [])
    
    # Get balances
    balance_response = await safe_api_call(
        f"/accounts/{account_id}/balances", 
        "GET", 
        tasty.api.get, 
        f"/accounts/{account_id}/balances"
    )
    
    # Get cash balance
    cash_balance = 0.0
    if 'cash-balance' in balance_response:
        cash_balance = float(balance_response.get('cash-balance', 0))
    
    return {
        "account_id": account_id,
        "positions": positions,
        "cash_balance": cash_balance
    }

async def get_stock_price(symbol: str) -> float:
    """Get stock price for a given symbol."""
    await initialize_tastytrade()
    
    # First try to get a quote
    quotes_response = await safe_api_call(
        "/quotes", 
        "GET", 
        tasty.api.get, 
        "/quotes",
        params=[('symbol[]', symbol)]
    )
    
    items = quotes_response.get('items', [])
    if items:
        # Get the price from the quote
        for item in items:
            if item.get('symbol') == symbol:
                return float(item.get('last', 0))
    
    # If quotes don't have the price, try using the streamer's last price
    logger.warning(f"Could not get price from quotes for {symbol}, trying alternative method")
    raise ValueError(f"Could not get price for {symbol}")

async def close_position(account_id: str, symbol: str, quantity: int) -> bool:
    """Close a position by selling shares."""
    await initialize_tastytrade()
    
    # Create an order to sell shares
    order_data = {
        "account-id": account_id,
        "symbol": symbol,
        "quantity": quantity,
        "order-type": "Market",
        "side": "Sell",
        "time-in-force": "Day"
    }
    
    # Send the order
    order_response = await safe_api_call(
        "/orders", 
        "POST", 
        tasty.api.get, 
        "/orders",
        data=order_data
    )
    
    order_id = order_response.get('order-id')
    if not order_id:
        logger.error(f"Failed to create sell order for {symbol}")
        return False
    
    # Check order status
    await asyncio.sleep(1)
    order_status_response = await safe_api_call(
        f"/accounts/{account_id}/orders/{order_id}", 
        "GET", 
        tasty.api.get, 
        f"/accounts/{account_id}/orders/{order_id}"
    )
    
    status = order_status_response.get('status')
    return status == 'Filled'

async def buy_stock(account_id: str, symbol: str, quantity: int, max_retries: int = 1) -> bool:
    """Buy stock by creating a market order."""
    await initialize_tastytrade()
    
    # Create a buy order
    order_data = {
        "account-id": account_id,
        "symbol": symbol,
        "quantity": quantity,
        "order-type": "Market",
        "side": "Buy",
        "time-in-force": "Day"
    }
    
    # Send the order
    order_response = await safe_api_call(
        "/orders", 
        "POST", 
        tasty.api.get, 
        "/orders",
        data=order_data
    )
    
    order_id = order_response.get('order-id')
    if not order_id:
        logger.error(f"Failed to create buy order for {symbol}")
        return False
    
    # Check order status
    await asyncio.sleep(1)
    order_status_response = await safe_api_call(
        f"/accounts/{account_id}/orders/{order_id}", 
        "GET", 
        tasty.api.get, 
        f"/accounts/{account_id}/orders/{order_id}"
    )
    
    status = order_status_response.get('status')
    if status == 'Filled':
        return True
    
    if max_retries > 0 and status != 'Rejected':
        logger.info(f"Order {order_id} not filled, retrying with limit order...")
        
        # Get current stock price
        stock_price = await get_stock_price(symbol)
        
        # Create a limit order with 1% higher price to ensure it gets filled
        limit_price = round(stock_price * 1.01, 2)
        
        retry_order_data = {
            "account-id": account_id,
            "symbol": symbol,
            "quantity": quantity,
            "order-type": "Limit",
            "price": str(limit_price),
            "side": "Buy",
            "time-in-force": "Day"
        }
        
        # Send the limit order
        retry_order_response = await safe_api_call(
            "/orders", 
            "POST", 
            tasty.api.get, 
            "/orders",
            data=retry_order_data
        )
        
        retry_order_id = retry_order_response.get('order-id')
        if not retry_order_id:
            logger.error(f"Failed to create retry buy order for {symbol}")
            return False
        
        # Check retry order status
        await asyncio.sleep(1)
        retry_status_response = await safe_api_call(
            f"/accounts/{account_id}/orders/{retry_order_id}", 
            "GET", 
            tasty.api.get, 
            f"/accounts/{account_id}/orders/{retry_order_id}"
        )
        
        retry_status = retry_status_response.get('status')
        return retry_status == 'Filled'
    
    return False

async def handle_trading_signal(signal: str) -> Dict:
    """Handle a trading signal."""
    try:
        # Initialize the trading API
        await initialize_tastytrade()
        
        # Get account information
        account_info = await get_account_info()
        account_id = account_info["account_id"]
        
        # Default stock symbol and quantity
        symbol = "QQQ"  # Default to QQQ ETF
        quantity = 5
        
        # Check if we have the position already
        positions = account_info.get("positions", [])
        has_position = False
        position_quantity = 0
        
        for position in positions:
            if position.get("symbol") == symbol:
                has_position = True
                position_quantity = position.get("quantity", 0)
                break
        
        # Process signal
        if signal == "long":
            if has_position and position_quantity > 0:
                return {
                    "status": "info",
                    "message": f"Already have a long position in {symbol}",
                    "position": {
                        "symbol": symbol,
                        "quantity": position_quantity
                    }
                }
            
            # Close any short positions first
            if has_position and position_quantity < 0:
                logger.info(f"Closing short position for {symbol}")
                await close_position(account_id, symbol, abs(position_quantity))
            
            # Buy stock
            logger.info(f"Buying {quantity} shares of {symbol}")
            success = await buy_stock(account_id, symbol, quantity)
            
            if success:
                return {
                    "status": "success",
                    "message": f"Successfully bought {quantity} shares of {symbol}",
                    "trade": {
                        "symbol": symbol,
                        "quantity": quantity,
                        "direction": "buy"
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to buy {quantity} shares of {symbol}"
                }
                
        elif signal == "short":
            # Close any long positions first
            if has_position and position_quantity > 0:
                logger.info(f"Closing long position for {symbol}")
                await close_position(account_id, symbol, position_quantity)
                
            # We don't actually open short positions due to brokerage limitations
            # Just close any existing long positions
            return {
                "status": "success",
                "message": f"Closed positions for {symbol} as part of short signal",
                "trade": {
                    "symbol": symbol,
                    "quantity": position_quantity if has_position else 0,
                    "direction": "sell"
                }
            }
        
        return {
            "status": "error",
            "message": f"Invalid signal: {signal}"
        }
        
    except Exception as e:
        logger.error(f"Error handling trading signal: {str(e)}")
        return {
            "status": "error",
            "message": f"Error processing trading signal: {str(e)}"
        } 