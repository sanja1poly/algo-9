"""
╔══════════════════════════════════════════════╗
║  FILE 4: market_feed.py                      ║
║  DhanHQ Live Market Feed via WebSocket       ║
╚══════════════════════════════════════════════╝

Real-time tick-by-tick data via DhanHQ WebSocket:
- LTP (Last Traded Price)
- Quote (with OI)
- Full Market Depth
"""

import threading
from dhanhq import DhanContext, MarketFeed
from config import DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN, logger


class LiveMarketFeed:
    """
    DhanHQ WebSocket based real-time market data
    
    Modes:
    - Ticker: LTP + LTT only (lightest)
    - Quote:  LTP + OHLC + OI + Volume (recommended)
    - Full:   Quote + Market Depth (heaviest)
    
    Limits:
    - Max 5 WebSocket connections per user
    - Max 5000 instruments per connection
    """
    
    def __init__(self, dhan_context: DhanContext = None):
        self.context = dhan_context or DhanContext(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
        self.feed = None
        self.is_connected = False
        self.latest_data = {}     # {security_id: {ltp, oi, volume, ...}}
        self._thread = None
    
    def start(self, instruments, version="v2"):
        """
        Start live feed in background thread
        
        Args:
            instruments: list of tuples
                [(MarketFeed.NSE, "1333", MarketFeed.Quote), ...]
            version: "v2" (use latest)
        
        Example:
            feed.start([
                (MarketFeed.NSE, "1333", MarketFeed.Quote),     # HDFC Bank
                (MarketFeed.NSE, "11915", MarketFeed.Ticker),   # TCS
            ])
        """
        try:
            self.feed = MarketFeed(self.context, instruments, version)
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            self.is_connected = True
            logger.info(f"📡 Market Feed started | {len(instruments)} instruments")
        except Exception as e:
            logger.error(f"❌ Market Feed start failed: {e}")
    
    def _run(self):
        """Background thread for websocket"""
        try:
            while True:
                self.feed.run_forever()
                response = self.feed.get_data()
                if response:
                    sec_id = str(response.get("security_id", response.get("securityId", "")))
                    if sec_id:
                        self.latest_data[sec_id] = response
        except Exception as e:
            logger.error(f"❌ Feed error: {e}")
            self.is_connected = False
    
    def get_ltp(self, security_id) -> float:
        """Get latest LTP for an instrument"""
        data = self.latest_data.get(str(security_id), {})
        return data.get("ltp", data.get("LTP", 0))
    
    def get_quote(self, security_id) -> dict:
        """Get full quote data"""
        return self.latest_data.get(str(security_id), {})
    
    def subscribe(self, instruments):
        """Subscribe to more instruments while running"""
        if self.feed:
            try:
                self.feed.subscribe_symbols(instruments)
                logger.info(f"📡 Subscribed {len(instruments)} more instruments")
            except Exception as e:
                logger.error(f"❌ Subscribe failed: {e}")
    
    def unsubscribe(self, instruments):
        """Unsubscribe instruments"""
        if self.feed:
            try:
                self.feed.unsubscribe_symbols(instruments)
            except Exception as e:
                logger.error(f"❌ Unsubscribe failed: {e}")
    
    def stop(self):
        """Disconnect WebSocket"""
        if self.feed:
            try:
                self.feed.disconnect()
                self.is_connected = False
                logger.info("📡 Market Feed disconnected")
            except:
                pass
