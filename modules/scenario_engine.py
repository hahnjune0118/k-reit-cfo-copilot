from __future__ import annotations

import numpy as np
import pandas as pd


CURRENT_YEAR = 2026


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return float(numerator) / float(denominator)


def debt_profile(debt: pd.DataFrame, current_year: int = CURRENT_YEAR) -> dict[str, float]:
    total_debt = float(debt["principal_krw_bn"].sum())
    near_term = debt[debt["maturity_year"] <= current_year + 2]
    weighted_floating = _safe_divide(
        (debt["principal_krw_bn"] * debt["floating_rate_pct"]).sum(),
        total_debt,
    )
    weighted_coupon = _safe_divide(
        (debt["principal_krw_bn"] * debt["coupon_pct"]).sum(),
        total_debt,
    )
    return {
        "total_debt_krw_bn": total_debt,
        "near_term_debt_krw_bn": float(near_term["principal_krw_bn"].sum()),
        "near_term_debt_pct": _safe_divide(near_term["principal_krw_bn"].sum(), total_debt) * 100,
        "floating_rate_pct": weighted_floating,
        "weighted_coupon_pct": weighted_coupon,
    }


def run_scenario(
    reit: pd.Series,
    assets: pd.DataFrame,
    debt: pd.DataFrame,
    rate_shock_bp: int = 0,
    rent_change_pct: float = 0.0,
    asset_value_change_pct: float = 0.0,
    tax_impact_pct: float = 0.0,
    base_market_rate_pct: float | None = None,
    current_year: int = CURRENT_YEAR,
) -> dict[str, float | str]:
    profile = debt_profile(debt, current_year=current_year)
    base_noi = float(reit["annual_noi_krw_bn"])
    base_ffo = float(reit["annual_ffo_krw_bn"])
    dividend = float(reit["dividend_payout_krw_bn"])
    base_asset_value = float(reit["gross_asset_value_krw_bn"])
    base_ltv_pct = _safe_divide(profile["total_debt_krw_bn"], base_asset_value) * 100
    occupancy = float(reit["occupancy_pct"])
    wale = float(reit["wale_years"])

    rent_delta = base_noi * rent_change_pct / 100
    adjusted_noi = base_noi + rent_delta

    if base_market_rate_pct is None or pd.isna(base_market_rate_pct):
        base_market_rate_pct = profile["weighted_coupon_pct"]
    market_rate_gap_bp = (float(base_market_rate_pct) - profile["weighted_coupon_pct"]) * 100
    effective_rate_shock_bp = rate_shock_bp + market_rate_gap_bp
    scenario_market_rate_pct = float(base_market_rate_pct) + rate_shock_bp / 100

    floating_debt = profile["total_debt_krw_bn"] * profile["floating_rate_pct"] / 100
    near_term_debt = profile["near_term_debt_krw_bn"]
    floating_interest_delta = floating_debt * effective_rate_shock_bp / 10000
    refinancing_interest_delta = near_term_debt * max(effective_rate_shock_bp, 0) / 10000 * 0.35
    total_interest_delta = floating_interest_delta + refinancing_interest_delta

    tax_delta = adjusted_noi * tax_impact_pct / 100
    ffo_estimate = base_ffo + rent_delta - total_interest_delta
    maintenance_capex_reserve = float((assets["noi_krw_bn"] * assets["capex_need_pct"] / 100).sum())
    affo_estimate = ffo_estimate - maintenance_capex_reserve - tax_delta
    tax_adjusted_cash_flow = affo_estimate

    adjusted_asset_value = base_asset_value * (1 + asset_value_change_pct / 100)
    stressed_ltv_pct = _safe_divide(profile["total_debt_krw_bn"], adjusted_asset_value) * 100
    ltv_change_pctp = stressed_ltv_pct - base_ltv_pct
    dividend_coverage = _safe_divide(tax_adjusted_cash_flow, dividend)
    dividend_buffer = tax_adjusted_cash_flow - dividend + float(reit["cash_balance_krw_bn"]) * 0.25

    near_term_share = profile["near_term_debt_pct"] / 100
    interest_burden_pct = _safe_divide(total_interest_delta, max(base_ffo, 1)) * 100
    refinancing_risk_score = np.clip(
        near_term_share * 45
        + (profile["floating_rate_pct"] / 100) * 25
        + max(stressed_ltv_pct - 45, 0) * 1.2
        + interest_burden_pct * 1.6,
        0,
        100,
    )
    dividend_score = np.clip(
        55
        + (dividend_coverage - 1) * 85
        + (occupancy - 97) * 2.5
        + (wale - 4.5) * 4
        - near_term_share * 18
        - max(stressed_ltv_pct - 50, 0) * 1.5,
        0,
        100,
    )

    return {
        "reit_name": str(reit["reit_name"]),
        "base_noi_krw_bn": base_noi,
        "scenario_adjusted_noi_krw_bn": adjusted_noi,
        "base_ffo_krw_bn": base_ffo,
        "ffo_estimate_krw_bn": ffo_estimate,
        "maintenance_capex_reserve_krw_bn": maintenance_capex_reserve,
        "affo_estimate_krw_bn": affo_estimate,
        "dividend_payout_krw_bn": dividend,
        "total_debt_krw_bn": profile["total_debt_krw_bn"],
        "near_term_debt_krw_bn": profile["near_term_debt_krw_bn"],
        "near_term_debt_pct": profile["near_term_debt_pct"],
        "floating_rate_pct": profile["floating_rate_pct"],
        "weighted_coupon_pct": profile["weighted_coupon_pct"],
        "base_market_rate_pct": float(base_market_rate_pct),
        "scenario_market_rate_pct": float(scenario_market_rate_pct),
        "market_rate_gap_bp": float(market_rate_gap_bp),
        "effective_rate_shock_bp": float(effective_rate_shock_bp),
        "rent_delta_krw_bn": rent_delta,
        "interest_delta_krw_bn": total_interest_delta,
        "interest_expense_impact_krw_bn": total_interest_delta,
        "tax_delta_krw_bn": tax_delta,
        "tax_adjusted_cash_flow_krw_bn": tax_adjusted_cash_flow,
        "dividend_coverage": dividend_coverage,
        "dividend_buffer_krw_bn": dividend_buffer,
        "adjusted_asset_value_krw_bn": adjusted_asset_value,
        "base_ltv_pct": base_ltv_pct,
        "stressed_ltv_pct": stressed_ltv_pct,
        "ltv_change_pctp": ltv_change_pctp,
        "refinancing_risk_score": float(refinancing_risk_score),
        "dividend_sustainability_score": float(dividend_score),
        "dividend_status": classify_dividend_status(dividend_coverage),
        "refinancing_status": classify_risk(refinancing_risk_score),
        "scenario_label": scenario_label(rate_shock_bp, rent_change_pct, asset_value_change_pct, tax_impact_pct),
    }


def scenario_label(
    rate_shock_bp: int,
    rent_change_pct: float,
    asset_value_change_pct: float,
    tax_impact_pct: float,
) -> str:
    return (
        f"금리 {rate_shock_bp:+}bp | rent {rent_change_pct:+.1f}% | "
        f"asset value {asset_value_change_pct:+.1f}% | tax impact {tax_impact_pct:+.1f}%"
    )


def classify_dividend_status(coverage: float) -> str:
    if coverage >= 1.15:
        return "Resilient"
    if coverage >= 1.0:
        return "Defensible"
    if coverage >= 0.9:
        return "Watch"
    return "Pressure"


def classify_risk(score: float) -> str:
    if score >= 70:
        return "High"
    if score >= 45:
        return "Medium"
    return "Low"


def scenario_waterfall(scenario: dict[str, float | str]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"driver": "Base FFO", "amount_krw_bn": scenario["base_ffo_krw_bn"], "measure": "absolute"},
            {"driver": "Rent change", "amount_krw_bn": scenario["rent_delta_krw_bn"], "measure": "relative"},
            {"driver": "금리/refi shock", "amount_krw_bn": -scenario["interest_delta_krw_bn"], "measure": "relative"},
            {"driver": "Capex reserve", "amount_krw_bn": -scenario["maintenance_capex_reserve_krw_bn"], "measure": "relative"},
            {"driver": "Tax impact", "amount_krw_bn": -scenario["tax_delta_krw_bn"], "measure": "relative"},
            {"driver": "AFFO estimate", "amount_krw_bn": scenario["affo_estimate_krw_bn"], "measure": "total"},
        ]
    )


def scenario_summary_table(base_case: dict[str, float | str], scenario: dict[str, float | str]) -> pd.DataFrame:
    rows = [
        ("Scenario-adjusted NOI", "KRW bn", "base_noi_krw_bn", "scenario_adjusted_noi_krw_bn"),
        ("Interest expense impact", "KRW bn", "interest_expense_impact_krw_bn", "interest_expense_impact_krw_bn"),
        ("FFO estimate", "KRW bn", "base_ffo_krw_bn", "ffo_estimate_krw_bn"),
        ("AFFO estimate", "KRW bn", "affo_estimate_krw_bn", "affo_estimate_krw_bn"),
        ("LTV", "%", "base_ltv_pct", "stressed_ltv_pct"),
        ("Dividend buffer", "KRW bn", "dividend_buffer_krw_bn", "dividend_buffer_krw_bn"),
        ("Refinancing Risk Score", "score", "refinancing_risk_score", "refinancing_risk_score"),
    ]
    summary = []
    for metric, unit, base_key, scenario_key in rows:
        base_value = float(base_case[base_key])
        scenario_value = float(scenario[scenario_key])
        summary.append(
            {
                "Metric": metric,
                "Base": base_value,
                "Scenario": scenario_value,
                "Change": scenario_value - base_value,
                "Unit": unit,
            }
        )
    return pd.DataFrame(summary)


def cfo_interpretation(scenario: dict[str, float | str]) -> dict[str, str]:
    buffer = float(scenario["dividend_buffer_krw_bn"])
    coverage = float(scenario["dividend_coverage"])
    ltv_change = float(scenario["ltv_change_pctp"])
    risk_score = float(scenario["refinancing_risk_score"])
    risk_level = str(scenario["refinancing_status"])

    if buffer < 0:
        buffer_view = "배당 buffer가 음수로 전환되어 배당 정책 재검토가 필요합니다."
    elif coverage < 1.0:
        buffer_view = "dividend coverage가 1.0x를 하회해 현금성 buffer와 배당 timing 점검이 필요합니다."
    else:
        buffer_view = "dividend coverage는 1.0x 이상이나 금리와 rent stress에 따른 buffer 축소 여부를 모니터링해야 합니다."

    if ltv_change > 3:
        ltv_view = "자산가치 하락으로 LTV가 의미 있게 상승해 lender covenant와 refinancing capacity 확인이 필요합니다."
    elif ltv_change > 0:
        ltv_view = "LTV가 상승했지만 단기적으로 관리 가능한 범위인지 covenant headroom 확인이 필요합니다."
    else:
        ltv_view = "LTV 부담은 완화되거나 제한적이며 cash-flow impact가 더 중요한 판단 변수입니다."

    if risk_score >= 70:
        action_view = "High risk 구간입니다. 24개월 내 maturity, floating-rate exposure, lender term sheet를 우선 확인해야 합니다."
    elif risk_score >= 45:
        action_view = "Medium risk 구간입니다. refinancing timetable과 금리 민감도를 board memo에 명확히 반영해야 합니다."
    else:
        action_view = "Low risk 구간입니다. downside scenario에서 배당 buffer와 LTV가 동시에 악화되는지 추적해야 합니다."

    return {
        "핵심 변화": buffer_view,
        "재무적 영향": f"{ltv_view} 현재 refinancing risk level은 {risk_level}이며 Risk Score는 {risk_score:.0f}/100입니다.",
        "CFO가 확인해야 할 사항": action_view,
    }


def run_peer_scenarios(
    reits: pd.DataFrame,
    assets: pd.DataFrame,
    debt: pd.DataFrame,
    rate_shock_bp: int = 0,
    rent_change_pct: float = 0.0,
    asset_value_change_pct: float = 0.0,
    tax_impact_pct: float = 0.0,
    base_market_rate_pct: float | None = None,
) -> pd.DataFrame:
    rows = []
    for _, reit in reits.iterrows():
        reit_assets = assets[assets["reit_id"] == reit["reit_id"]]
        reit_debt = debt[debt["reit_id"] == reit["reit_id"]]
        scenario = run_scenario(
            reit,
            reit_assets,
            reit_debt,
            rate_shock_bp=rate_shock_bp,
            rent_change_pct=rent_change_pct,
            asset_value_change_pct=asset_value_change_pct,
            tax_impact_pct=tax_impact_pct,
            base_market_rate_pct=base_market_rate_pct,
        )
        rows.append(scenario)
    return pd.DataFrame(rows)
