import pandas as pd
import plotly.express as px
import streamlit as st

from modules.ui_components import hero, setup_page, signal_card


setup_page(
    "1. 고객 Pain Point",
    "fragmented REIT data를 CFO-level decision intelligence로 전환",
)

hero(
    "Customer problem first",
    "이 앱은 회계 담당자용 내부 자동화가 아니라 client-facing AX prototype입니다",
    "상장 REIT CFO, AMC, IR팀이 겪는 capital-market pressure, dividend credibility, "
    "asset-level evidence, tax leakage, disclosure quality, AI Readiness 문제를 decision support 관점에서 정리합니다.",
)

pain_points = pd.DataFrame(
    [
        {
            "고객 Pain Point": "DART, IR deck, Excel, 내부 시스템에 데이터가 분산",
            "Business Risk": "리스크 인지 지연",
            "Copilot Response": "통합 CFO risk cockpit",
            "Business Impact": "경영진 attention allocation 속도 개선",
        },
        {
            "고객 Pain Point": "차입 만기와 금리 exposure가 별도 관리",
            "Business Risk": "refinancing risk 설명 지연",
            "Copilot Response": "debt maturity 및 rate stress monitor",
            "Business Impact": "lender 협의와 market-window 계획 조기화",
        },
        {
            "고객 Pain Point": "배당 지속 가능성 분석이 수작업 scenario에 의존",
            "Business Risk": "dividend credibility risk",
            "Copilot Response": "tax-adjusted dividend coverage score",
            "Business Impact": "board 및 investor guidance 신뢰도 개선",
        },
        {
            "고객 Pain Point": "세금 영향이 capital allocation 의사결정에 내재화되지 않음",
            "Business Risk": "hold/sell/refinance 판단에서 tax leakage 누락",
            "Copilot Response": "tax-adjusted Scenario Engine",
            "Business Impact": "세후 cash-flow 가시성 개선",
        },
        {
            "고객 Pain Point": "Investor Q&A 답변이 반복적이고 수작업 중심",
            "Business Risk": "투자자 communication 일관성 저하",
            "Copilot Response": "rule-based Memo 및 Q&A generator",
            "Business Impact": "management narrative consistency 강화",
        },
        {
            "고객 Pain Point": "공시 Data Quality 점검이 수작업으로 수행",
            "Business Risk": "governance 및 AI Readiness gap",
            "Copilot Response": "disclosure flags 및 AI Readiness diagnostics",
            "Business Impact": "AX transformation roadmap 구체화",
        },
        {
            "고객 Pain Point": "시장에 이슈가 보인 뒤에야 리스크 signal이 escalation",
            "Business Risk": "maturity, valuation, disclosure risk 대응 지연",
            "Copilot Response": "CFO early-warning cockpit",
            "Business Impact": "cross-functional response planning 조기화",
        },
    ]
)

st.subheader("Pain Point to Decision Outcome Map")
st.dataframe(pain_points, width="stretch", hide_index=True)

stakeholder_view = pd.DataFrame(
    [
        {"Stakeholder": "CFO", "Pain area": "배당 신뢰도", "Urgency": 92, "Current friction": 84},
        {"Stakeholder": "CFO", "Pain area": "refinancing planning", "Urgency": 95, "Current friction": 88},
        {"Stakeholder": "AMC", "Pain area": "asset-level evidence", "Urgency": 82, "Current friction": 76},
        {"Stakeholder": "AMC", "Pain area": "tax-aware hold/sell view", "Urgency": 78, "Current friction": 72},
        {"Stakeholder": "IR", "Pain area": "Investor Q&A consistency", "Urgency": 86, "Current friction": 80},
        {"Stakeholder": "IR", "Pain area": "disclosure quality", "Urgency": 81, "Current friction": 74},
        {"Stakeholder": "CFO", "Pain area": "early warning indicators", "Urgency": 88, "Current friction": 79},
        {"Stakeholder": "AMC", "Pain area": "control-ready AI adoption", "Urgency": 80, "Current friction": 75},
    ]
)

left, right = st.columns([1.2, 1])

with left:
    fig = px.bar(
        stakeholder_view,
        x="Urgency",
        y="Pain area",
        color="Stakeholder",
        orientation="h",
        color_discrete_map={"CFO": "#263b5e", "AMC": "#007c89", "IR": "#b76e00"},
        labels={"Pain area": "", "Urgency": "Decision urgency"},
    )
    fig.update_layout(height=390, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Consulting Narrative")
    signal_card(
        "CFO",
        "capital markets pressure",
        "refinancing exposure, dividend capacity, cash-flow sensitivity를 한 화면에서 판단해야 합니다.",
    )
    signal_card(
        "AMC",
        "asset evidence gap",
        "occupancy, WALE, tenant, capex, valuation을 asset Risk Score로 연결해야 합니다.",
    )
    signal_card(
        "IR",
        "narrative consistency",
        "approved metric과 disclosure flag에 기반한 반복 가능한 Investor Q&A가 필요합니다.",
    )
