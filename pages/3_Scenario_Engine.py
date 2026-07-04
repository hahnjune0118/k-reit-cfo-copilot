import streamlit as st

st.set_page_config(page_title="Scenario Engine", layout="wide")

st.title("3. Scenario Engine")
st.caption("Interest rate, rent, asset value, and tax-adjusted scenario analysis")

rate_shock = st.slider("Interest Rate Shock (bp)", -100, 200, 100, 50)
rent_change = st.slider("Rent Change (%)", -10, 10, 0, 1)
asset_value_change = st.slider("Asset Value Change (%)", -20, 10, -5, 1)
include_tax = st.checkbox("Include tax impact", value=True)

st.write("Selected Scenario")
st.json(
    {
        "interest_rate_shock_bp": rate_shock,
        "rent_change_percent": rent_change,
        "asset_value_change_percent": asset_value_change,
        "include_tax": include_tax,
    }
)