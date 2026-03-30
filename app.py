import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# --- CONFIG ---
# Direct key for initial setup (Note: In a final version, use st.secrets for security)
API_KEY = "gmvrvccr1cM5002CHvRk1GalZ_okbdrI"
BASE_URL = "https://api.massive.com/v3/snapshot/options/"

st.set_page_config(page_title="GEX Advisor Pro", layout="wide")

# Custom CSS for that 'Dark Pro' look
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stTextInput > div > div > input { color: #00ff00; }
    </style>
    """, unsafe_allow_case_with_distinction=True)

ticker = st.sidebar.text_input("ENTER TICKER", value="IWM").upper()

def fetch_gex(symbol):
    url = f"{BASE_URL}{symbol}?apiKey={API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        return None, None
    
    data = response.json()
    results = data.get('results', [])
    spot = data.get('underlying_price', 0)
    
    records = []
    for opt in results:
        gamma = opt.get('gamma', 0)
        oi = opt.get('open_interest', 0)
        strike = opt.get('strike_price')
        # Calculate GEX: Gamma * OI * 100 (contract multiplier)
        val = gamma * oi * 100
        if opt.get('contract_type') == 'put':
            val *= -1
        records.append({'strike': strike, 'gex': val})
    
    return pd.DataFrame(records), spot

try:
    df, spot_price = fetch_gex(ticker)
    if df is not None:
        # Group by strike to get Net GEX
        final_df = df.groupby('strike')['gex'].sum().reset_index()
        
        # Filter for strikes near the money for a cleaner chart
        final_df = final_df[(final_df['strike'] > spot_price * 0.9) & (final_df['strike'] < spot_price * 1.1)]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=final_df['gex'],
            y=final_df['strike'],
            orientation='h',
            marker_color=['#00ff00' if x > 0 else '#ff0000' for x in final_df['gex']],
            name="Net Gamma"
        ))

        # Spot Price Line
        fig.add_hline(y=spot_price, line_dash="dash", line_color="cyan", 
                     annotation_text=f"SPOT: {spot_price}", annotation_position="top right")

        fig.update_layout(
            title=f"<b>{ticker} TOTAL GAMMA EXPOSURE</b>",
            template="plotly_dark",
            height=800,
            xaxis_title="Gamma Exposure ($)",
            yaxis_title="Strike Price",
            bargap=0.1
        )
        st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.error("Connecting to Massive.com... Ensure ticker is valid.")
