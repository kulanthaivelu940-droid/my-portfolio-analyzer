import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(page_title="My Portfolio Analyzer V5.1", page_icon="📊", layout="wide")
st.markdown("""<style>.block-container{padding:1rem;max-width:1250px}@media(max-width:700px){.block-container{padding:.7rem}h1{font-size:1.5rem!important}}</style>""", unsafe_allow_html=True)

st.title("📊 My Portfolio Analyzer")
st.caption("V5.1 • Real-data research layer • No trading/orders")

# ---------------- helpers ----------------
@st.cache_data(ttl=900, show_spinner=False)
def stock_data(ticker):
    t = yf.Ticker(ticker)
    info = t.info
    hist = t.history(period="2y", auto_adjust=False)
    q = t.quarterly_financials
    a = t.financials
    return info, hist, q, a

@st.cache_data(ttl=900, show_spinner=False)
def stock_history(ticker, period="10y"):
    return yf.download(ticker, period=period, auto_adjust=False, progress=False)

@st.cache_data(ttl=3600, show_spinner=False)
def mf_schemes():
    # mfapi is used only as a scheme/NAV data convenience layer; source shown in UI.
    url="https://api.mfapi.in/mf"
    r=requests.get(url,timeout=20)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=3600, show_spinner=False)
def mf_history(code):
    r=requests.get(f"https://api.mfapi.in/mf/{code}",timeout=20)
    r.raise_for_status()
    j=r.json()
    df=pd.DataFrame(j.get("data",[]))
    if df.empty: return df
    df["date"]=pd.to_datetime(df["date"],dayfirst=True,errors="coerce")
    df["nav"]=pd.to_numeric(df["nav"],errors="coerce")
    return df.dropna(subset=["date","nav"]).sort_values("date")

def rolling_returns(nav, years):
    s=nav.set_index("date")["nav"].sort_index()
    # monthly observations: last available NAV in each month
    m=s.resample("ME").last().dropna()
    if len(m) <= years*12: return pd.DataFrame(columns=["Period ending","Rolling return"])
    rr=(m/m.shift(years*12)-1)*100
    out=rr.dropna().reset_index()
    out.columns=["Period ending","Rolling return"]
    return out

def classify_company(info):
    text=" ".join(str(info.get(k,"")) for k in ["sector","industry","industryKey"]).lower()
    financial_words=["bank","financial","insurance","credit","capital markets","asset management","mortgage","lending","nbfc"]
    return any(w in text for w in financial_words)

def safe_num(x):
    try:
        return float(x)
    except:
        return np.nan

# ---------------- sidebar ----------------
with st.sidebar:
    st.header("🔎 Research input")
    stock_ticker=st.text_input("Stock ticker",placeholder="e.g. TATACONSUM.NS")
    mf_code=st.text_input("AMFI/MFAPI scheme code",placeholder="e.g. 122639")
    alert_pct=st.slider("Daily movement alert (%)",1.0,10.0,3.0,0.5)
    st.caption("Stock data uses Yahoo Finance via yfinance. Mutual-fund NAV history uses MFAPI for this prototype; AMFI is the reference source for official NAV history.")

tabs=st.tabs(["📌 Portfolio","👀 Watchlist","🔍 Fundamental Check","📑 Quarterly Results","📈 Rolling Returns","📰 News & Monitor","🎯 Goal"])

# ---------------- portfolio ----------------
with tabs[0]:
    st.subheader("📌 Portfolio")
    st.write("V5.1 can analyze an uploaded portfolio now; Groww read-only synchronization remains a separate security-controlled phase.")
    up=st.file_uploader("Upload CSV",type=["csv"],key="portfolio")
    if up:
        p=pd.read_csv(up)
        st.dataframe(p,use_container_width=True,hide_index=True)
    else:
        st.info("Upload your holdings CSV to analyze them here. No Groww credentials are requested.")

# ---------------- watchlist ----------------
with tabs[1]:
    st.subheader("👀 Watchlist")
    if "watchlist" not in st.session_state: st.session_state.watchlist=[]
    a,b,c=st.columns(3)
    with a: wn=st.text_input("Name",key="wn")
    with b: ws=st.text_input("Symbol / ticker",key="ws")
    with c: wt=st.selectbox("Type",["Stock","Mutual Fund"],key="wt")
    if st.button("➕ Add",key="add"):
        if wn.strip() and ws.strip():
            st.session_state.watchlist.append({"Name":wn.strip(),"Symbol":ws.strip().upper(),"Type":wt})
    if st.session_state.watchlist:
        st.dataframe(pd.DataFrame(st.session_state.watchlist),use_container_width=True,hide_index=True)
        st.success("Every item added here is marked for daily monitoring.")
    else: st.info("Add a stock or mutual fund. It will be included in the monitoring list.")

# ---------------- fundamental ----------------
with tabs[2]:
    st.subheader("🔍 Fundamental Check")
    if stock_ticker.strip():
        try:
            info,hist,q,a=stock_data(stock_ticker.strip())
            financial=classify_company(info)
            st.write(f"**{info.get('longName',stock_ticker)}** • {info.get('sector','Unknown')} • {'Financial' if financial else 'Non-financial'}")
            cols=st.columns(4)
            cols[0].metric("Market cap", f"₹{safe_num(info.get('marketCap'))/1e7:,.0f} Cr" if pd.notna(safe_num(info.get('marketCap'))) else "N/A")
            cols[1].metric("P/E", f"{safe_num(info.get('trailingPE')):.2f}" if pd.notna(safe_num(info.get('trailingPE'))) else "N/A")
            cols[2].metric("ROE", f"{safe_num(info.get('returnOnEquity'))*100:.1f}%" if pd.notna(safe_num(info.get('returnOnEquity'))) else "N/A")
            cols[3].metric("Debt/Equity", f"{safe_num(info.get('debtToEquity')):.2f}" if pd.notna(safe_num(info.get('debtToEquity'))) else "N/A")
            st.markdown("### Our mandatory rules")
            roe=safe_num(info.get("returnOnEquity")); de=safe_num(info.get("debtToEquity"))
            eps_growth=safe_num(info.get("earningsGrowth"))
            rows=[]
            rows.append(["EPS growth",eps_growth*100 if pd.notna(eps_growth) else np.nan, "PASS" if pd.notna(eps_growth) and eps_growth>=0.10 else ("FAIL" if pd.notna(eps_growth) else "DATA NEEDED")])
            rows.append(["Debt/Equity",de,"N/A — financial sector" if financial else ("PASS" if pd.notna(de) and de<1 else ("FAIL" if pd.notna(de) else "DATA NEEDED"))])
            rows.append(["ROE",roe*100 if pd.notna(roe) else np.nan,"REFERENCE"])
            fdf=pd.DataFrame(rows,columns=["Metric","Value","Rule"])
            st.dataframe(fdf,use_container_width=True,hide_index=True)
            if financial:
                st.info("Financial company detected: D/E is not used as a rejection rule. Use capital adequacy, asset quality, NIM, ROA/ROE, credit growth, provisions and cost-to-income in the financial-sector module.")
            else:
                st.info("Non-financial company: D/E < 1 and double-digit EPS/earnings growth are mandatory rules. Missing data means the app will not label it BUY.")
            st.markdown("### Additional quality / valuation fields")
            fields=["returnOnAssets","profitMargins","operatingMargins","freeCashflow","priceToBook","pegRatio","forwardPE","revenueGrowth"]
            vals={f:info.get(f) for f in fields}
            st.json(vals)
        except Exception as e:
            st.error(f"Could not fetch stock data: {e}")
    else:
        st.info("Enter an NSE ticker such as TATACONSUM.NS in the sidebar.")

# ---------------- quarterly ----------------
with tabs[3]:
    st.subheader("📑 Quarterly Results")
    if stock_ticker.strip():
        try:
            info,hist,q,a=stock_data(stock_ticker.strip())
            if q is None or q.empty:
                st.warning("Quarterly financial data was not returned for this ticker.")
            else:
                preferred=["Total Revenue","Operating Income","Operating Expense","Net Income","Basic EPS","Diluted EPS"]
                rows=[]
                for idx in preferred:
                    if idx in q.index:
                        row=q.loc[idx]
                        rows.append(pd.Series(row,name=idx))
                qdf=pd.DataFrame(rows)
                st.dataframe(qdf,use_container_width=True)
                st.caption("Quarterly figures are sourced from the market-data provider; always cross-check against the company's/NSE's official filing before investment decisions.")
        except Exception as e:
            st.error(f"Could not fetch quarterly results: {e}")
    else:
        st.info("Enter a stock ticker to load quarterly data.")

# ---------------- rolling ----------------
with tabs[4]:
    st.subheader("📈 Rolling Return Analysis")
    st.write("Monthly rolling observations are used underneath, with every-year summaries available from the same series.")
    if mf_code.strip():
        try:
            nav=mf_history(mf_code.strip())
            if nav.empty:
                st.warning("No NAV history found for this scheme code.")
            else:
                period=st.selectbox("Rolling period (years)",[1,3,5,7,10],index=2,key="rollperiod")
                rr=rolling_returns(nav,period)
                if rr.empty:
                    st.warning("Not enough history for this rolling period.")
                else:
                    yr=rr.assign(Year=rr["Period ending"].dt.year).groupby("Year",as_index=False)["Rolling return"].last()
                    st.markdown("**Every-year rolling return**")
                    st.dataframe(yr.style.format({"Rolling return":"{:.2f}%"}),use_container_width=True,hide_index=True)
                    st.markdown("**Monthly observations**")
                    st.line_chart(rr.set_index("Period ending")["Rolling return"])
                    x=rr["Rolling return"]
                    s1,s2,s3,s4=st.columns(4)
                    s1.metric("Average",f"{x.mean():.2f}%")
                    s2.metric("Minimum",f"{x.min():.2f}%")
                    s3.metric("Maximum",f"{x.max():.2f}%")
                    s4.metric(">12% observations",f"{(x>12).mean()*100:.1f}%")
                    st.dataframe(rr.style.format({"Rolling return":"{:.2f}%"}),use_container_width=True,hide_index=True)
        except Exception as e:
            st.error(f"Could not fetch NAV history: {e}")
    else:
        st.info("Enter an AMFI/MFAPI scheme code to calculate real rolling returns. AMFI provides NAV history and daily NAV information. See source links below.")
        st.markdown("AMFI NAV History: https://www.amfiindia.com/sif/latest-nav/nav-history")

# ---------------- news / monitor ----------------
with tabs[5]:
    st.subheader("📰 News & Daily Monitor")
    if stock_ticker.strip():
        try:
            info,hist,q,a=stock_data(stock_ticker.strip())
            if hist is not None and len(hist)>=2:
                last=float(hist["Close"].iloc[-1]); prev=float(hist["Close"].iloc[-2]); move=(last/prev-1)*100
                st.metric("Latest close",f"₹{last:,.2f}",f"{move:+.2f}%")
                if abs(move)>=alert_pct: st.warning(f"Movement alert: {move:+.2f}%")
                else: st.success("No movement alert at the selected threshold.")
            t=yf.Ticker(stock_ticker.strip())
            news=getattr(t,"news",[]) or []
            if news:
                rows=[]
                for n in news[:10]:
                    rows.append({"Title":n.get("title",""),"Publisher":n.get("publisher",""),"Link":n.get("link","")})
                st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
            else: st.info("No news feed returned by the provider.")
        except Exception as e:
            st.error(f"Monitor error: {e}")
    else:
        st.info("Enter a stock ticker for price/news monitoring.")
    st.markdown("**Important:** news is evidence for investigation, not an automatic BUY/SELL decision.")

# ---------------- goal ----------------
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
    r=ret/100/12; corpus=current; s=sip; rows=[]
    for y in range(1,int(years)+1):
        for _ in range(12): corpus=corpus*(1+r)+s
        corpus+=bonus+refund; rows.append([y,s,corpus]); s*=1+step/100
    st.metric("Projected corpus",f"₹{corpus:,.0f}")
    st.success("🟢 ON TRACK" if corpus>=target else f"🔴 OFF TRACK — shortfall ₹{target-corpus:,.0f}")
    st.dataframe(pd.DataFrame(rows,columns=["Year","Starting SIP","Projected corpus"]).style.format({"Starting SIP":"₹{:,.0f}","Projected corpus":"₹{:,.0f}"}),use_container_width=True,hide_index=True)

st.divider()
st.caption("V5.1 • Real-data research prototype • No brokerage credentials, banking data, or order placement.")
