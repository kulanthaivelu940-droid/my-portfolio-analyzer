# My Portfolio Analyzer — V2

## What changed from V1

V2 adds a real Groww portfolio adapter and live-price adapter.

Groww's current API documentation supports:
- GET holdings
- GET positions
- Live LTP
- Live quote/OHLC
- Historical market data

The app uses the holdings endpoint and LTP endpoint for the first integration.

## Important security

Do NOT paste your Groww password into this app.

Use a Groww API access token. Groww's current documentation says access tokens expire daily at 6:00 AM. For deployment, use environment variables or Streamlit secrets rather than hard-coding credentials.

This V2 does not place orders.

## Run

pip install -r requirements.txt
streamlit run app.py

## Groww setup

1. Create/enable Groww Trading API access.
2. Generate an access token from Groww.
3. Start the app.
4. Paste the token into the sidebar.
5. The app fetches holdings and current LTPs.

## Current limitation

The app currently performs checks when opened/refreshed. True automatic intraday notifications require a background scheduler/worker plus a notification channel.

## Next V3

- News API/search integration
- Event-to-price-movement correlation
- Fundamental-data provider
- Mutual-fund NAV adapter
- Daily database/history
- Telegram/email/push notifications
- Market-open and market-close automated reports
- Portfolio risk/concentration analysis
- Buy-opportunity scoring based on the user's rules

Never commit API tokens to GitHub.
