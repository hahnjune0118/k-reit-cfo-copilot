from __future__ import annotations

from typing import Any

import pandas as pd

from modules.macro_assumptions import build_rate_scenarios, load_macro_assumptions
from modules.real_data_pipeline import build_metric_with_source, build_real_data_bundle


DATA_UNAVAILABLE = "데이터 미확보"
USER_INPUT_REQUIRED = "사용자 입력 필요"
MANUAL_VALIDATION = "manual validation 필요"
DISCLOSURE_ESTIMATE = "공시 기반 추정"
CALC_LIMITED = "산출 제한"
AUTO_COLLECTION_MISSING = "자동 수집 시도 후 미확보"
INFERRED_PROXY = "공시/시장 데이터 기반 proxy"
USER_OVERRIDE = "사용자 입력 보완값"


def _get_value(container: Any, key: str, default: Any = "") -> Any:
    return container.get(key, default) if hasattr(container, "get") else default


def _safe_pct(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return float(numerator) / float(denominator) * 100


def _present(value: object) -> bool:
    return value is not None and not pd.isna(value)


def _metric_value(metric: dict[str, Any] | None) -> Any:
    if not isinstance(metric, dict):
        return None
    return metric.get("value")


def _metric_source(metric: dict[str, Any] | None, fallback: str = AUTO_COLLECTION_MISSING) -> str:
    if not isinstance(metric, dict):
        return fallback
    return str(metric.get("source") or metric.get("data_source") or fallback)


def _metric_confidence(metric: dict[str, Any] | None) -> str:
    if not isinstance(metric, dict):
        return "Not available"
    return str(metric.get("confidence") or metric.get("confidence_level") or "Not available")


def _confidence_label(score: float) -> str:
    if score >= 75:
        return "High"
    if score >= 45:
        return "Medium"
    if score >= 20:
        return "Low"
    return "Not available"


def _risk_label(score: float | None) -> str:
    if score is None:
        return CALC_LIMITED
    if score >= 75:
        return "High"
    if score >= 55:
        return "Elevated"
    if score >= 35:
        return "Moderate"
    return "Low"


def _score_leverage(ltv_pct: float | None) -> float | None:
    if ltv_pct is None:
        return None
    return max(min((float(ltv_pct) - 30) * 1.6, 100), 0)


def _score_liquidity(cash: float | None, total_debt: float | None) -> float | None:
    ratio = _safe_pct(cash, total_debt)
    if ratio is None:
        return None
    return max(min(70 - ratio * 2.0, 100), 0)


def _score_interest_burden(interest_expense: float | None, revenue_or_noi: float | None) -> float | None:
    ratio = _safe_pct(interest_expense, revenue_or_noi)
    if ratio is None:
        return None
    return max(min(ratio * 2.2, 100), 0)


def _score_refinancing(near_term_pct: float | None, ltv_pct: float | None) -> float | None:
    if near_term_pct is None and ltv_pct is None:
        return None
    near_term = float(near_term_pct or 0)
    ltv = max(float(ltv_pct or 0) - 45, 0)
    return max(min(near_term * 1.1 + ltv * 1.2, 100), 0)


def _score_dividend(buffer: float | None, dividend: float | None) -> float | None:
    if buffer is None or dividend in (None, 0):
        return None
    ratio = float(buffer) / max(float(dividend), 1)
    return max(min(55 - ratio * 70, 100), 0)


def _score_macro(base_rate: float | None, spread: float | None) -> float | None:
    if base_rate is None and spread is None:
        return None
    return max(min(float(base_rate or 0) * 9 + float(spread or 0) * 12, 100), 0)


def _score_disclosure(disclosures: pd.DataFrame) -> float | None:
    if disclosures.empty:
        return None
    if "freshness_days" not in disclosures.columns:
        return 30
    days = pd.to_numeric(disclosures["freshness_days"], errors="coerce").dropna()
    if days.empty:
        return 30
    latest_days = float(days.min())
    return max(min((latest_days - 30) / 3, 100), 0)


def _score_market(recent_return: float | None) -> float | None:
    if recent_return is None:
        return None
    return max(min(45 - float(recent_return) * 1.2, 100), 0)


def build_real_reit_profile(selected_reit) -> dict[str, object]:
    return {
        "real_reit_name": str(_get_value(selected_reit, "real_reit_name", "선택 REIT") or "선택 REIT"),
        "ticker": str(_get_value(selected_reit, "ticker", "")),
        "corp_code": str(_get_value(selected_reit, "corp_code", "")),
        "notes": str(_get_value(selected_reit, "notes", "")),
        "source_type": "local real REIT master",
    }


def collect_real_reit_public_data(selected_reit, force_refresh: bool = False) -> dict[str, object]:
    bundle = build_real_data_bundle(selected_reit, force_refresh=force_refresh)
    market_rates = _market_rates_from_bundle(bundle)
    assumptions = load_macro_assumptions()
    macro_data = bundle["macro_data"]
    return {
        "real_data_bundle": bundle,
        "disclosures": bundle["disclosure_frame"],
        "disclosure_summary": _summarize_disclosures(bundle["disclosure_frame"]),
        "market_rates": market_rates,
        "macro_assumptions": assumptions,
        "base_rate": _macro_metric_to_rate_dict(macro_data.get("base_rate")),
        "refinancing_rate": _macro_refinancing_dict(macro_data),
        "rate_scenarios": macro_data.get("scenarios") if isinstance(macro_data.get("scenarios"), pd.DataFrame) else build_rate_scenarios(market_rates, assumptions),
    }


def _market_rates_from_bundle(bundle: dict[str, object]) -> pd.DataFrame:
    try:
        from modules.real_data_loader import load_real_market_rate_data

        return load_real_market_rate_data(use_api=True)
    except Exception:
        base = _metric_value(bundle.get("macro_data", {}).get("base_rate")) if isinstance(bundle.get("macro_data"), dict) else None
        frame = pd.DataFrame(
            [{"date": pd.Timestamp.today().normalize(), "market_rate_pct": base, "stat_code": "fallback", "item_code": "fallback", "source": "macro assumption"}]
        ).dropna(subset=["market_rate_pct"])
        frame.attrs["is_fallback"] = True
        frame.attrs["status_message"] = "ECOS 금리 데이터가 없거나 API fallback 상태입니다."
        return frame


def _summarize_disclosures(disclosures: pd.DataFrame) -> dict[str, object]:
    try:
        from modules.real_insights import summarize_disclosure_insights

        return summarize_disclosure_insights(disclosures)
    except Exception:
        return {
            "latest_disclosure": "조회 불가",
            "latest_periodic_report": "조회 불가",
            "latest_report_date_available": "조회 불가",
            "last_90_days_count": 0,
        }


def _macro_metric_to_rate_dict(metric: dict[str, Any] | None) -> dict[str, object]:
    return {
        "rate_pct": _metric_value(metric),
        "date": metric.get("as_of", "조회 불가") if isinstance(metric, dict) else "조회 불가",
        "source": _metric_source(metric, "macro assumption layer"),
        "basis": _metric_source(metric, "macro assumption layer"),
        "is_fallback": _metric_confidence(metric) != "High",
    }


def _macro_refinancing_dict(macro_data: dict[str, Any]) -> dict[str, object]:
    base = macro_data.get("base_rate", {})
    spread = macro_data.get("refinancing_spread", {})
    refi = macro_data.get("refinancing_rate_assumption", {})
    return {
        "base_rate_pct": _metric_value(base),
        "refinancing_spread_pct": _metric_value(spread),
        "refinancing_rate_pct": _metric_value(refi),
        "source": _metric_source(refi, "ECOS / macro assumption layer"),
        "basis": "ECOS / macro assumption layer",
        "is_fallback": _metric_confidence(refi) != "High",
    }


def _first_available_metric(bundle: dict[str, Any], locations: list[tuple[str, str]]) -> tuple[Any, dict[str, Any]]:
    for section, key in locations:
        source = bundle.get(section, {})
        if not isinstance(source, dict):
            continue
        metric = source.get(key)
        value = _metric_value(metric)
        if value is not None:
            return value, metric
    return None, build_metric_with_source("missing", None, "", AUTO_COLLECTION_MISSING, "Not available")


def _choose_metric_or_user(
    metric_value: Any,
    metric: dict[str, Any],
    user_value: float | None,
    name: str,
    unit: str = "KRW",
) -> tuple[Any, dict[str, Any]]:
    if metric_value is not None:
        return metric_value, metric
    if user_value is not None:
        return user_value, build_metric_with_source(name, user_value, unit, USER_OVERRIDE, "Medium", "자동 수집 후 사용자가 보완한 값입니다.")
    return None, build_metric_with_source(name, None, unit, AUTO_COLLECTION_MISSING, "Not available")


def estimate_real_reit_key_metrics(
    selected_reit,
    public_data: dict[str, object],
    assumptions: pd.DataFrame | None = None,
    user_inputs: dict[str, float | None] | None = None,
) -> dict[str, object]:
    del assumptions
    user_inputs = user_inputs or {}
    profile = build_real_reit_profile(selected_reit)
    bundle = public_data["real_data_bundle"]
    disclosure_summary = public_data.get("disclosure_summary", {})
    base_rate = public_data.get("base_rate", {})
    refi_rate = public_data.get("refinancing_rate", {})

    total_assets_value, total_assets_metric = _first_available_metric(bundle, [("financials", "total_assets")])
    total_debt_value, total_debt_metric = _first_available_metric(bundle, [("financials", "total_debt"), ("financials", "borrowings")])
    revenue_value, revenue_metric = _first_available_metric(bundle, [("financials", "revenue"), ("reit_specific", "rental_revenue")])
    operating_income_value, operating_income_metric = _first_available_metric(bundle, [("financials", "operating_income")])
    annual_noi_value, annual_noi_metric = _first_available_metric(bundle, [("reit_specific", "rental_revenue"), ("financials", "operating_income")])
    dividend_value, dividend_metric = _first_available_metric(bundle, [("reit_specific", "dividend_amount")])
    interest_value, interest_metric = _first_available_metric(bundle, [("financials", "finance_cost")])
    cash_value, cash_metric = _first_available_metric(bundle, [("financials", "cash_and_equivalents")])
    short_debt_value, short_debt_metric = _first_available_metric(bundle, [("financials", "short_term_debt"), ("financials", "current_liabilities")])
    long_debt_value, long_debt_metric = _first_available_metric(bundle, [("financials", "long_term_debt")])
    market_cap_value, market_cap_metric = _first_available_metric(bundle, [("market_data", "market_cap")])
    latest_price_value, latest_price_metric = _first_available_metric(bundle, [("market_data", "latest_price")])
    recent_return_value, recent_return_metric = _first_available_metric(bundle, [("market_data", "recent_return")])

    total_assets, total_assets_metric = _choose_metric_or_user(
        total_assets_value, total_assets_metric, user_inputs.get("total_assets_krw"), "total_assets"
    )
    total_debt, total_debt_metric = _choose_metric_or_user(
        total_debt_value, total_debt_metric, user_inputs.get("total_debt_krw"), "total_debt"
    )
    annual_noi, annual_noi_metric = _choose_metric_or_user(
        annual_noi_value, annual_noi_metric, user_inputs.get("annual_noi_krw"), "annual_noi"
    )
    dividend, dividend_metric = _choose_metric_or_user(
        dividend_value, dividend_metric, user_inputs.get("dividend_krw"), "dividend"
    )

    ltv_pct = _safe_pct(total_debt, total_assets)
    near_term_debt = short_debt_value if short_debt_value is not None else None
    near_term_debt_source = _metric_source(short_debt_metric)
    near_term_pct = _safe_pct(near_term_debt, total_debt)
    if near_term_pct is None and user_inputs.get("near_term_debt_pct") is not None and total_debt is not None:
        near_term_pct = user_inputs["near_term_debt_pct"]
        near_term_debt = total_debt * near_term_pct / 100
        near_term_debt_source = USER_OVERRIDE

    avg_coupon = user_inputs.get("average_coupon_pct")
    if avg_coupon is None and total_debt and interest_value:
        avg_coupon = _safe_pct(float(interest_value), float(total_debt))
    if avg_coupon is None:
        avg_coupon = refi_rate.get("refinancing_rate_pct")

    floating_pct = user_inputs.get("floating_debt_pct")
    if interest_value is None and total_debt is not None and avg_coupon is not None:
        interest_value = total_debt * float(avg_coupon) / 100
        interest_metric = build_metric_with_source(
            "interest_expense",
            interest_value,
            "KRW",
            INFERRED_PROXY,
            "Low",
            "총차입금과 refinancing rate/coupon proxy 기반 예비 이자비용 추정입니다.",
        )

    dividend_buffer = annual_noi - dividend - (interest_value or 0) if annual_noi is not None and dividend is not None else None
    dividend_buffer_metric = build_metric_with_source(
        "dividend_buffer",
        dividend_buffer,
        "KRW",
        "calculated from available real/proxy metrics" if dividend_buffer is not None else AUTO_COLLECTION_MISSING,
        "Low" if dividend_buffer is not None else "Not available",
        "NOI proxy, 배당금, 이자비용을 단순 차감한 MVP 지표입니다.",
    )

    metric_details = {
        "total_assets_krw": total_assets_metric,
        "total_debt_krw": total_debt_metric,
        "annual_noi_krw": annual_noi_metric,
        "dividend_krw": dividend_metric,
        "interest_expense_krw": interest_metric,
        "cash_krw": cash_metric,
        "short_term_debt_krw": short_debt_metric,
        "long_term_debt_krw": long_debt_metric,
        "market_cap_krw": market_cap_metric,
        "latest_price_krw": latest_price_metric,
        "recent_return_pct": recent_return_metric,
        "dividend_buffer_krw": dividend_buffer_metric,
        "base_rate_pct": bundle["macro_data"].get("base_rate", build_metric_with_source("base_rate", None, "%", AUTO_COLLECTION_MISSING, "Not available")),
        "refinancing_spread_pct": bundle["macro_data"].get(
            "refinancing_spread",
            build_metric_with_source("refinancing_spread", None, "%", AUTO_COLLECTION_MISSING, "Not available"),
        ),
        "refinancing_rate_pct": bundle["macro_data"].get(
            "refinancing_rate_assumption",
            build_metric_with_source("refinancing_rate_assumption", None, "%", AUTO_COLLECTION_MISSING, "Not available"),
        ),
    }

    source_map = {key: _metric_source(metric) for key, metric in metric_details.items()}
    source_map.update(
        {
            "base_rate_pct": base_rate.get("basis", "ECOS / macro assumption layer"),
            "refinancing_spread_pct": "ECOS / macro assumption layer",
            "ltv_pct": "calculated from OpenDART/user-confirmed metrics" if ltv_pct is not None else AUTO_COLLECTION_MISSING,
            "debt_maturity_wall": near_term_debt_source if near_term_debt is not None else AUTO_COLLECTION_MISSING,
            "latest_disclosure": "OpenDART API" if not public_data["disclosures"].attrs.get("is_fallback", True) else AUTO_COLLECTION_MISSING,
        }
    )

    return {
        "reit_name": profile["real_reit_name"],
        "latest_disclosure": disclosure_summary.get("latest_disclosure", "조회 불가"),
        "latest_periodic_report": disclosure_summary.get("latest_periodic_report", "조회 불가"),
        "latest_report_date": disclosure_summary.get("latest_report_date_available", "조회 불가"),
        "last_90_days_count": disclosure_summary.get("last_90_days_count", 0),
        "base_rate_pct": base_rate.get("rate_pct"),
        "base_rate_date": base_rate.get("date", "조회 불가"),
        "base_rate_source": base_rate.get("source", "ECOS / macro assumption layer"),
        "base_rate_basis": base_rate.get("basis", "ECOS / macro assumption layer"),
        "refinancing_rate_pct": refi_rate.get("refinancing_rate_pct"),
        "refinancing_spread_pct": refi_rate.get("refinancing_spread_pct"),
        "total_assets_krw": total_assets,
        "total_debt_krw": total_debt,
        "annual_noi_krw": annual_noi,
        "revenue_krw": revenue_value,
        "operating_income_krw": operating_income_value,
        "dividend_krw": dividend,
        "floating_debt_pct": floating_pct,
        "near_term_debt_pct": near_term_pct,
        "near_term_debt_krw": near_term_debt,
        "average_coupon_pct": avg_coupon,
        "interest_expense_krw": interest_value,
        "cash_krw": cash_value,
        "market_cap_krw": market_cap_value,
        "latest_price_krw": latest_price_value,
        "recent_return_pct": recent_return_value,
        "ltv_pct": ltv_pct,
        "dividend_buffer_krw": dividend_buffer,
        "metric_details": metric_details,
        "source_map": source_map,
        "missing_metrics": bundle.get("missing_metrics", []),
        "data_sources": bundle.get("data_sources", []),
    }


def build_real_reit_risk_indicators(metrics: dict[str, object], assumptions: pd.DataFrame | None = None) -> pd.DataFrame:
    del assumptions
    disclosures = metrics.get("_disclosures")
    disclosures_frame = disclosures if isinstance(disclosures, pd.DataFrame) else pd.DataFrame()
    categories = [
        {
            "Category": "leverage",
            "Indicator": "LTV / leverage",
            "Risk Score": _score_leverage(metrics.get("ltv_pct")),
            "Source": metrics["source_map"].get("ltv_pct", AUTO_COLLECTION_MISSING),
            "Confidence": "Medium" if metrics.get("ltv_pct") is not None else "Not available",
            "Interpretation": "총차입금과 총자산이 확보되면 LTV 기반 leverage pressure를 산출합니다.",
        },
        {
            "Category": "liquidity",
            "Indicator": "Cash-to-debt liquidity",
            "Risk Score": _score_liquidity(metrics.get("cash_krw"), metrics.get("total_debt_krw")),
            "Source": metrics["source_map"].get("cash_krw", AUTO_COLLECTION_MISSING),
            "Confidence": _metric_confidence(metrics["metric_details"].get("cash_krw")),
            "Interpretation": "현금및현금성자산과 총차입금의 상대 규모를 통해 liquidity buffer를 봅니다.",
        },
        {
            "Category": "interest_burden",
            "Indicator": "Interest burden",
            "Risk Score": _score_interest_burden(metrics.get("interest_expense_krw"), metrics.get("annual_noi_krw") or metrics.get("revenue_krw")),
            "Source": metrics["source_map"].get("interest_expense_krw", AUTO_COLLECTION_MISSING),
            "Confidence": _metric_confidence(metrics["metric_details"].get("interest_expense_krw")),
            "Interpretation": "이자비용이 NOI 또는 영업수익 proxy 대비 어느 정도 부담인지 확인합니다.",
        },
        {
            "Category": "refinancing",
            "Indicator": "Refinancing / maturity pressure",
            "Risk Score": _score_refinancing(metrics.get("near_term_debt_pct"), metrics.get("ltv_pct")),
            "Source": metrics["source_map"].get("debt_maturity_wall", AUTO_COLLECTION_MISSING),
            "Confidence": "Low" if metrics.get("near_term_debt_pct") is not None else "Not available",
            "Interpretation": "정확한 maturity table이 없으면 단기차입금 또는 유동부채 기반 proxy로 표시합니다.",
        },
        {
            "Category": "dividend",
            "Indicator": "Dividend buffer",
            "Risk Score": _score_dividend(metrics.get("dividend_buffer_krw"), metrics.get("dividend_krw")),
            "Source": metrics["source_map"].get("dividend_buffer_krw", AUTO_COLLECTION_MISSING),
            "Confidence": _metric_confidence(metrics["metric_details"].get("dividend_buffer_krw")),
            "Interpretation": "NOI proxy, 이자비용, 배당금 기반의 단순 buffer입니다.",
        },
        {
            "Category": "macro",
            "Indicator": "Macro rate pressure",
            "Risk Score": _score_macro(metrics.get("base_rate_pct"), metrics.get("refinancing_spread_pct")),
            "Source": "ECOS / macro assumption layer",
            "Confidence": "Low",
            "Interpretation": "기준금리와 refinancing spread proxy가 조달비용 민감도에 미치는 압력을 봅니다.",
        },
        {
            "Category": "disclosure",
            "Indicator": "Disclosure freshness",
            "Risk Score": _score_disclosure(disclosures_frame),
            "Source": metrics["source_map"].get("latest_disclosure", AUTO_COLLECTION_MISSING),
            "Confidence": "High" if not disclosures_frame.empty else "Not available",
            "Interpretation": "OpenDART 최근 공시 목록의 최신성만 factual data로 표시합니다.",
        },
        {
            "Category": "market",
            "Indicator": "Market signal",
            "Risk Score": _score_market(metrics.get("recent_return_pct")),
            "Source": metrics["source_map"].get("recent_return_pct", AUTO_COLLECTION_MISSING),
            "Confidence": _metric_confidence(metrics["metric_details"].get("recent_return_pct")),
            "Interpretation": "최근 가격 변화율은 valuation context이며 투자 의견으로 해석하지 않습니다.",
        },
    ]

    rows: list[dict[str, object]] = []
    for item in categories:
        score = item["Risk Score"]
        rows.append(
            {
                "Category": item["Category"],
                "Indicator": item["Indicator"],
                "Risk Score": score,
                "Risk Label": _risk_label(score),
                "Source": item["Source"],
                "Confidence": item["Confidence"],
                "Basis": item["Source"],
                "Interpretation": item["Interpretation"],
            }
        )
    return pd.DataFrame(rows)


def calculate_real_reit_risk_score(indicators: pd.DataFrame) -> dict[str, object]:
    scored = indicators[pd.to_numeric(indicators["Risk Score"], errors="coerce").notna()].copy()
    if len(scored) < 4:
        return {
            "risk_score": None,
            "risk_score_display": CALC_LIMITED,
            "risk_label": CALC_LIMITED,
            "confidence_level": "Low" if len(scored) else "Not available",
            "basis": "자동 수집/파싱 후에도 4개 미만의 risk component만 산출되어 partial indicators만 표시합니다.",
            "scored_categories": len(scored),
        }

    score = float(scored["Risk Score"].mean())
    confidence_points = min(len(scored) * 12, 80)
    high_confidence = scored["Confidence"].isin(["High", "Medium"]).sum()
    confidence_points += min(high_confidence * 4, 20)
    return {
        "risk_score": score,
        "risk_score_display": f"{score:.0f}/100",
        "risk_label": _risk_label(score),
        "confidence_level": _confidence_label(confidence_points),
        "basis": "available OpenDART/market/macro data + clearly labeled proxy calculations",
        "scored_categories": len(scored),
    }


def build_real_reit_cfo_alerts(
    metrics: dict[str, object],
    indicators: pd.DataFrame,
    assumptions: pd.DataFrame | None = None,
) -> pd.DataFrame:
    del assumptions
    rows: list[dict[str, object]] = []
    scored = indicators[pd.to_numeric(indicators["Risk Score"], errors="coerce").notna()].copy()
    for _, row in scored.sort_values("Risk Score", ascending=False).head(3).iterrows():
        rows.append(
            {
                "Alert": str(row["Indicator"]),
                "Why it matters": str(row["Interpretation"]),
                "Recommended action": "공시 원문, treasury 자료, 내부 KPI dictionary로 source와 계산식을 확인하세요.",
                "Basis": str(row["Source"]),
                "Confidence": str(row["Confidence"]),
            }
        )

    missing = [item for item in metrics.get("missing_metrics", []) if item in {"ffo", "affo", "wale", "tenant_concentration", "asset_level_noi", "debt_maturity_wall"}]
    if missing:
        rows.append(
            {
                "Alert": "핵심 REIT KPI 자동 수집 한계",
                "Why it matters": "FFO, AFFO, WALE, 임차인 집중도, 자산별 NOI는 CFO narrative와 Investor Q&A 품질에 직접 영향을 줍니다.",
                "Recommended action": "OpenDART 원문, 투자보고서, 회사 IR 자료를 확인하고 내부 자료로 validation하세요.",
                "Basis": "자동 수집 시도 후 미확보",
                "Confidence": "Not available",
            }
        )

    if not rows:
        rows.append(
            {
                "Alert": "자동 수집 데이터 검토",
                "Why it matters": "현재 확보된 factual data와 proxy 계산 결과를 CFO attention view에 연결했습니다.",
                "Recommended action": "Data Quality 페이지에서 source와 confidence를 확인하세요.",
                "Basis": "Real Data Pipeline",
                "Confidence": "Low",
            }
        )

    result = pd.DataFrame(rows).drop_duplicates("Alert").head(3)
    result.insert(0, "Rank", range(1, len(result) + 1))
    return result


def build_real_reit_debt_maturity_wall(
    selected_reit,
    public_data: dict[str, object],
    user_inputs: dict[str, float | None] | None = None,
) -> pd.DataFrame:
    del selected_reit, user_inputs
    bundle = public_data["real_data_bundle"]
    financials = bundle.get("financials", {})
    total_debt = _metric_value(financials.get("total_debt")) if isinstance(financials, dict) else None
    short_debt = _metric_value(financials.get("short_term_debt")) if isinstance(financials, dict) else None
    current_liabilities = _metric_value(financials.get("current_liabilities")) if isinstance(financials, dict) else None
    long_debt = _metric_value(financials.get("long_term_debt")) if isinstance(financials, dict) else None
    bonds = _metric_value(financials.get("bonds_payable")) if isinstance(financials, dict) else None

    if total_debt is None:
        wall = pd.DataFrame(columns=["구간", "금액", "Source", "Status"])
        wall.attrs["status_message"] = "자동 수집을 시도했으나 차입 만기 구조와 총차입금이 미확보되었습니다."
        return wall

    near_term = short_debt if short_debt is not None else current_liabilities
    rows = []
    if near_term is not None:
        rows.append(
            {
                "구간": "0~1년",
                "금액": float(near_term),
                "Source": "OpenDART 재무제표 기반 proxy",
                "Status": "Inferred",
            }
        )
    if long_debt is not None:
        rows.append(
            {
                "구간": "1년 이상",
                "금액": float(long_debt),
                "Source": "OpenDART 장기차입금 계정",
                "Status": "Disclosure Parsed",
            }
        )
    if bonds is not None:
        rows.append(
            {
                "구간": "사채 / 미분류",
                "금액": float(bonds),
                "Source": "OpenDART 사채 계정",
                "Status": "Disclosure Parsed",
            }
        )

    known = sum(row["금액"] for row in rows)
    residual = max(float(total_debt) - known, 0)
    if residual > 0:
        rows.append(
            {
                "구간": "미분류",
                "금액": residual,
                "Source": "총차입금 - 식별 차입금 residual",
                "Status": "Manual Validation Recommended",
            }
        )

    wall = pd.DataFrame(rows)
    wall.attrs["status_message"] = "공시 재무제표 계정 기반 debt maturity wall proxy입니다. 실제 차입 약정별 만기는 원문 주석 검증이 필요합니다."
    return wall


def build_real_reit_scenario_outputs(
    metrics: dict[str, object],
    assumptions: pd.DataFrame | None = None,
    user_inputs: dict[str, float | None] | None = None,
    rate_scenarios: pd.DataFrame | None = None,
) -> pd.DataFrame:
    del user_inputs
    scenarios = rate_scenarios if rate_scenarios is not None else build_rate_scenarios(None, assumptions)
    total_debt = metrics.get("total_debt_krw")
    annual_noi = metrics.get("annual_noi_krw")
    dividend = metrics.get("dividend_krw")
    near_term_debt = metrics.get("near_term_debt_krw") or 0
    floating_pct = metrics.get("floating_debt_pct")
    base_refi_rate = float(metrics.get("refinancing_rate_pct") or 0)

    rows: list[dict[str, object]] = []
    for _, scenario in scenarios.iterrows():
        rate = float(scenario["Scenario 기준금리"])
        interest_impact = None
        dividend_buffer = None
        pressure = CALC_LIMITED
        if total_debt is not None:
            floating_base = total_debt * float(floating_pct or 0) / 100
            refi_base = float(near_term_debt or 0)
            if floating_pct is None and refi_base == 0:
                refi_base = total_debt * 0.20
            rate_delta = max(rate - base_refi_rate, 0)
            interest_impact = floating_base * rate_delta / 100 + refi_base * rate_delta / 100
            pressure_score = _score_refinancing(metrics.get("near_term_debt_pct"), metrics.get("ltv_pct"))
            pressure = _risk_label(pressure_score)
        if annual_noi is not None and dividend is not None:
            dividend_buffer = annual_noi - dividend - (interest_impact or 0)
        rows.append(
            {
                "Scenario": scenario["Scenario"],
                "Scenario 기준금리": rate,
                "Interest expense impact": interest_impact,
                "Dividend buffer": dividend_buffer,
                "Refinancing pressure": pressure,
                "Source/Basis": scenario["Basis"],
            }
        )
    return pd.DataFrame(rows)


def build_real_reit_data_confidence_report(metrics: dict[str, object]) -> pd.DataFrame:
    rows = []
    details = metrics.get("metric_details", {})
    for metric_name, metric in details.items():
        confidence = _metric_confidence(metric)
        source = _metric_source(metric)
        rows.append(
            {
                "Metric": metric_name,
                "Source/Basis": source,
                "Confidence": confidence,
                "Value status": "확보" if _metric_value(metric) is not None else "미확보",
                "Validation": "권장" if confidence in {"High", "Medium"} else "필요",
                "Note": str(metric.get("note", "")) if isinstance(metric, dict) else "",
            }
        )

    for source in metrics.get("data_sources", []):
        rows.append(
            {
                "Metric": f"Source status - {source.get('source', '')}",
                "Source/Basis": source.get("source", ""),
                "Confidence": source.get("status", "Not available"),
                "Value status": "연결/시도",
                "Validation": "권장",
                "Note": "; ".join(str(item) for item in source.get("warnings", []) if item),
            }
        )
    return pd.DataFrame(rows)


def build_real_mode_analysis(selected_reit, user_inputs: dict[str, float | None] | None = None, force_refresh: bool = False) -> dict[str, object]:
    if not force_refresh:
        try:
            import streamlit as st

            force_refresh = bool(st.session_state.pop("force_refresh_real_data", False))
        except Exception:
            force_refresh = False
    profile = build_real_reit_profile(selected_reit)
    public_data = collect_real_reit_public_data(selected_reit, force_refresh=force_refresh)
    metrics = estimate_real_reit_key_metrics(
        selected_reit,
        public_data,
        assumptions=public_data["macro_assumptions"],
        user_inputs=user_inputs,
    )
    metrics["_disclosures"] = public_data["disclosures"]
    indicators = build_real_reit_risk_indicators(metrics, public_data["macro_assumptions"])
    score = calculate_real_reit_risk_score(indicators)
    alerts = build_real_reit_cfo_alerts(metrics, indicators, public_data["macro_assumptions"])
    wall = build_real_reit_debt_maturity_wall(selected_reit, public_data, user_inputs)
    scenarios = build_real_reit_scenario_outputs(
        metrics,
        public_data["macro_assumptions"],
        user_inputs,
        public_data["rate_scenarios"],
    )
    confidence = build_real_reit_data_confidence_report(metrics)
    return {
        "profile": profile,
        "public_data": public_data,
        "metrics": metrics,
        "indicators": indicators,
        "score": score,
        "alerts": alerts,
        "debt_maturity_wall": wall,
        "scenario_outputs": scenarios,
        "confidence_report": confidence,
    }
