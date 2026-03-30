import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# --- CONFIG ---
API_KEY = "gmvrvccr1cM5002CHvRk1GalZ_okbdrI"
# Trying the V2 endpoint which is more commonly open for standard keys
BASE_URL = "https://api.massive.com/v2/market/options/snapshot/"

st.set_page_config(page_title="GEX Advisor Pro", layout="wide")

st.sidebar.header("🎯 GEX SCANNER")
watchlist_input = st.sidebar.text_input("Watchlist", value="IWM, SPY, QQQ")
watchlist = [t.strip().upper() for t in watchlist_input.split(',')]
ticker = st.sidebar.selectbox("SELECT FOCUS TICKER", watchlist)

def fetch_gex_data(symbol):
    try:
        url = f"https://api.massive.com/v3/snapshot/options/{symbol}?apiKey={API_KEY}"
        
        # Adding headers to mimic a real browser request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 403:
            st.sidebar.error(f"403 Forbidden: Massive is blocking the connection. Check IP Whitelist settings in your Massive dashboard.")
            return None, None
            
        data = response.json()
        return pd.DataFrame(data.get('results', [])), data.get('underlying_price', 0)
    except Exception as e:
        st.sidebar.error(f"Error: {e}")
        return None, None

# --- MAIN UI ---
st.title(f"📊 {ticker} Exposure Profile")

df, spot_price = fetch_gex_data(ticker)

if df is not None and not df.empty:
    # Calculation Logic
    df['gex_val'] = df.apply(lambda x: (x.get('gamma', 0) * x.get('open_interest', 0) * 100) 
                            if x.get('side') == 'call' 
                            else -(x.get('gamma', 0) * x.get('open_interest', 0) * 100), axis=1)
    
    chart_df = df.groupby('strike')['gex_val'].sum().reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_df['gex_val'],
        y=chart_df['strike'],
        orientation='h',
        marker_color=['#00ff00' if x > 0 else '#ff4b4b' for x in chart_df['gex_val']],
    ))

    fig.add_hline(y=spot_price, line_dash="dash", line_color="cyan", annotation_text=f"SPOT: {spot_price}")
    fig.update_layout(template="plotly_dark", height=700)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("The API is currently returning a 403. Please verify your Massive.com subscription tier allows Snapshot access.")
