import plotly.express as px
import streamlit as st

from modules.data_loader import load_all_data
from modules.risk_scoring import executive_signal_table
from modules.ui_components import format_krw_bn, hero, is_real_api_mode, setup_page, signal_card

try:
    from modules.real_data_loader import load_real_reit_master
except Exception:
    def load_real_reit_master():
        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "real_reit_name": "Real REIT fallback",
                    "ticker": "",
                    "corp_code": "",
                    "notes": "real_data_loader module is unavailable.",
                }
            ]
        )

try:
    import modules.real_mode_components as real_components
except Exception:
    real_components = None


def _real_component(name, fallback):
    return getattr(real_components, name, fallback) if real_components is not None else fallback


def _fallback_real_mode_warning(*args, **kwargs):
    st.warning(
        "Real API Mode는 공개 API factual data와 사용자 입력 가정만 표시합니다. "
        "투자 의견, 신용 판단, 부정적 리스크 평가는 제공하지 않습니다."
    )


def _fallback_select_real_reit(*args, **kwargs):
    import pandas as pd

    st.sidebar.info("Real REIT 선택 컴포넌트를 불러오지 못해 fallback 값을 사용합니다.")
    return pd.Series({"real_reit_name": "선택 REIT", "ticker": "", "corp_code": "", "notes": ""})


def _fallback_real_reit_factual_panel(*args, **kwargs):
    st.info("Real REIT factual panel을 불러오지 못했습니다.")


def _fallback_ecos_market_rate_panel(*args, **kwargs):
    import pandas as pd

    st.info("ECOS Market Rate Panel을 불러오지 못했습니다.")
    return pd.DataFrame()


def _fallback_real_mode_cfo_interpretation(*args, **kwargs):
    st.info(
        "Real API Mode 해석 컴포넌트를 불러오지 못했습니다. "
        "공개 API 기반 factual data와 사용자 입력 기반 예비 시뮬레이션만 표시합니다."
    )


render_ecos_market_rate_panel = _real_component("render_ecos_market_rate_panel", _fallback_ecos_market_rate_panel)
render_real_mode_cfo_interpretation = _real_component(
    "render_real_mode_cfo_interpretation", _fallback_real_mode_cfo_interpretation
)
render_real_mode_warning = _real_component("render_real_mode_warning", _fallback_real_mode_warning)
render_real_reit_factual_panel = _real_component("render_real_reit_factual_panel", _fallback_real_reit_factual_panel)
select_real_reit = _real_component("select_real_reit", _fallback_select_real_reit)


setup_page(
    "K-REIT CFO Copilot",
    "상장 REIT CFO, AMC, IR팀을 위한 rule-based AX decision support prototype",
)

data = load_all_data()
signals = executive_signal_table(
    data["reits"],
    data["assets"],
    data["debt"],
    data["readiness"],
    data["flags"],
)

hero(
    "client-facing AX prototype",
    "금리, 차입, 자산, 세금, 배당, 공시 품질 리스크를 하나의 Dashboard로 연결",
    "K-REIT CFO Copilot은 상장 리츠 CFO, AMC, IR팀이 fragmented portfolio data를 "
    "Scenario Engine, CFO briefing memo, Investor Q&A, AI Readiness 진단으로 전환하도록 설계된 "
    "rule-based consulting-style decision intelligence prototype입니다.",
)

if is_real_api_mode():
    render_real_mode_warning()
    real_reit = select_real_reit("Landing Real REIT 선택")
    render_real_reit_factual_panel(real_reit)
    rates = render_ecos_market_rate_panel()
    render_real_mode_cfo_interpretation(real_reit, rates=rates)

    st.subheader("Real REIT API Mode Coverage")
    real_master = load_real_reit_master()
    st.dataframe(
        real_master.rename(
            columns={
                "real_reit_name": "Real REIT",
                "ticker": "Ticker",
                "corp_code": "OpenDART corp_code",
                "notes": "Notes",
            }
        ),
        width="stretch",
        hide_index=True,
    )
    st.info("Real API Mode에서는 sample Risk Score나 sample disclosure flags를 실제 REIT에 적용하지 않습니다.")
    st.stop()

col1, col2, col3 = st.columns(3)
with col1:
    signal_card(
        "고객 Pain Point",
        "분산된 의사결정",
        "차입, 자산, 세금, 배당, 공시 품질 데이터가 여러 파일과 보고서에 흩어져 있습니다.",
    )
with col2:
    signal_card(
        "Copilot Lens",
        "CFO action cockpit",
        "refinancing risk, dividend sustainability, Data Quality를 하나의 decision model로 연결합니다.",
    )
with col3:
    signal_card(
        "Business Impact",
        "보고와 커뮤니케이션 연결",
        "Scenario 결과를 CFO Memo, Investor Q&A, AX readiness roadmap으로 전환합니다.",
    )

st.subheader("Portfolio Signal Snapshot")

metric_cols = st.columns(4)
metric_cols[0].metric("Sample 상장 REIT", f"{len(data['reits'])}개")
metric_cols[1].metric("Gross asset value", format_krw_bn(data["reits"]["gross_asset_value_krw_bn"].sum()))
metric_cols[2].metric("Debt facility", f"{len(data['debt'])}건")
metric_cols[3].metric("Disclosure flags", f"{len(data['flags'])}건")

chart_col, table_col = st.columns([1.25, 1])

with chart_col:
    fig = px.bar(
        signals,
        x="reit_name",
        y="refinancing_risk_score",
        color="risk_tier",
        color_discrete_map={"High": "#c94f4f", "Medium": "#b76e00", "Low": "#007c89"},
        labels={"reit_name": "", "refinancing_risk_score": "Refinancing Risk Score"},
        text=signals["refinancing_risk_score"].round(0),
    )
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=20, b=10), showlegend=True)
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, width="stretch")

with table_col:
    st.dataframe(
        signals[
            [
                "reit_name",
                "dividend_status",
                "dividend_coverage",
                "refinancing_risk_score",
                "ai_readiness_score",
                "open_flags",
            ]
        ].rename(
            columns={
                "reit_name": "REIT",
                "dividend_status": "배당 상태",
                "dividend_coverage": "Coverage",
                "refinancing_risk_score": "Refi Risk",
                "ai_readiness_score": "AI Readiness",
                "open_flags": "Flags",
            }
        ),
        width="stretch",
        hide_index=True,
    )

st.subheader("Six Dashboard Modules")

modules = [
    {
        "Module": "고객 Pain Point",
        "핵심 질문": "CFO, AMC, IR팀의 업무 pain point는 어디에서 발생하는가?",
        "주요 Output": "Pain point와 business impact map",
    },
    {
        "Module": "CFO Executive Dashboard",
        "핵심 질문": "CFO가 지금 봐야 할 리스크 signal은 무엇인가?",
        "주요 Output": "배당, refinancing, AI Readiness, disclosure cockpit",
    },
    {
        "Module": "Scenario Engine",
        "핵심 질문": "금리, rent, asset value, tax impact가 cash flow를 어떻게 바꾸는가?",
        "주요 Output": "tax-adjusted cash flow 및 dividend coverage bridge",
    },
    {
        "Module": "자산 및 차입 리스크",
        "핵심 질문": "어떤 asset과 maturity가 리스크를 주도하는가?",
        "주요 Output": "asset Risk Score ranking 및 debt maturity wall",
    },
    {
        "Module": "AI Memo & Investor Q&A",
        "핵심 질문": "숫자를 어떤 management narrative로 설명할 것인가?",
        "주요 Output": "rule-based CFO Memo 및 Investor Q&A draft",
    },
    {
        "Module": "데이터 품질 및 AI Readiness",
        "핵심 질문": "AI-enabled reporting을 확장할 데이터 기반이 준비되어 있는가?",
        "주요 Output": "Data Quality 진단 및 AX readiness roadmap",
    },
]

st.dataframe(modules, width="stretch", hide_index=True)
