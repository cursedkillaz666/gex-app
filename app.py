import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
from streamlit_autorefresh import st_autorefresh

# 1. AUTO-REFRESH (Every 30 seconds)
st_autorefresh(interval=30000, key="gex_heartbeat")

# 2. PAGE CONFIG
st.set_page_config(page_title="GEX Advisor Pro", layout="wide")
st.markdown("<style>.main {background-color: #000000;}</style>", unsafe_allow_html=True)

# 3. SIDEBAR
st.sidebar.title("GEX SCANNER")
ticker_sym = st.sidebar.selectbox("TICKER", ["IWM", "SPY", "QQQ"])

# 4. DATA ENGINE
@st.cache_data(ttl=60)
def get_gex_data(symbol):
    try:
        tk = yf.Ticker(symbol)
        expiry = tk.options[0]
        chain = tk.option_chain(expiry)
        
        calls = chain.calls[['strike', 'openInterest']].copy()
        puts = chain.puts[['strike', 'openInterest']].copy()
        
        # Dual Side Logic: Calls positive, Puts negative
        calls['gex'] = calls['openInterest']
        puts['gex'] = -puts['openInterest']
        
        return pd.concat([calls, puts]), expiry
    except:
        return None, None

def get_live_price(symbol):
    try:
        tk = yf.Ticker(symbol)
        data = tk.history(period='1d', interval='1m')
        return data['Close'].iloc[-1] if not data.empty else None
    except:
        return None

# 5. EXECUTION
live_price = get_live_price(ticker_sym)
df, exp_date = get_gex_data(ticker_sym)

if df is not None and live_price:
    # Filter for strikes near the price
    chart_df = df.groupby('strike')['gex'].sum().reset_index()
    chart_df = chart_df[(chart_df['strike'] > live_price - 6) & (chart_df['strike'] < live_price + 6)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_df['gex'],
        y=chart_df['strike'],
        orientation='h',
        marker_color=['#00FF41' if x > 0 else '#FF3131' for x in chart_df['gex']],
        width=0.3
    ))

    # Center the 0 line so you see both sides
    max_val = chart_df['gex'].abs().max()

    fig.update_layout(
        template="plotly_dark",
        height=900,
        paper_bgcolor='black',
        plot_bgcolor='black',
        yaxis=dict(tickmode='linear', dtick=1.0, title="STRIKE", gridcolor='#222'),
        xaxis=dict(range=[-max_val, max_val], title="PUTS <--- 0 ---> CALLS", gridcolor='#222'),
        title=f"{ticker_sym} | Price: ${live_price:.2f} | Expiry: {exp_date}"
    )

    # Live Price Line
    fig.add_hline(y=live_price, line_dash="dash", line_color="#00D4FF", 
                 annotation_text=f"LIVE: ${live_price:.2f}", annotation_position="top right")

    st.plotly_chart(fig, use_container_width=True)
