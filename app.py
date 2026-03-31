import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np

# 1. PAGE SETUP
st.set_page_config(page_title="GEX Advisor Pro", layout="wide")

# Custom Dark Theme CSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    .stMetric { background-color: #1c2128; border: 1px solid #30363d; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 2. SIDEBAR & REFRESH
st.sidebar.header("🎯 GEX SCANNER")

if st.sidebar.button("🔄 REFRESH DATA"):
    st.cache_data.clear()
    st.rerun()

watchlist_input = st.sidebar.text_input("Watchlist", value="IWM, SPY, QQQ")
watchlist = [t.strip().upper() for t in watchlist_input.split(',')]
ticker_sym = st.sidebar.selectbox("SELECT FOCUS TICKER", watchlist)

# 3. DATA ENGINE
@st.cache_data(ttl=300)
def get_gex_data(symbol):
    try:
        tk = yf.Ticker(symbol)
        expiries = tk.options
        if not expiries: return None, None
        
        # Get nearest expiry
        opts = tk.option_chain(expiries[0])
        spot = tk.history(period="1d")['Close'].iloc[-1]
        
        calls = opts.calls[['strike', 'openInterest']].copy()
        puts = opts.puts[['strike', 'openInterest']].copy()
        
        # Professional Gamma Modeling
        def estimate_gamma(strike, spot):
            dist = abs(strike - spot)
            # Tighter std_dev (1%) makes the 'Magnet' bars look more accurate
            std_dev = spot * 0.01 
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

# 4. MAIN DASHBOARD
st.title(f"📊 {ticker_sym} Gamma Exposure Profile")
st.caption("Estimated GEX: Modeled using Open Interest and Price Proximity")

# Fetch Data
live_price = get_live_spot(ticker_sym)
df, data_spot = get_gex_data(ticker_sym)
final_spot = live_price if live_price else data_spot

if df is not None and final_spot:
    # Aggregating Net Gamma per Strike
    chart_df = df.groupby('strike')['gex'].sum().reset_index()
    
    # ZOOM: 1.5% range for high-definition levels
    zoom = 0.015
    chart_df = chart_df[(chart_df['strike'] > final_spot * (1-zoom)) & 
                        (chart_df['strike'] < final_spot * (1+zoom))]

    # Build the Chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_df['gex'],
        y=chart_df['strike'],
        orientation='h',
        marker_color=['#FF3131' if x < 0 else '#00FF41' for x in chart_df['gex']],
        name="Net GEX"
    ))

    # FIXING THE "EVERY 2 NUMBERS" ISSUE
    # For IWM, we want 0.5 increments. For SPY/QQQ, 1.0 increments.
    tick_spacing = 0.5 if ticker_sym == "IWM" else 1.0

    fig.update_layout(
        yaxis = dict(
            tickmode = 'linear',
            tick0 = round(final_spot * 2) / 2, # Rounds to nearest 0.5
            dtick = tick_spacing,
            gridcolor = '#30363d'
        ),
        xaxis = dict(gridcolor = '#30363d')
    )

    # LIVE PRICE LINE (The "Active" Level)
    fig.add_hline(y=final_spot, line_dash="dash", line_color="#00D4FF", 
                 annotation_text=f"LIVE: ${final_spot:.2f}", 
                 annotation_position="top right",
                 annotation_font=dict(color="#00D4FF", size=14))

    fig.update_layout(
        template="plotly_dark", 
        height=900, 
        bargap=0.1, # Professional bar thickness
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="PUT WALL (NEG
