"""
╔══════════════════════════════════════════════╗
║  FILE 3: option_chain_fetcher.py             ║
║  DhanHQ Option Chain Data Fetcher            ║
╚══════════════════════════════════════════════╝

Dhan API se Option Chain data fetch kare:
- OI, Greeks, Volume, LTP, Bid/Ask, IV
- Expiry List
- All strikes data
- Rate limit: 1 request per 3 seconds
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Optional, List

from dhan_client import DhanClient
from config import (
    SECURITY_IDS, UNDERLYING_SEGMENTS, LOT_SIZES,
    STRIKE_STEPS, logger
)


class OptionChainFetcher:
    """
    DhanHQ Option Chain Data fetcher
    
    - Real-time Option Chain via DhanHQ v2 API
    - OI, Greeks, Volume, LTP, Bid/Ask, IV
    - Support/Resistance detection
    - Max Pain calculation
    - PCR calculation
    """
    
    def __init__(self, dhan_client: DhanClient):
        self.dhan = dhan_client.dhan
        self.client = dhan_client
        self.oi_history = {}    # For OI trend tracking
        self.last_fetch_time = {}
        
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FETCH EXPIRY LIST
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def get_expiry_list(self, symbol="NIFTY") -> List[str]:
        """
        Get all available expiry dates for a symbol
        Returns list of dates like ["2025-03-27", "2025-04-03", ...]
        """
        try:
            sec_id = SECURITY_IDS[symbol]
            seg = UNDERLYING_SEGMENTS[symbol]
            
            response = self.dhan.option_chain(
                under_security_id=sec_id,
                under_exchange_segment=seg,
            )
            
            if response and response.get("status") == "success":
                # Extract unique expiry dates from response
                data = response.get("data", {})
                expiries = sorted(set(
                    item.get("expiryDate", "")
                    for item in data if item.get("expiryDate")
                ))
                return expiries
            
            return []
        
        except Exception as e:
            logger.error(f"❌ Expiry list fetch failed for {symbol}: {e}")
            return []
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FETCH FULL OPTION CHAIN
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def fetch_option_chain(self, symbol="NIFTY", expiry=None) -> Optional[Dict]:
        """
        Fetch complete Option Chain from DhanHQ
        
        DhanHQ Option Chain API:
        - Endpoint: POST /v2/optionchain
        - Rate Limit: 1 request per 3 seconds
        - Returns: OI, Greeks, Volume, LTP, Bid/Ask, IV for all strikes
        
        Args:
            symbol: "NIFTY", "BANKNIFTY", etc.
            expiry: "2025-03-27" (if None, uses nearest)
        
        Returns:
            dict with all parsed option chain data
        """
        # Rate limiting
        now = time.time()
        last = self.last_fetch_time.get(symbol, 0)
        if now - last < 3:
            wait = 3 - (now - last)
            time.sleep(wait)
        
        try:
            sec_id = SECURITY_IDS[symbol]
            seg = UNDERLYING_SEGMENTS[symbol]
            step = STRIKE_STEPS[symbol]
            lot_size = LOT_SIZES[symbol]
            
            # Fetch from DhanHQ API
            if expiry:
                response = self.dhan.option_chain(
                    under_security_id=sec_id,
                    under_exchange_segment=seg,
                    expiry=expiry,
                )
            else:
                response = self.dhan.option_chain(
                    under_security_id=sec_id,
                    under_exchange_segment=seg,
                )
            
            self.last_fetch_time[symbol] = time.time()
            
            if not response or response.get("status") != "success":
                logger.error(f"❌ Option chain fetch failed: {response}")
                return None
            
            # Parse the raw data
            return self._parse_option_chain(response, symbol, step, lot_size)
        
        except Exception as e:
            logger.error(f"❌ Option chain error for {symbol}: {e}")
            return None
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PARSE OPTION CHAIN
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def _parse_option_chain(self, response, symbol, step, lot_size) -> Dict:
        """
        DhanHQ Option Chain response ko structured format me parse
        
        DhanHQ response me har strike ke liye milta hai:
        - oi (Open Interest)
        - greeks (delta, gamma, theta, vega)
        - volume
        - ltp (Last Traded Price)
        - best_bid / best_ask
        - iv (Implied Volatility)
        """
        raw_data = response.get("data", [])
        
        if not raw_data:
            logger.warning(f"⚠️ Empty option chain for {symbol}")
            return None
        
        # Parse into structured format
        chain = []
        total_ce_oi = total_pe_oi = 0
        total_ce_vol = total_pe_vol = 0
        total_ce_oi_chg = total_pe_oi_chg = 0
        max_ce_oi = max_pe_oi = 0
        max_ce_oi_strike = max_pe_oi_strike = 0
        max_ce_oi_chg = max_pe_oi_chg = 0
        max_ce_oi_chg_strike = max_pe_oi_chg_strike = 0
        
        underlying_price = 0
        current_expiry = None
        
        # DhanHQ returns data as list of option entries
        # Each entry has: security_id, expiry, strike_price, option_type, oi, volume, ltp, etc.
        
        # Group by strike price
        strikes_data = {}
        
        for item in raw_data:
            strike = item.get("strikePrice", item.get("strike_price", 0))
            opt_type = item.get("optionType", item.get("option_type", ""))
            expiry = item.get("expiryDate", item.get("expiry", ""))
            
            if not current_expiry:
                current_expiry = expiry
            
            # Get underlying from the response
            spot = item.get("underlyingValue", item.get("underlying_value", 0))
            if spot > 0:
                underlying_price = spot
            
            if strike not in strikes_data:
                strikes_data[strike] = {"strike": strike, "expiry": expiry}
            
            # Option data
            oi = item.get("oi", item.get("openInterest", 0)) or 0
            oi_chg = item.get("oiChange", item.get("changeinOpenInterest", 0)) or 0
            volume = item.get("volume", item.get("totalTradedVolume", 0)) or 0
            ltp = item.get("ltp", item.get("lastPrice", 0)) or 0
            iv = item.get("iv", item.get("impliedVolatility", 0)) or 0
            bid = item.get("bestBid", item.get("bidprice", 0)) or 0
            ask = item.get("bestAsk", item.get("askPrice", 0)) or 0
            bid_qty = item.get("bestBidQty", item.get("bidQty", 0)) or 0
            ask_qty = item.get("bestAskQty", item.get("askQty", 0)) or 0
            sec_id = item.get("securityId", item.get("security_id", ""))
            
            # Greeks
            greeks = item.get("greeks", {})
            delta = greeks.get("delta", 0) or 0
            gamma = greeks.get("gamma", 0) or 0
            theta = greeks.get("theta", 0) or 0
            vega = greeks.get("vega", 0) or 0
            
            prefix = "ce" if opt_type.upper() in ["CALL", "CE"] else "pe"
            
            strikes_data[strike][f"{prefix}_oi"] = oi
            strikes_data[strike][f"{prefix}_oi_chg"] = oi_chg
            strikes_data[strike][f"{prefix}_vol"] = volume
            strikes_data[strike][f"{prefix}_ltp"] = ltp
            strikes_data[strike][f"{prefix}_iv"] = iv
            strikes_data[strike][f"{prefix}_bid"] = bid
            strikes_data[strike][f"{prefix}_ask"] = ask
            strikes_data[strike][f"{prefix}_bid_qty"] = bid_qty
            strikes_data[strike][f"{prefix}_ask_qty"] = ask_qty
            strikes_data[strike][f"{prefix}_delta"] = delta
            strikes_data[strike][f"{prefix}_gamma"] = gamma
            strikes_data[strike][f"{prefix}_theta"] = theta
            strikes_data[strike][f"{prefix}_vega"] = vega
            strikes_data[strike][f"{prefix}_sec_id"] = sec_id
            
            # Aggregate
            if prefix == "ce":
                total_ce_oi += oi
                total_ce_vol += volume
                total_ce_oi_chg += oi_chg
                if oi > max_ce_oi:
                    max_ce_oi = oi
                    max_ce_oi_strike = strike
                if oi_chg > max_ce_oi_chg:
                    max_ce_oi_chg = oi_chg
                    max_ce_oi_chg_strike = strike
            else:
                total_pe_oi += oi
                total_pe_vol += volume
                total_pe_oi_chg += oi_chg
                if oi > max_pe_oi:
                    max_pe_oi = oi
                    max_pe_oi_strike = strike
                if oi_chg > max_pe_oi_chg:
                    max_pe_oi_chg = oi_chg
                    max_pe_oi_chg_strike = strike
        
        # Build chain list
        for strike, data in sorted(strikes_data.items()):
            # Fill missing values with 0
            for prefix in ["ce", "pe"]:
                for field in ["oi", "oi_chg", "vol", "ltp", "iv", "bid", "ask",
                             "bid_qty", "ask_qty", "delta", "gamma", "theta", "vega", "sec_id"]:
                    key = f"{prefix}_{field}"
                    if key not in data:
                        data[key] = 0 if field != "sec_id" else ""
            chain.append(data)
        
        df = pd.DataFrame(chain)
        
        # ATM Strike
        atm = int(round(underlying_price / step) * step) if underlying_price > 0 else 0
        
        # PCR
        pcr_oi = round(total_pe_oi / total_ce_oi, 3) if total_ce_oi > 0 else 0
        pcr_vol = round(total_pe_vol / total_ce_vol, 3) if total_ce_vol > 0 else 0
        
        # Near ATM data
        near_strikes = [atm + (i * step) for i in range(-5, 6)]
        near_df = df[df['strike'].isin(near_strikes)] if len(df) > 0 else pd.DataFrame()
        
        near_ce_oi = near_df['ce_oi'].sum() if len(near_df) > 0 else 0
        near_pe_oi = near_df['pe_oi'].sum() if len(near_df) > 0 else 0
        near_ce_chg = near_df['ce_oi_chg'].sum() if len(near_df) > 0 else 0
        near_pe_chg = near_df['pe_oi_chg'].sum() if len(near_df) > 0 else 0
        near_pcr = round(near_pe_oi / near_ce_oi, 3) if near_ce_oi > 0 else 0
        
        # ATM IV
        atm_row = df[df['strike'] == atm] if len(df) > 0 else pd.DataFrame()
        atm_ce_iv = atm_row.iloc[0]['ce_iv'] if len(atm_row) > 0 else 15
        atm_pe_iv = atm_row.iloc[0]['pe_iv'] if len(atm_row) > 0 else 15
        atm_iv = (atm_ce_iv + atm_pe_iv) / 2
        iv_skew = atm_ce_iv - atm_pe_iv
        
        # Max Pain
        max_pain = self._calculate_max_pain(df) if len(df) > 0 else atm
        
        # Top OI Strikes
        top_ce_oi = df.nlargest(3, 'ce_oi')[['strike', 'ce_oi', 'ce_oi_chg']].to_dict('records') if len(df) > 0 else []
        top_pe_oi = df.nlargest(3, 'pe_oi')[['strike', 'pe_oi', 'pe_oi_chg']].to_dict('records') if len(df) > 0 else []
        
        # OI History tracking
        self._track_oi_history(symbol, total_ce_oi, total_pe_oi, pcr_oi,
                              max_ce_oi_strike, max_pe_oi_strike)
        
        result = {
            "symbol": symbol,
            "underlying": underlying_price,
            "atm": atm,
            "step": step,
            "lot_size": lot_size,
            "expiry": current_expiry,
            "chain_df": df,
            "chain": chain,
            
            # OI Summary
            "total_ce_oi": total_ce_oi,
            "total_pe_oi": total_pe_oi,
            "pcr_oi": pcr_oi,
            "pcr_vol": pcr_vol,
            "near_pcr": near_pcr,
            
            # Support / Resistance
            "resistance": max_ce_oi_strike,
            "support": max_pe_oi_strike,
            "max_ce_oi": max_ce_oi,
            "max_pe_oi": max_pe_oi,
            
            # OI Change
            "total_ce_oi_change": total_ce_oi_chg,
            "total_pe_oi_change": total_pe_oi_chg,
            "near_ce_chg": near_ce_chg,
            "near_pe_chg": near_pe_chg,
            "max_ce_chg_strike": max_ce_oi_chg_strike,
            "max_pe_chg_strike": max_pe_oi_chg_strike,
            
            # IV
            "atm_iv": atm_iv,
            "atm_ce_iv": atm_ce_iv,
            "atm_pe_iv": atm_pe_iv,
            "iv_skew": iv_skew,
            
            # Max Pain
            "max_pain": max_pain,
            "max_pain_deviation": round((max_pain - underlying_price) / underlying_price * 100, 2) if underlying_price > 0 else 0,
            
            # Near ATM
            "near_df": near_df,
            "near_ce_oi": near_ce_oi,
            "near_pe_oi": near_pe_oi,
            
            # Top Strikes
            "top_ce_oi": top_ce_oi,
            "top_pe_oi": top_pe_oi,
            
            # OI History
            "oi_history": self.oi_history.get(symbol, []),
            
            "timestamp": datetime.now().isoformat(),
        }
        
        logger.info(
            f"📊 {symbol} | Spot: ₹{underlying_price:,.2f} | ATM: {atm} | "
            f"PCR: {pcr_oi} | Support: {max_pe_oi_strike} | Resistance: {max_ce_oi_strike}"
        )
        
        return result
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MAX PAIN CALCULATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def _calculate_max_pain(self, df) -> int:
        """
        Max Pain = Strike jaha option writers ka loss minimum hoga
        Market expiry ke time iske paas close hoti hai
        """
        pain_values = {}
        
        for target in df['strike'].unique():
            total_pain = 0
            for _, row in df.iterrows():
                # CE writers loss
                if target > row['strike']:
                    total_pain += (target - row['strike']) * row['ce_oi']
                # PE writers loss
                if target < row['strike']:
                    total_pain += (row['strike'] - target) * row['pe_oi']
            pain_values[target] = total_pain
        
        if pain_values:
            return int(min(pain_values, key=pain_values.get))
        return 0
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # OI HISTORY TRACKING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def _track_oi_history(self, symbol, ce_oi, pe_oi, pcr,
                          resistance, support):
        """OI changes track kare over time"""
        if symbol not in self.oi_history:
            self.oi_history[symbol] = []
        
        self.oi_history[symbol].append({
            "time": datetime.now().isoformat(),
            "total_ce_oi": ce_oi,
            "total_pe_oi": pe_oi,
            "pcr": pcr,
            "max_ce_oi_strike": resistance,
            "max_pe_oi_strike": support,
        })
        
        # Keep last 100 snapshots
        if len(self.oi_history[symbol]) > 100:
            self.oi_history[symbol] = self.oi_history[symbol][-100:]
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PRETTY PRINT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    def print_summary(self, data: Dict):
        """Beautiful option chain summary"""
        if not data:
            print("❌ No data!")
            return
        
        print(f"\n{'═'*65}")
        print(f"  🇮🇳 OPTION CHAIN — {data['symbol']} via DhanHQ")
        print(f"{'═'*65}")
        print(f"  📊 Spot:         ₹{data['underlying']:>12,.2f}")
        print(f"  🎯 ATM:           {data['atm']:>12}")
        print(f"  📅 Expiry:        {data['expiry']:>12}")
        print(f"  ───────────────────────────────────────")
        print(f"  📈 PCR (OI):      {data['pcr_oi']:>12}")
        print(f"  📈 PCR (Vol):     {data['pcr_vol']:>12}")
        print(f"  📈 Near ATM PCR:  {data['near_pcr']:>12}")
        print(f"  💀 Max Pain:      {data['max_pain']:>12} ({data['max_pain_deviation']:+.2f}%)")
        print(f"  ───────────────────────────────────────")
        print(f"  🟢 Support:       {data['support']:>12} (PE OI: {data['max_pe_oi']:,})")
        print(f"  🔴 Resistance:    {data['resistance']:>12} (CE OI: {data['max_ce_oi']:,})")
        print(f"  📏 Range:         {data['support']} — {data['resistance']}")
        print(f"  ───────────────────────────────────────")
        print(f"  📊 ATM IV:        {data['atm_iv']:>11.1f}%")
        print(f"  📊 IV Skew:       {data['iv_skew']:>+11.1f}")
        print(f"  📊 CE OI Change:  {data['total_ce_oi_change']:>+12,}")
        print(f"  📊 PE OI Change:  {data['total_pe_oi_change']:>+12,}")
        print(f"{'═'*65}")
