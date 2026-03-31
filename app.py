import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
from streamlit_autorefresh import st_autorefresh

# 1. AUTO-REFRESH (Every 30 seconds to update the blue 'LIVE' line)
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
        
        # Dual Side Logic: 
        # Calls = Positive (Right side of 0)
        # Puts = Negative (Left side of 0)
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
    # Filter for strikes near the price (Zoom in like the Primo photo)
    chart_df = df.groupby('strike')['gex'].sum().reset_index()
    chart_df = chart_df[(chart_df['strike'] > live_price - 6) & (chart_df['strike'] < live_price + 6)]

    fig = go.Figure()
    
    # --- COLOR FIX ---
    # Green (#00FF41) for positive values (Calls)
    # Red (#FF3131) for negative values (Puts)
    colors = ['#00FF41' if x > 0 else '#FF3131' for x in chart_df['gex']]

    fig.add_trace(go.Bar(
        x=chart_df['gex'],
        y=chart_df['strike'],
        orientation='h',
        marker_color=colors,
        width=0.4,
        marker_line_width=0
    ))

    # Center the 0 line so you see both sides equally
    max_val = chart_df['gex'].abs().max()

    fig.update_layout(
        template="plotly_dark",
        height=900,
        paper_bgcolor='black',
        plot_bgcolor='black',
        yaxis=dict(
            tickmode='linear', 
            dtick=1.0, 
            title="STRIKE", 
            gridcolor='#222',
            fixedrange=True
        ),
        xaxis=dict(
            range=[-max_val, max_val], 
            title="PUTS (RED) <--- 0 ---> CALLS (GREEN)", 
            gridcolor='#222',
            zerolinecolor="#666",
            zerolinewidth=2
        ),
        title=f"{ticker_sym} | Price: ${live_price:.2f} | Expiry: {exp_date}",
        margin=dict(l=50, r=50, t=80, b=50)
    )

    # Live Price Line (Blue Dashed)
    fig.add_hline(y=live_price, line_dash="dash", line_color="#00D4FF", 
                 annotation_text=f"LIVE: ${live_price:.2f}", 
                 annotation_position="top right",
                 annotation_font_size=14,
                 annotation_font_color="#00D4FF")

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.info("Market data syncing... If it's the weekend, price will reflect Friday's close.")
