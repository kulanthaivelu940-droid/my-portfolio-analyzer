import streamlit as st
import pandas as pd
import numpy as np
import requests, re
import yfinance as yf
from urllib.parse import quote_plus

st.set_page_config(page_title="My Portfolio Analyzer",page_icon="📊",layout="wide")
st.title("📊 My Portfolio Analyzer")
st.caption("Final Core Version • Portfolio + Fundamentals + Funds + Rolling Returns + Quarterly Results + Two-Way Monitoring")

@st.cache_data(ttl=1800)
def stock_bundle(ticker):
    t=yf.Ticker(ticker)
    return t.info,t.history(period="10y",auto_adjust=False),t.quarterly_financials,t.financials,getattr(t,"news",[]) or []

@st.cache_data(ttl=3600)
def mf_catalog():
    r=requests.get("https://api.mfapi.in/mf",timeout=30); r.raise_for_status()
    return pd.DataFrame(r.json())

@st.cache_data(ttl=1800)
def mf_history(code):
    r=requests.get(f"https://api.mfapi.in/mf/{code}",timeout=30); r.raise_for_status()
    d=pd.DataFrame(r.json().get("data",[]))
    if d.empty:return d
    d["date"]=pd.to_datetime(d["date"],dayfirst=True,errors="coerce")
    d["nav"]=pd.to_numeric(d["nav"],errors="coerce")
    return d.dropna(subset=["date","nav"]).sort_values("date")

def num(x):
    try:return float(x)
    except:return np.nan

def financial_company(info):
    text=" ".join(str(info.get(k,"")) for k in ["sector","industry","industryKey"]).lower()
    return any(w in text for w in ["bank","financial","insurance","credit","capital markets","asset management","mortgage","lending","nbfc"])

def fund_search(cat,q):
    terms=q.lower().split()
    mask=pd.Series(True,index=cat.index)
    for term in terms: mask &= cat.schemeName.str.lower().str.contains(re.escape(term),na=False)
    x=cat[mask]
    direct=x[x.schemeName.str.contains("direct",case=False,na=False)]
    growth=direct[direct.schemeName.str.contains("growth",case=False,na=False)]
    return (growth if not growth.empty else direct if not direct.empty else x).head(50)

def rolling(nav,years):
    s=nav.set_index("date")["nav"].sort_index().resample("ME").last().dropna()
    return ((s/s.shift(years*12)-1)*100).dropna().rename("Rolling return").reset_index().rename(columns={"date":"Period ending"})

with st.sidebar:
    st.header("🔎 Research")
    ticker=st.text_input("Stock ticker",placeholder="TATACONSUM.NS")
    fund_query=st.text_input("Mutual fund search",placeholder="Parag Parikh Flexi Cap")
    alert=st.slider("Movement alert (%)",1.0,20.0,5.0,.5)

tabs=st.tabs(["📌 Portfolio","👀 Watchlist","🔍 Fundamental Engine","📑 Quarterly Results","📈 Rolling Returns","📰 Daily Monitor","🎯 Goal"])

with tabs[0]:
    st.subheader("📌 Portfolio")
    up=st.file_uploader("Upload holdings CSV",type=["csv"])
    if up: st.dataframe(pd.read_csv(up),use_container_width=True,hide_index=True)
    else: st.info("Upload your holdings CSV. Groww read-only synchronization remains a separate security-controlled integration.")

with tabs[1]:
    st.subheader("👀 Watchlist")
    if "watch" not in st.session_state: st.session_state.watch=[]
    a,b,c=st.columns(3)
    with a:n=st.text_input("Name",key="wn")
    with b:s=st.text_input("Ticker / code",key="ws")
    with c:k=st.selectbox("Type",["Stock","Mutual Fund"],key="wk")
    if st.button("➕ Add to monitoring") and n and s: st.session_state.watch.append({"Name":n,"Ticker/Code":s.upper(),"Type":k})
    st.dataframe(pd.DataFrame(st.session_state.watch),use_container_width=True,hide_index=True) if st.session_state.watch else st.info("No items yet.")

with tabs[2]:
    st.subheader("🔍 Complete Fundamental Engine")
    if ticker:
        try:
            info,h,q,a,news=stock_bundle(ticker)
            fin=financial_company(info); eg=num(info.get("earningsGrowth")); de=num(info.get("debtToEquity"))
            rows=[
                ["Current EPS/earnings growth",eg*100 if pd.notna(eg) else np.nan,">=10%","PASS" if pd.notna(eg) and eg>=.10 else "FAIL" if pd.notna(eg) else "DATA NEEDED"],
                ["Debt / Equity",de,"<1 for non-financials","N/A — financial" if fin else "PASS" if pd.notna(de) and de<1 else "FAIL" if pd.notna(de) else "DATA NEEDED"],
                ["ROE",num(info.get("returnOnEquity"))*100 if pd.notna(num(info.get("returnOnEquity"))) else np.nan,"Quality","REFERENCE"],
                ["ROCE","Requires validated filing","Quality","DATA NEEDED"],
                ["Free Cash Flow",num(info.get("freeCashflow")),"Positive preferred","REFERENCE"],
                ["FCF conversion","Requires multi-year cash-flow data","Quality","DATA NEEDED"],
                ["Promoter holding / pledge","Requires exchange shareholding data","Quality","DATA NEEDED"],
                ["Competitive advantage / moat","Qualitative research","Quality","REVIEW"],
                ["P/E",num(info.get("trailingPE")),"Compare industry/history","REFERENCE"],
                ["PEG",num(info.get("pegRatio")),"Compare growth","REFERENCE"],
                ["Industry P/E","Requires peer dataset","Valuation","DATA NEEDED"],
                ["Historical P/E","Requires validated history","Valuation","DATA NEEDED"],
                ["5Y/10Y Revenue CAGR","Requires validated annual series","Growth","DATA NEEDED"],
                ["5Y/10Y Profit CAGR","Requires validated annual series","Growth","DATA NEEDED"],
                ["5Y/10Y EPS CAGR","Requires validated annual series","Growth","DATA NEEDED"],
                ["Growth consistency","Requires validated multi-year series","Growth","DATA NEEDED"],
            ]
            st.write(f"**{info.get('longName',ticker)}** • {'Financial' if fin else 'Non-financial'}")
            st.dataframe(pd.DataFrame(rows,columns=["Metric","Value","Category","Status"]),use_container_width=True,hide_index=True)
            mandatory="PASS" if (pd.notna(eg) and eg>=.10 and (fin or (pd.notna(de) and de<1))) else "FAIL" if (pd.notna(eg) and eg<.10) or (not fin and pd.notna(de) and de>=1) else "DATA NEEDED"
            if mandatory=="PASS": st.success("🟢 Mandatory filters PASS. Continue with quality and valuation.")
            elif mandatory=="FAIL": st.error("🔴 Mandatory filter failed under your checklist.")
            else: st.warning("🟡 DATA NEEDED. Do not label this stock BUY until required data is verified.")
            if fin:
                st.info("Financial company: D/E is excluded. Use ROA, ROE, NIM, GNPA/NNPA, capital adequacy, provision coverage, credit growth and cost-to-income.")
        except Exception as e: st.error(f"Fundamental data error: {e}")
    else: st.info("Enter an NSE ticker such as TATACONSUM.NS.")

with tabs[3]:
    st.subheader("📑 Quarterly Results")
    if ticker:
        try:
            info,h,q,a,news=stock_bundle(ticker)
            st.dataframe(q,use_container_width=True) if q is not None and not q.empty else st.warning("Quarterly data was not returned.")
            st.caption("Cross-check important figures against company/NSE filings.")
        except Exception as e: st.error(f"Quarterly data error: {e}")
    else: st.info("Enter a stock ticker.")

with tabs[4]:
    st.subheader("📈 Mutual Fund Rolling Returns")
    if fund_query:
        try:
            cat=mf_catalog(); res=fund_search(cat,fund_query)
            if res.empty: st.warning("No fund found. Try a shorter name.")
            else:
                labels=[f"{r.schemeName} | {r.schemeCode}" for _,r in res.iterrows()]
                choice=st.selectbox("Select fund",labels); code=choice.split("|")[-1].strip()
                period=st.selectbox("Rolling period",[1,3,5,7,10],index=2,format_func=lambda x:f"{x}Y")
                rr=rolling(mf_history(code),period)
                if rr.empty: st.warning("Not enough NAV history.")
                else:
                    yr=rr.assign(Year=rr["Period ending"].dt.year).groupby("Year",as_index=False)["Rolling return"].last()
                    st.dataframe(yr.style.format({"Rolling return":"{:.2f}%"}),use_container_width=True,hide_index=True)
                    st.line_chart(rr.set_index("Period ending")["Rolling return"])
                    x=rr["Rolling return"]; a,b,c,d=st.columns(4)
                    a.metric("Average",f"{x.mean():.2f}%"); b.metric("Median",f"{x.median():.2f}%"); c.metric("Minimum",f"{x.min():.2f}%"); d.metric(">12%",f"{(x>12).mean()*100:.1f}%")
                    st.write(f"**>10% observations:** {(x>10).mean()*100:.1f}%")
                    with st.expander("All monthly observations"): st.dataframe(rr,use_container_width=True,hide_index=True)
        except Exception as e: st.error(f"Rolling-return error: {e}")
    else: st.info("Search by fund name — no scheme code required.")

with tabs[5]:
    st.subheader("📰 Daily Two-Way Monitor")
    if ticker:
        try:
            info,h,q,a,news=stock_bundle(ticker); close=h["Close"].dropna()
            move=(float(close.iloc[-1])/float(close.iloc[-2])-1)*100 if len(close)>=2 else np.nan
            st.metric("Latest close",f"₹{float(close.iloc[-1]):,.2f}",f"{move:+.2f}%")
            if move>=alert: st.success(f"📈 Positive alert: +{move:.2f}% — review valuation.")
            elif move<=-alert:
                st.error(f"📉 Downside alert: {move:.2f}% — investigate before buying.")
                st.markdown("**Potential accumulation test:** fundamentals intact + no structural deterioration + attractive valuation.")
            else: st.info("No threshold event today.")
            if news:
                for n in news[:10]:
                    title=n.get("title","News"); pub=n.get("publisher",""); link=n.get("link","")
                    st.markdown(f"**{title}** — {pub}  "+(f"[Open article]({link})" if link else ""))
            else: st.link_button("Search latest news",f"https://news.google.com/search?q={quote_plus(ticker)}")
            st.info("A price fall alone is never treated as a BUY signal. Causes are labelled confirmed only when supported by evidence.")
        except Exception as e: st.error(f"Monitor error: {e}")
    else: st.info("Enter a stock ticker.")

with tabs[6]:
    st.subheader("🎯 Editable Wealth Planner")
    target=st.number_input("Target corpus (₹)",100000.,1000000000.,10000000.,100000.,format="%.0f")
    years=st.number_input("Investment period",1,40,10)
    sip=st.number_input("Monthly SIP (₹)",0.,10000000.,20000.,1000.,format="%.0f")
    step=st.number_input("Annual SIP step-up (%)",0.,100.,15.)
    ret=st.number_input("Expected return (%)",0.,30.,12.)
    bonus=st.number_input("Annual bonus (₹)",0.,10000000.,100000.,10000.,format="%.0f")
    refund=st.number_input("Annual tax refund (₹)",0.,10000000.,50000.,5000.,format="%.0f")
    current=st.number_input("Current corpus (₹)",0.,1000000000.,0.,10000.,format="%.0f")
    r=ret/100/12; corpus=current; s=sip; rows=[]
    for y in range(1,years+1):
        for _ in range(12): corpus=corpus*(1+r)+s
        corpus+=bonus+refund; rows.append([y,s,corpus]); s*=1+step/100
    st.metric("Projected corpus",f"₹{corpus:,.0f}")
    st.success("🟢 ON TRACK" if corpus>=target else f"🔴 OFF TRACK — shortfall ₹{target-corpus:,.0f}")
    st.dataframe(pd.DataFrame(rows,columns=["Year","Starting SIP","Projected corpus"]),use_container_width=True,hide_index=True)

st.divider(); st.caption("Final Core Version • Research-only • No brokerage credentials, banking data or order placement.")
