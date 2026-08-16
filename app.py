import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
from datetime import datetime, timedelta
from urllib.parse import quote_plus

st.set_page_config(page_title="My Portfolio Analyzer V5.2", page_icon="📊", layout="wide")
st.markdown("""<style>.block-container{padding:1rem;max-width:1250px}@media(max-width:700px){.block-container{padding:.7rem}h1{font-size:1.5rem!important}}</style>""",unsafe_allow_html=True)

st.title("📊 My Portfolio Analyzer")
st.caption("V5.2 • Automatic fund search + rolling returns + news research • No trading/orders")

@st.cache_data(ttl=3600,show_spinner=False)
def mf_catalog():
    r=requests.get("https://api.mfapi.in/mf",timeout=25)
    r.raise_for_status()
    return pd.DataFrame(r.json())

@st.cache_data(ttl=1800,show_spinner=False)
def mf_history(code):
    r=requests.get(f"https://api.mfapi.in/mf/{code}",timeout=25)
    r.raise_for_status()
    j=r.json()
    df=pd.DataFrame(j.get("data",[]))
    if df.empty:return df
    df["date"]=pd.to_datetime(df["date"],dayfirst=True,errors="coerce")
    df["nav"]=pd.to_numeric(df["nav"],errors="coerce")
    return df.dropna(subset=["date","nav"]).sort_values("date")

def rolling_returns(nav,years):
    s=nav.set_index("date")["nav"].sort_index()
    m=s.resample("ME").last().dropna()
    rr=(m/m.shift(years*12)-1)*100
    return rr.dropna().rename("Rolling return").reset_index().rename(columns={"date":"Period ending"})

def annual_last(rr):
    return rr.assign(Year=rr["Period ending"].dt.year).groupby("Year",as_index=False)["Rolling return"].last()

def search_funds(catalog,query):
    q=" ".join(query.lower().split())
    if not q:return pd.DataFrame()
    # Prefer direct + growth variants.
    name=catalog["schemeName"].astype(str)
    score=name.str.lower().map(lambda s: sum(w in s for w in q.split()))
    out=catalog.assign(_score=score)
    mask=name.str.lower().str.contains("|".join(map(lambda x:__import__("re").escape(x),q.split())),regex=True,na=False)
    out=out[mask].sort_values("_score",ascending=False)
    direct=out[out.schemeName.str.contains("direct",case=False,na=False)]
    growth=direct[direct.schemeName.str.contains("growth",case=False,na=False)]
    return (growth if not growth.empty else direct if not direct.empty else out).head(30).drop(columns="_score")

@st.cache_data(ttl=900,show_spinner=False)
def stock_bundle(ticker):
    t=yf.Ticker(ticker)
    return t.info,t.history(period="1y",auto_adjust=False),t.quarterly_financials

@st.cache_data(ttl=900,show_spinner=False)
def stock_news(ticker):
    t=yf.Ticker(ticker)
    return getattr(t,"news",[]) or []

def safe(x):
    try:return float(x)
    except:return np.nan

def financial_company(info):
    text=" ".join(str(info.get(k,"")) for k in ["sector","industry","industryKey"]).lower()
    words=["bank","financial","insurance","credit","capital markets","asset management","mortgage","lending","nbfc"]
    return any(w in text for w in words)

with st.sidebar:
    st.header("🔎 Research")
    ticker=st.text_input("Stock ticker",placeholder="TATACONSUM.NS")
    fund_search=st.text_input("Mutual fund name",placeholder="Parag Parikh Flexi Cap")
    alert=st.slider("Price movement alert (%)",1.0,10.0,3.0,.5)
    st.caption("No Groww credentials are requested. V5.2 is research-only.")

tabs=st.tabs(["📌 Portfolio","👀 Watchlist","🔍 Fundamental Check","📑 Quarterly Results","📈 Rolling Returns","📰 News & Monitor","🎯 Goal"])

with tabs[0]:
    st.subheader("📌 Portfolio")
    st.info("Upload a holdings CSV for analysis. Groww read-only synchronization will be added only after the research modules are stable.")
    up=st.file_uploader("Portfolio CSV",type=["csv"],key="p")
    if up: st.dataframe(pd.read_csv(up),use_container_width=True,hide_index=True)

with tabs[1]:
    st.subheader("👀 Watchlist")
    if "watch" not in st.session_state:st.session_state.watch=[]
    a,b,c=st.columns(3)
    with a:n=st.text_input("Name",key="n")
    with b:s=st.text_input("Symbol",key="s")
    with c:k=st.selectbox("Type",["Stock","Mutual Fund"],key="k")
    if st.button("➕ Add",key="add"):
        if n and s:st.session_state.watch.append({"Name":n,"Symbol":s.upper(),"Type":k})
    if st.session_state.watch:st.dataframe(pd.DataFrame(st.session_state.watch),use_container_width=True,hide_index=True)
    else:st.info("No watchlist items yet.")

with tabs[2]:
    st.subheader("🔍 Fundamental Check")
    if ticker.strip():
        try:
            info,hist,q=stock_bundle(ticker.strip())
            fin=financial_company(info)
            st.write(f"**{info.get('longName',ticker)}** • {info.get('sector','Unknown')} • {'Financial' if fin else 'Non-financial'}")
            a,b,c,d=st.columns(4)
            a.metric("P/E",f"{safe(info.get('trailingPE')):.2f}" if pd.notna(safe(info.get('trailingPE'))) else "N/A")
            b.metric("ROE",f"{safe(info.get('returnOnEquity'))*100:.1f}%" if pd.notna(safe(info.get('returnOnEquity'))) else "N/A")
            c.metric("D/E",f"{safe(info.get('debtToEquity')):.2f}" if pd.notna(safe(info.get('debtToEquity'))) else "N/A")
            d.metric("Earnings growth",f"{safe(info.get('earningsGrowth'))*100:.1f}%" if pd.notna(safe(info.get('earningsGrowth'))) else "N/A")
            eg=safe(info.get("earningsGrowth"));de=safe(info.get("debtToEquity"))
            rows=[["EPS/earnings growth",eg*100 if pd.notna(eg) else np.nan,"PASS" if pd.notna(eg) and eg>=.10 else ("FAIL" if pd.notna(eg) else "DATA NEEDED")]]
            rows.append(["Debt/Equity",de,"N/A — financial company" if fin else ("PASS" if pd.notna(de) and de<1 else ("FAIL" if pd.notna(de) else "DATA NEEDED"))])
            st.dataframe(pd.DataFrame(rows,columns=["Metric","Value","Rule"]),use_container_width=True,hide_index=True)
            st.info("Financial companies: D/E is not a rejection rule. Non-financial companies: D/E < 1 is mandatory. Missing key data never becomes an automatic BUY.")
        except Exception as e:st.error(f"Data error: {e}")
    else:st.info("Enter a stock ticker in the sidebar.")

with tabs[3]:
    st.subheader("📑 Quarterly Results")
    if ticker.strip():
        try:
            info,hist,q=stock_bundle(ticker.strip())
            if q is None or q.empty:st.warning("Quarterly data was not returned for this ticker.")
            else:
                st.dataframe(q,use_container_width=True)
                st.caption("Cross-check important figures with the company's/NSE's official filings.")
        except Exception as e:st.error(f"Quarterly data error: {e}")
    else:st.info("Enter a stock ticker.")

with tabs[4]:
    st.subheader("📈 Rolling Returns — automatic fund search")
    if not fund_search:
        st.info("Type a fund name in the sidebar. Example: Parag Parikh Flexi Cap Fund")
    else:
        try:
            cat=mf_catalog()
            results=search_funds(cat,fund_search)
            if results.empty:
                st.warning("No matching schemes found. Try a shorter fund name.")
            else:
                labels=[f"{r.schemeName}  |  {r.schemeCode}" for _,r in results.iterrows()]
                choice=st.selectbox("Select scheme",labels)
                code=choice.split("|")[-1].strip()
                period=st.selectbox("Rolling period",[1,3,5,7,10],index=2,format_func=lambda x:f"{x}Y")
                nav=mf_history(code)
                if nav.empty:st.warning("NAV history unavailable for this scheme.")
                else:
                    rr=rolling_returns(nav,period)
                    if rr.empty:st.warning(f"Not enough NAV history for {period}Y rolling return.")
                    else:
                        st.markdown("### Every-year rolling return")
                        yr=annual_last(rr)
                        st.dataframe(yr.style.format({"Rolling return":"{:.2f}%"}),use_container_width=True,hide_index=True)
                        st.markdown("### Monthly rolling observations")
                        st.line_chart(rr.set_index("Period ending")["Rolling return"])
                        x=rr["Rolling return"]
                        a,b,c,d=st.columns(4)
                        a.metric("Average",f"{x.mean():.2f}%")
                        b.metric("Minimum",f"{x.min():.2f}%")
                        c.metric("Maximum",f"{x.max():.2f}%")
                        d.metric(">12%",f"{(x>12).mean()*100:.1f}%")
                        with st.expander("View all monthly observations"):
                            st.dataframe(rr.style.format({"Rolling return":"{:.2f}%"}),use_container_width=True,hide_index=True)
                        st.caption("NAV data is retrieved through MFAPI. Validate important fund figures against AMFI/fund-house records.")
        except Exception as e:
            st.error(f"Fund search/data error: {e}")

with tabs[5]:
    st.subheader("📰 News & Monitor")
    if not ticker.strip():
        st.info("Enter a stock ticker in the sidebar.")
    else:
        try:
            info,hist,q=stock_bundle(ticker.strip())
            if hist is not None and len(hist)>=2:
                close=hist["Close"].dropna()
                move=(float(close.iloc[-1])/float(close.iloc[-2])-1)*100
                a,b=st.columns(2)
                a.metric("Latest close",f"₹{float(close.iloc[-1]):,.2f}")
                b.metric("Daily movement",f"{move:+.2f}%")
                if abs(move)>=alert:st.warning(f"🔔 Movement alert: {move:+.2f}%")
                else:st.success("No movement alert at your selected threshold.")
            news=stock_news(ticker.strip())
            if not news:
                st.warning("The market-data provider returned no news for this ticker.")
                st.markdown("### Search latest news manually")
                st.link_button("Google News search",f"https://news.google.com/search?q={quote_plus(ticker.strip())}")
            else:
                st.markdown("### Recent provider news")
                for n in news[:10]:
                    title=n.get("title","News")
                    publisher=n.get("publisher","")
                    link=n.get("link","")
                    if link:st.markdown(f"**{title}** — {publisher}  \n[Open article]({link})")
                    else:st.write(f"**{title}** — {publisher}")
            st.info("News is evidence for investigation, not proof of causation. The app will label causes as confirmed or possible rather than inventing reasons.")
        except Exception as e:
            st.error(f"News/monitor error: {e}")

with tabs[6]:
    st.subheader("🎯 Goal Planner")
    target=st.number_input("Target corpus (₹)",100000.,1000000000.,10000000.,100000.,format="%.0f")
    years=st.number_input("Investment period (years)",1,40,10,1)
    sip=st.number_input("Monthly SIP (₹)",0.,10000000.,20000.,1000.,format="%.0f")
    step=st.number_input("Annual SIP step-up (%)",0.,100.,15.,1.)
    ret=st.number_input("Expected return (%)",0.,30.,12.,.5)
    bonus=st.number_input("Annual bonus (₹)",0.,10000000.,100000.,10000.,format="%.0f")
    refund=st.number_input("Annual tax refund (₹)",0.,10000000.,50000.,5000.,format="%.0f")
    current=st.number_input("Current corpus (₹)",0.,1000000000.,0.,10000.,format="%.0f")
    r=ret/100/12;corpus=current;s=sip;rows=[]
    for y in range(1,int(years)+1):
        for _ in range(12):corpus=corpus*(1+r)+s
        corpus+=bonus+refund;rows.append([y,s,corpus]);s*=1+step/100
    st.metric("Projected corpus",f"₹{corpus:,.0f}")
    st.success("🟢 ON TRACK" if corpus>=target else f"🔴 OFF TRACK — shortfall ₹{target-corpus:,.0f}")

st.divider()
st.caption("V5.2 • Research-only • No Groww credentials, banking information or order placement.")
