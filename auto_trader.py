"""
╔══════════════════════════════════════════════╗
║  FILE 9: auto_trader.py                      ║
║  🤖 MAIN AUTO TRADING BOT                    ║
║  Combines everything. Runs the show.         ║
╚══════════════════════════════════════════════╝
"""

import time
import schedule
from datetime import datetime, time as dtime

from config import TradingConfig, logger
from dhan_client import DhanClient
from option_chain_fetcher import OptionChainFetcher
from market_feed import LiveMarketFeed
from confluence_scorer import ConfluenceScorer
from trade_builder import TradeBuilder
from virtual_portfolio import VirtualPortfolio


class AutoTrader:
    """
    🤖 THE MAIN BOT
    
    Flow:
    1. Fetch Option Chain from DhanHQ
    2. Run 4-category Confluence Scoring
    3. If score >= 85 → Build & Execute Trade
    4. Monitor SL/Target every cycle
    5. Close all at 3:15 PM
    """
    
    def __init__(self, config: TradingConfig = None):
        self.config = config or TradingConfig()
        
        # Initialize all components
        logger.info("🚀 Initializing Auto Trader...")
        self.client = DhanClient()
        self.oc_fetcher = OptionChainFetcher(self.client)
        self.scorer = ConfluenceScorer()
        self.builder = TradeBuilder(self.config)
        self.portfolio = VirtualPortfolio(self.config)
        
        self.is_running = False
        self.cycle = 0
    
    def _is_market_open(self):
        now = datetime.now()
        if now.weekday() >= 5:
            return False
        t = now.time()
        return dtime(9, 15) <= t <= dtime(15, 30)
    
    def _check_daily_loss(self):
        today = datetime.now().strftime("%Y-%m-%d")
        realized = self.portfolio.data["daily_pnl"].get(today, 0)
        unrealized = sum(t["current_pnl"] for t in self.portfolio.data["open_trades"])
        total = realized + unrealized
        
        if total <= -self.config.max_daily_loss:
            logger.warning(f"🛑 DAILY LOSS LIMIT! ₹{total:,.2f}")
            self.portfolio.close_all()
            return False
        return True
    
    def run_cycle(self):
        """Main cycle — every 3 minutes"""
        if not self._is_market_open():
            return
        
        self.cycle += 1
        now = datetime.now()
        
        logger.info(f"━━━ Cycle #{self.cycle} | {now.strftime('%H:%M:%S')} ━━━")
        
        if not self._check_daily_loss():
            return
        
        for symbol in self.config.symbols:
            try:
                # 1. Fetch Option Chain from DhanHQ
                data = self.oc_fetcher.fetch_option_chain(symbol)
                if not data:
                    continue
                
                self.oc_fetcher.print_summary(data)
                
                # 2. Update existing positions
                if data.get("chain_df") is not None and len(data["chain_df"]) > 0:
                    self.portfolio.update_pnl(data["chain_df"], symbol)
                self.portfolio.check_sl_target()
                
                # 3. Confluence Scoring
                confluence = self.scorer.calculate(data)
                self.portfolio.log_confluence(confluence)
                self.scorer.print_confluence(confluence, symbol)
                
                # 4. Exit time check
                if now.time() >= dtime(self.config.exit_hour, self.config.exit_minute):
                    logger.info(f"🕐 EXIT TIME — closing all")
                    self.portfolio.close_all()
                    continue
                
                # 5. Entry window check
                entry_start = dtime(self.config.entry_start_hour, self.config.entry_start_minute)
                entry_end = dtime(self.config.entry_end_hour, self.config.entry_end_minute)
                
                if not (entry_start <= now.time() <= entry_end):
                    continue
                
                # 6. Already have position?
                has_open = any(
                    t["symbol"] == symbol and t["status"] == "OPEN"
                    for t in self.portfolio.data["open_trades"]
                )
                if has_open:
                    continue
                
                # 7. Max trades check
                today = now.strftime("%Y-%m-%d")
                today_count = sum(
                    1 for t in self.portfolio.data["open_trades"] + self.portfolio.data["closed_trades"]
                    if t.get("entry_time", "").startswith(today)
                )
                if today_count >= self.config.max_trades_per_day:
                    continue
                
                # 8. THE DECISION
                if confluence.should_trade and confluence.win_rate >= self.config.min_confluence_score:
                    logger.info(f"✅ Score {confluence.win_rate:.1f}% >= {self.config.min_confluence_score}% → TRADE!")
                    
                    trade = self.builder.build(data, confluence)
                    if trade:
                        self.builder.print_trade(trade)
                        self.portfolio.execute_trade(trade)
                else:
                    logger.info(f"🔴 Score {confluence.win_rate:.1f}% < {self.config.min_confluence_score}% → WAIT")
            
            except Exception as e:
                logger.error(f"❌ Error in {symbol}: {e}")
                import traceback
                traceback.print_exc()
        
        self.portfolio.dashboard()
    
    def start(self):
        """Start the bot"""
        self.is_running = True
        
        print(f"\n{'🇮🇳'*20}")
        print(f"  🤖 DHAN HQ CONFLUENCE AUTO TRADER")
        print(f"{'🇮🇳'*20}")
        print(f"  📊 Symbols:    {', '.join(self.config.symbols)}")
        print(f"  💰 Capital:    ₹{self.config.initial_capital:,.0f}")
        print(f"  🎯 Min Score:  {self.config.min_confluence_score}%")
        print(f"  🛑 Max Loss:   ₹{self.config.max_daily_loss:,.0f}/day")
        print(f"  🔄 Interval:   {self.config.check_interval_seconds}s")
        print(f"{'═'*50}\n")
        
        self.run_cycle()
        
        schedule.every(self.config.check_interval_seconds).seconds.do(self.run_cycle)
        schedule.every().day.at("15:35").do(self._eod)
        
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
    
    def _eod(self):
        logger.info("📋 END OF DAY REPORT")
        self.portfolio.close_all()
        self.portfolio.dashboard()
        self.cycle = 0
    
    def stop(self):
        self.is_running = False
        logger.info("🛑 Bot Stopped!")
    
    def analyze_once(self, symbol="NIFTY"):
        """Manual one-time analysis"""
        data = self.oc_fetcher.fetch_option_chain(symbol)
        if not data:
            return None
        
        self.oc_fetcher.print_summary(data)
        confluence = self.scorer.calculate(data)
        self.scorer.print_confluence(confluence, symbol)
        
        if confluence.should_trade:
            trade = self.builder.build(data, confluence)
            if trade:
                self.builder.print_trade(trade)
                ans = input("\n  Execute? (y/n): ").strip().lower()
                if ans == 'y':
                    self.portfolio.execute_trade(trade)
        
        return confluence
