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
            std_dev = spot * 0.02 
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

    fig.update_layout(
        template="plotly_dark",
        height=750,
        xaxis_title="Negative Gamma (Put Wall) vs Positive Gamma (Call Wall)",
        yaxis_title="Strike Price",
        bargap=0.2
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Fetching latest market levels...")
