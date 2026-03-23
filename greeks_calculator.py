"""
╔══════════════════════════════════════════════╗
║  FILE 5: greeks_calculator.py                ║
║  Black-Scholes Option Greeks Calculator      ║
╚══════════════════════════════════════════════╝

Calculate:
- Delta, Gamma, Theta, Vega, Rho
- Theoretical option price
- Implied Volatility (Newton-Raphson)
- Probability of Profit (OTM at expiry)
- Expected Move
"""

import numpy as np
from scipy.stats import norm
from datetime import datetime


class GreeksCalculator:
    """
    Black-Scholes Greeks Calculator for Indian Markets
    
    IMPORTANT for understanding:
    - DELTA: ₹1 move in underlying → option me kitna change
    - GAMMA: Delta kitna fast badlega
    - THETA: Har din kitna value kam hoga (SELLER ka fayda!)
    - VEGA: IV 1% change → premium me kitna change
    """
    
    RISK_FREE_RATE = 0.065    # India 10-year bond yield ~6.5%
    TRADING_DAYS = 252
    
    @staticmethod
    def _d1(S, K, T, r, sigma):
        return (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    
    @staticmethod
    def _d2(S, K, T, r, sigma):
        return GreeksCalculator._d1(S, K, T, r, sigma) - sigma * np.sqrt(T)
    
    @classmethod
    def option_price(cls, S, K, T, sigma, opt_type="CE", r=None):
        """Theoretical option price (Black-Scholes)"""
        r = r or cls.RISK_FREE_RATE
        if T <= 0:
            T = 0.0001
        d1 = cls._d1(S, K, T, r, sigma)
        d2 = cls._d2(S, K, T, r, sigma)
        
        if opt_type.upper() in ["CE", "CALL"]:
            return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:
            return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    @classmethod
    def greeks(cls, S, K, T, sigma, opt_type="CE", r=None):
        """
        Calculate all Greeks
        
        Returns: dict with delta, gamma, theta, vega
        """
        r = r or cls.RISK_FREE_RATE
        if T <= 0:
            T = 0.0001
        
        d1 = cls._d1(S, K, T, r, sigma)
        d2 = cls._d2(S, K, T, r, sigma)
        sqrt_T = np.sqrt(T)
        
        gamma = norm.pdf(d1) / (S * sigma * sqrt_T)
        vega = S * norm.pdf(d1) * sqrt_T / 100
        
        if opt_type.upper() in ["CE", "CALL"]:
            delta = norm.cdf(d1)
            theta = (-(S * norm.pdf(d1) * sigma) / (2 * sqrt_T)
                    - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
        else:
            delta = norm.cdf(d1) - 1
            theta = (-(S * norm.pdf(d1) * sigma) / (2 * sqrt_T)
                    + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
        
        return {
            "delta": round(delta, 4),
            "gamma": round(gamma, 6),
            "theta": round(theta, 2),
            "vega": round(vega, 2),
        }
    
    @classmethod
    def implied_volatility(cls, market_price, S, K, T, opt_type="CE", r=None):
        """Calculate IV from market price using Newton-Raphson"""
        r = r or cls.RISK_FREE_RATE
        if T <= 0:
            T = 0.0001
        
        sigma = 0.20
        for _ in range(100):
            price = cls.option_price(S, K, T, sigma, opt_type, r)
            diff = price - market_price
            if abs(diff) < 0.01:
                return round(sigma, 4)
            
            d1 = cls._d1(S, K, T, r, sigma)
            v = S * norm.pdf(d1) * np.sqrt(T)
            if v < 0.0001:
                break
            sigma -= diff / v
            sigma = max(sigma, 0.001)
        
        return round(sigma, 4)
    
    @classmethod
    def prob_otm(cls, S, K, T, sigma, opt_type="CE", r=None):
        """
        Probability that option expires OTM (worthless)
        = Option SELLER ka win probability
        """
        r = r or cls.RISK_FREE_RATE
        if T <= 0:
            T = 0.0001
        d2 = cls._d2(S, K, T, r, sigma)
        
        if opt_type.upper() in ["CE", "CALL"]:
            return round(norm.cdf(-d2) * 100, 2)
        else:
            return round(norm.cdf(d2) * 100, 2)
    
    @classmethod
    def expected_move(cls, S, T, sigma):
        """IV based expected price move"""
        return round(S * sigma * np.sqrt(T), 2)
    
    @staticmethod
    def days_to_expiry(expiry_str, fmt="%Y-%m-%d"):
        """Expiry date se trading days calculate"""
        try:
            expiry = datetime.strptime(expiry_str, fmt)
            days = max((expiry - datetime.now()).days, 0)
            return days, max(days / 365, 0.0001)  # (days, years)
        except:
            return 7, 7 / 365
