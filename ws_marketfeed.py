import asyncio
import websockets
import logging
from app.config import settings

log = logging.getLogger("dhan.ws")

class DhanMarketFeedWS:
    def __init__(self):
        self.url = (
            f"wss://api-feed.dhan.co?"
            f"version=2&token={settings.dhan_access_token}"
            f"&clientId={settings.dhan_client_id}&authType=2"
        )

    async def connect_and_run(self):
        async with websockets.connect(self.url, ping_interval=20) as ws:
            log.info("WS connected")
            await self.subscribe_underlying(ws)
            await self.read_loop(ws)

    async def subscribe_underlying(self, ws):
        # Note: Dhan expects JSON subscribe messages; response is binary. <!--citation:2-->
        msg = {
            "RequestCode": 15,
            "InstrumentCount": 1,
            "InstrumentList": [{
                "ExchangeSegment": settings.underlying_exchange_segment,
                "SecurityId": settings.underlying_security_id
            }]
        }
        await ws.send(__import__("json").dumps(msg))
        log.info("Subscribed underlying %s", settings.underlying_security_id)

    async def read_loop(self, ws):
        while True:
            data = await ws.recv()  # binary frames expected
            # TODO: decode binary packet using DhanHQ-py marketfeed decoder
            log.debug("Got %d bytes", len(data))

def start_ws():
    asyncio.run(DhanMarketFeedWS().connect_and_run())
