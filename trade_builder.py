"""
╔══════════════════════════════════════════════╗
║  FILE 7: trade_builder.py                    ║
║  Build Exact Trade Legs When Score >= 85     ║
╚══════════════════════════════════════════════╝
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from config import StrategyType, TradeDirection, TradingConfig, logger


@dataclass
class TradeSetup:
    symbol: str
    strategy: StrategyType
    direction: TradeDirection
    legs: List[Dict]
    win_rate: float
    max_profit: float
    max_loss: float
    risk_reward: float
    stop_loss: float
    target: float
    breakevens: List[float]
    confluence_score: float
    reasoning: List[str]


class TradeBuilder:
    """Build exact trade legs based on confluence result"""
    
    def __init__(self, config: TradingConfig = None):
        self.config = config or TradingConfig()
    
    def build(self, data: Dict, confluence) -> Optional[TradeSetup]:
        if not confluence.should_trade:
            return None
        
        strategy = confluence.recommended_strategy
        
        if strategy in [StrategyType.IRON_CONDOR, StrategyType.IRON_CONDOR_BULLISH, StrategyType.IRON_CONDOR_BEARISH]:
            return self._build_iron_condor(data, confluence)
        elif strategy == StrategyType.BULL_PUT_SPREAD:
            return self._build_bull_put_spread(data, confluence)
        elif strategy == StrategyType.BEAR_CALL_SPREAD:
            return self._build_bear_call_spread(data, confluence)
        else:
            return self._build_iron_condor(data, confluence)
    
    def _get_premium(self, df, strike, opt_type):
        """Get LTP from chain dataframe"""
        row = df[df['strike'] == strike]
        if len(row) > 0:
            col = f"{opt_type.lower()}_ltp"
            return row.iloc[0].get(col, 0) or 0
        return 0
    
    def _get_sec_id(self, df, strike, opt_type):
        """Get Dhan security_id from chain"""
        row = df[df['strike'] == strike]
        if len(row) > 0:
            col = f"{opt_type.lower()}_sec_id"
            return str(row.iloc[0].get(col, ""))
        return ""
    
    def _build_iron_condor(self, data, confluence) -> TradeSetup:
        df = data["chain_df"]
        step = data["step"]
        lot_size = data["lot_size"]
        support = data["support"]
        resistance = data["resistance"]
        
        sell_ce = resistance
        sell_pe = support
        wing = step * 2
        buy_ce = sell_ce + wing
        buy_pe = sell_pe - wing
        
        # Skew adjustment
        if confluence.recommended_strategy == StrategyType.IRON_CONDOR_BULLISH:
            sell_ce = resistance + step
        elif confluence.recommended_strategy == StrategyType.IRON_CONDOR_BEARISH:
            sell_pe = support - step
        
        sell_ce_prem = self._get_premium(df, sell_ce, "ce")
        buy_ce_prem = self._get_premium(df, buy_ce, "ce")
        sell_pe_prem = self._get_premium(df, sell_pe, "pe")
        buy_pe_prem = self._get_premium(df, buy_pe, "pe")
        
        net_credit = sell_ce_prem - buy_ce_prem + sell_pe_prem - buy_pe_prem
        max_profit = net_credit * lot_size
        max_loss = (wing - net_credit) * lot_size
        rr = round(max_profit / max_loss, 2) if max_loss > 0 else 0
        
        legs = [
            {"type": "CE", "strike": sell_ce, "action": "SELL", "premium": sell_ce_prem,
             "lots": 1, "sec_id": self._get_sec_id(df, sell_ce, "ce")},
            {"type": "CE", "strike": buy_ce, "action": "BUY", "premium": buy_ce_prem,
             "lots": 1, "sec_id": self._get_sec_id(df, buy_ce, "ce")},
            {"type": "PE", "strike": sell_pe, "action": "SELL", "premium": sell_pe_prem,
             "lots": 1, "sec_id": self._get_sec_id(df, sell_pe, "pe")},
            {"type": "PE", "strike": buy_pe, "action": "BUY", "premium": buy_pe_prem,
             "lots": 1, "sec_id": self._get_sec_id(df, buy_pe, "pe")},
        ]
        
        return TradeSetup(
            symbol=data["symbol"],
            strategy=StrategyType.IRON_CONDOR,
            direction=confluence.direction,
            legs=legs,
            win_rate=confluence.win_rate,
            max_profit=max_profit,
            max_loss=max_loss,
            risk_reward=rr,
            stop_loss=max_loss * self.config.sl_multiplier,
            target=max_profit * self.config.target_multiplier,
            breakevens=[sell_pe - net_credit, sell_ce + net_credit],
            confluence_score=confluence.total_score,
            reasoning=confluence.reasoning,
        )
    
    def _build_bull_put_spread(self, data, confluence) -> TradeSetup:
        df = data["chain_df"]
        step = data["step"]
        lot_size = data["lot_size"]
        support = data["support"]
        
        sell_pe = support
        buy_pe = sell_pe - step * 3
        width = sell_pe - buy_pe
        
        sell_prem = self._get_premium(df, sell_pe, "pe")
        buy_prem = self._get_premium(df, buy_pe, "pe")
        net_credit = sell_prem - buy_prem
        max_profit = net_credit * lot_size
        max_loss = (width - net_credit) * lot_size
        
        legs = [
            {"type": "PE", "strike": sell_pe, "action": "SELL", "premium": sell_prem,
             "lots": 1, "sec_id": self._get_sec_id(df, sell_pe, "pe")},
            {"type": "PE", "strike": buy_pe, "action": "BUY", "premium": buy_prem,
             "lots": 1, "sec_id": self._get_sec_id(df, buy_pe, "pe")},
        ]
        
        return TradeSetup(
            symbol=data["symbol"], strategy=StrategyType.BULL_PUT_SPREAD,
            direction=TradeDirection.BULLISH, legs=legs,
            win_rate=confluence.win_rate,
            max_profit=max_profit, max_loss=max_loss,
            risk_reward=round(max_profit/max_loss, 2) if max_loss > 0 else 0,
            stop_loss=max_loss * self.config.sl_multiplier,
            target=max_profit * self.config.target_multiplier,
            breakevens=[sell_pe - net_credit],
            confluence_score=confluence.total_score, reasoning=confluence.reasoning,
        )
    
    def _build_bear_call_spread(self, data, confluence) -> TradeSetup:
        df = data["chain_df"]
        step = data["step"]
        lot_size = data["lot_size"]
        resistance = data["resistance"]
        
        sell_ce = resistance
        buy_ce = sell_ce + step * 3
        width = buy_ce - sell_ce
        
        sell_prem = self._get_premium(df, sell_ce, "ce")
        buy_prem = self._get_premium(df, buy_ce, "ce")
        net_credit = sell_prem - buy_prem
        max_profit = net_credit * lot_size
        max_loss = (width - net_credit) * lot_size
        
        legs = [
            {"type": "CE", "strike": sell_ce, "action": "SELL", "premium": sell_prem,
             "lots": 1, "sec_id": self._get_sec_id(df, sell_ce, "ce")},
            {"type": "CE", "strike": buy_ce, "action": "BUY", "premium": buy_prem,
             "lots": 1, "sec_id": self._get_sec_id(df, buy_ce, "ce")},
        ]
        
        return TradeSetup(
            symbol=data["symbol"], strategy=StrategyType.BEAR_CALL_SPREAD,
            direction=TradeDirection.BEARISH, legs=legs,
            win_rate=confluence.win_rate,
            max_profit=max_profit, max_loss=max_loss,
            risk_reward=round(max_profit/max_loss, 2) if max_loss > 0 else 0,
            stop_loss=max_loss * self.config.sl_multiplier,
            target=max_profit * self.config.target_multiplier,
            breakevens=[sell_ce + net_credit],
            confluence_score=confluence.total_score, reasoning=confluence.reasoning,
        )
    
    def print_trade(self, trade: TradeSetup):
        if not trade:
            return
        print(f"\n  {'🟢'*20}")
        print(f"  📋 {trade.strategy.value} | {trade.symbol}")
        print(f"  🎯 Win Rate: {trade.win_rate:.1f}% | Score: {trade.confluence_score}")
        print(f"  💰 Max Profit: ₹{trade.max_profit:,.2f}")
        print(f"  💀 Max Loss:   ₹{trade.max_loss:,.2f}")
        print(f"  🛑 SL: ₹{trade.stop_loss:,.2f} | 🎯 TGT: ₹{trade.target:,.2f}")
        print(f"  📏 Breakevens: {trade.breakevens}")
        for leg in trade.legs:
            e = "📤" if leg["action"] == "SELL" else "📥"
            print(f"    {e} {leg['action']} {trade.symbol} {leg['strike']} {leg['type']} @ ₹{leg['premium']:.2f}")
        print(f"  {'🟢'*20}")
