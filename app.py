import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# --- CONFIG ---
API_KEY = "gmvrvccr1cM5002CHvRk1GalZ_okbdrI"
BASE_URL = "https://api.massive.com/v3/snapshot/options/"

st.set_page_config(page_title="GEX Advisor Pro", layout="wide")

# --- UI STYLING (FIXED ERROR HERE) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    .stMetric { background-color: #1c2128; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR SCANNER ---
st.sidebar.header("🎯 GEX SCANNER")
watchlist_input = st.sidebar.text_input("Watchlist (comma separated)", value="IWM, SPY, QQQ, TSLA")
watchlist = [t.strip().upper() for t in watchlist_input.split(',')]
ticker = st.sidebar.selectbox("SELECT FOCUS TICKER", watchlist)

def fetch_gex_data(symbol):
    try:
        url = f"{BASE_URL}{symbol}?apiKey={API_KEY}"
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None, None
        data = response.json()
        return pd.DataFrame(data.get('results', [])), data.get('underlying_price', 0)
    except:
        return None, None

# Run Scanner Logic
scanner_results = []
for t in watchlist:
    raw_df, spot = fetch_gex_data(t)
    if raw_df is not None and not raw_df.empty:
        # Calculate Net Gamma
        raw_df['calc_gex'] = raw_df.apply(lambda x: (x['gamma'] * x['open_interest'] * 100) if x['contract_type'] == 'call' else -(x['gamma'] * x['open_interest'] * 100), axis=1)
        total_net_gex = raw_df['calc_gex'].sum()
        regime = "Positive 🟢" if total_net_gex > 0 else "Negative 🔴"
        scanner_results.append({"Ticker": t, "Net GEX": f"${total_net_gex:,.0f}", "Regime": regime})

if scanner_results:
    st.sidebar.table(pd.DataFrame(scanner_results))

# --- MAIN CHART LOGIC ---
st.title(f"📊 {ticker} Exposure Profile")

df, spot_price = fetch_gex_data(ticker)

if df is not None and not df.empty:
    df['gex_val'] = df.apply(lambda x: (x['gamma'] * x['open_interest'] * 100) if x['contract_type'] == 'call' else -(x['gamma'] * x['open_interest'] * 100), axis=1)
    chart_df = df.groupby('strike_price')['gex_val'].sum().reset_index()
    
    # Filter for strikes near spot
    chart_df = chart_df[(chart_df['strike_price'] > spot_price * 0.95) & (chart_df['strike_price'] < spot_price * 1.05)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_df['gex_val'],
        y=chart_df['strike_price'],
        orientation='h',
        marker_color=['#00ff00' if x > 0 else '#ff4b4b' for x in chart_df['gex_val']],
    ))

    fig.add_hline(y=spot_price, line_dash="dash", line_color="#58a6ff", 
                 annotation_text=f"SPOT: {spot_price}", annotation_position="top right")

    fig.update_layout(template="plotly_dark", height=700)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Data load failed. Please check your API key or Ticker.")
