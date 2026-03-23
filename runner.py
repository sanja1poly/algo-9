import threading
import logging
from app.logging_setup import setup_logging
from app.dhan.rest import DhanRest
from app.data.option_chain import OptionChainPoller

log = logging.getLogger("runner")

def main():
    setup_logging()
    dhan = DhanRest()

    poller = OptionChainPoller(dhan)

    t = threading.Thread(target=poller.run_forever, daemon=True)
    t.start()

    log.info("Services started (option chain poller).")
    # TODO: start WS + strategy loop + paper broker loop
    t.join()

if __name__ == "__main__":
    main()
