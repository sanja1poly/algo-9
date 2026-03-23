"""
╔══════════════════════════════════════════════╗
║  FILE 2: dhan_client.py                      ║
║  DhanHQ API Client - Central Connection      ║
╚══════════════════════════════════════════════╝

DhanHQ v2 SDK wrapper for:
- Authentication
- Order Management (virtual mode)
- Position Management
- Fund/Margin Info
"""

from dhanhq import DhanContext, dhanhq
from config import (
    DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN,
    EXCHANGE_SEGMENTS, logger
)


class DhanClient:
    """
    Central DhanHQ API Client
    
    Dhan theke SABKUCH access hoga ei class diye:
    - Option Chain data
    - Live Market Feed
    - Order Placement (virtual)
    - Positions & Holdings
    - Fund Limits
    """
    
    def __init__(self, client_id=None, access_token=None):
        self.client_id = client_id or DHAN_CLIENT_ID
        self.access_token = access_token or DHAN_ACCESS_TOKEN
        
        # Initialize DhanHQ Context (v2.1+)
        self.context = DhanContext(self.client_id, self.access_token)
        self.dhan = dhanhq(self.context)
        
        logger.info(f"✅ DhanHQ Client initialized | Client ID: {self.client_id[:4]}****")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ORDER MANAGEMENT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def place_order(self, security_id, exchange_segment, transaction_type,
                    quantity, order_type, product_type, price=0,
                    trigger_price=0, disclosed_quantity=0, validity="DAY",
                    drv_expiry_date=None, drv_option_type=None,
                    drv_strike_price=None):
        """
        Place order on Dhan
        
        Args:
            security_id: str - Dhan security ID
            exchange_segment: str - "NSE_FNO", "NSE_EQ" etc.
            transaction_type: str - "BUY" or "SELL"
            quantity: int - Number of shares/lots
            order_type: str - "MARKET", "LIMIT", "SL", "SLM"
            product_type: str - "INTRADAY", "CNC", "MARGIN"
            price: float - Limit price (0 for market)
            trigger_price: float - Stop loss trigger
            drv_expiry_date: str - Expiry date for F&O
            drv_option_type: str - "CALL" or "PUT"
            drv_strike_price: float - Strike price
        """
        try:
            response = self.dhan.place_order(
                security_id=security_id,
                exchange_segment=exchange_segment,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type=order_type,
                product_type=product_type,
                price=price,
                trigger_price=trigger_price,
                disclosed_quantity=disclosed_quantity,
                validity=validity,
                drv_expiry_date=drv_expiry_date,
                drv_option_type=drv_option_type,
                drv_strike_price=drv_strike_price,
            )
            logger.info(f"📋 Order placed: {transaction_type} {security_id} qty={quantity}")
            return response
        except Exception as e:
            logger.error(f"❌ Order failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def place_slice_order(self, security_id, exchange_segment, transaction_type,
                          quantity, order_type, product_type, price=0):
        """Place sliced order (for qty > freeze limit)"""
        try:
            response = self.dhan.place_slice_order(
                security_id=security_id,
                exchange_segment=exchange_segment,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type=order_type,
                product_type=product_type,
                price=price,
            )
            return response
        except Exception as e:
            logger.error(f"❌ Slice order failed: {e}")
            return {"status": "error", "message": str(e)}
    
    def modify_order(self, order_id, order_type, quantity, price,
                     trigger_price=0, disclosed_quantity=0, validity="DAY"):
        """Modify existing order"""
        try:
            return self.dhan.modify_order(
                order_id=order_id,
                order_type=order_type,
                quantity=quantity,
                price=price,
                trigger_price=trigger_price,
                disclosed_quantity=disclosed_quantity,
                validity=validity,
            )
        except Exception as e:
            logger.error(f"❌ Modify failed: {e}")
            return None
    
    def cancel_order(self, order_id):
        """Cancel pending order"""
        try:
            return self.dhan.cancel_order(order_id)
        except Exception as e:
            logger.error(f"❌ Cancel failed: {e}")
            return None
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ORDER/TRADE INFO
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_order_list(self):
        """Get all orders for today"""
        try:
            return self.dhan.get_order_list()
        except Exception as e:
            logger.error(f"❌ Get orders failed: {e}")
            return []
    
    def get_order_by_id(self, order_id):
        """Get specific order details"""
        try:
            return self.dhan.get_order_by_id(order_id)
        except Exception as e:
            return None
    
    def get_trade_book(self):
        """Get all executed trades for today"""
        try:
            return self.dhan.get_trade_book()
        except Exception as e:
            return []
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PORTFOLIO
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_positions(self):
        """Get all open positions"""
        try:
            return self.dhan.get_positions()
        except Exception as e:
            logger.error(f"❌ Get positions failed: {e}")
            return []
    
    def get_holdings(self):
        """Get all holdings in demat"""
        try:
            return self.dhan.get_holdings()
        except Exception as e:
            return []
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FUND LIMITS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_fund_limits(self):
        """Get trading account balance & margin"""
        try:
            return self.dhan.get_fund_limits()
        except Exception as e:
            logger.error(f"❌ Get funds failed: {e}")
            return None
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INSTRUMENT LIST
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_security_list(self, mode="compact"):
        """Download instrument master list"""
        try:
            return self.dhan.fetch_security_list(mode)
        except Exception as e:
            logger.error(f"❌ Fetch security list failed: {e}")
            return None
