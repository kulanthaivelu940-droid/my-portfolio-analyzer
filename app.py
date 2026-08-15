import os
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="My Portfolio Analyzer", page_icon="📊", layout="wide")

st.title("📊 My Portfolio Analyzer — V2")
st.caption("Groww portfolio monitoring • price alerts • news/fundamental analysis framework")

# ---------- Groww API ----------
GROWW_BASE = "https://api.groww.in/v1"

def groww_headers(token):
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "X-API-VERSION": "1.0",
    }

def get_groww_holdings(token):
    r = requests.get(
        f"{GROWW_BASE}/holdings/user",
        headers=groww_headers(token),
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("payload", {}).get("holdings", [])

def get_ltp(token, symbols):
    if not symbols:
        return {}
    exchange_symbols = ",".join(f"NSE_{s}" for s in symbols)
    r = requests.get(
        f"{GROWW_BASE}/live-data/ltp",
        headers=groww_headers(token),
        params={"segment": "CASH", "exchange_symbols": exchange_symbols},
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("payload", {})

# ---------- Sidebar ----------
st.sidebar.header("Connection")
token = st.sidebar.text_input(
    "Groww API access token",
    type="password",
    help="For testing only. Prefer Streamlit secrets/environment variables in a deployed version."
)

st.sidebar.caption("Groww access tokens expire daily at 6:00 AM according to current Groww API documentation.")

uploaded = st.sidebar.file_uploader(
    "Or upload portfolio CSV",
    type=["csv"],
)

# ---------- Load portfolio ----------
portfolio = None
source = "CSV/demo"

if token:
    try:
        holdings = get_groww_holdings(token)
        if holdings:
            rows = []
            for h in holdings:
                rows.append({
                    "type": "Stock",
                    "name": h.get("trading_symbol", ""),
                    "symbol": h.get("trading_symbol", ""),
                    "units": float(h.get("quantity", 0)),
                    "avg_price": float(h.get("average_price", 0)),
                    "current_price": None,
                })
            portfolio = pd.DataFrame(rows)
            source = "Groww API"
            symbols = portfolio["symbol"].dropna().astype(str).tolist()
            prices = get_ltp(token, symbols)
            portfolio["current_price"] = portfolio["symbol"].map(
                lambda s: prices.get(f"NSE_{s}")
            )
    except Exception as e:
        st.sidebar.error(f"Groww connection failed: {e}")

if portfolio is None and uploaded:
    portfolio = pd.read_csv(uploaded)
    source = "CSV"

if portfolio is None:
    portfolio = pd.DataFrame([
        ["Stock","Example Stock","EXAMPLE",10,1000,1080],
        ["Stock","Example Midcap","MIDCAP",20,500,475],
        ["Mutual Fund","Parag Parikh Flexi Cap Fund","PPFCF",100,80,86],
        ["Mutual Fund","HDFC Mid Cap Fund","HDFCMID",120,150,158],
    ], columns=["type","name","symbol","units","avg_price","current_price"])
    st.info("Showing demo data. Connect Groww or upload your CSV.")

required = {"type","name","symbol","units","avg_price","current_price"}
missing = required - set(portfolio.columns)
if missing:
    st.error("Missing columns: " + ", ".join(sorted(missing)))
    st.stop()

# Keep unavailable live prices from breaking the dashboard
portfolio["current_price"] = pd.to_numeric(portfolio["current_price"], errors="coerce")
portfolio["avg_price"] = pd.to_numeric(portfolio["avg_price"], errors="coerce")
portfolio["units"] = pd.to_numeric(portfolio["units"], errors="coerce")
portfolio["invested"] = portfolio["units"] * portfolio["avg_price"]
portfolio["value"] = portfolio["units"] * portfolio["current_price"]
portfolio["pnl"] = portfolio["value"] - portfolio["invested"]
portfolio["pnl_pct"] = portfolio["pnl"] / portfolio["invested"] * 100

invested = portfolio["invested"].sum()
value = portfolio["value"].sum()
pnl = portfolio["pnl"].sum()
pnl_pct = pnl / invested * 100 if invested else 0

# ---------- Dashboard ----------
st.caption(f"Data source: {source} • {datetime.now().strftime('%d %b %Y, %I:%M %p')}")

a,b,c,d = st.columns(4)
a.metric("Invested", f"₹{invested:,.0f}")
b.metric("Current value", f"₹{value:,.0f}")
c.metric("P&L", f"₹{pnl:,.0f}")
d.metric("P&L %", f"{pnl_pct:.2f}%")

st.divider()

st.subheader("📌 Holdings")
view = portfolio[["type","name","symbol","units","avg_price","current_price","invested","value","pnl","pnl_pct"]].copy()
view.columns = ["Type","Name","Symbol","Units","Avg price","Current price","Invested","Value","P&L","P&L %"]
st.dataframe(view.style.format({
    "Avg price":"₹{:,.2f}", "Current price":"₹{:,.2f}",
    "Invested":"₹{:,.0f}", "Value":"₹{:,.0f}", "P&L":"₹{:,.0f}", "P&L %":"{:.2f}%"
}), use_container_width=True, hide_index=True)

st.subheader("🥧 Allocation")
st.bar_chart(portfolio.groupby("type")["value"].sum())

# ---------- Alert engine ----------
st.subheader("🔔 Movement Alert Engine")
threshold = st.slider("Alert threshold (%)", 1.0, 10.0, 3.0, 0.5)
st.write("Live monitoring logic:")
st.code("""IF absolute(price_change) >= threshold:
    create_alert()
    fetch_recent_news()
    classify_reason()
    estimate_fundamental_impact()
    show HOLD / WATCH / REVIEW
""", language="text")

st.warning(
    "A real-time scheduler/notification worker is needed for automatic intraday alerts. "
    "This Streamlit prototype runs the checks when the app is opened/refreshed."
)

# ---------- News analysis ----------
st.subheader("📰 Why did it move?")
st.write("""
V2's analysis pipeline is designed to classify each significant move as:
- Company-specific news
- Earnings/results
- Corporate action
- Sector-wide movement
- Market-wide movement
- Macro/event-driven
- Technical/volume-driven
- No reliable reason found

The final production version will attach source links and a confidence level.
""")

# ---------- Fundamental rules ----------
st.subheader("🔍 Your Fundamental Engine")
rules = pd.DataFrame([
    ["Revenue CAGR", "Double-digit preferred", "Pending data provider"],
    ["Profit CAGR", "Double-digit preferred", "Pending data provider"],
    ["EPS CAGR", "Double-digit — REQUIRED", "Pending data provider"],
    ["Debt / Equity", "< 1 — REQUIRED for non-financials", "Pending data provider"],
    ["ROE", "Strong and consistent", "Pending data provider"],
    ["ROCE", "Strong and consistent", "Pending data provider"],
    ["Free Cash Flow", "Positive / healthy conversion", "Pending data provider"],
    ["Promoter holding/pledge", "Prefer strong holding / 0% pledge", "Pending data provider"],
    ["P/E", "Compare industry + own history", "Pending data provider"],
    ["PEG", "Growth should justify valuation", "Pending data provider"],
], columns=["Metric","Your rule","Status"])
st.dataframe(rules, use_container_width=True, hide_index=True)

# ---------- Goal ----------
st.subheader("🎯 ₹1 Crore / 10-Year Goal")
goal = 10_000_000
progress = min(max(value, 0) / goal, 1.0)
st.progress(progress)
st.write(f"Current portfolio: ₹{value:,.0f} / ₹1,00,00,000 — {progress*100:.2f}%")

st.caption(
    "This app is decision-support software. It does not guarantee returns and does not place orders."
)
