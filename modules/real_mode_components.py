"""
Real API Mode components for K-REIT CFO Copilot v12.

This module keeps Real API Mode conservative:
- factual OpenDART / ECOS data
- user-input hypothetical scenario
- no investment opinion
- no credit judgment
- no fabricated risk flags for real listed REITs
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from modules.ui_components import format_krw_bn


REAL_API_MODE_DISCLAIMER = (
    "Real API Mode는 OpenDART·ECOS 등 공개 API로 조회 가능한 사실 정보와 사용자가 직접 입력한 "
    "가정만을 기반으로 합니다. 본 화면은 실제 기업에 대한 투자 의견, 신용 판단, 부정적 리스크 평가를 "
    "제공하지 않습니다."
)
V11_EXPLANATION = "v12에서는 공개 API, 공시 원문 parser, market/public data, macro proxy, 사용자 보완값, 데이터 미확보 항목을 source/confidence와 함께 구분합니다."
V10_EXPLANATION = V11_EXPLANATION
DATA_AVAILABILITY_EXPLANATION = (
    "공개 API로 자동화 가능한 데이터, 사용자 입력이 필요한 데이터, 고객 내부자료 또는 manual validation이 "
    "필요한 데이터를 구분합니다."
)
SAMPLE_MODE_NOTICE = "Demo / Sample Mode의 회사명, 수치, Risk Score, 공시 신호는 모두 fictional sample data입니다."


def _format_krw_bn(value: float, digits: int = 0) -> str:
    return format_krw_bn(value, digits)


def _format_pct(value: float, digits: int = 1) -> str:
    return f"{value:,.{digits}f}%"


def render_real_mode_warning() -> None:
    st.warning(REAL_API_MODE_DISCLAIMER)
    st.caption(V11_EXPLANATION)


def render_real_mode_disclaimer(**kwargs: Any) -> None:
    render_real_mode_warning()


def render_sample_mode_notice() -> None:
    st.caption(SAMPLE_MODE_NOTICE)


def select_real_reit(label: str = "Real REIT 선택") -> pd.Series:
    try:
        from modules.real_data_loader import get_selected_real_reit, load_real_reit_master
        from modules.ui_components import get_sidebar_selected_real_reit_name

        master = load_real_reit_master()
        if master.empty:
            raise ValueError("real_reit_master.csv is empty")
        selected_name = get_sidebar_selected_real_reit_name()
        if not selected_name:
            selected_name = st.sidebar.selectbox(label, master["real_reit_name"].tolist(), key=f"{label}_real_reit")
        return get_selected_real_reit(selected_name)
    except Exception as exc:
        st.sidebar.warning(f"Real REIT 선택 컴포넌트를 불러오지 못해 fallback 값을 사용합니다. ({exc})")
        return pd.Series({"real_reit_name": "선택 REIT", "ticker": "", "corp_code": "", "notes": ""})


def render_real_reit_factual_panel(real_reit: pd.Series | dict[str, Any] | None = None) -> None:
    real_reit = real_reit if real_reit is not None else {}
    get_value = real_reit.get if hasattr(real_reit, "get") else lambda key, default="": default

    st.markdown(f"**선택 REIT:** {str(get_value('real_reit_name', '선택 REIT') or '선택 REIT')}")

    note = str(get_value("notes", "")).strip()
    if note:
        st.caption(note)


def render_opendart_disclosure_monitor(
    selected_reit=None,
    disclosures=None,
    disclosure_data=None,
    **kwargs: Any,
) -> pd.DataFrame:
    st.markdown("### OpenDART 공시 모니터")

    if isinstance(selected_reit, pd.DataFrame) and disclosures is None and disclosure_data is None:
        data = selected_reit
        selected_reit = None
    else:
        data = disclosures if disclosures is not None else disclosure_data

    if selected_reit is not None:
        try:
            name = (
                selected_reit.get("real_reit_name")
                or selected_reit.get("reit_name")
                or selected_reit.get("name")
                or "선택 REIT"
            )
        except AttributeError:
            name = str(selected_reit)
        st.caption(f"선택 REIT: {name}")

    if data is None:
        try:
            from modules.real_data_loader import load_real_disclosure_data

            data = load_real_disclosure_data(selected_reit)
        except Exception as exc:
            data = pd.DataFrame()
            data.attrs["is_fallback"] = True
            data.attrs["status_message"] = f"OpenDART 공시 데이터를 조회하지 못했습니다: {exc}"

    if not isinstance(data, pd.DataFrame):
        data = pd.DataFrame(data)

    try:
        from modules.real_insights import summarize_disclosure_insights

        _render_disclosure_insight_cards(summarize_disclosure_insights(data))
    except Exception:
        pass

    if data.empty:
        st.info(data.attrs.get("status_message", "OpenDART 공시 데이터가 없거나 API fallback 상태입니다."))
        return data

    display_columns = [
        "report_nm",
        "rcept_dt",
        "report_type",
        "rcept_no",
        "disclosure_link",
        "freshness_indicator",
        "is_key_report",
    ]
    display = data[[column for column in display_columns if column in data.columns]].head(20)
    st.dataframe(
        display.rename(
            columns={
                "report_nm": "공시명",
                "rcept_dt": "접수일",
                "report_type": "보고서 유형",
                "rcept_no": "접수번호",
                "disclosure_link": "공시 링크",
                "freshness_indicator": "공시 freshness",
                "is_key_report": "정기/주요 공시 여부",
            }
        ),
        width="stretch",
        hide_index=True,
        column_config={"공시 링크": st.column_config.LinkColumn("공시 링크")},
    )
    st.caption(
        "공시 freshness와 정기공시 여부는 원문 확인을 돕기 위한 factual indicator입니다. "
        "공시 빈도만으로 재무상태, 투자위험, 신용도를 판단하지 않습니다."
    )
    return data


def _render_disclosure_insight_cards(insights: dict[str, object]) -> None:
    cols = st.columns(5)
    cols[0].metric("최근 정기공시", str(insights.get("latest_periodic_report", "조회 불가")))
    cols[1].metric("최근 주요 공시", str(insights.get("latest_key_report", "조회 불가")))
    cols[2].metric("최근 90일 공시 건수", f"{int(insights.get('last_90_days_count', 0))}건")
    cols[3].metric("정기공시 업데이트 상태", str(insights.get("periodic_update_status", "조회 불가")))
    cols[4].metric("분석 가능한 최신 보고일", str(insights.get("latest_report_date_available", "조회 불가")))


def render_ecos_market_rate_panel(rates=None, market_rate_data=None, **kwargs: Any) -> pd.DataFrame:
    st.markdown("### ECOS 금리 요약")

    data = rates if rates is not None else market_rate_data
    if data is None:
        try:
            from modules.real_data_loader import load_real_market_rate_data

            data = load_real_market_rate_data(use_api=True)
        except Exception as exc:
            data = pd.DataFrame()
            data.attrs["is_fallback"] = True
            data.attrs["status_message"] = f"ECOS 금리 데이터를 조회하지 못했습니다: {exc}"

    if not isinstance(data, pd.DataFrame):
        data = pd.DataFrame(data)

    try:
        from modules.real_insights import summarize_ecos_insights

        insights = summarize_ecos_insights(data)
    except Exception:
        insights = {
            "latest_rate": None,
            "latest_date": "조회 불가",
            "recent_direction": "조회 불가",
            "scenario_base_rate": None,
            "source_status": "ECOS fallback",
            "shock_table": pd.DataFrame(columns=["Scenario", "Shock bp", "Scenario rate"]),
        }

    _render_ecos_insight_cards(insights)

    if data.empty:
        st.info(data.attrs.get("status_message", "ECOS 금리 데이터가 없거나 API fallback 상태입니다."))
        return data

    status_message = str(data.attrs.get("status_message", "")).strip()
    if data.attrs.get("is_fallback", True):
        st.info("ECOS 금리 데이터가 없어 fallback 기준금리를 사용합니다.")
    elif status_message:
        st.caption(status_message)
    return data


def _render_ecos_insight_cards(insights: dict[str, object]) -> None:
    latest_rate = insights.get("latest_rate")
    base_rate = insights.get("scenario_base_rate")
    direction_raw = str(insights.get("recent_direction", "데이터 부족"))
    if "상승" in direction_raw:
        direction = "상승"
    elif "하락" in direction_raw:
        direction = "하락"
    elif "보합" in direction_raw:
        direction = "보합"
    else:
        direction = "데이터 부족"
    cols = st.columns(4)
    cols[0].metric("기준금리", "데이터 없음" if latest_rate is None else _format_pct(float(latest_rate)))
    cols[1].metric("최근 기준일", str(insights.get("latest_date", "조회 불가")))
    cols[2].metric("최근 방향성", direction)
    cols[3].metric("Scenario 기준금리", "데이터 없음" if base_rate is None else _format_pct(float(base_rate)))


def render_real_mode_manual_scenario(real_reit: pd.Series | dict[str, Any] | None = None) -> dict[str, object] | None:
    st.subheader("Real Mode 사용자 입력 기반 예비 시뮬레이션")
    st.caption(
        "사용자 입력값 기반 시뮬레이션은 예비적인 구조 검토이며, 공개 API만으로 검증된 수치가 아닙니다."
    )

    with st.expander("Manual Scenario Bridge", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_assets = st.number_input("총자산 (억 원)", min_value=0.0, value=0.0, step=100.0)
            annual_noi = st.number_input("연간 NOI (억 원)", min_value=0.0, value=0.0, step=10.0)
        with col2:
            total_debt = st.number_input("총차입금 (억 원)", min_value=0.0, value=0.0, step=100.0)
            dividend = st.number_input("연간 배당금 (억 원)", min_value=0.0, value=0.0, step=10.0)
        with col3:
            floating_pct = st.number_input("변동금리 차입 비중 (%)", min_value=0.0, max_value=100.0, value=45.0, step=5.0)
            avg_coupon = st.number_input("평균 이자율 (%)", min_value=0.0, max_value=20.0, value=4.2, step=0.1)
        with col4:
            near_term_pct = st.number_input("1~2년 만기도래 차입 비중 (%)", min_value=0.0, max_value=100.0, value=45.0, step=5.0)
            rate_shock = st.slider("금리 shock (bp)", -50, 200, 50, 25)

        rent_change = st.slider("임대료 변화율 (%)", -10.0, 10.0, 0.0, 0.5)
        asset_value_change = st.slider("자산가치 변화율 (%)", -20.0, 10.0, 0.0, 0.5)
        include_tax_effect = st.checkbox("단순 세금효과 반영 여부", value=False)

    if total_assets <= 0 or total_debt <= 0 or annual_noi <= 0 or dividend <= 0:
        st.info("Real Mode scenario 계산에는 총자산, 총차입금, 연간 NOI, 연간 배당금 사용자 입력이 필요합니다.")
        return None

    try:
        from modules.real_data_loader import load_real_market_rate_data
        from modules.real_insights import calculate_manual_real_scenario

        rates = load_real_market_rate_data(use_api=True)
        base_rate = float(rates.sort_values("date").iloc[-1]["market_rate_pct"]) if not rates.empty else avg_coupon
        get_value = real_reit.get if hasattr(real_reit, "get") else lambda key, default="": default
        scenario = calculate_manual_real_scenario(
            real_reit_name=str(get_value("real_reit_name", "선택 REIT")),
            total_assets=total_assets / 10,
            total_debt=total_debt / 10,
            annual_noi=annual_noi / 10,
            dividend_amount=dividend / 10,
            floating_debt_pct=floating_pct,
            average_coupon_pct=avg_coupon,
            near_term_debt_pct=near_term_pct,
            rate_shock_bp=rate_shock,
            rent_change_pct=rent_change,
            asset_value_change_pct=asset_value_change,
            include_tax_effect=include_tax_effect,
            base_market_rate_pct=base_rate,
        )
    except Exception as exc:
        st.info(f"Manual scenario calculation을 실행하지 못했습니다: {exc}")
        return None

    cols = st.columns(4)
    cols[0].metric("사용자 입력 기반 LTV", _format_pct(float(scenario["user_input_ltv_pct"])))
    cols[1].metric(
        "사용자 입력 기반 interest expense",
        _format_krw_bn(float(scenario["user_input_interest_expense_krw_bn"]), 1),
    )
    cols[2].metric("사용자 입력 기반 dividend buffer", _format_krw_bn(float(scenario["dividend_buffer_krw_bn"]), 1))
    cols[3].metric("사용자 입력 기반 refinancing pressure", str(scenario["user_input_refinancing_pressure"]))

    summary = pd.DataFrame(
        [
            {"Metric": "AFFO estimate", "Value": _format_krw_bn(float(scenario["affo_estimate_krw_bn"]), 1)},
            {"Metric": "Dividend coverage", "Value": f'{float(scenario["dividend_coverage"]):,.2f}x'},
            {"Metric": "Stressed LTV", "Value": _format_pct(float(scenario["stressed_ltv_pct"]))},
            {"Metric": "Refinancing pressure", "Value": str(scenario["user_input_refinancing_pressure"])},
        ]
    )
    st.dataframe(summary, width="stretch", hide_index=True)
    st.warning(
        "현재 표시되는 manual scenario 결과는 사용자가 입력한 가정에 따른 예비 시뮬레이션입니다. "
        "실제 투자 판단, 기업 평가, 신용 판단, 세무자문 또는 감사 판단으로 사용해서는 안 됩니다."
    )
    return scenario


def render_real_mode_manual_scenario_bridge(**kwargs: Any):
    return render_real_mode_manual_scenario(**kwargs)


def render_real_mode_cfo_interpretation(
    selected_reit=None,
    disclosure_data=None,
    market_rate_data=None,
    manual_scenario=None,
    disclosures=None,
    rates=None,
    scenario=None,
    **kwargs: Any,
) -> None:
    if disclosures is not None and disclosure_data is None:
        disclosure_data = disclosures

    if rates is not None and market_rate_data is None:
        market_rate_data = rates

    if scenario is not None and manual_scenario is None:
        manual_scenario = scenario

    st.markdown("### CFO 해석 메모")
    st.info(REAL_API_MODE_DISCLAIMER)

    if selected_reit is not None:
        try:
            reit_name = (
                selected_reit.get("real_reit_name")
                or selected_reit.get("reit_name")
                or selected_reit.get("name")
                or "선택 REIT"
            )
        except AttributeError:
            reit_name = str(selected_reit)

        st.markdown(f"**선택 REIT:** {reit_name}")

    st.markdown(
        """
        #### 해석 기준

        - OpenDART 기준 최근 공시 목록은 분석 가능한 최신 보고서를 확인하기 위한 factual data입니다.
        - ECOS 기준 금리 데이터는 Scenario Engine의 기준금리 가정으로 활용할 수 있습니다.
        - 사용자 입력값 기반 시뮬레이션은 예비적인 구조 검토이며, 공개 API만으로 검증된 수치가 아닙니다.
        - 정확한 FFO, AFFO, WALE, 임차인 집중도, 자산별 NOI, 차입 만기 구조는 사업보고서 세부 주석 또는 고객 내부 자료 확인이 필요합니다.
        """
    )

    if manual_scenario is not None:
        st.warning(
            """
            현재 표시되는 manual scenario 결과는 사용자가 입력한 가정에 따른 예비 시뮬레이션입니다.

            실제 투자 판단, 기업 평가, 신용 판단, 세무자문 또는 감사 판단으로 사용해서는 안 됩니다.
            """
        )


def get_data_availability_matrix() -> pd.DataFrame:
    rows = [
        {
            "Metric": "회사명 / ticker",
            "Source": "Real REIT master / KRX / OpenDART",
            "API availability": "부분 가능",
            "Automation level": "High",
            "Manual validation required?": "No",
            "Notes": "상장 REIT master data로 관리 가능",
        },
        {
            "Metric": "OpenDART 공시 목록",
            "Source": "OpenDART",
            "API availability": "가능",
            "Automation level": "High",
            "Manual validation required?": "No",
            "Notes": "공시명, 접수일, 접수번호 조회 가능",
        },
        {
            "Metric": "최근 정기공시",
            "Source": "OpenDART",
            "API availability": "가능",
            "Automation level": "High",
            "Manual validation required?": "Low",
            "Notes": "사업보고서·반기보고서·분기보고서 확인",
        },
        {
            "Metric": "기준금리 / 시장금리",
            "Source": "ECOS",
            "API availability": "가능",
            "Automation level": "High",
            "Manual validation required?": "No",
            "Notes": "ECOS 기준 금리 데이터는 Scenario Engine의 기준금리 가정으로 활용할 수 있습니다.",
        },
        {
            "Metric": "주가 / 시가총액",
            "Source": "KRX / external market data",
            "API availability": "부분 가능",
            "Automation level": "Medium",
            "Manual validation required?": "Low",
            "Notes": "pykrx 또는 public market data fallback을 우선 시도하고, 실패 시 미확보로 표시합니다.",
        },
        {
            "Metric": "FFO / AFFO",
            "Source": "사업보고서 / IR 자료 / 내부자료",
            "API availability": "제한적",
            "Automation level": "Low",
            "Manual validation required?": "Yes",
            "Notes": "공시 원문 parser가 먼저 시도하며, REIT별 산식과 조정항목은 manual validation이 필요합니다.",
        },
        {
            "Metric": "WALE",
            "Source": "사업보고서 주석 / IR 자료 / 내부자료",
            "API availability": "제한적",
            "Automation level": "Low",
            "Manual validation required?": "Yes",
            "Notes": "공시 원문 parser가 먼저 시도하며, 자산별 임대차 만기 데이터 검증이 필요합니다.",
        },
        {
            "Metric": "임차인 집중도",
            "Source": "사업보고서 주석 / 내부 임대차 자료",
            "API availability": "제한적",
            "Automation level": "Low",
            "Manual validation required?": "Yes",
            "Notes": "공시 원문 parser가 먼저 시도하며, 주요 임차인 및 매출 비중 검증이 필요합니다.",
        },
        {
            "Metric": "자산별 NOI",
            "Source": "사업보고서 / 운용보고서 / 내부자료",
            "API availability": "제한적",
            "Automation level": "Low",
            "Manual validation required?": "Yes",
            "Notes": "공시 원문 parser가 먼저 시도하며, 자산별 수익·비용 배분 검증이 필요합니다.",
        },
        {
            "Metric": "차입 만기 구조",
            "Source": "사업보고서 주석 / 차입 약정 자료",
            "API availability": "부분 가능",
            "Automation level": "Medium",
            "Manual validation required?": "Yes",
            "Notes": "OpenDART 재무제표와 원문 parser를 먼저 시도하고, 차입 조건은 검증이 필요합니다.",
        },
        {
            "Metric": "세금효과",
            "Source": "세법 검토 / 내부 거래자료",
            "API availability": "불가",
            "Automation level": "Low",
            "Manual validation required?": "Yes",
            "Notes": "자산 매각, 배당, 법인세, 지방세 등 별도 검토 필요",
        },
        {
            "Metric": "Investor Q&A",
            "Source": "공시 / IR / 사용자 입력",
            "API availability": "부분 가능",
            "Automation level": "Medium",
            "Manual validation required?": "Yes",
            "Notes": "현재 v12는 rule-based이며 외부 LLM API를 사용하지 않습니다.",
        },
    ]
    return pd.DataFrame(rows)


def data_availability_matrix() -> pd.DataFrame:
    return get_data_availability_matrix()


def render_data_availability_matrix(
    matrix: pd.DataFrame | None = None,
    title: str = "Data Availability Matrix",
    **kwargs: Any,
) -> pd.DataFrame:
    if matrix is None:
        matrix = get_data_availability_matrix()

    st.markdown(f"### {title}")
    st.caption(DATA_AVAILABILITY_EXPLANATION)
    st.dataframe(matrix, width="stretch", hide_index=True)
    st.info(
        "v12는 자동 수집과 공시 parser를 먼저 시도한 뒤, FFO, AFFO, WALE, 임차인 집중도, 자산별 NOI, "
        "세금효과처럼 고객 내부자료 검증이 필요한 항목만 manual validation으로 분리합니다."
    )
    return matrix


def render_real_mode_data_quality_status(**kwargs: Any):
    st.markdown("### Real API Mode 데이터 품질 상태")
    st.info(
        "OpenDART·ECOS 연결 상태, fallback 여부, manual validation 필요 항목을 구분합니다. "
        "FFO, AFFO, WALE, 임차인 집중도, 자산별 NOI, 차입 만기 구조는 내부 자료 확인이 필요합니다."
    )
    return None


def render_real_mode_dashboard_summary(**kwargs: Any):
    st.markdown("### Real API Mode Dashboard Summary")
    st.info("실제 상장 REIT에는 공개 API 기반 factual public data와 사용자 입력 가정만 표시합니다.")
    return None


def _fallback_renderer(*args: Any, **kwargs: Any):
    st.info(
        "Real API Mode 컴포넌트를 불러오지 못했습니다. "
        "v10에서는 공개 API 기반 factual data와 사용자 입력 기반 예비 시뮬레이션을 구분합니다."
    )
    return None


def __getattr__(name: str):
    if name.startswith("render_"):
        return _fallback_renderer
    raise AttributeError(f"module 'modules.real_mode_components' has no attribute {name!r}")


__all__ = [
    "DATA_AVAILABILITY_EXPLANATION",
    "REAL_API_MODE_DISCLAIMER",
    "V10_EXPLANATION",
    "V11_EXPLANATION",
    "data_availability_matrix",
    "get_data_availability_matrix",
    "render_data_availability_matrix",
    "render_ecos_market_rate_panel",
    "render_opendart_disclosure_monitor",
    "render_real_mode_cfo_interpretation",
    "render_real_mode_dashboard_summary",
    "render_real_mode_data_quality_status",
    "render_real_mode_disclaimer",
    "render_real_mode_manual_scenario",
    "render_real_mode_manual_scenario_bridge",
    "render_real_mode_warning",
    "render_real_reit_factual_panel",
    "render_sample_mode_notice",
    "select_real_reit",
]
