import plotly.express as px
import streamlit as st

from modules.data_loader import load_all_data, reit_id_from_name, reit_options
from modules.risk_scoring import debt_maturity_wall, refinancing_risk_table, score_assets
from modules.ui_components import format_krw_bn, hero, setup_page


setup_page("4. Asset & Debt Risk", "Identify asset-level and debt maturity risk drivers")

data = load_all_data()
reits = data["reits"]
assets = data["assets"]
debt = data["debt"]
flags = data["flags"]

scope_options = ["All listed REITs"] + reit_options(reits)
scope = st.sidebar.selectbox("Scope", scope_options)

if scope == "All listed REITs":
    scope_reits = reits
    scope_assets = assets
    scope_debt = debt
    scope_flags = flags
    title_name = "listed K-REIT sample"
else:
    reit_id = reit_id_from_name(reits, scope)
    scope_reits = reits[reits["reit_id"] == reit_id]
    scope_assets = assets[assets["reit_id"] == reit_id]
    scope_debt = debt[debt["reit_id"] == reit_id]
    scope_flags = flags[flags["reit_id"] == reit_id]
    title_name = scope

hero(
    "Risk driver map",
    f"Asset and debt risk view for {title_name}",
    "This page ranks assets by operating risk and connects that view to maturity concentration, floating-rate "
    "exposure, and disclosure items that can affect investor confidence.",
)

refi = refinancing_risk_table(scope_reits, scope_debt)
total_debt = scope_debt["principal_krw_bn"].sum()
near_term = refi["near_term_debt_krw_bn"].sum()
avg_refi_score = refi["refinancing_risk_score"].mean()

cols = st.columns(4)
cols[0].metric("Debt in scope", format_krw_bn(total_debt, 0))
cols[1].metric("Near-term maturity", format_krw_bn(near_term, 0))
cols[2].metric("Avg refi risk", f"{avg_refi_score:.0f}/100")
cols[3].metric("Disclosure flags", f"{len(scope_flags)}")

left, right = st.columns([1.1, 1])

with left:
    st.subheader("Debt Maturity Wall")
    wall = debt_maturity_wall(scope_debt).merge(reits[["reit_id", "reit_name"]], on="reit_id", how="left")
    fig = px.bar(
        wall,
        x="maturity_year",
        y="principal_krw_bn",
        color="reit_name",
        barmode="stack",
        color_discrete_sequence=["#263b5e", "#007c89", "#b76e00", "#c94f4f"],
        labels={"maturity_year": "Maturity year", "principal_krw_bn": "Principal (KRW bn)", "reit_name": "REIT"},
    )
    fig.update_layout(height=400, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Refinancing Risk Ranking")
    st.dataframe(
        refi[
            [
                "reit_name",
                "risk_tier",
                "refinancing_risk_score",
                "near_term_debt_pct",
                "floating_rate_pct",
                "weighted_coupon_pct",
                "ltv_pct",
            ]
        ].rename(
            columns={
                "reit_name": "REIT",
                "risk_tier": "Risk",
                "refinancing_risk_score": "Score",
                "near_term_debt_pct": "Near-term %",
                "floating_rate_pct": "Floating %",
                "weighted_coupon_pct": "Coupon %",
                "ltv_pct": "LTV %",
            }
        ),
        width="stretch",
        hide_index=True,
    )

asset_scores = score_assets(scope_assets).merge(reits[["reit_id", "reit_name"]], on="reit_id", how="left")

st.subheader("Asset Risk Ranking")
asset_chart = px.scatter(
    asset_scores,
    x="wale_years",
    y="asset_risk_score",
    size="asset_value_krw_bn",
    color="risk_tier",
    hover_name="asset_name",
    hover_data=["reit_name", "sector", "occupancy_pct", "top_tenant_share_pct", "capex_need_pct"],
    color_discrete_map={"High": "#c94f4f", "Medium": "#b76e00", "Low": "#007c89"},
    labels={"wale_years": "WALE (years)", "asset_risk_score": "Asset risk score"},
)
asset_chart.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(asset_chart, width="stretch")

st.dataframe(
    asset_scores[
        [
            "reit_name",
            "asset_name",
            "sector",
            "location",
            "asset_value_krw_bn",
            "occupancy_pct",
            "wale_years",
            "top_tenant_share_pct",
            "capex_need_pct",
            "risk_tier",
            "asset_risk_score",
            "strategic_importance",
        ]
    ].rename(
        columns={
            "reit_name": "REIT",
            "asset_name": "Asset",
            "asset_value_krw_bn": "Value KRW bn",
            "occupancy_pct": "Occupancy %",
            "wale_years": "WALE",
            "top_tenant_share_pct": "Top tenant %",
            "capex_need_pct": "Capex need %",
            "risk_tier": "Risk",
            "asset_risk_score": "Score",
            "strategic_importance": "Strategic note",
        }
    ),
    width="stretch",
    hide_index=True,
)

if not scope_flags.empty:
    st.subheader("Disclosure Flags Affecting Risk Narrative")
    st.dataframe(
        scope_flags[["area", "flag", "severity", "decision_risk", "recommended_action"]].rename(
            columns={
                "area": "Area",
                "flag": "Flag",
                "severity": "Severity",
                "decision_risk": "Decision risk",
                "recommended_action": "Recommended action",
            }
        ),
        width="stretch",
        hide_index=True,
    )

