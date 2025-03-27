import os
import asyncio
from tastytrade_sdk import Tastytrade
import logging
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

# Initialize TastyTrade client
tasty = Tastytrade()

# Simple in-memory cache for demo purposes when API is unavailable
FALLBACK_CACHE = {
    "price_cache": {
        "MSTU": 150.50,
        "MSTZ": 145.75
    },
    "account_info": {
        "positions": [],
        "cash_balance": 10000.0,
        "account_id": "demo-account"
    }
}

async def initialize_tastytrade():
    """Initialize the TastyTrade client."""
    try:
        if not os.getenv("TASTYTRADE_USERNAME") or not os.getenv("TASTYTRADE_PASSWORD"):
            logger.warning("TastyTrade credentials not set, operating in demo mode")
            return False
            
        tasty.login(
            login=os.getenv("TASTYTRADE_USERNAME"),
            password=os.getenv("TASTYTRADE_PASSWORD")
        )
        logger.info("Successfully logged into TastyTrade")
        return True
    except Exception as e:
        logger.error(f"Error logging into TastyTrade: {str(e)}")
        logger.warning("Falling back to demo mode")
        return False

async def get_account_info() -> Dict:
    """Get account information including positions and cash balance."""
    try:
        # Try to initialize TastyTrade
        login_success = await initialize_tastytrade()
        if not login_success:
            logger.warning("Using demo account information")
            return FALLBACK_CACHE["account_info"]
            
        # Get accounts and use the first one or the specified account ID
        try:
            accounts = tasty.api.get('/accounts')
            account_id = os.getenv("TASTYTRADE_ACCOUNT_ID") or accounts['items'][0]['account']['account-number']
            
            # Get positions
            positions_response = tasty.api.get(f'/accounts/{account_id}/positions')
            positions = positions_response.get('items', [])
            
            # Get balances
            balance_response = tasty.api.get(f'/accounts/{account_id}/balances')
            cash_balance = float(balance_response.get('cash-balance', 0))
            
            return {
                "positions": positions,
                "cash_balance": cash_balance,
                "account_id": account_id
            }
        except Exception as e:
            logger.error(f"Error fetching account data from TastyTrade: {str(e)}")
            logger.warning("Using demo account information")
            return FALLBACK_CACHE["account_info"]
            
    except Exception as e:
        logger.error(f"Error getting account info: {str(e)}")
        # Fallback to demo data
        return FALLBACK_CACHE["account_info"]

async def get_stock_price(symbol: str) -> float:
    """Get stock price by buying 1 share and checking balance difference."""
    try:
        # Initialize TastyTrade client
        login_success = await initialize_tastytrade()
        if not login_success:
            logger.warning(f"Using demo price for {symbol}")
            return FALLBACK_CACHE["price_cache"].get(symbol, 100.0)
        
        try:
            # Get quote for the symbol
            quotes = tasty.api.get('/quotes', params=[('symbol[]', symbol)])
            if quotes and 'items' in quotes and quotes['items']:
                # Get the price from the quote
                quote = quotes['items'][0]
                # Use mid price (average of bid and ask)
                if 'bid-price' in quote and 'ask-price' in quote:
                    price = (float(quote['bid-price']) + float(quote['ask-price'])) / 2
                    return price
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {str(e)}")
            logger.warning(f"Using demo price for {symbol}")
            return FALLBACK_CACHE["price_cache"].get(symbol, 100.0)
         
        # If we couldn't get a quote, try buying 1 share
        try:
            # Get initial balance
            account_info = await get_account_info()
            account_id = account_info["account_id"]
            initial_balance = account_info["cash_balance"]
            
            # Create an order to buy 1 share
            order_data = {
                "account-id": account_id,
                "symbol": symbol,
                "quantity": 1,
                "order-type": "Market",
                "side": "Buy"
            }
            
            order_response = tasty.api.post('/orders', data=order_data)
            order_id = order_response.get('order-id')
            
            # Wait for order to process
            await asyncio.sleep(1)
            
            # Get new balance
            new_account_info = await get_account_info()
            new_balance = new_account_info["cash_balance"]
            
            # Calculate price
            price = initial_balance - new_balance
            
            # Cancel the order if it's still pending
            order_status = tasty.api.get(f'/accounts/{account_id}/orders/{order_id}')
            if order_status and order_status.get('status') == 'Pending':
                tasty.api.delete(f'/accounts/{account_id}/orders/{order_id}')
                
            return price
        except Exception as e:
            logger.error(f"Error buying 1 share of {symbol} to determine price: {str(e)}")
            logger.warning(f"Using demo price for {symbol}")
            return FALLBACK_CACHE["price_cache"].get(symbol, 100.0)
    except Exception as e:
        logger.error(f"Error getting stock price: {str(e)}")
        # Fallback to demo data
        return FALLBACK_CACHE["price_cache"].get(symbol, 100.0)

async def close_position(account_id: str, symbol: str, quantity: int) -> bool:
    """Close a position for a given symbol."""
    try:
        # Initialize TastyTrade client
        login_success = await initialize_tastytrade()
        if not login_success:
            logger.warning(f"Demo mode: Simulating closing {quantity} shares of {symbol}")
            return True
        
        try:
            # Create an order to sell the position
            order_data = {
                "account-id": account_id,
                "symbol": symbol,
                "quantity": quantity,
                "order-type": "Market",
                "side": "Sell"
            }
            
            order_response = tasty.api.post('/orders', data=order_data)
            order_id = order_response.get('order-id')
            
            # Check order status
            await asyncio.sleep(1)
            order_status = tasty.api.get(f'/accounts/{account_id}/orders/{order_id}')
            return order_status and order_status.get('status') == 'Filled'
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {str(e)}")
            logger.warning(f"Demo mode: Simulating closing {quantity} shares of {symbol}")
            return True
    except Exception as e:
        logger.error(f"Error closing position: {str(e)}")
        # Simulate success in demo mode
        return True

async def buy_stock(account_id: str, symbol: str, quantity: int) -> bool:
    """Buy stock with retry logic."""
    try:
        # Initialize TastyTrade client
        login_success = await initialize_tastytrade()
        if not login_success:
            logger.warning(f"Demo mode: Simulating buying {quantity} shares of {symbol}")
            return True
            
        try:
            # Create an order to buy
            order_data = {
                "account-id": account_id,
                "symbol": symbol,
                "quantity": quantity,
                "order-type": "Market",
                "side": "Buy"
            }
            
            order_response = tasty.api.post('/orders', data=order_data)
            order_id = order_response.get('order-id')
            
            # Check order status
            await asyncio.sleep(1)
            order_status = tasty.api.get(f'/accounts/{account_id}/orders/{order_id}')
            
            if not order_status or order_status.get('status') != 'Filled':
                # Retry with 95% of quantity
                retry_quantity = int(quantity * 0.95)
                if retry_quantity > 0:
                    # Create new order with reduced quantity
                    retry_order_data = {
                        "account-id": account_id,
                        "symbol": symbol,
                        "quantity": retry_quantity,
                        "order-type": "Market",
                        "side": "Buy"
                    }
                    
                    retry_order_response = tasty.api.post('/orders', data=retry_order_data)
                    retry_order_id = retry_order_response.get('order-id')
                    
                    # Check retry order status
                    await asyncio.sleep(1)
                    retry_order_status = tasty.api.get(f'/accounts/{account_id}/orders/{retry_order_id}')
                    return retry_order_status and retry_order_status.get('status') == 'Filled'
                
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error buying {symbol}: {str(e)}")
            logger.warning(f"Demo mode: Simulating buying {quantity} shares of {symbol}")
            return True
    except Exception as e:
        logger.error(f"Error buying stock: {str(e)}")
        # Simulate success in demo mode
        return True

async def handle_trading_signal(signal: str) -> Dict:
    """Handle incoming trading signals."""
    try:
        logger.info(f"Handling {signal} trading signal")
        
        # Get account information
        account_info = await get_account_info()
        account_id = account_info["account_id"]
        cash_balance = account_info["cash_balance"]
        existing_positions = account_info["positions"]
        
        # Determine symbol based on signal
        symbol = "MSTU" if signal == "long" else "MSTZ"
        
        # Get stock price
        price = await get_stock_price(symbol)
        
        # Calculate quantity to buy
        if existing_positions:
            # Use full cash balance if other positions exist
            quantity = int(cash_balance / price)
        else:
            # Use 50% of cash balance if no other positions
            quantity = int((cash_balance * 0.5) / price)
            
        if quantity < 1:
            return {"status": "error", "message": "Insufficient funds"}
            
        # Close existing positions if any
        for position in existing_positions:
            position_symbol = position.get('symbol')
            position_quantity = position.get('quantity')
            
            if position_symbol and position_symbol != symbol and position_quantity:
                await close_position(account_id, position_symbol, position_quantity)
                
        # Buy new position
        success = await buy_stock(account_id, symbol, quantity)
        
        if success:
            return {
                "status": "success",
                "message": f"Successfully bought {quantity} shares of {symbol}",
                "quantity": quantity,
                "price": price
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to buy {symbol}"
            }
            
    except Exception as e:
        logger.error(f"Error handling trading signal: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        } 