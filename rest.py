import requests
from app.config import settings

BASE_URL = "https://api.dhan.co/v2"

class DhanRest:
    def __init__(self, access_token: str | None = None):
        self.access_token = access_token or settings.dhan_access_token

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "access-token": self.access_token,
        }

    def option_chain(self, payload: dict) -> dict:
        # Option Chain endpoint is documented at /v2/optionchain. <!--citation:1-->
        url = f"{BASE_URL}/optionchain"
        r = requests.post(url, headers=self._headers(), json=payload, timeout=20)
        r.raise_for_status()
        return r.json()

    def option_chain_expiry_list(self, payload: dict) -> dict:
        url = f"{BASE_URL}/optionchain/expirylist"
        r = requests.post(url, headers=self._headers(), json=payload, timeout=20)
        r.raise_for_status()
        return r.json()

    def intraday_ohlc(self, payload: dict) -> dict:
        # /charts/intraday is documented. <!--citation:3-->
        url = f"{BASE_URL}/charts/intraday"
        r = requests.post(url, headers=self._headers(), json=payload, timeout=20)
        r.raise_for_status()
        return r.json()
