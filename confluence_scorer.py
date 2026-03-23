"""
╔══════════════════════════════════════════════╗
║  FILE 6: confluence_scorer.py                ║
║  🧠 MULTI-STRATEGY CONFLUENCE SCORING        ║
║  THE BRAIN OF THE SYSTEM                     ║
╚══════════════════════════════════════════════╝

4 Scoring Categories (25 pts each = 100 total):
1. OI Analysis         /25
2. Greeks & IV         /25
3. PCR & Volume        /25
4. Price Action        /25

TRADE ONLY IF TOTAL >= 85
"""

import numpy as np
from datetime import datetime, time as dtime
from dataclasses import dataclass, field
from typing import List, Dict

from config import TradeDirection, ConfidenceLevel, StrategyType, logger
from greeks_calculator import GreeksCalculator


@dataclass
class StrategyScore:
    name: str
    score: float              # 0-25
    direction: TradeDirection
    confidence: float         # 0-100%
    signals: List[str]

@dataclass
class ConfluenceResult:
    total_score: float
    win_rate: float
    confidence: ConfidenceLevel
    direction: TradeDirection
    should_trade: bool
    scores: List[StrategyScore]
    recommended_strategy: StrategyType
    reasoning: List[str]
    timestamp: str


class ConfluenceScorer:
    """
    🧠 Sab strategies combine karke ek final score deta hai
    
    Score >= 85 → TRADE ✅
    Score < 85  → NO TRADE 🔴
    """
    
    def __init__(self):
        self.greeks = GreeksCalculator()
    
    def calculate(self, data: Dict) -> ConfluenceResult:
        """Master confluence calculation"""
        
        s1 = self._score_oi(data)
        s2 = self._score_greeks_iv(data)
        s3 = self._score_pcr_volume(data)
        s4 = self._score_price_action(data)
        
        all_scores = [s1, s2, s3, s4]
        total = sum(s.score for s in all_scores)
        
        # Direction consensus
        dirs = [s.direction for s in all_scores if s.direction != TradeDirection.NEUTRAL]
        bull = sum(1 for d in dirs if "BULLISH" in d.value)
        bear = sum(1 for d in dirs if "BEARISH" in d.value)
        
        if bull > bear:
            direction = TradeDirection.STRONG_BULLISH if bull >= 3 else TradeDirection.BULLISH
        elif bear > bull:
            direction = TradeDirection.STRONG_BEARISH if bear >= 3 else TradeDirection.BEARISH
        else:
            direction = TradeDirection.NEUTRAL
        
        # Win rate
        win_rate = total
        if len(set(d.value for d in dirs)) == 1 and len(dirs) >= 2:
            win_rate += 3
        for s in all_scores:
            if s.score < 10:
                win_rate -= 5
        win_rate = min(max(win_rate, 0), 100)
        
        # Confidence
        if win_rate >= 90:
            conf = ConfidenceLevel.EXTREME
        elif win_rate >= 85:
            conf = ConfidenceLevel.VERY_HIGH
        elif win_rate >= 80:
            conf = ConfidenceLevel.HIGH
        elif win_rate >= 70:
            conf = ConfidenceLevel.MEDIUM
        elif win_rate >= 60:
            conf = ConfidenceLevel.LOW
        else:
            conf = ConfidenceLevel.NO_TRADE
        
        should_trade = win_rate >= 85
        
        # Strategy selection
        if not should_trade:
            strategy = StrategyType.NO_TRADE
        elif direction == TradeDirection.NEUTRAL:
            strategy = StrategyType.IRON_CONDOR
        elif "BULLISH" in direction.value:
            strategy = StrategyType.BULL_PUT_SPREAD if win_rate >= 90 else StrategyType.IRON_CONDOR_BULLISH
        elif "BEARISH" in direction.value:
            strategy = StrategyType.BEAR_CALL_SPREAD if win_rate >= 90 else StrategyType.IRON_CONDOR_BEARISH
        else:
            strategy = StrategyType.IRON_CONDOR
        
        reasoning = [f"Score: {total}/100 → Win Rate: {win_rate:.1f}%"]
        reasoning.append(f"Direction: {direction.value}")
        for s in all_scores:
            reasoning.append(f"  {s.name}: {s.score:.1f}/25")
        
        result = ConfluenceResult(
            total_score=total,
            win_rate=round(win_rate, 1),
            confidence=conf,
            direction=direction,
            should_trade=should_trade,
            scores=all_scores,
            recommended_strategy=strategy,
            reasoning=reasoning,
            timestamp=datetime.now().isoformat(),
        )
        
        logger.info(f"🧠 Confluence: {total}/100 | Win: {win_rate:.1f}% | "
                    f"{'✅ TRADE' if should_trade else '🔴 NO TRADE'}")
        
        return result
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SCORE 1: OI ANALYSIS (Max 25)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def _score_oi(self, data: Dict) -> StrategyScore:
        score = 0
        signals = []
        direction = TradeDirection.NEUTRAL
        
        near_ce_chg = data.get("near_ce_chg", 0)
        near_pe_chg = data.get("near_pe_chg", 0)
        spot = data.get("underlying", 0)
        support = data.get("support", 0)
        resistance = data.get("resistance", 0)
        
        # 1a. OI Change Direction (8 pts)
        if near_pe_chg > 0 and near_ce_chg < 0:
            score += 8
            direction = TradeDirection.STRONG_BULLISH
            signals.append(f"🟢 Strong Bullish OI: PE↑ CE↓")
        elif near_pe_chg > 0 and near_ce_chg > 0:
            ratio = near_pe_chg / (near_ce_chg + 1)
            if ratio > 1.5:
                score += 6; direction = TradeDirection.BULLISH
                signals.append(f"🟢 Bullish bias: PE building faster")
            elif ratio < 0.67:
                score += 4; direction = TradeDirection.BEARISH
                signals.append(f"🔴 Bearish bias: CE building faster")
            else:
                score += 7; direction = TradeDirection.NEUTRAL
                signals.append(f"🟡 Range-bound: Both OI building")
        elif near_ce_chg > 0 and near_pe_chg < 0:
            score += 8; direction = TradeDirection.STRONG_BEARISH
            signals.append(f"🔴 Strong Bearish OI: CE↑ PE↓")
        else:
            score += 3
            signals.append("⚪ OI unwinding")
        
        # 1b. Support/Resistance walls (7 pts)
        if spot > 0 and resistance > support > 0:
            range_pct = (resistance - support) / spot * 100
            if range_pct > 3:
                score += 7; signals.append(f"✅ Wide range: {range_pct:.1f}%")
            elif range_pct > 2:
                score += 5; signals.append(f"✅ Good range: {range_pct:.1f}%")
            elif range_pct > 1:
                score += 3; signals.append(f"⚠️ Narrow range")
            else:
                score += 1; signals.append(f"❌ Very narrow range")
        
        # 1c. Spot within range (5 pts)
        if support < spot < resistance and resistance > support:
            dist = (spot - support) / (resistance - support) * 100
            if 30 <= dist <= 70:
                score += 5; signals.append(f"✅ Spot centered in range")
            elif 20 <= dist <= 80:
                score += 3; signals.append(f"⚠️ Spot slightly off-center")
            else:
                score += 1; signals.append(f"❌ Spot near boundary")
        
        # 1d. OI Concentration (5 pts)
        top_ce = data.get("top_ce_oi", [])
        top_pe = data.get("top_pe_oi", [])
        if len(top_ce) >= 2 and len(top_pe) >= 2:
            ce_conc = top_ce[0].get('ce_oi', 0) / (top_ce[1].get('ce_oi', 1) + 1)
            pe_conc = top_pe[0].get('pe_oi', 0) / (top_pe[1].get('pe_oi', 1) + 1)
            if ce_conc > 1.5 and pe_conc > 1.5:
                score += 5; signals.append(f"✅ Strong OI walls")
            elif ce_conc > 1.2 or pe_conc > 1.2:
                score += 3; signals.append(f"⚠️ Moderate OI walls")
            else:
                score += 1; signals.append(f"❌ Weak OI walls")
        
        return StrategyScore("OI_ANALYSIS", min(score, 25), direction, min(score/25*100, 100), signals)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SCORE 2: GREEKS & IV (Max 25)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def _score_greeks_iv(self, data: Dict) -> StrategyScore:
        score = 0
        signals = []
        direction = TradeDirection.NEUTRAL
        
        iv = data.get("atm_iv", 15)
        iv_skew = data.get("iv_skew", 0)
        spot = data.get("underlying", 0)
        atm = data.get("atm", 0)
        step = data.get("step", 50)
        expiry = data.get("expiry", "")
        
        _, T = GreeksCalculator.days_to_expiry(expiry) if expiry else (7, 7/365)
        
        # 2a. IV Level (7 pts)
        if iv > 20:
            score += 7; signals.append(f"✅ High IV ({iv:.1f}%)")
        elif iv > 15:
            score += 5; signals.append(f"✅ Good IV ({iv:.1f}%)")
        elif iv > 11:
            score += 3; signals.append(f"⚠️ Normal IV ({iv:.1f}%)")
        else:
            score += 1; signals.append(f"❌ Low IV ({iv:.1f}%)")
        
        # 2b. IV Skew (5 pts)
        if abs(iv_skew) < 2:
            score += 5; signals.append(f"✅ Balanced IV skew")
        elif abs(iv_skew) < 5:
            score += 4; signals.append(f"⚠️ Moderate skew ({iv_skew:+.1f})")
            direction = TradeDirection.BEARISH if iv_skew > 0 else TradeDirection.BULLISH
        else:
            score += 2; signals.append(f"❌ High skew ({iv_skew:+.1f})")
        
        # 2c. Probability of Profit (7 pts)
        if spot > 0 and iv > 0:
            sell_ce = atm + step * 3
            sell_pe = atm - step * 3
            sigma = iv / 100
            
            prob_ce = self.greeks.prob_otm(spot, sell_ce, T, sigma, "CE")
            prob_pe = self.greeks.prob_otm(spot, sell_pe, T, sigma, "PE")
            combined = prob_ce * prob_pe / 100
            
            if combined > 75:
                score += 7; signals.append(f"✅ High prob: {combined:.1f}%")
            elif combined > 60:
                score += 5; signals.append(f"✅ Good prob: {combined:.1f}%")
            elif combined > 45:
                score += 3; signals.append(f"⚠️ Moderate prob: {combined:.1f}%")
            else:
                score += 1; signals.append(f"❌ Low prob: {combined:.1f}%")
        
        # 2d. Expected Move vs Range (6 pts)
        if spot > 0 and iv > 0:
            exp_move = self.greeks.expected_move(spot, T, iv / 100)
            oi_range = data.get("resistance", 0) - data.get("support", 0)
            
            if oi_range > 0 and exp_move < oi_range * 0.6:
                score += 6; signals.append(f"✅ Exp move (₹{exp_move:.0f}) < OI range (₹{oi_range:.0f})")
            elif oi_range > 0 and exp_move < oi_range * 0.8:
                score += 4; signals.append(f"⚠️ Exp move near OI range")
            else:
                score += 1; signals.append(f"❌ Exp move exceeds OI range")
        
        return StrategyScore("GREEKS_IV", min(score, 25), direction, min(score/25*100, 100), signals)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SCORE 3: PCR & VOLUME (Max 25)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def _score_pcr_volume(self, data: Dict) -> StrategyScore:
        score = 0
        signals = []
        direction = TradeDirection.NEUTRAL
        
        pcr_oi = data.get("pcr_oi", 0)
        pcr_vol = data.get("pcr_vol", 0)
        near_pcr = data.get("near_pcr", 0)
        
        # 3a. PCR OI (8 pts)
        if 0.8 <= pcr_oi <= 1.2:
            score += 8; direction = TradeDirection.NEUTRAL
            signals.append(f"✅ Neutral PCR ({pcr_oi})")
        elif 1.2 < pcr_oi <= 1.5:
            score += 6; direction = TradeDirection.BULLISH
            signals.append(f"🟢 Bullish PCR ({pcr_oi})")
        elif 0.6 <= pcr_oi < 0.8:
            score += 6; direction = TradeDirection.BEARISH
            signals.append(f"🔴 Bearish PCR ({pcr_oi})")
        elif pcr_oi > 1.5:
            score += 4; direction = TradeDirection.STRONG_BULLISH
            signals.append(f"🟢🟢 Very bullish PCR ({pcr_oi})")
        elif pcr_oi < 0.6:
            score += 4; direction = TradeDirection.STRONG_BEARISH
            signals.append(f"🔴🔴 Very bearish PCR ({pcr_oi})")
        
        # 3b. PCR Alignment (5 pts)
        pcr_diff = abs(pcr_oi - pcr_vol)
        if pcr_diff < 0.2:
            score += 5; signals.append(f"✅ PCR aligned")
        elif pcr_diff < 0.4:
            score += 3; signals.append(f"⚠️ PCR slight divergence")
        else:
            score += 1; signals.append(f"❌ PCR divergence")
        
        # 3c. Near ATM PCR (5 pts)
        if 0.7 <= near_pcr <= 1.3:
            score += 5; signals.append(f"✅ Near ATM PCR balanced ({near_pcr})")
        elif 0.5 <= near_pcr <= 1.5:
            score += 3; signals.append(f"⚠️ Near ATM PCR: {near_pcr}")
        else:
            score += 1; signals.append(f"❌ Near ATM PCR extreme")
        
        # 3d. Bid-Ask spread quality (7 pts)
        df = data.get("chain_df", None)
        atm = data.get("atm", 0)
        if df is not None and len(df) > 0:
            atm_row = df[df['strike'] == atm]
            if len(atm_row) > 0:
                ce_spread = abs(atm_row.iloc[0].get('ce_ask', 0) - atm_row.iloc[0].get('ce_bid', 0))
                pe_spread = abs(atm_row.iloc[0].get('pe_ask', 0) - atm_row.iloc[0].get('pe_bid', 0))
                avg_spread = (ce_spread + pe_spread) / 2
                
                if avg_spread < 2:
                    score += 7; signals.append(f"✅ Tight spreads (₹{avg_spread:.1f})")
                elif avg_spread < 5:
                    score += 5; signals.append(f"✅ Good spreads (₹{avg_spread:.1f})")
                elif avg_spread < 10:
                    score += 3; signals.append(f"⚠️ Moderate spreads")
                else:
                    score += 1; signals.append(f"❌ Wide spreads")
        
        return StrategyScore("PCR_VOLUME", min(score, 25), direction, min(score/25*100, 100), signals)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SCORE 4: PRICE ACTION (Max 25)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def _score_price_action(self, data: Dict) -> StrategyScore:
        score = 0
        signals = []
        direction = TradeDirection.NEUTRAL
        
        spot = data.get("underlying", 0)
        max_pain = data.get("max_pain", 0)
        
        # 4a. Max Pain alignment (7 pts)
        if spot > 0 and max_pain > 0:
            dev_pct = abs(max_pain - spot) / spot * 100
            if dev_pct < 0.5:
                score += 7; signals.append(f"✅ Spot AT max pain")
            elif dev_pct < 1.0:
                score += 5; signals.append(f"✅ Near max pain ({dev_pct:.2f}%)")
            elif dev_pct < 2.0:
                score += 3; signals.append(f"⚠️ {dev_pct:.2f}% from max pain")
            else:
                score += 1; signals.append(f"❌ Far from max pain")
        
        # 4b. OI Trend consistency (8 pts)
        history = data.get("oi_history", [])
        if len(history) >= 3:
            pcrs = [h["pcr"] for h in history[-3:]]
            stable = all(abs(pcrs[i] - pcrs[i-1]) < 0.15 for i in range(1, len(pcrs)))
            if stable:
                score += 6; signals.append(f"✅ PCR stable")
            else:
                score += 2; signals.append(f"⚠️ PCR unstable")
            
            supports = [h["max_pe_oi_strike"] for h in history[-3:]]
            resistances = [h["max_ce_oi_strike"] for h in history[-3:]]
            if len(set(supports)) == 1 and len(set(resistances)) == 1:
                score += 2; signals.append(f"✅ S/R levels locked")
        else:
            score += 3; signals.append(f"ℹ️ Building history...")
        
        # 4c. Time of day (5 pts)
        now = datetime.now().time()
        if dtime(10, 30) <= now <= dtime(14, 0):
            score += 5; signals.append(f"✅ Prime trading window")
        elif dtime(9, 30) <= now <= dtime(10, 30):
            score += 3; signals.append(f"⚠️ First hour")
        elif dtime(14, 0) <= now <= dtime(15, 0):
            score += 4; signals.append(f"✅ Afternoon theta")
        else:
            score += 1; signals.append(f"⚠️ Off-peak")
        
        # 4d. Expiry day factor (5 pts)
        expiry = data.get("expiry", "")
        if expiry:
            dte, _ = GreeksCalculator.days_to_expiry(expiry)
            if dte == 0:
                score += 5; signals.append(f"🔥 EXPIRY DAY!")
            elif dte == 1:
                score += 4; signals.append(f"✅ 1 DTE")
            elif dte <= 3:
                score += 3; signals.append(f"✅ {dte} DTE")
            elif dte <= 7:
                score += 2; signals.append(f"⚠️ {dte} DTE")
            else:
                score += 1; signals.append(f"❌ {dte} DTE")
        
        return StrategyScore("PRICE_ACTION", min(score, 25), direction, min(score/25*100, 100), signals)
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DISPLAY
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def print_confluence(self, c: ConfluenceResult, symbol: str):
        bar_fill = int(c.total_score / 5)
        bar = "█" * bar_fill + "░" * (20 - bar_fill)
        emoji = "🟢" if c.win_rate >= 85 else "🟡" if c.win_rate >= 70 else "🔴"
        
        print(f"\n  ┌────────────────────────────────────────┐")
        print(f"  │ 🧠 CONFLUENCE — {symbol:<22} │")
        print(f"  ├────────────────────────────────────────┤")
        print(f"  │ [{bar}] {c.total_score:>5.0f}/100 │")
        print(f"  │ Win Rate:   {emoji} {c.win_rate:>5.1f}%                 │")
        print(f"  │ Direction:  {c.direction.value:<26} │")
        print(f"  │ Strategy:   {c.recommended_strategy.value:<26} │")
        print(f"  ├────────────────────────────────────────┤")
        for s in c.scores:
            b = "█" * int(s.score) + "░" * (25 - int(s.score))
            print(f"  │ {s.name:<14} [{b}] {s.score:>4.0f}/25│")
        print(f"  ├────────────────────────────────────────┤")
        if c.should_trade:
            print(f"  │  ✅ TRADE SIGNAL! Score >= 85          │")
        else:
            print(f"  │  🔴 NO TRADE. Waiting...               │")
        print(f"  └────────────────────────────────────────┘")
        
        for s in c.scores:
            print(f"\n  ── {s.name} ({s.score:.0f}/25) ──")
            for sig in s.signals:
                print(f"    {sig}")
