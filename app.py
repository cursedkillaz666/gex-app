import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# --- CONFIG ---
API_KEY = "gmvrvccr1cM5002CHvRk1GalZ_okbdrI"
# Using the Contracts endpoint instead of Snapshots
BASE_URL = "https://api.massive.com/v3/market/options/contracts"

st.set_page_config(page_title="GEX Advisor Pro", layout="wide")

st.sidebar.header("🎯 GEX SCANNER (Basic)")
watchlist_input = st.sidebar.text_input("Watchlist", value="IWM, SPY, QQQ")
watchlist = [t.strip().upper() for t in watchlist_input.split(',')]
ticker = st.sidebar.selectbox("SELECT FOCUS TICKER", watchlist)

def fetch_basic_data(symbol):
    try:
        # Fetching the list of all active contracts for the ticker
        url = f"{BASE_URL}?underlying_ticker={symbol}&limit=1000&apiKey={API_KEY}"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            st.sidebar.error(f"Error: {response.status_code}. Basic plan might be limited.")
            return None
            
        data = response.json()
        return pd.DataFrame(data.get('results', []))
    except Exception as e:
        return None

# --- MAIN UI ---
st.title(f"📊 {ticker} Open Interest Profile")
st.caption("Proxy for GEX: Using OI concentrations to find 'Walls' and 'Magnets'")

df = fetch_basic_data(ticker)

if df is not None and not df.empty:
    # Filter for the nearest expiration to match the "0DTE/Weekly" feel of the X post
    df['expiration_date'] = pd.to_datetime(df['expiration_date'])
    nearest_expiry = df['expiration_date'].min()
    df = df[df['expiration_date'] == nearest_expiry]

    # Calculate Proxy GEX (Calls +, Puts -)
    df['net_oi'] = df.apply(lambda x: x['open_interest'] if x['contract_type'] == 'call' else -x['open_interest'], axis=1)
    
    chart_df = df.groupby('strike_price')['net_oi'].sum().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_df['net_oi'],
        y=chart_df['strike_price'],
        orientation='h',
        marker_color=['#00ff00' if x > 0 else '#ff4b4b' for x in chart_df['net_oi']],
        name="Net Open Interest"
    ))

    fig.update_layout(
        template="plotly_dark",
        height=700,
        title=f"OI Magnets for {ticker} (Expiry: {nearest_expiry.date()})",
        xaxis_title="Net Open Interest (Proxy for Gamma)",
        yaxis_title="Strike Price"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data returned. Ensure you are using a major ticker like SPY or IWM.")
