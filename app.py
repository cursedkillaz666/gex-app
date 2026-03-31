import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import numpy as np

# 1. THEME SETUP
st.set_page_config(page_title="GEX Advisor Pro", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; }
    [data-testid="stSidebar"] { background-color: #0e1117; }
    </style>
    """, unsafe_allow_html=True)

# 2. SIDEBAR
st.sidebar.title("GEX SCANNER")
ticker_sym = st.sidebar.selectbox("TICKER", ["IWM", "SPY", "QQQ"])
if st.sidebar.button("REFRESH"):
    st.cache_data.clear()
    st.rerun()

# 3. DATA ENGINE
@st.cache_data(ttl=300)
def get_primo_data(symbol):
    try:
        tk = yf.Ticker(symbol)
        expiry = tk.options[0]
        chain = tk.option_chain(expiry)
        
        # Base spot for gamma scaling
        base_spot = tk.history(period='1d')['Close'].iloc[-1]
        
        def calc_gamma(row, is_call):
            dist = abs(row['strike'] - base_spot)
            # Gaussian scaling creates the "needle" look from the photo
            gamma_factor = np.exp(-(dist**2) / (2 * (base_spot * 0.006)**2))
            return row['openInterest'] * gamma_factor * (1 if is_call else -1)

        calls = chain.calls.copy()
        puts = chain.puts.copy()
        calls['gex'] = calls.apply(lambda x: calc_gamma(x, True), axis=1)
        puts['gex'] = puts.apply(lambda x: calc_gamma(x, False), axis=1)
        
        return pd.concat([calls, puts]), expiry
    except:
        return None, None

def get_live_price(symbol):
    try:
        # Pulling 1m interval for the most 'live' feel possible
        tk = yf.Ticker(symbol)
        data = tk.history(period='1d', interval='1m')
        return data['Close'].iloc[-1] if not data.empty else None
    except:
        return None

# 4. CHART BUILDING
live_price = get_live_price(ticker_sym)
df, exp_date = get_primo_data(ticker_sym)

if df is not None and live_price:
    chart_df = df.groupby('strike')['gex'].sum().reset_index()
    
    # Range: +/- 5 points from current price to show both Call/Put walls
    chart_df = chart_df[(chart_df['strike'] > live_price - 5) & (chart_df['strike'] < live_price + 5)]

    fig = go.Figure()
    
    # Adding Dual-Sided Bars
    fig.add_trace(go.Bar(
        x=chart_df['gex'],
        y=chart_df['strike'],
        orientation='h',
        marker=dict(
            color=['#00FF41' if x > 0 else '#FF3131' for x in chart_df['gex']],
            line=dict(width=0)
        ),
        width=0.25 # Sharp, thin bars like the community scanner
    ))

    # Real-Time Price Line
    fig.add_hline(y=live_price, line_dash="dash", line_color="#00D4FF", 
                 annotation_text=f"LIVE: ${live_price:.2f}", 
                 annotation_position="top right",
                 annotation_font=dict(color="#00D4FF", size=14))

    fig.update_layout(
        template="plotly_dark",
        height=850,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(
            showgrid=True, gridcolor='#222', 
            tickmode='linear', dtick=1.0,
            title="STRIKE"
        ),
        xaxis=dict(
            showgrid=True, gridcolor='#222', 
            title="PUT GEX (LEFT) | CALL GEX (RIGHT)",
            zerolinecolor="#555"
        ),
        title=f"{ticker_sym} Gamma Profile | Expiry: {exp_date}",
        margin=dict(l=20, r=20, t=60, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Market is closed or syncing... Check ticker or refresh.")
