from __future__ import annotations

from typing import Any

import pandas as pd

from modules.real_mode_analytics import build_real_mode_analysis
from modules.real_reit_risk_model import build_component, calculate_overall_from_components, components_to_frame
from modules.source_confidence import (
    build_collected_metrics_table,
    build_metric,
    build_source_inventory,
    confidence_distribution,
    metric_confidence,
    metric_source,
    metric_source_type,
    metric_value,
    not_available_metric,
)


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return float(numerator) / float(denominator)


def _pct(numerator: float | None, denominator: float | None) -> float | None:
    ratio = _safe_div(numerator, denominator)
    return None if ratio is None else ratio * 100


def _num(value: Any) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _source_for(metrics: dict[str, Any], key: str) -> str:
    details = metrics.get("metric_details", {})
    return metric_source(details.get(key), metrics.get("source_map", {}).get(key, "Not Available"))


def _confidence_for(metrics: dict[str, Any], key: str) -> str:
    details = metrics.get("metric_details", {})
    return metric_confidence(details.get(key))


def _derived_metric(name: str, value: Any, unit: str, method: str, confidence: str = "Low") -> dict[str, Any]:
    return build_metric(
        name,
        value,
        unit,
        "calculated from source-tagged Real API Mode metrics",
        confidence if value is not None else "Not Available",
        source_type="Inferred Proxy" if value is not None else "Not Available",
        calculation_method=method,
        warning="" if value is not None else "필수 입력 metric이 부족해 산출하지 못했습니다.",
    )


def build_real_reit_metrics_bundle(selected_reit: Any, user_inputs: dict[str, float | None] | None = None, force_refresh: bool = False) -> dict[str, Any]:
    return build_real_mode_analysis(selected_reit, user_inputs=user_inputs or {}, force_refresh=force_refresh)


def derive_core_financial_metrics(analysis: dict[str, Any]) -> dict[str, Any]:
    metrics = analysis["metrics"]
    total_assets = _num(metrics.get("total_assets_krw"))
    total_debt = _num(metrics.get("total_debt_krw"))
    equity = metric_value(analysis["public_data"]["real_data_bundle"].get("financials", {}).get("total_equity"))
    cash = _num(metrics.get("cash_krw"))
    interest = _num(metrics.get("interest_expense_krw"))
    revenue_or_noi = _num(metrics.get("annual_noi_krw") or metrics.get("revenue_krw") or metrics.get("operating_income_krw"))
    dividend = _num(metrics.get("dividend_krw"))
    dividend_buffer = _num(metrics.get("dividend_buffer_krw"))

    return {
        "ltv": _derived_metric("ltv", _pct(total_debt, total_assets), "%", "total_debt / total_assets"),
        "debt_to_assets": _derived_metric("debt_to_assets", _pct(total_debt, total_assets), "%", "total_debt / total_assets"),
        "debt_to_equity": _derived_metric("debt_to_equity", _pct(total_debt, _num(equity)), "%", "total_debt / total_equity"),
        "cash_to_debt": _derived_metric("cash_to_debt", _pct(cash, total_debt), "%", "cash / total_debt"),
        "interest_burden": _derived_metric("interest_burden", _pct(interest, revenue_or_noi), "%", "interest expense / NOI or revenue proxy"),
        "dividend_buffer": _derived_metric("dividend_buffer", dividend_buffer, "KRW", "NOI proxy - dividend - interest expense"),
        "dividend_buffer_pct": _derived_metric("dividend_buffer_pct", _pct(dividend_buffer, dividend), "%", "dividend buffer / dividend"),
    }


def derive_debt_metrics(analysis: dict[str, Any]) -> dict[str, Any]:
    metrics = analysis["metrics"]
    total_debt = _num(metrics.get("total_debt_krw"))
    near_term_debt = _num(metrics.get("near_term_debt_krw"))
    near_term_pct = _num(metrics.get("near_term_debt_pct")) or _pct(near_term_debt, total_debt)
    ltv = _num(metrics.get("ltv_pct"))
    refi_rate = _num(metrics.get("refinancing_rate_pct"))
    refinancing_pressure = None
    if near_term_pct is not None or ltv is not None:
        refinancing_pressure = min(max(float(near_term_pct or 0) * 1.1 + max(float(ltv or 0) - 45, 0) * 1.2, 0), 100)
    return {
        "estimated_refinancing_rate": _derived_metric("estimated_refinancing_rate", refi_rate, "%", "base rate + refinancing spread proxy"),
        "refinancing_pressure_index": _derived_metric(
            "refinancing_pressure_index",
            refinancing_pressure,
            "score",
            "near-term debt ratio and LTV pressure proxy",
        ),
        "near_term_debt_pct": _derived_metric("near_term_debt_pct", near_term_pct, "%", "near-term debt / total debt"),
    }


def derive_market_metrics(analysis: dict[str, Any]) -> dict[str, Any]:
    metrics = analysis["metrics"]
    recent_return = _num(metrics.get("recent_return_pct"))
    score = None if recent_return is None else min(max(45 - recent_return * 1.2, 0), 100)
    return {
        "market_stress_signal": _derived_metric("market_stress_signal", score, "score", "recent market return pressure proxy"),
        "market_cap": analysis["public_data"]["real_data_bundle"].get("market_data", {}).get(
            "market_cap", not_available_metric("market_cap", "KRW")
        ),
    }


def derive_dividend_metrics(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "dividend_buffer": derive_core_financial_metrics(analysis)["dividend_buffer"],
        "dividend_buffer_pct": derive_core_financial_metrics(analysis)["dividend_buffer_pct"],
    }


def derive_macro_sensitivity(analysis: dict[str, Any]) -> dict[str, Any]:
    metrics = analysis["metrics"]
    total_debt = _num(metrics.get("total_debt_krw"))
    floating_pct = _num(metrics.get("floating_debt_pct")) or 0.0
    near_term_debt = _num(metrics.get("near_term_debt_krw")) or ((total_debt or 0) * 0.2 if total_debt else 0)
    base = (total_debt or 0) * floating_pct / 100 + near_term_debt
    impact_100bp = base * 0.01 if base else None
    return {
        "rate_sensitivity_score": _derived_metric(
            "rate_sensitivity_score",
            min(max((impact_100bp or 0) / max(total_debt or 1, 1) * 5000, 0), 100) if impact_100bp is not None else None,
            "score",
            "+100bp impact / total debt proxy",
        ),
        "interest_impact_100bp": _derived_metric("interest_impact_100bp", impact_100bp, "KRW", "floating debt and near-term refi base x 100bp"),
    }


def derive_refinancing_metrics(analysis: dict[str, Any]) -> dict[str, Any]:
    return derive_debt_metrics(analysis)


def derive_disclosure_metrics(analysis: dict[str, Any]) -> dict[str, Any]:
    metrics = analysis["metrics"]
    latest_report_date = str(metrics.get("latest_report_date", "조회 불가"))
    last_90_days_count = _num(metrics.get("last_90_days_count")) or 0
    if latest_report_date == "조회 불가":
        score = None
    else:
        score = min(100, 60 + last_90_days_count * 5)
    return {
        "disclosure_freshness_score": _derived_metric(
            "disclosure_freshness_score",
            score,
            "score",
            "latest periodic disclosure availability and recent disclosure count proxy",
            "Medium" if score is not None else "Not Available",
        )
    }


def derive_data_confidence_score(analysis: dict[str, Any]) -> dict[str, Any]:
    table = analysis.get("confidence_report", pd.DataFrame())
    if table.empty or "Confidence" not in table.columns:
        return _derived_metric("data_confidence_score", None, "score", "source confidence distribution")
    weights = {"High": 100, "Medium": 70, "Low": 40, "Not available": 0, "Not Available": 0}
    scores = [weights.get(str(value), 0) for value in table["Confidence"].tolist()]
    score = sum(scores) / len(scores) if scores else None
    return _derived_metric("data_confidence_score", score, "score", "average confidence score across collected metrics")


def _component_score_from_metric(metric: dict[str, Any], invert: bool = False) -> float | None:
    value = _num(metric_value(metric))
    if value is None:
        return None
    value = max(min(value, 100), 0)
    return 100 - value if invert else value


def _build_risk_model(analysis: dict[str, Any], derived: dict[str, dict[str, Any]]) -> dict[str, Any]:
    metrics = analysis["metrics"]
    ltv = _num(metric_value(derived["core"]["ltv"]))
    cash_to_debt = _num(metric_value(derived["core"]["cash_to_debt"]))
    interest_burden = _num(metric_value(derived["core"]["interest_burden"]))
    refi_pressure = _num(metric_value(derived["debt"]["refinancing_pressure_index"]))
    dividend_buffer_pct = _num(metric_value(derived["core"]["dividend_buffer_pct"]))
    market_signal = _num(metric_value(derived["market"]["market_stress_signal"]))
    data_confidence = _num(metric_value(derived["data_confidence_score"]))

    disclosure_score = None
    if metrics.get("last_90_days_count") is not None:
        latest = str(metrics.get("latest_report_date", "조회 불가"))
        disclosure_score = 25 if latest != "조회 불가" else None

    components = [
        build_component(
            "Leverage",
            None if ltv is None else max((ltv - 35) * 1.6, 0),
            source=_source_for(metrics, "total_debt_krw"),
            confidence=_confidence_for(metrics, "total_debt_krw"),
            explanation="LTV가 높을수록 자산가치 하락과 refinancing 협상에서 완충력이 낮아질 수 있습니다.",
            recommended_action="총차입금, 감정가, 담보 조건을 기준으로 covenant headroom을 재확인하세요.",
        ),
        build_component(
            "Liquidity",
            None if cash_to_debt is None else max(70 - cash_to_debt * 2, 0),
            source=_source_for(metrics, "cash_krw"),
            confidence=_confidence_for(metrics, "cash_krw"),
            explanation="cash-to-debt 비율은 단기 유동성 대응 여력을 보여주는 proxy입니다.",
            recommended_action="현금성자산, 미사용 한도, 배당 지급 일정의 월별 bridge를 확인하세요.",
        ),
        build_component(
            "Interest Rate",
            None if interest_burden is None else min(interest_burden * 2.2, 100),
            source=_source_for(metrics, "interest_expense_krw"),
            confidence=_confidence_for(metrics, "interest_expense_krw"),
            explanation="이자비용 부담은 금리 shock이 AFFO와 배당 buffer로 전달되는 경로입니다.",
            recommended_action="변동금리 비중과 hedge 여부를 treasury 자료로 보완하세요.",
        ),
        build_component(
            "Refinancing",
            refi_pressure,
            source=metrics.get("source_map", {}).get("debt_maturity_wall", "Not Available"),
            confidence="Low" if refi_pressure is not None else "Not Available",
            explanation="단기 만기 비중과 LTV를 결합한 refinancing pressure proxy입니다.",
            recommended_action="1~2년 만기 차입과 금리 재설정 조건을 우선 점검하세요.",
        ),
        build_component(
            "Dividend Sustainability",
            None if dividend_buffer_pct is None else max(55 - dividend_buffer_pct * 0.7, 0),
            source=metric_source(derived["core"]["dividend_buffer"]),
            confidence=metric_confidence(derived["core"]["dividend_buffer"]),
            explanation="배당 buffer는 NOI proxy, 이자비용, 배당금의 단순 차감 지표입니다.",
            recommended_action="FFO/AFFO bridge와 실제 배당 정책을 내부 자료로 검증하세요.",
        ),
        build_component(
            "Market Signal",
            market_signal,
            source=_source_for(metrics, "recent_return_pct"),
            confidence=_confidence_for(metrics, "recent_return_pct"),
            explanation="최근 market return은 투자 의견이 아니라 capital market context 신호입니다.",
            recommended_action="주가 변동 원인을 공시, 금리, 섹터 흐름으로 분해하세요.",
        ),
        build_component(
            "Disclosure Freshness",
            disclosure_score,
            source=metrics.get("source_map", {}).get("latest_disclosure", "OpenDART API"),
            confidence="High" if disclosure_score is not None else "Not Available",
            explanation="최근 정기공시와 주요공시의 최신성은 IR 대응 품질의 전제입니다.",
            recommended_action="최신 사업보고서, 반기보고서, 주요사항보고서를 기준 문서로 지정하세요.",
        ),
        build_component(
            "Data Quality",
            None if data_confidence is None else 100 - data_confidence,
            source="Real Data Pipeline source inventory",
            confidence="Medium" if data_confidence is not None else "Not Available",
            explanation="source/confidence가 높은 metric이 많을수록 CFO Dashboard 신뢰성이 높아집니다.",
            recommended_action="Not Available metric을 내부 KPI dictionary와 공시 parser 개선 과제로 분리하세요.",
        ),
    ]
    return calculate_overall_from_components(components)


def _scenario_action(row: pd.Series) -> str:
    pressure = str(row.get("Refinancing pressure", "Not Available"))
    buffer_value = _num(row.get("Dividend buffer"))
    if pressure in {"High", "Elevated"}:
        return "차입 만기별 refinancing plan과 금리 민감도 bridge를 우선 확인"
    if buffer_value is not None and buffer_value < 0:
        return "배당 buffer와 AFFO 조정 항목을 IR narrative 전에 재검증"
    return "기준 가정과 source confidence를 유지하며 board memo에 반영"


def _build_v12_scenarios(analysis: dict[str, Any], base_score: float | None) -> pd.DataFrame:
    scenarios = analysis.get("scenario_outputs", pd.DataFrame()).copy()
    if scenarios.empty:
        return scenarios
    base_rate = _num(scenarios.iloc[0].get("Scenario 기준금리")) or 0.0
    rows: list[dict[str, Any]] = []
    for _, row in scenarios.iterrows():
        rate = _num(row.get("Scenario 기준금리"))
        buffer = _num(row.get("Dividend buffer"))
        migration = None
        if base_score is not None:
            migration = min(max(base_score + max((rate or base_rate) - base_rate, 0) * 4 + (10 if buffer is not None and buffer < 0 else 0), 0), 100)
        rows.append(
            {
                "Scenario": row.get("Scenario"),
                "Scenario 기준금리": rate,
                "Interest expense impact": row.get("Interest expense impact"),
                "Refinancing rate impact": None if rate is None else rate - base_rate,
                "Dividend buffer impact": buffer,
                "LTV sensitivity": analysis["metrics"].get("ltv_pct"),
                "Refinancing pressure": row.get("Refinancing pressure"),
                "Risk score migration": migration,
                "CFO action": _scenario_action(row),
                "Source/Basis": row.get("Source/Basis", row.get("Basis", "macro scenario assumption")),
            }
        )
    return pd.DataFrame(rows)


def _build_peer_comparison(analysis: dict[str, Any], derived: dict[str, dict[str, Any]]) -> pd.DataFrame:
    metrics = analysis["metrics"]
    rows = [
        {
            "Metric": "LTV",
            "Selected REIT": metric_value(derived["core"]["ltv"]),
            "Peer Average": "데이터 미확보",
            "Top / Bottom Context": "Peer financial metrics는 실시간 OpenDART 수집 성공 시 확장",
            "Source": metric_source(derived["core"]["ltv"]),
            "Confidence": metric_confidence(derived["core"]["ltv"]),
        },
        {
            "Metric": "Market Cap",
            "Selected REIT": metrics.get("market_cap_krw"),
            "Peer Average": "데이터 미확보",
            "Top / Bottom Context": "KRX/public market data 수집 성공 시 peer average 산출",
            "Source": _source_for(metrics, "market_cap_krw"),
            "Confidence": _confidence_for(metrics, "market_cap_krw"),
        },
        {
            "Metric": "Disclosure Freshness",
            "Selected REIT": metrics.get("latest_report_date"),
            "Peer Average": "데이터 미확보",
            "Top / Bottom Context": "OpenDART disclosure list를 peer 전체로 확장 예정",
            "Source": metrics.get("source_map", {}).get("latest_disclosure", "OpenDART API"),
            "Confidence": "High" if metrics.get("latest_report_date") not in {None, "조회 불가"} else "Not Available",
        },
        {
            "Metric": "Rate Sensitivity",
            "Selected REIT": metric_value(derived["macro"]["rate_sensitivity_score"]),
            "Peer Average": "데이터 미확보",
            "Top / Bottom Context": "변동금리 비중과 만기 구조 자동 파싱 후 peer 비교 가능",
            "Source": metric_source(derived["macro"]["rate_sensitivity_score"]),
            "Confidence": metric_confidence(derived["macro"]["rate_sensitivity_score"]),
        },
        {
            "Metric": "Refinancing Pressure",
            "Selected REIT": metric_value(derived["debt"]["refinancing_pressure_index"]),
            "Peer Average": "데이터 미확보",
            "Top / Bottom Context": "차입 만기 구조 parser 정확도 개선 후 peer ranking 가능",
            "Source": metric_source(derived["debt"]["refinancing_pressure_index"]),
            "Confidence": metric_confidence(derived["debt"]["refinancing_pressure_index"]),
        },
    ]
    return pd.DataFrame(rows)


def build_real_reit_dashboard_model(
    selected_reit: Any,
    user_inputs: dict[str, float | None] | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    analysis = build_real_reit_metrics_bundle(selected_reit, user_inputs=user_inputs, force_refresh=force_refresh)
    core = derive_core_financial_metrics(analysis)
    debt = derive_debt_metrics(analysis)
    market = derive_market_metrics(analysis)
    dividend = derive_dividend_metrics(analysis)
    macro = derive_macro_sensitivity(analysis)
    disclosure = derive_disclosure_metrics(analysis)
    data_confidence_score = derive_data_confidence_score(analysis)
    derived = {
        "core": core,
        "debt": debt,
        "market": market,
        "dividend": dividend,
        "macro": macro,
        "disclosure": disclosure,
        "data_confidence_score": data_confidence_score,
    }
    risk_model = _build_risk_model(analysis, derived)
    component_frame = components_to_frame(risk_model["components"])
    scenario_frame = _build_v12_scenarios(analysis, risk_model.get("overall_score"))
    bundle = analysis["public_data"]["real_data_bundle"]
    collected_metrics = build_collected_metrics_table(bundle)
    return {
        "analysis": analysis,
        "profile": analysis["profile"],
        "metrics": analysis["metrics"],
        "derived": derived,
        "risk_model": risk_model,
        "risk_components": component_frame,
        "cfo_alerts": _build_alerts_from_risk_model(risk_model),
        "scenario_outputs": scenario_frame,
        "debt_maturity_wall": analysis["debt_maturity_wall"],
        "peer_comparison": _build_peer_comparison(analysis, derived),
        "source_inventory": build_source_inventory(bundle),
        "collected_metrics": collected_metrics,
        "missing_metrics": bundle.get("missing_metrics", []),
        "confidence_distribution": confidence_distribution(bundle),
        "parsed_evidence_snippets": bundle.get("parsed_tables", {}).get("report_evidence_snippets", []),
        "raw_bundle": bundle,
    }


def _build_alerts_from_risk_model(risk_model: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(risk_model.get("top_drivers", [])[:5], start=1):
        level = item.get("level", "Not Available")
        severity = "High" if level == "High" else "Watch" if level in {"Elevated", "Moderate"} else "Low"
        rows.append(
            {
                "Priority": index,
                "Severity": severity,
                "Alert": item.get("component", ""),
                "Why": item.get("explanation", ""),
                "CFO Action": item.get("recommended_cfo_action", ""),
                "Source": item.get("source", ""),
                "Confidence": item.get("confidence", "Not Available"),
            }
        )
    if not rows:
        rows.append(
            {
                "Priority": 1,
                "Severity": "Watch",
                "Alert": "Real data coverage",
                "Why": "API key 또는 공개 데이터 부족으로 CFO-grade component score가 제한적입니다.",
                "CFO Action": "OpenDART API key, ECOS key, 내부 treasury 자료 연결 상태를 확인하세요.",
                "Source": "Real Data Pipeline",
                "Confidence": "Not Available",
            }
        )
    return pd.DataFrame(rows)
