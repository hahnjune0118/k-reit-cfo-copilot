import plotly.express as px
import pandas as pd
import streamlit as st

from modules.data_loader import load_all_data, reit_id_from_name, reit_options
from modules.real_reit_analytics import build_real_reit_dashboard_model
from modules.risk_scoring import debt_maturity_wall, refinancing_risk_table, score_assets
from modules.ui_components import format_krw, format_krw_bn, get_real_mode_user_inputs, hero, is_real_api_mode, setup_page

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
    import pandas as pd

    st.sidebar.info("Real REIT 선택 컴포넌트를 불러오지 못해 fallback 값을 사용합니다.")
    return pd.Series({"real_reit_name": "선택 REIT", "ticker": "", "corp_code": "", "notes": ""})


def _fallback_real_reit_factual_panel(*args, **kwargs):
    st.info("Real REIT factual panel을 불러오지 못했습니다.")


def _fallback_empty_frame_component(message):
    def _inner(*args, **kwargs):
        import pandas as pd

        st.info(message)
        return pd.DataFrame()

    return _inner


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
render_real_mode_warning = _real_component("render_real_mode_warning", _fallback_real_mode_warning)
render_real_reit_factual_panel = _real_component("render_real_reit_factual_panel", _fallback_real_reit_factual_panel)
select_real_reit = _real_component("select_real_reit", _fallback_select_real_reit)


setup_page("4. 자산 및 차입 리스크", "asset-level Risk Score와 debt maturity wall 진단")

if is_real_api_mode():
    hero(
        "v12 Real Asset & Debt Risk",
        "차입 구성, maturity wall, refinancing pressure, interest sensitivity를 CFO 검토 항목으로 전환",
        "OpenDART 재무제표와 공시 원문 parser를 먼저 사용하고, 담보·금리조건·자산별 NOI처럼 구조화가 어려운 항목은 manual validation으로 분리합니다.",
    )
    real_reit = select_real_reit("Real REIT 선택")
    model = build_real_reit_dashboard_model(real_reit, get_real_mode_user_inputs())
    metrics = model["metrics"]
    derived = model["derived"]
    risk_model = model["risk_model"]

    cols = st.columns(4)
    cols[0].metric("총차입금", format_krw(metrics.get("total_debt_krw")))
    cols[1].metric("LTV", "데이터 없음" if metrics.get("ltv_pct") is None else f"{float(metrics['ltv_pct']):.1f}%")
    refi_pressure = derived["debt"]["refinancing_pressure_index"].get("value")
    cols[2].metric("Refinancing Pressure", "데이터 없음" if refi_pressure is None else f"{float(refi_pressure):.0f}/100")
    cols[3].metric("Overall Risk", "Not Available" if risk_model["overall_score"] is None else f"{float(risk_model['overall_score']):.0f}/100", risk_model["overall_level"])

    st.subheader("Debt Composition")
    raw_financials = model["raw_bundle"].get("financials", {})
    debt_rows = []
    for label, key in [
        ("Short-term debt", "short_term_debt"),
        ("Long-term debt", "long_term_debt"),
        ("Borrowings", "borrowings"),
        ("Bonds payable", "bonds_payable"),
        ("Current liabilities", "current_liabilities"),
        ("Noncurrent liabilities", "noncurrent_liabilities"),
    ]:
        metric = raw_financials.get(key, {})
        debt_rows.append(
            {
                "항목": label,
                "금액": format_krw(metric.get("value") if isinstance(metric, dict) else None),
                "Source": metric.get("source", "Not Available") if isinstance(metric, dict) else "Not Available",
                "Confidence": metric.get("confidence", "Not Available") if isinstance(metric, dict) else "Not Available",
                "Warning": metric.get("warning", metric.get("note", "")) if isinstance(metric, dict) else "",
            }
        )
    st.dataframe(pd.DataFrame(debt_rows), width="stretch", hide_index=True)

    st.subheader("Debt Maturity Wall")
    wall = model["debt_maturity_wall"].copy()
    if wall.empty:
        st.info(wall.attrs.get("status_message", "자동 수집을 시도했으나 차입 만기 구조가 미확보되었습니다."))
    else:
        chart_wall = wall.copy()
        fig = px.bar(chart_wall, x="구간", y="금액", color="Status", labels={"금액": "금액"})
        fig.update_layout(height=330, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig, width="stretch")
        wall["금액"] = wall["금액"].map(format_krw)
        st.dataframe(wall, width="stretch", hide_index=True)

    st.subheader("Debt & Asset Risk Components")
    components = model["risk_components"]
    debt_components = components[components["component"].isin(["Leverage", "Liquidity", "Interest Rate", "Refinancing", "Data Quality"])]
    st.dataframe(debt_components, width="stretch", hide_index=True)

    st.subheader("Interest Expense Sensitivity")
    sensitivity = model["scenario_outputs"][["Scenario", "Scenario 기준금리", "Interest expense impact", "Refinancing pressure", "CFO action", "Source/Basis"]].copy()
    sensitivity["Scenario 기준금리"] = sensitivity["Scenario 기준금리"].map(lambda value: "데이터 없음" if pd.isna(value) else f"{float(value):.2f}%")
    sensitivity["Interest expense impact"] = sensitivity["Interest expense impact"].map(format_krw)
    st.dataframe(sensitivity, width="stretch", hide_index=True)

    st.subheader("Debt Note Evidence Snippets")
    snippets = model.get("parsed_evidence_snippets", [])
    if snippets:
        for item in snippets[:5]:
            st.caption(f"[OpenDART Parsed] {item.get('keyword', '')}: {item.get('snippet', '')}")
    else:
        st.info("담보, 금리조건, 만기 schedule 관련 공시 원문 snippet은 아직 자동 추출되지 않았습니다. 사업보고서 주석 또는 내부 treasury 자료 확인이 필요합니다.")

    st.info("CFO 해석: 이 화면은 실제 투자 의견이나 신용 판단을 제공하지 않습니다. 차입 구성과 금리 민감도는 공개 API와 parser 기반 예비 진단이며, 정확한 만기표·담보·금리조건은 세부 주석 및 내부 차입 약정 검증이 필요합니다.")
    st.stop()

data = load_all_data()
reits = data["reits"]
assets = data["assets"]
debt = data["debt"]
flags = data["flags"]

scope_options = ["전체 상장 REIT sample"] + reit_options(reits)
scope = st.sidebar.selectbox("분석 범위", scope_options)

if scope == "전체 상장 REIT sample":
    scope_reits = reits
    scope_assets = assets
    scope_debt = debt
    scope_flags = flags
    title_name = "전체 상장 REIT sample"
else:
    reit_id = reit_id_from_name(reits, scope)
    scope_reits = reits[reits["reit_id"] == reit_id]
    scope_assets = assets[assets["reit_id"] == reit_id]
    scope_debt = debt[debt["reit_id"] == reit_id]
    scope_flags = flags[flags["reit_id"] == reit_id]
    title_name = scope

hero(
    "Risk driver map",
    f"{title_name}: asset 및 debt risk view",
    "이 화면은 occupancy, WALE, tenant concentration, capex need를 기반으로 asset Risk Score를 산출하고 "
    "maturity concentration, floating-rate exposure, disclosure flags와 연결합니다.",
)

refi = refinancing_risk_table(scope_reits, scope_debt, scope_assets)
total_debt = scope_debt["principal_krw_bn"].sum()
near_term = refi["near_term_debt_krw_bn"].sum()
avg_refi_score = refi["refinancing_risk_score"].mean()

cols = st.columns(4)
cols[0].metric("Debt in scope", format_krw_bn(total_debt, 0))
cols[1].metric("Near-term maturity", format_krw_bn(near_term, 0))
cols[2].metric("Avg refi Risk Score", f"{avg_refi_score:.0f}/100")
cols[3].metric("Disclosure flags", f"{len(scope_flags)}건")

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
        labels={"maturity_year": "Maturity year", "principal_krw_bn": "Principal", "reit_name": "REIT"},
        text=wall["principal_krw_bn"].map(format_krw_bn),
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
                "risk_tier": "Risk tier",
                "refinancing_risk_score": "Refi Risk Score",
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
asset_display = asset_scores.copy()
asset_display["asset_value_display"] = asset_display["asset_value_krw_bn"].map(format_krw_bn)

st.subheader("Asset Risk Ranking")
asset_chart = px.scatter(
    asset_display,
    x="wale_years",
    y="asset_risk_score",
    size="asset_value_krw_bn",
    color="risk_tier",
    hover_name="asset_name",
    hover_data={
        "reit_name": True,
        "sector": True,
        "asset_value_display": True,
        "asset_value_krw_bn": False,
        "occupancy_pct": True,
        "top_tenant_share_pct": True,
        "capex_need_pct": True,
    },
    color_discrete_map={"High": "#c94f4f", "Medium": "#b76e00", "Low": "#007c89"},
    labels={"wale_years": "WALE (years)", "asset_risk_score": "Asset Risk Score"},
)
asset_chart.update_layout(height=420, margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(asset_chart, width="stretch")

st.dataframe(
    asset_display[
        [
            "reit_name",
            "asset_name",
            "sector",
            "location",
            "asset_value_display",
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
            "asset_value_display": "자산가치",
            "occupancy_pct": "Occupancy %",
            "wale_years": "WALE",
            "top_tenant_share_pct": "Top tenant %",
            "capex_need_pct": "Capex need %",
            "risk_tier": "Risk tier",
            "asset_risk_score": "Asset Risk Score",
            "strategic_importance": "전략적 해석",
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
                "area": "공시 영역",
                "flag": "Flag",
                "severity": "Severity",
                "decision_risk": "의사결정 리스크",
                "recommended_action": "권고 Action",
            }
        ),
        width="stretch",
        hide_index=True,
    )
