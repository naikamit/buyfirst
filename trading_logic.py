import os
import asyncio
from tastytrade import Tastytrade
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Initialize TastyTrade client
tt = Tastytrade(
    username=os.getenv("TASTYTRADE_USERNAME"),
    password=os.getenv("TASTYTRADE_PASSWORD")
)

async def get_account_info() -> Dict:
    """Get account information including positions and cash balance."""
    try:
        accounts = await tt.get_accounts()
        account = accounts[0]  # Use first account
        positions = await account.get_positions()
        balance = await account.get_balance()
        return {
            "positions": positions,
            "cash_balance": float(balance.get("cash_balance", 0)),
            "account_id": account.id
        }
    except Exception as e:
        logger.error(f"Error getting account info: {str(e)}")
        raise

async def get_stock_price(symbol: str) -> float:
    """Get stock price by buying 1 share and checking balance difference."""
    try:
        # Get initial balance
        initial_balance = (await get_account_info())["cash_balance"]
        
        # Attempt to buy 1 share
        order = await tt.create_order(
            account_id=os.getenv("TASTYTRADE_ACCOUNT_ID"),
            symbol=symbol,
            quantity=1,
            order_type="market"
        )
        
        # Wait for order to process
        await asyncio.sleep(1)
        
        # Get new balance
        new_balance = (await get_account_info())["cash_balance"]
        
        # Calculate price
        price = initial_balance - new_balance
        
        # Cancel the order if it's still pending
        if order.status == "pending":
            await tt.cancel_order(order.id)
            
        return price
    except Exception as e:
        logger.error(f"Error getting stock price: {str(e)}")
        raise

async def close_position(symbol: str, quantity: int) -> bool:
    """Close a position for a given symbol."""
    try:
        order = await tt.create_order(
            account_id=os.getenv("TASTYTRADE_ACCOUNT_ID"),
            symbol=symbol,
            quantity=-quantity,  # Negative quantity for selling
            order_type="market"
        )
        return order.status == "filled"
    except Exception as e:
        logger.error(f"Error closing position: {str(e)}")
        return False

async def buy_stock(symbol: str, quantity: int) -> bool:
    """Buy stock with retry logic."""
    try:
        order = await tt.create_order(
            account_id=os.getenv("TASTYTRADE_ACCOUNT_ID"),
            symbol=symbol,
            quantity=quantity,
            order_type="market"
        )
        
        if order.status != "filled":
            # Retry with 95% of quantity
            retry_quantity = int(quantity * 0.95)
            if retry_quantity > 0:
                order = await tt.create_order(
                    account_id=os.getenv("TASTYTRADE_ACCOUNT_ID"),
                    symbol=symbol,
                    quantity=retry_quantity,
                    order_type="market"
                )
                
        return order.status == "filled"
    except Exception as e:
        logger.error(f"Error buying stock: {str(e)}")
        return False

async def handle_trading_signal(signal: str) -> Dict:
    """Handle incoming trading signals."""
    try:
        # Get account information
        account_info = await get_account_info()
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
            if position.symbol != symbol:
                await close_position(position.symbol, position.quantity)
                
        # Buy new position
        success = await buy_stock(symbol, quantity)
        
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