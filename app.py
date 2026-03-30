import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="GEX Advisor Pro", layout="wide")

# --- UI STYLING ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    </style>
    """, unsafe_allow_html=True)

st.sidebar.header("🎯 GEX SCANNER")
watchlist_input = st.sidebar.text_input("Watchlist", value="IWM, SPY, QQQ")
watchlist = [t.strip().upper() for t in watchlist_input.split(',')]
ticker_sym = st.sidebar.selectbox("SELECT FOCUS TICKER", watchlist)

def get_oi_data(symbol):
    try:
        tk = yf.Ticker(symbol)
        # Get the nearest expiration date
        expiries = tk.options
        if not expiries:
            return None, None
        
        # Pull the full chain for the nearest expiry
        opts = tk.option_chain(expiries[0])
        calls = opts.calls[['strike', 'openInterest']].copy()
        puts = opts.puts[['strike', 'openInterest']].copy()
        
        calls['net_oi'] = calls['openInterest']
        puts['net_oi'] = -puts['openInterest']
        
        combined = pd.concat([calls, puts])
        spot = tk.history(period="1d")['Close'].iloc[-1]
        return combined, spot
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None, None

# --- MAIN UI ---
st.title(f"📊 {ticker_sym} Exposure Profile")
st.caption("Visualizing Open Interest 'Magnets' and 'Walls'")

df, spot_price = get_oi_data(ticker_sym)

if df is not None:
    # Group by strike for the chart
    chart_df = df.groupby('strike')['net_oi'].sum().reset_index()
    
    # Filter strikes to show the 'Active Zone' (±5% from spot)
    chart_df = chart_df[(chart_df['strike'] > spot_price * 0.95) & (chart_df['strike'] < spot_price * 1.05)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_df['net_oi'],
        y=chart_df['strike'],
        orientation='h',
        marker_color=['#00ff00' if x > 0 else '#ff4b4b' for x in chart_df['net_oi']],
        name="Net Open Interest"
    ))

    # Add Spot Price Line
    fig.add_hline(y=spot_price, line_dash="dash", line_color="#58a6ff", 
                 annotation_text=f"SPOT: ${spot_price:.2f}", annotation_position="top right")

    fig.update_layout(
        template="plotly_dark",
        height=750,
        xaxis_title="Put OI (Red) vs Call OI (Green)",
        yaxis_title="Strike Price",
        bargap=0.1
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Loading market data...")
