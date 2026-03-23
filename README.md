# Dhan Options Ensemble (Paper Trading)

Intraday option-chain based ensemble system for NSE options using DhanHQ v2 APIs.
Trades only when estimated win probability >= 0.85 and all risk/liquidity gates pass.

Key DhanHQ endpoints used:
- Option Chain API (REST) - rate limit: 1 unique request / 3 seconds
- Live Market Feed (WebSocket) - up to 5 connections, 5000 instruments/connection
- Historical data (optional) for calibration/backtesting

This repo focuses on:
- Real-time data ingestion (poll chain + ws spot)
- Feature extraction from option chain
- Strategy ensemble scoring
- Paper execution with realistic fills & charges
