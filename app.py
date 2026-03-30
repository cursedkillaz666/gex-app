import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# --- CONFIG ---
API_KEY = "gmvrvccr1cM5002CHvRk1GalZ_okbdrI"
BASE_URL = "https://api.massive.com/v3/snapshot/options/"

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
ticker = st.sidebar.selectbox("SELECT FOCUS TICKER", watchlist)

def fetch_gex_data(symbol):
    try:
        url = f"{BASE_URL}{symbol}?apiKey={API_KEY}"
        response = requests.get(url, timeout=10)
        
        # DEBUG: Show us what's happening behind the scenes
        if response.status_code != 200:
            st.sidebar.error(f"API Error: {response.status_code} for {symbol}")
            return None, None
            
        data = response.json()
        results = data.get('results', [])
        
        if not results:
            st.sidebar.warning(f"No options data found for {symbol}")
            return None, None
            
        return pd.DataFrame(results), data.get('underlying_price', 0)
    except Exception as e:
        st.sidebar.error(f"Connection Failed: {e}")
        return None, None

# --- MAIN LOGIC ---
st.title(f"📊 {ticker} Exposure Profile")

df, spot_price = fetch_gex_data(ticker)

if df is not None and not df.empty:
    # Calculate GEX
    df['gex_val'] = df.apply(lambda x: (x.get('gamma', 0) * x.get('open_interest', 0) * 100) 
                            if x.get('contract_type') == 'call' 
                            else -(x.get('gamma', 0) * x.get('open_interest', 0) * 100), axis=1)
    
    chart_df = df.groupby('strike_price')['gex_val'].sum().reset_index()
    
    # Dynamic zoom around spot price
    chart_df = chart_df[(chart_df['strike_price'] > spot_price * 0.96) & (chart_df['strike_price'] < spot_price * 1.04)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_df['gex_val'],
        y=chart_df['strike_price'],
        orientation='h',
        marker_color=['#00ff00' if x > 0 else '#ff4b4b' for x in chart_df['gex_val']],
    ))

    fig.add_hline(y=spot_price, line_dash="dash", line_color="#58a6ff", 
                 annotation_text=f"SPOT: ${spot_price:.2f}", annotation_position="top right")

    fig.update_layout(template="plotly_dark", height=700, xaxis_title="Net Gamma ($)", yaxis_title="Strike")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Check the sidebar for API status. It might be waiting for market data.")
