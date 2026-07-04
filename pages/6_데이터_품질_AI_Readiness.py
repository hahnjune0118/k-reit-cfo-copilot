import numpy as np
import plotly.express as px
import streamlit as st

from modules.data_loader import load_all_data, reit_id_from_name, reit_options
from modules.risk_scoring import readiness_score
from modules.ui_components import hero, setup_page


setup_page(
    "6. 데이터 품질 및 AI Readiness",
    "AX transformation을 위한 Data Quality와 AI Readiness 진단",
)

data = load_all_data()
reits = data["reits"]
readiness = data["readiness"]
flags = data["flags"]

selected_name = st.sidebar.selectbox("REIT 선택", reit_options(reits), index=0)
reit_id = reit_id_from_name(reits, selected_name)
reit_readiness = readiness[readiness["reit_id"] == reit_id].copy()
reit_flags = flags[flags["reit_id"] == reit_id].copy()
all_scores = readiness_score(readiness, flags).merge(reits[["reit_id", "reit_name"]], on="reit_id", how="left")
selected_score = readiness_score(reit_readiness, reit_flags)["ai_readiness_score"].iloc[0]

hero(
    "AI Readiness diagnostic",
    f"{selected_name}: reporting data에서 AI-enabled decision workflow로",
    "AI Readiness score는 structured data, KPI standardization, scenario logic, tax-finance integration, "
    "governance 수준을 평가합니다.",
)

status = "Pilot ready" if selected_score >= 3.6 else "기반 정비 필요" if selected_score < 3.0 else "Targeted remediation"

cols = st.columns(4)
cols[0].metric("AI Readiness Score", f"{selected_score:.1f}/5", status)
cols[1].metric("Open flags", f"{len(reit_flags)}건")
cols[2].metric("High-severity flags", f"{int((reit_flags['severity'] == 'High').sum())}건")
cols[3].metric("Readiness dimensions", f"{len(reit_readiness)}개")

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
    st.subheader("Peer AI Readiness")
    peer_fig = px.bar(
        all_scores.sort_values("ai_readiness_score"),
        x="ai_readiness_score",
        y="reit_name",
        orientation="h",
        color="ai_readiness_score",
        color_continuous_scale=["#c94f4f", "#b76e00", "#007c89"],
        range_x=[0, 5],
        labels={"ai_readiness_score": "AI Readiness", "reit_name": ""},
    )
    peer_fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10), coloraxis_showscale=False)
    st.plotly_chart(peer_fig, width="stretch")

st.subheader("AI Readiness Roadmap")
roadmap = reit_readiness.copy()
roadmap["priority"] = np.select(
    [roadmap["score"] < 3.0, roadmap["score"] < 3.6],
    ["Immediate", "Near-term"],
    default="Scale",
)
st.dataframe(
    roadmap[["dimension", "score", "priority", "interpretation", "next_step"]].rename(
        columns={
            "dimension": "진단 영역",
            "score": "Score",
            "priority": "Priority",
            "interpretation": "해석",
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
                "area": "공시 영역",
                "severity": "Severity",
                "status": "Status",
                "decision_risk": "의사결정 리스크",
                "recommended_action": "권고 Action",
            }
        ),
        width="stretch",
        hide_index=True,
    )
