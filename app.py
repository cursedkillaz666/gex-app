import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np

# 1. SETUP & STYLING
st.set_page_config(page_title="GEX Advisor Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    </style>
    """, unsafe_allow_html=True)

# 2. SIDEBAR CONTROLS
st.sidebar.header("🎯 GEX SCANNER")

if st.sidebar.button("🔄 REFRESH DATA"):
    st.cache_data.clear()
    st.rerun()

watchlist_input = st.sidebar.text_input("Watchlist", value="IWM, SPY, QQQ")
watchlist = [t.strip().upper() for t in watchlist_input.split(',')]
ticker_sym = st.sidebar.selectbox("SELECT FOCUS TICKER", watchlist)

# 3. DATA FUNCTIONS
@st.cache_data(ttl=300)
def get_gex_data(symbol):
    try:
        tk = yf.Ticker(symbol)
        expiries = tk.options
        if not expiries: return None, None
        
        opts = tk.option_chain(expiries[0])
        spot = tk.history(period="1d")['Close'].iloc[-1]
        
        calls = opts.calls[['strike', 'openInterest']].copy()
        puts = opts.puts[['strike', 'openInterest']].copy()
        
        # Gamma Estimation Logic
        def estimate_gamma(strike, spot):
            dist = abs(strike - spot)
            std_dev = spot * 0.015 # Controls how "tight" the gamma looks
            return np.exp(-(dist**2) / (2 * std_dev**2))

        calls['gex'] = calls.apply(lambda x: x['openInterest'] * estimate_gamma(x['strike'], spot), axis=1)
        puts['gex'] = puts.apply(lambda x: -x['openInterest'] * estimate_gamma(x['strike'], spot), axis=1)
        
        return pd.concat([calls, puts]), spot
    except:
        return None, None

def get_live_spot(symbol):
    try:
        tk = yf.Ticker(symbol)
        data = tk.history(period='1d', interval='1m')
        return data['Close'].iloc[-1] if not data.empty else None
    except:
        return None

# 4. MAIN EXECUTION
st.title(f"📊 {ticker_sym} Gamma Exposure Profile")
st.caption("Estimated GEX: Modeled using Open Interest and Price Proximity")

# Fetch Data
live_price = get_live_spot(ticker_sym)
df, data_spot = get_gex_data(ticker_sym)

# Use live price if available
final_spot = live_price if live_price else data_spot

if df is not None and final_spot:
    chart_df = df.groupby('strike')['gex'].sum().reset_index()
    
    # ZOOM: Show strikes within 2.5% of price
    chart_df = chart_df[(chart_df['strike'] > final_spot * 0.975) & (chart_df['strike'] < final_spot * 1.025)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_df['gex'],
        y=chart_df['strike'],
        orientation='h',
        marker_color=['#FF3131' if x < 0 else '#00FF41' for x in chart_df['gex']],
        name="Net GEX"
    ))

    # Real-time Price Line
    fig.add_hline(y=final_spot, line_dash="dash", line_color="#00D4FF", 
                 annotation_text=f"LIVE: ${final_spot:.2f}", annotation_position="top right")

    fig.update_layout(
        template="plotly_dark", 
        height=800, 
        bargap=0.05,
        xaxis_title="NEGATIVE GEX (PUTS) <---> POSITIVE GEX (CALLS)",
        yaxis_title="STRIKE PRICE"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Market data is loading... If it stays empty, check the ticker symbol.")
