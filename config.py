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
