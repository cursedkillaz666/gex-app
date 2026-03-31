import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
from streamlit_autorefresh import st_autorefresh

# 1. LIVE REFRESH (Updates every 30 seconds)
st_autorefresh(interval=30000, key="fizzbuzz")

# 2. THEME SETUP
st.set_page_config(page_title="GEX Advisor Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; }
    [data-testid="stSidebar"] { background-color: #0e1117; }
    </style>
    """, unsafe_allow_html=True)

# 3. SIDEBAR
st.sidebar.title("GEX SCANNER")
ticker_sym = st.sidebar.selectbox("TICKER", ["IWM", "SPY", "QQQ"])
if st.sidebar.button("MANUAL REFRESH"):
    st.cache_data.clear()
    st.rerun()

# 4. DATA ENGINE
@st.cache_data(ttl=60) # Lower TTL for more 'live' options data
def get_primo_data(symbol):
    try:
        tk = yf.Ticker(symbol)
        expiry = tk.options[0]
        chain = tk.option_chain(expiry)
        spot = tk.history(period='1d')['Close'].iloc[-1]
        
        def calc_gamma(row, is_call):
            dist = abs(row['strike'] - spot)
            # Slightly wider factor (0.01) ensures the 'other side' stays visible
            gamma_factor = np.exp(-(dist**2) / (2 * (spot * 0.01)**2))
            return row['openInterest'] * gamma_factor * (1 if is_call else -1)

        calls, puts = chain.calls.copy(), chain.puts.copy()
        calls['gex'] = calls.apply(lambda x: calc_gamma(x, True), axis=1)
        puts['gex'] = puts.apply(lambda x: calc_gamma(x, False), axis=1)
        return pd.concat([calls, puts]), expiry, spot
    except:
        return None, None, None

def get_live_price(symbol):
    try:
        tk = yf.Ticker(symbol)
        data = tk.history(period='1d', interval='1m')
        return data['Close'].iloc[-1] if not data.empty else None
    except: return None

# 5. EXECUTION
live_price = get_live_price(ticker_sym)
df, exp_date, data_spot = get_primo_data(ticker_sym)
final_spot = live_price if live_price else data_spot

if df is not None and final_spot:
    chart_df = df.groupby('strike')['gex'].sum().reset_index()
    
    # Range: Show +/- 7 points to capture the full Call/Put landscape
    chart_df = chart_df[(chart_df['strike'] > final_spot - 7) & (chart_df['strike'] < final_spot + 7)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_df['gex'],
        y=chart_df['strike'],
        orientation='h',
        marker=dict(color=['#00FF41' if x > 0 else '#FF3131' for x in chart_df['gex']], line=dict(width=0)),
        width=0.3
    ))

    # SYMMETRICAL X-AXIS FIX
    # This forces the 0 to be centered so you see both sides equally
    max_gex = chart_df['gex'].abs().max()
    
    fig.update_layout(
        template="plotly_dark",
        height=900,
        plot_bgcolor='black',
        paper_bgcolor='black',
        yaxis=dict(showgrid=True, gridcolor='#222', tickmode='linear', dtick=1.0, title="STRIKE"),
        xaxis=dict(
            showgrid=True, gridcolor='#222', 
            range=[-max_gex, max_gex], # THIS IS THE DUAL-SIDE FIX
            title="PUT GEX <--- 0 ---> CALL GEX"
        ),
        title=f"{ticker_sym} | Live: ${final_spot:.2f} | Expiry: {exp_date}"
    )

    fig.add_hline(y=final_spot, line_dash="dash", line_color="#00D4FF", 
                 annotation_text=f"LIVE: ${final_spot:.2f}", annotation_position="top right")

    st.plotly_chart(fig, use_container_width=True)
