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
    current_year: int = CURRENT_YEAR,
) -> dict[str, float | str]:
    profile = debt_profile(debt, current_year=current_year)
    base_noi = float(reit["annual_noi_krw_bn"])
    base_ffo = float(reit["annual_ffo_krw_bn"])
    dividend = float(reit["dividend_payout_krw_bn"])
    base_asset_value = float(reit["gross_asset_value_krw_bn"])
    occupancy = float(reit["occupancy_pct"])
    wale = float(reit["wale_years"])

    rent_delta = base_noi * rent_change_pct / 100
    adjusted_noi = base_noi + rent_delta

    floating_debt = profile["total_debt_krw_bn"] * profile["floating_rate_pct"] / 100
    near_term_debt = profile["near_term_debt_krw_bn"]
    floating_interest_delta = floating_debt * rate_shock_bp / 10000
    refinancing_interest_delta = near_term_debt * max(rate_shock_bp, 0) / 10000 * 0.35
    total_interest_delta = floating_interest_delta + refinancing_interest_delta

    tax_delta = adjusted_noi * tax_impact_pct / 100
    tax_adjusted_cash_flow = base_ffo + rent_delta - total_interest_delta - tax_delta

    adjusted_asset_value = base_asset_value * (1 + asset_value_change_pct / 100)
    stressed_ltv_pct = _safe_divide(profile["total_debt_krw_bn"], adjusted_asset_value) * 100
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
        "base_ffo_krw_bn": base_ffo,
        "dividend_payout_krw_bn": dividend,
        "total_debt_krw_bn": profile["total_debt_krw_bn"],
        "near_term_debt_krw_bn": profile["near_term_debt_krw_bn"],
        "near_term_debt_pct": profile["near_term_debt_pct"],
        "floating_rate_pct": profile["floating_rate_pct"],
        "weighted_coupon_pct": profile["weighted_coupon_pct"],
        "rent_delta_krw_bn": rent_delta,
        "interest_delta_krw_bn": total_interest_delta,
        "tax_delta_krw_bn": tax_delta,
        "tax_adjusted_cash_flow_krw_bn": tax_adjusted_cash_flow,
        "dividend_coverage": dividend_coverage,
        "dividend_buffer_krw_bn": dividend_buffer,
        "adjusted_asset_value_krw_bn": adjusted_asset_value,
        "stressed_ltv_pct": stressed_ltv_pct,
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
        f"{rate_shock_bp:+}bp rates | {rent_change_pct:+.1f}% rent | "
        f"{asset_value_change_pct:+.1f}% asset value | {tax_impact_pct:+.1f}% tax drag"
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
            {"driver": "Rate/refi shock", "amount_krw_bn": -scenario["interest_delta_krw_bn"], "measure": "relative"},
            {"driver": "Tax impact", "amount_krw_bn": -scenario["tax_delta_krw_bn"], "measure": "relative"},
            {"driver": "Scenario cash flow", "amount_krw_bn": scenario["tax_adjusted_cash_flow_krw_bn"], "measure": "total"},
        ]
    )


def run_peer_scenarios(
    reits: pd.DataFrame,
    assets: pd.DataFrame,
    debt: pd.DataFrame,
    rate_shock_bp: int = 0,
    rent_change_pct: float = 0.0,
    asset_value_change_pct: float = 0.0,
    tax_impact_pct: float = 0.0,
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
        )
        rows.append(scenario)
    return pd.DataFrame(rows)
