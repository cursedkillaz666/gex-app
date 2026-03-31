import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# 1. PAGE SETUP
st.set_page_config(page_title="GEX Advisor Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    </style>
    """, unsafe_allow_html=True)

# 2. SIDEBAR
st.sidebar.header("🎯 GEX SCANNER")

if st.sidebar.button("🔄 REFRESH DATA"):
    st.cache_data.clear()
    st.rerun()

watchlist_input = st.sidebar.text_input("Watchlist", value="IWM, SPY, QQQ")
watchlist = [t.strip().upper() for t in watchlist_input.split(',')]
ticker_sym = st.sidebar.selectbox("SELECT FOCUS TICKER", watchlist)

# 3. DATA ENGINE
@st.cache_data(ttl=300)
def get_market_data(symbol):
    try:
        tk = yf.Ticker(symbol)
        expiries = tk.options
        if not expiries: return None, None
        
        # Get nearest expiry chain
        opts = tk.option_chain(expiries[0])
        
        calls = opts.calls[['strike', 'openInterest']].copy()
        puts = opts.puts[['strike', 'openInterest']].copy()
        
        # Net Open Interest (The 'Weight')
        calls['val'] = calls['openInterest']
        puts['val'] = -puts['openInterest']
        
        combined = pd.concat([calls, puts])
        return combined, expiries[0]
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
st.title(f"📊 {ticker_sym} Exposure Profile")

live_price = get_live_spot(ticker_sym)
df, expiry = get_market_data(ticker_sym)

if df is not None and live_price:
    st.caption(f"Showing Nearest Expiry: {expiry} | Current Price: ${live_price:.2f}")
    
    # Aggregate data by strike
    chart_df = df.groupby('strike')['val'].sum().reset_index()
    
    # ZOOM: 2.0% range for high detail
    chart_df = chart_df[(chart_df['strike'] > live_price * 0.98) & 
                        (chart_df['strike'] < live_price * 1.02)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_df['val'],
        y=chart_df['strike'],
        orientation='h',
        marker_color=['#FF3131' if x < 0 else '#00FF41' for x in chart_df['val']],
        name="Net Exposure"
    ))

    # Y-AXIS PRECISION
    # dtick=0.5 ensures every half-point is labeled for IWM
    tick_spacing = 0.5 if ticker_sym == "IWM" else 1.0

    # THE FIX: Increased height and bargap to prevent overlapping
    fig.update_layout(
        template="plotly_dark", 
        height=1200,   # Taller chart stretches the Y-axis
        bargap=0.4,    # More space between bars so they don't cover multiple lines
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis_title="PUTS (RED) <---> CALLS (GREEN)",
        yaxis_title="STRIKE PRICE",
        yaxis = dict(
            tickmode = 'linear',
            tick0 = round(live_price * 2) / 2,
            dtick = tick_spacing,
            gridcolor = '#333'
        ),
        xaxis = dict(gridcolor = '#333')
    )

    # LIVE PRICE LINE
    fig.add_hline(y=live_price, line_dash="dash", line_color="#00D4FF", 
                 annotation_text=f"LIVE: ${live_price:.2f}", 
                 annotation_position="top right",
                 annotation_font=dict(color="#00D4FF", size=14))
    
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Syncing market levels...")
