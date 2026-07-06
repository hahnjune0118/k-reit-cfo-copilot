import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.data_loader import load_all_data, load_market_rate_data, reit_id_from_name, reit_options
from modules.real_reit_analytics import build_real_reit_dashboard_model
from modules.scenario_engine import (
    cfo_interpretation,
    run_peer_scenarios,
    run_scenario,
    scenario_summary_table,
    scenario_waterfall,
)
from modules.ui_components import format_krw, format_krw_bn, format_pct, get_real_mode_user_inputs, hero, is_real_api_mode, setup_page

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


def _format_summary_value(value: float, unit: str) -> str:
    if unit in {"KRW_BN", "원"}:
        return format_krw_bn(value, 1)
    if unit == "%":
        return format_pct(value, 1)
    if unit == "score":
        return f"{value:,.0f}/100"
    return f"{value:,.1f}"


setup_page(
    "3. Scenario Engine",
    "금리, 임대료, 자산가치, 세금효과 변화가 배당가능성과 refinancing risk에 미치는 영향",
)

if is_real_api_mode():
    hero(
        "v12 Real Scenario Engine",
        "금리, credit spread, refinancing pressure가 배당 buffer와 risk migration으로 이어지는 CFO decision view",
        "Base Case, Rate +50bp, Rate +100bp, Credit Spread +50bp, Combined Stress, Downside Macro, Upside Macro를 기본 case로 제공합니다. 수동 slider는 advanced override로만 사용합니다.",
    )
    real_reit = select_real_reit("Real REIT 선택")
    model = build_real_reit_dashboard_model(real_reit, get_real_mode_user_inputs())
    metrics = model["metrics"]
    scenario_outputs = model["scenario_outputs"].copy()

    top_cols = st.columns(4)
    top_cols[0].metric("선택 REIT", model["profile"].get("real_reit_name", "선택 REIT"))
    top_cols[1].metric("Base Rate", "데이터 미확보" if metrics.get("base_rate_pct") is None else f"{float(metrics['base_rate_pct']):.2f}%")
    top_cols[2].metric("Refinancing Rate", "데이터 미확보" if metrics.get("refinancing_rate_pct") is None else f"{float(metrics['refinancing_rate_pct']):.2f}%")
    top_cols[3].metric("Risk Score Type", model["risk_model"].get("score_type", "Limited"))

    st.subheader("Scenario Summary Table")
    display = scenario_outputs.copy()
    for column in ["Scenario 기준금리", "Refinancing rate impact", "LTV sensitivity", "Risk score migration"]:
        if column in display.columns:
            display[column] = display[column].map(lambda value: "데이터 미확보" if pd.isna(value) else f"{float(value):.2f}")
    for column in ["Interest expense impact", "Dividend buffer impact"]:
        if column in display.columns:
            display[column] = display[column].map(format_krw)
    st.dataframe(display, width="stretch", hide_index=True)

    chart_df = model["scenario_outputs"].copy()
    left, right = st.columns(2)
    with left:
        st.subheader("Dividend Buffer Impact")
        if not chart_df.empty and chart_df["Dividend buffer impact"].notna().any():
            fig = px.bar(chart_df, x="Scenario", y="Dividend buffer impact", color="Scenario", labels={"Dividend buffer impact": "Dividend buffer impact"})
            fig.update_layout(height=330, margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Dividend buffer는 OpenDART/공시 parser에서 확보된 NOI proxy와 배당금이 부족하면 산출이 제한됩니다.")
    with right:
        st.subheader("Risk Score Migration")
        if not chart_df.empty and chart_df["Risk score migration"].notna().any():
            fig = px.line(chart_df, x="Scenario", y="Risk score migration", markers=True, labels={"Risk score migration": "Risk Score"})
            fig.update_layout(height=330, margin=dict(l=10, r=10, t=20, b=10), yaxis=dict(range=[0, 100]))
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("Risk score migration은 산출 가능한 component가 부족하면 제한됩니다.")

    st.subheader("CFO Interpretation")
    st.markdown(
        """
        - **핵심 변화**: 금리와 spread 상승은 interest expense impact와 refinancing rate impact를 통해 배당 buffer를 압박할 수 있습니다.
        - **재무적 영향**: 현재 결과는 공개 API, 공시 parser, macro proxy, 사용자 보완값을 구분해 계산한 MVP 수준의 예비 시뮬레이션입니다.
        - **CFO가 확인해야 할 사항**: FFO/AFFO bridge, 실제 차입 만기표, 변동금리 비중, hedge 조건, 세금효과는 내부 자료로 검증해야 합니다.
        """
    )

    with st.expander("Advanced manual override", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.slider("추가 금리 충격 (bp)", -50, 200, 50, 25, key="v12_manual_rate_shock")
        with col2:
            st.slider("임대료 변화율 (%)", -10.0, 10.0, 0.0, 0.5, key="v12_manual_rent_change")
        with col3:
            st.slider("자산가치 변화율 (%)", -20.0, 10.0, 0.0, 0.5, key="v12_manual_asset_change")
        with col4:
            st.checkbox("세금효과 반영 여부", value=True, key="v12_manual_tax_toggle")
        st.caption("Advanced override는 사용자 입력 기반 예비 sensitivity입니다. Real API Mode의 source-tagged factual data와 구분해서 해석해야 합니다.")

    render_real_mode_cfo_interpretation(real_reit, scenario=scenario_outputs)
    st.stop()

data = load_all_data()
market_rates = load_market_rate_data(use_api=True)
reits = data["reits"]
assets = data["assets"]
debt = data["debt"]
latest_market_rate = market_rates.sort_values("date").iloc[-1]
base_market_rate = float(latest_market_rate["market_rate_pct"])
rate_source = market_rates.attrs.get("source", "sample")
rate_status_message = market_rates.attrs.get("status_message", "")
rate_fallback = bool(market_rates.attrs.get("is_fallback", True))

selected_name = st.sidebar.selectbox("REIT 선택", reit_options(reits), index=0)
reit_id = reit_id_from_name(reits, selected_name)
reit = reits[reits["reit_id"] == reit_id].iloc[0]
reit_assets = assets[assets["reit_id"] == reit_id]
reit_debt = debt[debt["reit_id"] == reit_id]

hero(
    "Scenario Engine",
    "CFO decision support를 위한 scenario-adjusted metrics",
    "이 화면은 금리, 임대료, 자산가치, 세금효과 변화가 dividend buffer와 refinancing risk에 어떤 영향을 주는지 "
    "간단하고 투명한 MVP 계산 방식으로 보여줍니다.",
)

st.subheader("Market Rate Assumption")
rate_cols = st.columns(3)
rate_cols[0].metric("Base market rate", format_pct(base_market_rate), rate_source)
rate_cols[1].metric("ECOS 연결 상태", "Sample fallback" if rate_fallback else "Connected")
rate_cols[2].metric("Scenario rate", format_pct(base_market_rate + 1.0), "slider 적용 전 예시 +100bp")
st.caption(
    f"Scenario Engine은 ECOS API에서 시장금리 데이터를 가져오려고 시도합니다. "
    f"현재 기준 데이터는 {'sample/default data' if rate_fallback else 'real ECOS API data'}입니다. {rate_status_message}"
)

st.subheader("Scenario Assumptions")
col1, col2, col3, col4 = st.columns(4)
with col1:
    rate_shock = st.slider("금리 충격 (bp)", -50, 200, 100, 25)
with col2:
    rent_change = st.slider("임대료 변화율 (%)", -10.0, 10.0, -2.0, 0.5)
with col3:
    asset_value_change = st.slider("자산가치 변화율 (%)", -20.0, 10.0, -5.0, 0.5)
with col4:
    include_tax_effect = st.checkbox("세금효과 반영 여부", value=True)

tax_impact = 1.0 if include_tax_effect else 0.0
base_case = run_scenario(
    reit,
    reit_assets,
    reit_debt,
    rate_shock_bp=0,
    rent_change_pct=0.0,
    asset_value_change_pct=0.0,
    tax_impact_pct=tax_impact,
    base_market_rate_pct=base_market_rate,
)
scenario = run_scenario(
    reit,
    reit_assets,
    reit_debt,
    rate_shock_bp=rate_shock,
    rent_change_pct=rent_change,
    asset_value_change_pct=asset_value_change,
    tax_impact_pct=tax_impact,
    base_market_rate_pct=base_market_rate,
)

st.caption(
    "MVP 계산 가정: 세금효과를 반영하면 scenario-adjusted NOI의 1.0%를 tax drag로 차감합니다. "
    "AFFO estimate는 FFO estimate에서 maintenance capex reserve와 tax drag를 차감한 단순 추정치입니다."
)

metric_cols = st.columns(4)
metric_cols[0].metric("Scenario-adjusted NOI", format_krw_bn(scenario["scenario_adjusted_noi_krw_bn"], 1))
metric_cols[1].metric("Interest expense impact", format_krw_bn(scenario["interest_expense_impact_krw_bn"], 1))
metric_cols[2].metric("FFO estimate", format_krw_bn(scenario["ffo_estimate_krw_bn"], 1))
metric_cols[3].metric("AFFO estimate", format_krw_bn(scenario["affo_estimate_krw_bn"], 1))

metric_cols = st.columns(4)
metric_cols[0].metric("Scenario market rate", format_pct(scenario["scenario_market_rate_pct"]), f"{scenario['effective_rate_shock_bp']:+.0f}bp effective shock")
metric_cols[1].metric("LTV change", f"{scenario['ltv_change_pctp']:+.1f}p", format_pct(scenario["stressed_ltv_pct"]))
metric_cols[2].metric("Dividend buffer", format_krw_bn(scenario["dividend_buffer_krw_bn"], 1), scenario["dividend_status"])
metric_cols[3].metric(
    "Refinancing risk level",
    scenario["refinancing_status"],
    f"Risk Score {scenario['refinancing_risk_score']:.0f}/100",
)

st.subheader("Scenario Summary Table")
summary = scenario_summary_table(base_case, scenario)
summary_display = summary.copy()
for column in ["Base", "Scenario", "Change"]:
    summary_display[column] = summary_display.apply(
        lambda row: _format_summary_value(row[column], row["Unit"]),
        axis=1,
    )
summary_display["Unit"] = summary_display["Unit"].replace({"KRW_BN": "원"})
st.dataframe(
    summary_display.rename(
        columns={
            "Metric": "Metric",
            "Base": "Base case",
            "Scenario": "Scenario case",
            "Change": "Change",
            "Unit": "Unit",
        }
    ),
    width="stretch",
    hide_index=True,
)

chart_left, chart_right = st.columns(2)

with chart_left:
    st.subheader("Dividend Buffer Impact")
    buffer_chart = pd.DataFrame(
        [
            {"Case": "Base", "Dividend buffer": base_case["dividend_buffer_krw_bn"]},
            {"Case": "Scenario", "Dividend buffer": scenario["dividend_buffer_krw_bn"]},
        ]
    )
    fig = px.bar(
        buffer_chart,
        x="Case",
        y="Dividend buffer",
        color="Case",
        text=buffer_chart["Dividend buffer"].map(format_krw_bn),
        color_discrete_map={"Base": "#263b5e", "Scenario": "#007c89"},
        labels={"Dividend buffer": "Dividend buffer"},
    )
    fig.add_hline(y=0, line_dash="dash", line_color="#667085")
    fig.update_layout(height=370, margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
    fig.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, width="stretch")

with chart_right:
    st.subheader("LTV Impact")
    ltv_chart = pd.DataFrame(
        [
            {"Case": "Base", "LTV": base_case["base_ltv_pct"]},
            {"Case": "Scenario", "LTV": scenario["stressed_ltv_pct"]},
        ]
    )
    fig = px.bar(
        ltv_chart,
        x="Case",
        y="LTV",
        color="Case",
        text=ltv_chart["LTV"].round(1),
        color_discrete_map={"Base": "#263b5e", "Scenario": "#b76e00"},
        labels={"LTV": "LTV (%)"},
    )
    fig.update_layout(height=370, margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False)
    st.plotly_chart(fig, width="stretch")

left, right = st.columns([1.2, 1])

with left:
    st.subheader("AFFO Bridge")
    waterfall = scenario_waterfall(scenario)
    fig = go.Figure(
        go.Waterfall(
            x=waterfall["driver"],
            y=waterfall["amount_krw_bn"],
            measure=waterfall["measure"],
            connector={"line": {"color": "#667085"}},
            increasing={"marker": {"color": "#007c89"}},
            decreasing={"marker": {"color": "#c94f4f"}},
            totals={"marker": {"color": "#263b5e"}},
        )
    )
    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="금액",
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Peer Impact Under Same Scenario")
    peer = run_peer_scenarios(
        reits,
        assets,
        debt,
        rate_shock_bp=rate_shock,
        rent_change_pct=rent_change,
        asset_value_change_pct=asset_value_change,
        tax_impact_pct=tax_impact,
        base_market_rate_pct=base_market_rate,
    )
    peer_chart = px.bar(
        peer.sort_values("dividend_buffer_krw_bn"),
        x="reit_name",
        y="dividend_buffer_krw_bn",
        color="refinancing_status",
        color_discrete_map={"High": "#c94f4f", "Medium": "#b76e00", "Low": "#007c89"},
        labels={"reit_name": "", "dividend_buffer_krw_bn": "Dividend buffer"},
        text=peer["dividend_buffer_krw_bn"].map(format_krw_bn),
    )
    peer_chart.add_hline(y=0, line_dash="dash", line_color="#667085")
    peer_chart.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10))
    peer_chart.update_traces(textposition="outside", cliponaxis=False)
    st.plotly_chart(peer_chart, width="stretch")

interpretation = cfo_interpretation(scenario)
st.markdown(
    f"""
    <div class="consulting-hero">
        <div class="eyebrow">CFO Interpretation</div>
        <div class="hero-title">금리, 임대료, 자산가치, 세금효과 변화가 배당가능성과 refinancing risk에 미치는 영향</div>
        <div class="hero-body">
            <strong>핵심 변화</strong><br>{interpretation["핵심 변화"]}<br><br>
            <strong>재무적 영향</strong><br>{interpretation["재무적 영향"]}<br><br>
            <strong>CFO가 확인해야 할 사항</strong><br>{interpretation["CFO가 확인해야 할 사항"]}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
