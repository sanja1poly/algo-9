from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    dhan_client_id: str = os.getenv("DHAN_CLIENT_ID", "")
    dhan_access_token: str = os.getenv("DHAN_ACCESS_TOKEN", "")

    underlying_security_id: str = os.getenv("UNDERLYING_SECURITY_ID", "")
    underlying_exchange_segment: str = os.getenv("UNDERLYING_EXCHANGE_SEGMENT", "NSE_EQ")
    underlying_instrument: str = os.getenv("UNDERLYING_INSTRUMENT", "EQUITY")

    optionchain_poll_seconds: int = int(os.getenv("OPTIONCHAIN_POLL_SECONDS", "3"))

    min_win_prob: float = float(os.getenv("MIN_WIN_PROB", "0.85"))

settings = Settings()
"""
╔══════════════════════════════════════════════╗
║  FILE 1: config.py                           ║
║  Application Configuration & Constants       ║
╚══════════════════════════════════════════════╝
"""

import os
from dotenv import load_dotenv
from enum import Enum
from dataclasses import dataclass

# Load .env file
load_dotenv()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🔐 DHAN HQ CREDENTIALS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "YOUR_CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🇮🇳 INSTRUMENT CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# DhanHQ Security IDs for Indices
SECURITY_IDS = {
    "NIFTY": 13,
    "BANKNIFTY": 25,
    "FINNIFTY": 27,
    "MIDCPNIFTY": 442,
    "SENSEX": 51,
}

# Lot Sizes (as of 2025 - verify current lot sizes)
LOT_SIZES = {
    "NIFTY": 75,
    "BANKNIFTY": 30,
    "FINNIFTY": 40,
    "MIDCPNIFTY": 50,
    "SENSEX": 20,
}

# Strike Step Size
STRIKE_STEPS = {
    "NIFTY": 50,
    "BANKNIFTY": 100,
    "FINNIFTY": 50,
    "MIDCPNIFTY": 25,
    "SENSEX": 100,
}

# DhanHQ Exchange Segments
EXCHANGE_SEGMENTS = {
    "NSE_EQ": "NSE_EQ",
    "NSE_FNO": "NSE_FNO",
    "BSE_EQ": "BSE_EQ",
    "BSE_FNO": "BSE_FNO",
    "IDX_I": "IDX_I",
    "NSE_CURRENCY": "NSE_CURRENCY",
    "MCX_COMM": "MCX_COMM",
}

# Underlying Segment for Option Chain API
UNDERLYING_SEGMENTS = {
    "NIFTY": "IDX_I",
    "BANKNIFTY": "IDX_I",
    "FINNIFTY": "IDX_I",
    "MIDCPNIFTY": "IDX_I",
    "SENSEX": "IDX_I",
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🤖 TRADING CONFIGURATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class TradingConfig:
    """All trading parameters in one place"""
    
    # Symbols to trade
    symbols: list = None
    
    # Capital
    initial_capital: float = 500000.0      # ₹5 Lakh virtual
    
    # Confluence
    min_confluence_score: int = 85          # Only trade >= 85%
    
    # Risk Management
    max_trades_per_day: int = 3
    max_daily_loss: float = 8000.0         # ₹8000 max loss per day
    max_position_size_pct: float = 0.25    # Max 25% capital per trade
    
    # Stop Loss / Target
    sl_multiplier: float = 0.5             # 50% of max loss
    target_multiplier: float = 0.5         # 50% of max profit
    
    # Timing (IST)
    entry_start_hour: int = 9
    entry_start_minute: int = 25
    entry_end_hour: int = 14
    entry_end_minute: int = 30
    exit_hour: int = 15
    exit_minute: int = 15
    
    # Intervals
    check_interval_seconds: int = 180      # 3 minutes
    option_chain_interval: int = 5         # Option chain every 5 seconds
    
    # Brokerage (Dhan charges)
    brokerage_per_order: float = 20.0      # ₹20 flat per executed order
    stt_rate: float = 0.000625             # STT on sell side
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["NIFTY", "BANKNIFTY"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📊 ENUMS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TradeDirection(Enum):
    STRONG_BULLISH = "STRONG_BULLISH"
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"

class ConfidenceLevel(Enum):
    NO_TRADE = "NO_TRADE"          # < 60
    LOW = "LOW"                    # 60-70
    MEDIUM = "MEDIUM"              # 70-80
    HIGH = "HIGH"                  # 80-85
    VERY_HIGH = "VERY_HIGH"        # 85-90   ← MIN FOR TRADE
    EXTREME = "EXTREME"            # 90-100

class StrategyType(Enum):
    IRON_CONDOR = "IRON_CONDOR"
    IRON_CONDOR_BULLISH = "IRON_CONDOR_BULLISH"
    IRON_CONDOR_BEARISH = "IRON_CONDOR_BEARISH"
    BULL_PUT_SPREAD = "BULL_PUT_SPREAD"
    BEAR_CALL_SPREAD = "BEAR_CALL_SPREAD"
    SHORT_STRANGLE = "SHORT_STRANGLE"
    NO_TRADE = "NO_TRADE"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📂 PATHS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
PORTFOLIO_FILE = os.path.join(DATA_DIR, "portfolio.json")

# Create dirs if not exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 📝 LOGGING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import logging

def setup_logger(name="auto_trader"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # File handler
    fh = logging.FileHandler(os.path.join(LOG_DIR, "trades.log"))
    fh.setLevel(logging.INFO)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

logger = setup_logger()
