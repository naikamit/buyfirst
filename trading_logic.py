import os
import asyncio
from tastytrade_sdk import Tastytrade
import logging
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

# Initialize TastyTrade client
tasty = Tastytrade()

async def initialize_tastytrade():
    """Initialize the TastyTrade client."""
    try:
        tasty.login(
            login=os.getenv("TASTYTRADE_USERNAME"),
            password=os.getenv("TASTYTRADE_PASSWORD")
        )
        logger.info("Successfully logged into TastyTrade")
    except Exception as e:
        logger.error(f"Error logging into TastyTrade: {str(e)}")
        raise

async def get_account_info() -> Dict:
    """Get account information including positions and cash balance."""
    try:
        await initialize_tastytrade()
        
        # Get accounts and use the first one or the specified account ID
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
        logger.error(f"Error getting account info: {str(e)}")
        raise

async def get_stock_price(symbol: str) -> float:
    """Get stock price by buying 1 share and checking balance difference."""
    try:
        # Initialize TastyTrade client
        await initialize_tastytrade()
        
        # Get initial balance
        account_info = await get_account_info()
        account_id = account_info["account_id"]
        initial_balance = account_info["cash_balance"]
        
        # Get quote for the symbol
        quotes = tasty.api.get('/quotes', params=[('symbol[]', symbol)])
        if quotes and 'items' in quotes and quotes['items']:
            # Get the price from the quote
            quote = quotes['items'][0]
            # Use mid price (average of bid and ask)
            if 'bid-price' in quote and 'ask-price' in quote:
                price = (float(quote['bid-price']) + float(quote['ask-price'])) / 2
                return price
        
        # If we couldn't get a quote, buy 1 share
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
        logger.error(f"Error getting stock price: {str(e)}")
        raise

async def close_position(account_id: str, symbol: str, quantity: int) -> bool:
    """Close a position for a given symbol."""
    try:
        # Initialize TastyTrade client
        await initialize_tastytrade()
        
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
        logger.error(f"Error closing position: {str(e)}")
        return False

async def buy_stock(account_id: str, symbol: str, quantity: int) -> bool:
    """Buy stock with retry logic."""
    try:
        # Initialize TastyTrade client
        await initialize_tastytrade()
        
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
        logger.error(f"Error buying stock: {str(e)}")
        return False

async def handle_trading_signal(signal: str) -> Dict:
    """Handle incoming trading signals."""
    try:
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