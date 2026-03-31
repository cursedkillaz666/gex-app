import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="GEX Advisor Pro", layout="wide")

# --- UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    </style>
    """, unsafe_allow_html=True)

st.sidebar.header("🎯 GEX SCANNER")

# Refresh Button Logic
if st.sidebar.button("🔄 REFRESH DATA"):
    st.cache_data.clear()
    st.rerun()

watchlist_input = st.sidebar.text_input("Watchlist", value="IWM, SPY, QQQ")
watchlist = [t.strip().upper() for t in watchlist_input.split(',')]
ticker_sym = st.sidebar.selectbox("SELECT FOCUS TICKER", watchlist)

@st.cache_data(ttl=300) # Cache for 5 minutes
def get_gex_data(symbol):
    try:
        tk = yf.Ticker(symbol)
        expiries = tk.options
        if not expiries: return None, None
        
        opts = tk.option_chain(expiries[0])
        spot = tk.history(period="1d")['Close'].iloc[-1]
        
        calls = opts.calls[['strike', 'openInterest']].copy()
        puts = opts.puts[['strike', 'openInterest']].copy()
        
        # --- GAMMA PROXY CALCULATION ---
        # Real Gamma peaks at the spot price. We simulate this using a normal distribution curve.
        def estimate_gamma(strike, spot):
            dist = abs(strike - spot)
            # Standard deviation roughly 2% of price for tight clustering
            std_dev = spot * 0.01  # New: 1% range 
            return np.exp(-(dist**2) / (2 * std_dev**2))

        calls['gex'] = calls.apply(lambda x: x['openInterest'] * estimate_gamma(x['strike'], spot), axis=1)
        puts['gex'] = puts.apply(lambda x: -x['openInterest'] * estimate_gamma(x['strike'], spot), axis=1)
        
        combined = pd.concat([calls, puts])
        return combined, spot
    except Exception as e:
        return None, None

# --- MAIN UI ---
st.title(f"📊 {ticker_sym} Gamma Exposure Profile")
st.caption("Estimated GEX: Combining Open Interest with Price Sensitivity")

df, spot_price = get_gex_data(ticker_sym)

if df is not None:
    chart_df = df.groupby('strike')['gex'].sum().reset_index()
    
    # Filter for the 'Squeeze Zone'
    chart_df = chart_df[(chart_df['strike'] > spot_price * 0.96) & (chart_df['strike'] < spot_price * 1.04)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_df['gex'],
        y=chart_df['strike'],
        orientation='h',
        marker_color=['#00ff00' if x > 0 else '#ff4b4b' for x in chart_df['gex']],
        name="Net GEX"
    ))

    # Spot Price Line
    fig.add_hline(y=spot_price, line_dash="dash", line_color="#58a6ff", 
                 annotation_text=f"SPOT: ${spot_price:.2f}", annotation_position="top right")

  # --- REFINED VISUAL LOGIC ---
if df is not None:
    chart_df = df.groupby('strike')['gex'].sum().reset_index()
    
    # ZOOM IN: Only show strikes within 2% of price to make bars look massive
    chart_df = chart_df[(chart_df['strike'] > spot_price * 0.98) & (chart_df['strike'] < spot_price * 1.02)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_df['gex'],
        y=chart_df['strike'],
        orientation='h',
        marker_color=['#FF3131' if x < 0 else '#00FF41' for x in chart_df['gex']], # Neon Red/Green
        name="Net GEX"
    ))

    # Spot Price Line
    fig.add_hline(y=spot_price, line_dash="dash", line_color="#00D4FF", 
                 annotation_text=f"PRICE: ${spot_price:.2f}", annotation_position="top right")

    fig.update_layout(
        template="plotly_dark",
        height=800, # Taller chart
        xaxis_title="PUT WALL (NEGATIVE GEX) <---> CALL WALL (POSITIVE GEX)",
        yaxis_title="STRIKE PRICE",
        bargap=0.05, # Smaller gap = thicker, more "solid" looking bars
        font=dict(family="Courier New, monospace", size=12, color="white")
    )
    st.plotly_chart(fig, use_container_width=True)
    def get_live_spot(symbol):
    try:
        # Fetching '1m' interval to get the most recent price action
        tk = yf.Ticker(symbol)
        data = tk.history(period='1d', interval='1m')
        return data['Close'].iloc[-1]
    except:
        return None

# --- Inside your Main UI ---
spot_price = get_live_spot(ticker_sym)
df, _ = get_gex_data(ticker_sym) # Use the cached options data

if spot_price and df is not None:
    # This ensures the blue 'PRICE' line moves even if the bars are cached
    fig.add_hline(y=spot_price, line_dash="dash", line_color="#00D4FF", 
                 annotation_text=f"LIVE PRICE: ${spot_price:.2f}", 
                 annotation_position="top right")
