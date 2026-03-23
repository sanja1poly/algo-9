"""
╔══════════════════════════════════════════════╗
║  FILE 8: virtual_portfolio.py                ║
║  Virtual ₹ Paper Trading Portfolio           ║
╚══════════════════════════════════════════════╝
"""

import json
import os
from datetime import datetime
from config import PORTFOLIO_FILE, TradingConfig, LOT_SIZES, logger


class VirtualPortfolio:
    """Virtual trading with ₹ — real data, fake money"""
    
    def __init__(self, config: TradingConfig = None):
        self.config = config or TradingConfig()
        self.data = self._load()
    
    def _load(self):
        if os.path.exists(PORTFOLIO_FILE):
            with open(PORTFOLIO_FILE, 'r') as f:
                return json.load(f)
        p = {
            "initial_capital": self.config.initial_capital,
            "available_margin": self.config.initial_capital,
            "used_margin": 0,
            "open_trades": [],
            "closed_trades": [],
            "realized_pnl": 0,
            "brokerage_paid": 0,
            "daily_pnl": {},
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "skipped": 0,
            "confluence_log": [],
            "created": datetime.now().isoformat(),
        }
        self._save(p)
        return p
    
    def _save(self, d=None):
        d = d or self.data
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(d, f, indent=2, default=str)
    
    def log_confluence(self, confluence):
        self.data["confluence_log"].append({
            "time": confluence.timestamp,
            "score": confluence.total_score,
            "win_rate": confluence.win_rate,
            "traded": confluence.should_trade,
        })
        if not confluence.should_trade:
            self.data["skipped"] += 1
        if len(self.data["confluence_log"]) > 500:
            self.data["confluence_log"] = self.data["confluence_log"][-500:]
        self._save()
    
    def execute_trade(self, trade_setup) -> bool:
        lot_size = LOT_SIZES.get(trade_setup.symbol, 50)
        
        # Margin calculation
        margin = 0
        for leg in trade_setup.legs:
            if leg["action"] == "SELL":
                margin += leg["strike"] * lot_size * 0.12
            else:
                margin += leg["premium"] * lot_size
        
        if len(trade_setup.legs) >= 4:
            margin *= 0.35
        elif len(trade_setup.legs) == 2:
            margin *= 0.5
        
        if margin > self.data["available_margin"]:
            logger.warning(f"❌ Insufficient margin! Need ₹{margin:,.0f}")
            return False
        
        brokerage = self.config.brokerage_per_order * len(trade_setup.legs)
        
        record = {
            "id": f"T{self.data['total_trades']+1:04d}",
            "symbol": trade_setup.symbol,
            "strategy": trade_setup.strategy.value,
            "direction": trade_setup.direction.value,
            "legs": trade_setup.legs,
            "win_rate": trade_setup.win_rate,
            "score": trade_setup.confluence_score,
            "max_profit": trade_setup.max_profit,
            "max_loss": trade_setup.max_loss,
            "sl": trade_setup.stop_loss,
            "target": trade_setup.target,
            "breakevens": trade_setup.breakevens,
            "margin": round(margin, 2),
            "brokerage": brokerage,
            "entry_time": datetime.now().isoformat(),
            "status": "OPEN",
            "current_pnl": 0,
        }
        
        self.data["open_trades"].append(record)
        self.data["available_margin"] -= (margin + brokerage)
        self.data["used_margin"] += margin
        self.data["brokerage_paid"] += brokerage
        self.data["total_trades"] += 1
        self._save()
        
        logger.info(f"✅ TRADE EXECUTED: {record['id']} | {trade_setup.strategy.value} | Score: {trade_setup.confluence_score}")
        return True
    
    def update_pnl(self, chain_df, symbol):
        """Update open trades PnL from live data"""
        for trade in self.data["open_trades"]:
            if trade["status"] != "OPEN" or trade["symbol"] != symbol:
                continue
            
            total_pnl = 0
            lot_size = LOT_SIZES.get(symbol, 50)
            
            for leg in trade["legs"]:
                row = chain_df[chain_df['strike'] == leg['strike']]
                if len(row) > 0:
                    col = f"{leg['type'].lower()}_ltp"
                    current = row.iloc[0].get(col, 0) or 0
                    
                    if leg['action'] == 'SELL':
                        total_pnl += (leg['premium'] - current) * lot_size
                    else:
                        total_pnl += (current - leg['premium']) * lot_size
            
            trade["current_pnl"] = round(total_pnl, 2)
        self._save()
    
    def check_sl_target(self):
        for trade in list(self.data["open_trades"]):
            if trade["status"] != "OPEN":
                continue
            
            if trade["current_pnl"] <= -abs(trade["sl"]):
                logger.info(f"🛑 SL HIT: {trade['id']} | PnL: ₹{trade['current_pnl']:,.2f}")
                self._close(trade, "STOP_LOSS")
            elif trade["current_pnl"] >= abs(trade["target"]):
                logger.info(f"🎯 TARGET HIT: {trade['id']} | PnL: ₹{trade['current_pnl']:,.2f}")
                self._close(trade, "TARGET")
    
    def _close(self, trade, reason):
        brokerage = self.config.brokerage_per_order * len(trade["legs"])
        net_pnl = trade["current_pnl"] - brokerage
        
        trade["status"] = "CLOSED"
        trade["exit_time"] = datetime.now().isoformat()
        trade["reason"] = reason
        trade["final_pnl"] = round(net_pnl, 2)
        
        self.data["realized_pnl"] += net_pnl
        self.data["brokerage_paid"] += brokerage
        self.data["available_margin"] += trade["margin"] + net_pnl
        self.data["used_margin"] -= trade["margin"]
        
        if net_pnl > 0:
            self.data["wins"] += 1
        else:
            self.data["losses"] += 1
        
        today = datetime.now().strftime("%Y-%m-%d")
        self.data["daily_pnl"][today] = self.data["daily_pnl"].get(today, 0) + net_pnl
        
        self.data["closed_trades"].append(trade)
        self.data["open_trades"].remove(trade)
        self._save()
    
    def close_all(self):
        for trade in list(self.data["open_trades"]):
            if trade["status"] == "OPEN":
                self._close(trade, "EOD")
    
    def dashboard(self):
        open_pnl = sum(t["current_pnl"] for t in self.data["open_trades"])
        total_val = self.data["available_margin"] + self.data["used_margin"] + open_pnl
        ret = ((total_val - self.data["initial_capital"]) / self.data["initial_capital"]) * 100
        closed = self.data["wins"] + self.data["losses"]
        wr = (self.data["wins"] / closed * 100) if closed > 0 else 0
        
        print(f"\n{'═'*60}")
        print(f"  💼 VIRTUAL PORTFOLIO DASHBOARD")
        print(f"{'═'*60}")
        print(f"  💰 Capital:      ₹{self.data['initial_capital']:>12,.2f}")
        print(f"  💎 Value:        ₹{total_val:>12,.2f} ({ret:+.2f}%)")
        print(f"  💵 Available:    ₹{self.data['available_margin']:>12,.2f}")
        print(f"  🔒 Used:         ₹{self.data['used_margin']:>12,.2f}")
        print(f"  📈 Realized:     ₹{self.data['realized_pnl']:>12,.2f}")
        print(f"  📊 Unrealized:   ₹{open_pnl:>12,.2f}")
        print(f"  💸 Brokerage:    ₹{self.data['brokerage_paid']:>12,.2f}")
        print(f"  ─────────────────────────────────────────")
        print(f"  📋 Trades:       {self.data['total_trades']:>12}")
        print(f"  🚫 Skipped:      {self.data['skipped']:>12}")
        print(f"  ✅ Wins:         {self.data['wins']:>12}")
        print(f"  ❌ Losses:       {self.data['losses']:>12}")
        print(f"  🎯 Win Rate:     {wr:>11.1f}%")
        
        for t in self.data["open_trades"]:
            e = "🟢" if t["current_pnl"] >= 0 else "🔴"
            print(f"\n    {t['id']} | {t['strategy']:<20} | {e} ₹{t['current_pnl']:>10,.2f}")
        print(f"{'═'*60}")
    
    def reset(self):
        if os.path.exists(PORTFOLIO_FILE):
            os.remove(PORTFOLIO_FILE)
        self.data = self._load()
        logger.info("🔄 Portfolio reset!")
