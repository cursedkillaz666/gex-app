import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np
from streamlit_autorefresh import st_autorefresh

# 1. LIVE HEARTBEAT (30s)
st_autorefresh(interval=30000, key="gex_spy_qqq_fix")

# 2. PAGE CONFIG
st.set_page_config(page_title="GEX Advisor Pro", layout="wide")
st.markdown("<style>.main {background-color: #000000;}</style>", unsafe_allow_html=True)

# 3. SIDEBAR
st.sidebar.title("GEX SCANNER")
ticker_sym = st.sidebar.selectbox("TICKER", ["SPY", "QQQ", "IWM"])

# 4. DATA ENGINE (Strict Separation)
@st.cache_data(ttl=60)
def get_gex_data(symbol):
    try:
        tk = yf.Ticker(symbol)
        expiry = tk.options[0]
        chain = tk.option_chain(expiry)
        spot = tk.history(period='1d')['Close'].iloc[-1]
        
        # Gaussian Math for the 'Spikes'
        def calc_weight(strike, spot):
            dist = abs(strike - spot)
            return np.exp(-(dist**2) / (2 * (spot * 0.008)**2))

        # --- CALLS (Always Right/Green) ---
        c = chain.calls[['strike', 'openInterest']].copy()
        c['gex'] = c.apply(lambda x: x['openInterest'] * calc_weight(x['strike'], spot), axis=1)
        
        # --- PUTS (Always Left/Red) ---
        p = chain.puts[['strike', 'openInterest']].copy()
        p['gex'] = p.apply(lambda x: -x['openInterest'] * calc_weight(x['strike'], spot), axis=1)
        
        combined = pd.concat([c, p])
        return combined.groupby('strike')['gex'].sum().reset_index(), expiry, spot
    except:
        return None, None, None

# 5. EXECUTION
df, exp_date, live_price = get_gex_data(ticker_sym)

if df is not None and live_price:
    # Match the Zoom Level from Primo's Photo (+/- 6 points)
    chart_df = df[(df['strike'] > live_price - 6) & (df['strike'] < live_price + 6)]

    # Dynamic Color Assignment based on Value
    # Positive (Right) = Green | Negative (Left) = Red
    colors = ['#00FF41' if x >= 0 else '#FF3131' for x in chart_df['gex']]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_df['gex'],
        y=chart_df['strike'],
        orientation='h',
        marker_color=colors,
        width=0.4, # Professional bar thickness
        marker_line_width=0
    ))

    # Center the 0 line
    max_abs = chart_df['gex'].abs().max()

    fig.update_layout(
        template="plotly_dark",
        height=900,
        paper_bgcolor='black',
        plot_bgcolor='black',
        yaxis=dict(tickmode='linear', dtick=1.0, title="STRIKE", gridcolor='#222'),
        xaxis=dict(
            range=[-max_abs, max_abs], 
            title="PUT GEX (RED) <--- 0 ---> CALL GEX (GREEN)", 
            gridcolor='#222',
            zerolinecolor="#ffffff",
            zerolinewidth=2
        ),
        title=f"{ticker_sym} GEX | Spot: ${live_price:.2f} | Expiry: {exp_date}",
        margin=dict(l=50, r=50, t=80, b=50)
    )

    # Blue Live Price Magnet
    fig.add_hline(y=live_price, line_dash="dash", line_color="#00D4FF", 
                 annotation_text=f"LIVE: ${live_price:.2f}", 
                 annotation_position="top right",
                 annotation_font_color="#00D4FF")

    st.plotly_chart(fig, use_container_width=True)
