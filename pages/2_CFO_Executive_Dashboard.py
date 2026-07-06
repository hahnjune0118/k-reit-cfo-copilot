import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.data_loader import load_all_data, reit_id_from_name, reit_options
from modules.risk_scoring import attention_scores, debt_maturity_wall, score_assets, top_cfo_alerts
from modules.scenario_engine import run_scenario
from modules.ui_components import format_krw_bn, hero, is_real_api_mode, setup_page

try:
    import modules.real_mode_components as real_components
except Exception:
    real_components = None


def _real_component(name, fallback):
    return getattr(real_components, name, fallback) if real_components is not None else fallback


def _fallback_real_mode_warning(*args, **kwargs):
    st.warning(
        "Real API Mode는 OpenDART·ECOS 등 공개 API로 조회 가능한 사실 정보와 사용자가 직접 입력한 "
        "가정만을 기반으로 합니다. 본 화면은 실제 기업에 대한 투자 의견, 신용 판단, 부정적 리스크 평가를 "
        "제공하지 않습니다."
    )


def _fallback_select_real_reit(*args, **kwargs):
    st.sidebar.info("Real REIT 선택 컴포넌트를 불러오지 못해 fallback 값을 사용합니다.")
    return pd.Series({"real_reit_name": "선택 REIT", "ticker": "", "corp_code": "", "notes": ""})


def _fallback_real_reit_factual_panel(*args, **kwargs):
    st.info("Real REIT factual panel을 불러오지 못했습니다.")


def _fallback_empty_frame_component(message):
    def _inner(*args, **kwargs):
        st.info(message)
        return pd.DataFrame()

    return _inner


def _fallback_manual_scenario(*args, **kwargs):
    st.info("Real Mode manual scenario 컴포넌트를 불러오지 못했습니다.")
    return None


def _fallback_real_mode_cfo_interpretation(*args, **kwargs):
    st.info(
        "Real API Mode 해석 컴포넌트를 불러오지 못했습니다. "
        "공개 API 기반 factual data와 사용자 입력 기반 예비 시뮬레이션만 표시합니다."
    )


render_ecos_market_rate_panel = _real_component(
    "render_ecos_market_rate_panel", _fallback_empty_frame_component("ECOS 금리 데이터가 없거나 API fallback 상태입니다.")
)
render_opendart_disclosure_monitor = _real_component(
    "render_opendart_disclosure_monitor", _fallback_empty_frame_component("OpenDART Disclosure Monitor를 불러오지 못했습니다.")
)
render_real_mode_cfo_interpretation = _real_component(
    "render_real_mode_cfo_interpretation", _fallback_real_mode_cfo_interpretation
)
render_real_mode_manual_scenario = _real_component("render_real_mode_manual_scenario", _fallback_manual_scenario)
render_real_mode_warning = _real_component("render_real_mode_warning", _fallback_real_mode_warning)
render_real_reit_factual_panel = _real_component("render_real_reit_factual_panel", _fallback_real_reit_factual_panel)
select_real_reit = _real_component("select_real_reit", _fallback_select_real_reit)


LABEL_COLORS = {"Low": "#007c89", "Watch": "#b76e00", "High": "#c94f4f"}


def risk_badge(label: str) -> str:
    color = LABEL_COLORS.get(label, "#667085")
    return (
        f"<span style='background:{color}; color:#fff; padding:3px 9px; "
        f"border-radius:6px; font-size:0.78rem; font-weight:700;'>{label}</span>"
    )


def scenario_dividend_comparison(reit, assets, debt) -> pd.DataFrame:
    cases = [
        {"Scenario": "Base", "rate": 0, "rent": 0.0, "value": 0.0, "tax": 1.0},
        {"Scenario": "Rate +100bp", "rate": 100, "rent": 0.0, "value": 0.0, "tax": 1.0},
        {"Scenario": "Rent -5%", "rate": 0, "rent": -5.0, "value": 0.0, "tax": 1.0},
        {"Scenario": "Combined downside", "rate": 150, "rent": -5.0, "value": -10.0, "tax": 1.0},
    ]
    rows = []
    for case in cases:
        result = run_scenario(
            reit,
            assets,
            debt,
            rate_shock_bp=case["rate"],
            rent_change_pct=case["rent"],
            asset_value_change_pct=case["value"],
            tax_impact_pct=case["tax"],
        )
        rows.append(
            {
                "Scenario": case["Scenario"],
                "Dividend coverage": result["dividend_coverage"],
                "Dividend buffer": result["dividend_buffer_krw_bn"],
                "Refinancing Risk Score": result["refinancing_risk_score"],
            }
        )
    return pd.DataFrame(rows)


setup_page(
    "2. CFO Executive Dashboard",
    "CFO가 오늘 어디에 attention을 먼저 배분해야 하는지 보여주는 Dashboard",
)

if is_real_api_mode():
    hero(
        "Real API Mode",
        "공개 API 기반 factual executive view",
        "Real API Mode에서는 실제 상장 REIT에 sample Risk Score를 적용하지 않습니다. "
        "OpenDART 공시와 ECOS market rate 등 공개 API 기반 사실 정보만 표시합니다.",
    )
    render_real_mode_warning()
    real_reit = select_real_reit("Executive Real REIT 선택")
    render_real_reit_factual_panel(real_reit)
    disclosures = render_opendart_disclosure_monitor(real_reit)
    rates = render_ecos_market_rate_panel()
    scenario = render_real_mode_manual_scenario(real_reit)
    render_real_mode_cfo_interpretation(real_reit, disclosures=disclosures, rates=rates, scenario=scenario)
    st.info("CFO Alerts, Overall Risk Score, Dividend Sustainability Score는 Sample Mode 또는 사용자 입력 기반 Scenario에서만 제공합니다.")
    st.stop()

data = load_all_data()
reits = data["reits"]
assets = data["assets"]
debt = data["debt"]
flags = data["flags"]
readiness = data["readiness"]

selected_name = st.sidebar.selectbox("Portfolio 선택", reit_options(reits), index=0)
reit_id = reit_id_from_name(reits, selected_name)
reit = reits[reits["reit_id"] == reit_id].iloc[0]
reit_assets = assets[assets["reit_id"] == reit_id]
reit_debt = debt[debt["reit_id"] == reit_id]
reit_flags = flags[flags["reit_id"] == reit_id]
reit_readiness = readiness[readiness["reit_id"] == reit_id]

base = run_scenario(reit, reit_assets, reit_debt)
category_scores, overall = attention_scores(reit, reit_assets, reit_debt, reit_flags, reit_readiness)
alerts = top_cfo_alerts(category_scores)

hero(
    "Attention Allocation Dashboard",
    f"{selected_name}: CFO가 오늘 가장 먼저 확인해야 할 리스크",
    f"Management priority: {reit['management_priority']}. 이 Dashboard는 단순 데이터 표시가 아니라 "
    "Refinancing Risk, Dividend Sustainability, Asset Risk, Disclosure Quality, AI Readiness 중 "
    "어디에 CFO attention을 먼저 배분해야 하는지 보여줍니다.",
)

top_cols = st.columns(4)
top_cols[0].metric("Overall Risk Score", f"{overall['overall_score']:.0f}/100", overall["overall_label"])
top_cols[1].metric("Dividend coverage", f"{base['dividend_coverage']:.2f}x", base["dividend_status"])
top_cols[2].metric("Dividend buffer", format_krw_bn(base["dividend_buffer_krw_bn"], 1))
top_cols[3].metric("AI Readiness", f"{overall['ai_readiness_score']:.1f}/5", f"{overall['open_flags']} flags")

st.markdown(
    f"""
    <div class="consulting-hero">
        <div class="eyebrow">Overall CFO Signal</div>
        <div class="hero-title">현재 Overall Risk Label: {risk_badge(str(overall["overall_label"]))}</div>
        <div class="hero-body">
            Overall Risk Score는 refinancing, dividend, asset, disclosure, AI Readiness를 가중 평균한 attention allocation score입니다.
            점수가 높을수록 CFO가 오늘 먼저 확인해야 할 리스크입니다.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Risk Indicators")
indicator_cols = st.columns(5)
for col, (_, row) in zip(indicator_cols, category_scores.sort_values("category").iterrows()):
    with col:
        st.markdown(
            f"""
            <div class="signal-card">
                <div class="signal-label">{row['category']}</div>
                <div class="signal-value">{row['score']:.0f}/100</div>
                <div class="signal-detail">{risk_badge(row['label'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

left, right = st.columns([1.05, 1])

with left:
    st.subheader("Risk Score by Category")
    risk_fig = px.bar(
        category_scores.sort_values("score"),
        x="score",
        y="category",
        orientation="h",
        color="label",
        color_discrete_map=LABEL_COLORS,
        labels={"score": "Risk Score", "category": ""},
        text=category_scores.sort_values("score")["score"].round(0),
    )
    risk_fig.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10), showlegend=True)
    risk_fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(risk_fig, width="stretch")

with right:
    st.subheader("Dividend Sustainability Scenario Comparison")
    dividend_scenarios = scenario_dividend_comparison(reit, reit_assets, reit_debt)
    div_fig = go.Figure()
    div_fig.add_trace(
        go.Bar(
            x=dividend_scenarios["Scenario"],
            y=dividend_scenarios["Dividend buffer"],
            name="Dividend buffer",
            marker_color="#007c89",
            yaxis="y",
            text=dividend_scenarios["Dividend buffer"].round(1),
            textposition="outside",
        )
    )
    div_fig.add_trace(
        go.Scatter(
            x=dividend_scenarios["Scenario"],
            y=dividend_scenarios["Dividend coverage"],
            name="Dividend coverage",
            mode="lines+markers",
            marker_color="#c94f4f",
            yaxis="y2",
        )
    )
    div_fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis=dict(title="Dividend buffer (KRW bn)"),
        yaxis2=dict(title="Coverage (x)", overlaying="y", side="right", range=[0, max(1.4, dividend_scenarios["Dividend coverage"].max() + 0.1)]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    div_fig.add_hline(y=0, line_dash="dash", line_color="#667085")
    st.plotly_chart(div_fig, width="stretch")

st.subheader("Top 3 CFO Alerts")
for _, alert in alerts.iterrows():
    st.markdown(
        f"""
        <div class="consulting-hero">
            <div class="eyebrow">Alert #{int(alert['alert_rank'])} · {alert['category']} · {risk_badge(alert['label'])}</div>
            <div class="hero-title">CFO가 오늘 가장 먼저 확인해야 할 리스크</div>
            <div class="hero-body">
                <strong>왜 이 리스크가 중요한가</strong><br>{alert['why']}<br><br>
                <strong>권고 액션</strong><br>{alert['action']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

bottom_left, bottom_right = st.columns([1.15, 1])

with bottom_left:
    st.subheader("Debt Maturity Wall")
    wall = debt_maturity_wall(reit_debt)
    fig = px.bar(
        wall,
        x="maturity_year",
        y="principal_krw_bn",
        color_discrete_sequence=["#263b5e"],
        labels={"maturity_year": "Maturity year", "principal_krw_bn": "Principal (KRW bn)"},
        text="principal_krw_bn",
    )
    fig.update_layout(height=330, margin=dict(l=10, r=10, t=20, b=10))
    fig.update_traces(texttemplate="%{text:.0f}", textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, width="stretch")

with bottom_right:
    st.subheader("Asset & Disclosure Evidence")
    asset_scores = score_assets(reit_assets).head(3)
    attention = asset_scores[["asset_name", "risk_tier", "asset_risk_score"]].rename(
        columns={"asset_name": "Asset", "risk_tier": "Risk tier", "asset_risk_score": "Asset Risk Score"}
    )
    st.dataframe(attention, width="stretch", hide_index=True)
    if not reit_flags.empty:
        st.dataframe(
            reit_flags[["area", "severity", "recommended_action"]].rename(
                columns={"area": "공시 영역", "severity": "Severity", "recommended_action": "권고 Action"}
            ),
            width="stretch",
            hide_index=True,
        )
