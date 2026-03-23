import time
import logging
from app.dhan.rest import DhanRest
from app.config import settings

log = logging.getLogger("data.option_chain")

class OptionChainPoller:
    def __init__(self, dhan: DhanRest):
        self.dhan = dhan
        self.last = None

    def fetch_chain(self, underlying_security_id: str, exchange_segment: str, expiry: str | None = None) -> dict:
        # Payload will follow Dhan's optionchain docs; adjust keys as per actual doc examples. <!--citation:1-->
        payload = {
            "UnderlyingSecurityId": underlying_security_id,
            "ExchangeSegment": exchange_segment,
            # expiry selection approach:
            # - either pass expiryCode / expiryDate depending on Dhan spec
            # - or call expirylist first and pick nearest
        }
        data = self.dhan.option_chain(payload)
        self.last = data
        return data

    def run_forever(self):
        while True:
            t0 = time.time()
            try:
                chain = self.fetch_chain(settings.underlying_security_id, settings.underlying_exchange_segment)
                log.info("Option chain updated")
                # TODO: push to cache/event bus
            except Exception as e:
                log.exception("Option chain poll error: %s", e)

            # must respect 3 sec unique request limit. <!--citation:1-->
            dt = time.time() - t0
            sleep_s = max(0.0, settings.optionchain_poll_seconds - dt)
            time.sleep(sleep_s)
