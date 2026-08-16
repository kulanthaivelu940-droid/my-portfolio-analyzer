import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="My Portfolio Analyzer", page_icon="📊", layout="wide")

st.markdown("""
<style>
.block-container {padding:1rem; max-width:1200px;}
@media(max-width:700px){.block-container{padding:.7rem} h1{font-size:1.6rem!important}}
</style>
""", unsafe_allow_html=True)

st.title("📊 My Portfolio Analyzer")
st.caption("V4 • Android-friendly • Editable wealth goal planner")

demo = pd.DataFrame([
    ["Stock","Example Stock","EXAMPLE",10,1000,1080,2.1],
    ["Stock","Example Midcap","MIDCAP",20,500,475,-3.4],
    ["Mutual Fund","Parag Parikh Flexi Cap Fund","PPFCF",100,80,86,-1.2],
    ["Mutual Fund","HDFC Mid Cap Fund","HDFCMID",120,150,158,-0.8],
], columns=["type","name","symbol","units","avg_price","current_price","daily_pct"])

with st.sidebar:
    st.header("⚙️ Portfolio")
    uploaded = st.file_uploader("Upload portfolio CSV", type=["csv"])
    threshold = st.slider("Price alert threshold (%)", 1.0, 10.0, 3.0, 0.5)
    st.caption("Groww integration will be added through secure secrets.")

portfolio = pd.read_csv(uploaded) if uploaded else demo.copy()
required = {"type","name","symbol","units","avg_price","current_price"}
if not required.issubset(portfolio.columns):
    st.error("CSV must contain: " + ", ".join(sorted(required)))
    st.stop()

for c in ["units","avg_price","current_price"]:
    portfolio[c] = pd.to_numeric(portfolio[c], errors="coerce")
portfolio["invested"] = portfolio.units * portfolio.avg_price
portfolio["value"] = portfolio.units * portfolio.current_price
portfolio["pnl"] = portfolio.value - portfolio.invested
portfolio["pnl_pct"] = portfolio.pnl / portfolio.invested * 100
portfolio["daily_pct"] = pd.to_numeric(portfolio.get("daily_pct",0), errors="coerce").fillna(0)

invested, value = portfolio.invested.sum(), portfolio.value.sum()
pnl = portfolio.pnl.sum()
pnl_pct = pnl/invested*100 if invested else 0

a,b = st.columns(2)
a.metric("Portfolio value", f"₹{value:,.0f}")
b.metric("Total P&L", f"₹{pnl:,.0f} ({pnl_pct:.2f}%)")

tabs = st.tabs(["📌 Portfolio","🔔 Alerts","📰 News AI","🔍 Fundamentals","🎯 Goal Planner"])

with tabs[0]:
    st.subheader("Holdings")
    v = portfolio[["type","name","symbol","units","avg_price","current_price","pnl","pnl_pct"]].rename(
        columns={"type":"Type","name":"Name","symbol":"Symbol","units":"Units","avg_price":"Avg","current_price":"LTP","pnl":"P&L","pnl_pct":"P&L %"})
    st.dataframe(v.style.format({"Avg":"₹{:,.2f}","LTP":"₹{:,.2f}","P&L":"₹{:,.0f}","P&L %":"{:.2f}%"}), use_container_width=True, hide_index=True)
    st.subheader("Allocation")
    st.bar_chart(portfolio.groupby("type").value.sum())

with tabs[1]:
    st.subheader("🔔 Movement Alerts")
    alerts = portfolio[portfolio.daily_pct.abs() >= threshold]
    if alerts.empty:
        st.success("No current demo holdings cross your alert threshold.")
    else:
        for _, r in alerts.iterrows():
            st.warning(f"{'🟢' if r.daily_pct > 0 else '🔴'} **{r['name']}** moved **{r.daily_pct:+.2f}%** today.")
    st.caption("Automatic intraday monitoring will be connected to the live data engine.")

with tabs[2]:
    st.subheader("📰 Why did it move?")
    st.markdown("- Company-specific news\n- Earnings / guidance\n- Order / acquisition / corporate action\n- Sector-wide movement\n- Market / macro movement\n- Technical / volume movement\n- No reliable reason found")
    st.info("Live news search and source-linked analysis will be connected after the data/notification backend.")

with tabs[3]:
    st.subheader("🔍 Your Fundamental Rules")
    rules = pd.DataFrame([
        ["Revenue CAGR","Double-digit preferred"],
        ["Profit CAGR","Double-digit preferred"],
        ["EPS CAGR","Double-digit — REQUIRED"],
        ["Debt / Equity","< 1 — REQUIRED for non-financials"],
        ["ROE / ROCE","Strong and consistent"],
        ["Free Cash Flow","Positive / healthy conversion"],
        ["Promoter pledge","Prefer 0%"],
        ["P/E / PEG","Compare with industry + own history"],
    ], columns=["Metric","Rule"])
    st.dataframe(rules, use_container_width=True, hide_index=True)

with tabs[4]:
    st.subheader("🎯 Editable 10-Year Wealth Goal")
    st.write("Change the settings anytime. The projection updates immediately.")

    c1,c2 = st.columns(2)
    with c1:
        target = st.number_input("Target corpus (₹)", 100000.0, 1000000000.0, 10000000.0, 100000.0, format="%.0f")
        years = st.number_input("Investment period (years)", 1, 40, 10, 1)
        current_sip = st.number_input("Current monthly SIP (₹)", 0.0, 10000000.0, 20000.0, 1000.0, format="%.0f")
        step_up = st.number_input("Annual SIP step-up (%)", 0.0, 100.0, 15.0, 1.0)
    with c2:
        expected_return = st.number_input("Expected annual return (%)", 0.0, 30.0, 12.0, 0.5)
        annual_bonus = st.number_input("Annual bonus investment (₹)", 0.0, 10000000.0, 100000.0, 10000.0, format="%.0f")
        annual_refund = st.number_input("Annual tax-refund investment (₹)", 0.0, 10000000.0, 50000.0, 5000.0, format="%.0f")
        current_corpus = st.number_input("Current corpus (₹)", 0.0, 1000000000.0, float(value), 10000.0, format="%.0f")

    monthly_rate = expected_return / 100 / 12
    corpus, sip = current_corpus, current_sip
    rows = []
    for year in range(1, int(years)+1):
        for _ in range(12):
            corpus = corpus * (1 + monthly_rate) + sip
        corpus += annual_bonus + annual_refund
        rows.append([year, sip, corpus])
        sip *= 1 + step_up/100
    projection = corpus

    lo, hi = 0.0, max(current_sip*5, target/max(int(years)*12,1)*2, 100000.0)
    for _ in range(70):
        mid = (lo+hi)/2
        c, s = current_corpus, mid
        for y in range(1, int(years)+1):
            for _ in range(12):
                c = c*(1+monthly_rate)+s
            c += annual_bonus+annual_refund
            s *= 1+step_up/100
        if c >= target: hi = mid
        else: lo = mid
    required_sip = hi

    progress = min(max(current_corpus/target,0),1)
    st.progress(progress)
    m1,m2,m3 = st.columns(3)
    m1.metric("Current corpus", f"₹{current_corpus:,.0f}")
    m2.metric("Projected corpus", f"₹{projection:,.0f}")
    m3.metric("Required starting SIP", f"₹{required_sip:,.0f}")

    gap = projection-target
    if gap >= 0: st.success(f"🟢 ON TRACK — projected surplus: ₹{gap:,.0f}")
    else: st.error(f"🔴 OFF TRACK — projected shortfall: ₹{abs(gap):,.0f}")

    st.subheader("Year-by-year projection")
    pdf = pd.DataFrame(rows, columns=["Year","Monthly SIP at start","Projected corpus"])
    st.dataframe(pdf.style.format({"Monthly SIP at start":"₹{:,.0f}","Projected corpus":"₹{:,.0f}"}), use_container_width=True, hide_index=True)

    st.subheader("Return sensitivity")
    sens=[]
    for rate in [10,12,14]:
        c,s=current_corpus,current_sip
        r=rate/100/12
        for y in range(1,int(years)+1):
            for _ in range(12): c=c*(1+r)+s
            c += annual_bonus+annual_refund
            s *= 1+step_up/100
        sens.append([f"{rate}%",c,"ON TRACK" if c>=target else "OFF TRACK"])
    st.dataframe(pd.DataFrame(sens,columns=["Return","Projected corpus","Status"]).style.format({"Projected corpus":"₹{:,.0f}"}), use_container_width=True, hide_index=True)
    st.info("Projection is an estimate, not a guaranteed return. Actual returns fluctuate; taxes and fees are not modelled.")

st.divider()
st.caption(f"V4 • Refreshed {datetime.now().strftime('%d %b %Y, %I:%M %p')} • No orders are placed by this app.")
