import numpy as np
import plotly.express as px
import streamlit as st

from modules.data_loader import load_all_data, reit_id_from_name, reit_options
from modules.risk_scoring import readiness_score
from modules.ui_components import hero, setup_page


setup_page(
    "6. Data Quality & AI Readiness",
    "Diagnose whether the client has the data foundation required for AX transformation",
)

data = load_all_data()
reits = data["reits"]
readiness = data["readiness"]
flags = data["flags"]

selected_name = st.sidebar.selectbox("REIT", reit_options(reits), index=0)
reit_id = reit_id_from_name(reits, selected_name)
reit_readiness = readiness[readiness["reit_id"] == reit_id].copy()
reit_flags = flags[flags["reit_id"] == reit_id].copy()
all_scores = readiness_score(readiness, flags).merge(reits[["reit_id", "reit_name"]], on="reit_id", how="left")
selected_score = readiness_score(reit_readiness, reit_flags)["ai_readiness_score"].iloc[0]

hero(
    "AX readiness diagnostic",
    f"{selected_name}: from reporting data to AI-enabled decision workflows",
    "The score evaluates whether the client has the structured data, standardized KPIs, scenario logic, "
    "tax-finance integration, and governance needed to scale AI-assisted CFO workflows.",
)

status = "Pilot ready" if selected_score >= 3.6 else "Foundation build required" if selected_score < 3.0 else "Targeted remediation"

cols = st.columns(4)
cols[0].metric("AI readiness score", f"{selected_score:.1f}/5", status)
cols[1].metric("Open flags", f"{len(reit_flags)}")
cols[2].metric("High-severity flags", f"{int((reit_flags['severity'] == 'High').sum())}")
cols[3].metric("Readiness dimensions", f"{len(reit_readiness)}")

left, right = st.columns([1.15, 1])

with left:
    st.subheader("Dimension Scorecard")
    fig = px.bar(
        reit_readiness.sort_values("score"),
        x="score",
        y="dimension",
        orientation="h",
        color="score",
        color_continuous_scale=["#c94f4f", "#b76e00", "#007c89"],
        range_x=[0, 5],
        labels={"score": "Score", "dimension": ""},
    )
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10), coloraxis_showscale=False)
    st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Peer Readiness")
    peer_fig = px.bar(
        all_scores.sort_values("ai_readiness_score"),
        x="ai_readiness_score",
        y="reit_name",
        orientation="h",
        color="ai_readiness_score",
        color_continuous_scale=["#c94f4f", "#b76e00", "#007c89"],
        range_x=[0, 5],
        labels={"ai_readiness_score": "AI readiness", "reit_name": ""},
    )
    peer_fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10), coloraxis_showscale=False)
    st.plotly_chart(peer_fig, width="stretch")

st.subheader("Readiness Roadmap")
roadmap = reit_readiness.copy()
roadmap["priority"] = np.select(
    [roadmap["score"] < 3.0, roadmap["score"] < 3.6],
    ["Immediate", "Near-term"],
    default="Scale",
)
st.dataframe(
    roadmap[["dimension", "score", "priority", "interpretation", "next_step"]].rename(
        columns={
            "dimension": "Dimension",
            "score": "Score",
            "priority": "Priority",
            "interpretation": "Interpretation",
            "next_step": "Next step",
        }
    ),
    width="stretch",
    hide_index=True,
)

if not reit_flags.empty:
    st.subheader("Disclosure Flags Feeding AI Readiness")
    st.dataframe(
        reit_flags[["area", "severity", "status", "decision_risk", "recommended_action"]].rename(
            columns={
                "area": "Area",
                "severity": "Severity",
                "status": "Status",
                "decision_risk": "Decision risk",
                "recommended_action": "Recommended action",
            }
        ),
        width="stretch",
        hide_index=True,
    )

