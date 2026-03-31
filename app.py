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

# 3. DATA ENGINE (The "Gamma" Secret)
@st.cache_data(ttl=300)
def get_primo_data(symbol):
    try:
        tk = yf.Ticker(symbol)
        expiry = tk.options[0]
        chain = tk.option_chain(expiry)
        spot = tk.history(period='1d')['Close'].iloc[-1]
        
        # We need to simulate Gamma because free APIs don't provide it
        # Real Gamma = OpenInterest * PriceSensitivity
        def calc_gamma(row, is_call):
            # The closer to the price, the "sharper" the gamma spike
            dist = abs(row['strike'] - spot)
            gamma_factor = np.exp(-(dist**2) / (2 * (spot * 0.005)**2))
            return row['openInterest'] * gamma_factor * (1 if is_call else -1)

        calls = chain.calls.copy()
        puts = chain.puts.copy()
        calls['gex'] = calls.apply(lambda x: calc_gamma(x, True), axis=1)
        puts['gex'] = puts.apply(lambda x: calc_gamma(x, False), axis=1)
        
        return pd.concat([calls, puts]), spot, expiry
    except:
        return None, None, None

# 4. CHART BUILDING
df, live_price, exp_date = get_primo_data(ticker_sym)

if df is not None:
    chart_df = df.groupby('strike')['gex'].sum().reset_index()
    
    # Tight zoom to match the IWM update photo
    chart_df = chart_df[(chart_df['strike'] > live_price - 5) & (chart_df['strike'] < live_price + 5)]

    fig = go.Figure()
    
    # Adding the Bars (Thin & Precise)
    fig.add_trace(go.Bar(
        x=chart_df['gex'],
        y=chart_df['strike'],
        orientation='h',
        marker=dict(
            color=['#00FF41' if x > 0 else '#FF3131' for x in chart_df['gex']],
            line=dict(width=0)
        ),
        width=0.2 # Makes bars thin like the photo
    ))

    # The Blue "Spot" Line
    fig.add_hline(y=live_price, line_dash="dash", line_color="#00D4FF", 
                 annotation_text=f"PRICE: ${live_price:.2f}", annotation_position="top right")

    # Layout to match the "X" Post aesthetics
    fig.update_layout(
        template="plotly_dark",
        height=800,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(
            showgrid=True, gridcolor='#333', 
            tickmode='linear', dtick=1.0, # Shows every single dollar level
            title="STRIKE"
        ),
        xaxis=dict(showgrid=True, gridcolor='#333', title="GAMMA EXPOSURE"),
        title=f"{ticker_sym} GEX Profile | Expiry: {exp_date}"
    )

    st.plotly_chart(fig, use_container_width=True)
