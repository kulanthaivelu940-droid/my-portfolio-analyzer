import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="My Portfolio Analyzer V5", page_icon="📊", layout="wide")

st.markdown("""
<style>
.block-container{padding:1rem;max-width:1200px}
@media(max-width:700px){.block-container{padding:.7rem}h1{font-size:1.55rem!important}}
</style>
""", unsafe_allow_html=True)

st.title("📊 My Portfolio Analyzer")
st.caption("V5 • Investment Research & Monitoring")

demo = pd.DataFrame([
    ["Stock","Example Stock","EXAMPLE","Non-financial",10,1000,1080,2.1],
    ["Stock","Example Midcap","MIDCAP","Non-financial",20,500,475,-3.4],
    ["Mutual Fund","Parag Parikh Flexi Cap Fund","PPFCF","Mutual Fund",100,80,86,-1.2],
    ["Mutual Fund","HDFC Mid Cap Fund","HDFCMID","Mutual Fund",120,150,158,-0.8],
], columns=["type","name","symbol","sector_type","units","avg_price","current_price","daily_pct"])

with st.sidebar:
    st.header("⚙️ Settings")
    uploaded = st.file_uploader("Upload portfolio CSV", type=["csv"])
    threshold = st.slider("Daily movement alert (%)", 1.0, 10.0, 3.0, 0.5)
    st.caption("V5 is research-ready. Live market/news data and Groww read-only integration come in the data-connect phase.")

portfolio = pd.read_csv(uploaded) if uploaded else demo.copy()
needed = {"type","name","symbol","units","avg_price","current_price"}
if not needed.issubset(portfolio.columns):
    st.error("CSV must contain: " + ", ".join(sorted(needed)))
    st.stop()

for c in ["units","avg_price","current_price"]:
    portfolio[c] = pd.to_numeric(portfolio[c], errors="coerce").fillna(0)
portfolio["daily_pct"] = pd.to_numeric(portfolio.get("daily_pct",0), errors="coerce").fillna(0)
portfolio["invested"] = portfolio.units * portfolio.avg_price
portfolio["value"] = portfolio.units * portfolio.current_price
portfolio["pnl"] = portfolio.value - portfolio.invested
portfolio["pnl_pct"] = portfolio.pnl.div(portfolio.invested.replace(0,pd.NA))*100

tabs = st.tabs(["📌 Portfolio","👀 Watchlist","🔍 Stock Research","📑 Quarterly Results","📈 Rolling Returns","🔔 Daily Monitor","🎯 Goal"])

with tabs[0]:
    st.subheader("Current portfolio")
    a,b,c=st.columns(3)
    a.metric("Value",f"₹{portfolio.value.sum():,.0f}")
    b.metric("Invested",f"₹{portfolio.invested.sum():,.0f}")
    c.metric("P&L",f"₹{portfolio.pnl.sum():,.0f}")
    view=portfolio[["type","name","symbol","units","avg_price","current_price","pnl","pnl_pct"]].rename(
        columns={"type":"Type","name":"Name","symbol":"Symbol","units":"Units","avg_price":"Avg","current_price":"LTP","pnl":"P&L","pnl_pct":"P&L %"})
    st.dataframe(view.style.format({"Avg":"₹{:,.2f}","LTP":"₹{:,.2f}","P&L":"₹{:,.0f}","P&L %":"{:.2f}%"}),use_container_width=True,hide_index=True)

with tabs[1]:
    st.subheader("👀 Stock & Mutual Fund Watchlist")
    st.write("Anything added here is intended to become part of daily monitoring automatically.")
    if "watchlist" not in st.session_state: st.session_state.watchlist=[]
    a,b,c=st.columns(3)
    with a: name=st.text_input("Name",placeholder="e.g. Tata Consumer")
    with b: symbol=st.text_input("Symbol",placeholder="e.g. TATACONSUM")
    with c: kind=st.selectbox("Type",["Stock","Mutual Fund"])
    if st.button("➕ Add to Watchlist"):
        if name.strip() and symbol.strip():
            st.session_state.watchlist.append({"Name":name.strip(),"Symbol":symbol.strip().upper(),"Type":kind})
            st.success(f"Added {name} to watchlist.")
        else: st.warning("Enter both name and symbol.")
    if st.session_state.watchlist:
        st.dataframe(pd.DataFrame(st.session_state.watchlist),use_container_width=True,hide_index=True)
        st.info("Live price/NAV and news monitoring will activate when the data provider is connected.")
    else: st.info("No watchlist items yet.")

with tabs[2]:
    st.subheader("🔍 Fundamental Research")
    st.write("Mandatory rules before a non-financial stock can become a Buy Candidate:")
    st.markdown("**EPS growth: double-digit — REQUIRED**  |  **D/E < 1 — REQUIRED for non-financials**")
    st.markdown("**Financial companies:** D/E is excluded; use sector-appropriate metrics instead.")
    st.markdown("""
**Growth:** 5Y/10Y revenue CAGR • 5Y/10Y profit CAGR • 5Y/10Y EPS CAGR • current earnings growth

**Quality:** ROE • ROCE • FCF • FCF conversion • promoter holding/pledge • competitive advantage

**Valuation:** P/E • P/E vs industry • P/E vs own history • PEG • expected growth vs valuation
""")
    st.info("Live company fundamentals will be populated from verified sources. No invented figures are shown.")

with tabs[3]:
    st.subheader("📑 Quarterly Results Tracker")
    st.write("Track Revenue, EBITDA, margin, PAT, EPS, YoY/QoQ growth, FCF, debt, ROE/ROCE and management guidance.")
    q = pd.DataFrame({"Quarter":["Q1","Q2","Q3","Q4"],"Revenue":["Pending"]*4,"PAT":["Pending"]*4,"EPS":["Pending"]*4,"YoY":["—"]*4,"QoQ":["—"]*4,"Trend":["🟡 Pending"]*4})
    st.dataframe(q,use_container_width=True,hide_index=True)
    st.info("Verified quarterly data will be connected in the data layer.")

with tabs[4]:
    st.subheader("📈 Rolling Return Analysis")
    st.selectbox("Fund",["Parag Parikh Flexi Cap Fund","HDFC Mid Cap Fund","Add another fund"])
    st.selectbox("Rolling period",[1,3,5,7,10],index=2,format_func=lambda x:f"{x}Y")
    st.write("Recommended: monthly rolling observations + an every-year summary.")
    st.dataframe(pd.DataFrame(columns=["Period ending","Rolling return"]),use_container_width=True,hide_index=True)
    st.markdown("Summary: every available year • monthly observations • average • median • minimum • maximum • % above 10% • **% above 12%** • best/worst period • benchmark comparison")
    st.info("Real rolling returns require verified historical NAV data; no placeholder percentages are presented as real performance.")

with tabs[5]:
    st.subheader("🔔 Daily Portfolio + Watchlist Monitor")
    alerts=portfolio[portfolio.daily_pct.abs()>=threshold]
    if alerts.empty: st.success("No demo holding currently crosses your alert threshold.")
    else:
        for _,r in alerts.iterrows(): st.warning(f"{'🟢' if r.daily_pct>0 else '🔴'} {r['name']} moved {r.daily_pct:+.2f}%")
    st.markdown("**Workflow:** movement detection → verified news → reason classification → fundamentals → valuation → HOLD/WATCH/ACCUMULATE/REVIEW → notification.")

with tabs[6]:
    st.subheader("🎯 Goal Planner")
    target=st.number_input("Target corpus (₹)",100000.,1000000000.,10000000.,100000.,format="%.0f")
    years=st.number_input("Investment period (years)",1,40,10,1)
    sip=st.number_input("Monthly SIP (₹)",0.,10000000.,20000.,1000.,format="%.0f")
    step=st.number_input("Annual SIP step-up (%)",0.,100.,15.,1.)
    ret=st.number_input("Expected return (%)",0.,30.,12.,.5)
    bonus=st.number_input("Annual bonus (₹)",0.,10000000.,100000.,10000.,format="%.0f")
    refund=st.number_input("Annual tax refund (₹)",0.,10000000.,50000.,5000.,format="%.0f")
    current=st.number_input("Current corpus (₹)",0.,1000000000.,float(portfolio.value.sum()),10000.,format="%.0f")
    r=ret/100/12; corpus=current; s=sip; rows=[]
    for y in range(1,int(years)+1):
        for _ in range(12): corpus=corpus*(1+r)+s
        corpus+=bonus+refund; rows.append([y,s,corpus]); s*=1+step/100
    st.metric("Projected corpus",f"₹{corpus:,.0f}")
    st.success("🟢 ON TRACK" if corpus>=target else f"🔴 OFF TRACK — shortfall ₹{target-corpus:,.0f}")
    st.dataframe(pd.DataFrame(rows,columns=["Year","Starting SIP","Projected corpus"]).style.format({"Starting SIP":"₹{:,.0f}","Projected corpus":"₹{:,.0f}"}),use_container_width=True,hide_index=True)

st.divider()
st.caption(f"V5 • {datetime.now().strftime('%d %b %Y, %I:%M %p')} • Research-only: no orders are placed.")
