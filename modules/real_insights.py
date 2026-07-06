from __future__ import annotations

import pandas as pd

from modules.scenario_engine import run_scenario


PERIODIC_REPORT_TYPES = {"사업보고서", "반기보고서", "분기보고서"}
KEY_REPORT_TYPES = PERIODIC_REPORT_TYPES | {"주요사항보고서", "투자설명서"}


def data_availability_matrix() -> pd.DataFrame:
    from modules.real_mode_components import get_data_availability_matrix

    return get_data_availability_matrix()


def _blank(value: object, default: str = "조회 불가") -> str:
    if value is None or pd.isna(value):
        return default
    text = str(value).strip()
    return text or default


def summarize_disclosure_insights(disclosures: pd.DataFrame) -> dict[str, object]:
    if disclosures.empty:
        return {
            "source_status": disclosures.attrs.get("status_message", "OpenDART fallback"),
            "latest_disclosure": "조회 불가",
            "latest_periodic_report": "조회 불가",
            "latest_key_report": "조회 불가",
            "last_90_days_count": 0,
            "periodic_update_status": "OpenDART 공시 조회 결과가 없어 확인 불가",
            "latest_report_date_available": "조회 불가",
        }

    data = disclosures.copy()
    data["rcept_dt_parsed"] = pd.to_datetime(data["rcept_dt"], errors="coerce", format="%Y%m%d")
    latest = data.sort_values("rcept_dt", ascending=False).iloc[0]
    periodic = data[data["report_type"].isin(PERIODIC_REPORT_TYPES)].sort_values("rcept_dt", ascending=False)
    key_reports = data[data["report_type"].isin(KEY_REPORT_TYPES)].sort_values("rcept_dt", ascending=False)
    cutoff = pd.Timestamp.today().normalize() - pd.Timedelta(days=90)
    last_90 = int((data["rcept_dt_parsed"] >= cutoff).sum())

    if periodic.empty:
        periodic_status = "최근 조회 범위에서 정기공시를 확인하지 못했습니다."
        latest_periodic = "조회 불가"
        latest_periodic_date = "조회 불가"
    else:
        periodic_row = periodic.iloc[0]
        periodic_status = f"최근 정기공시는 {periodic_row['report_type']}입니다."
        latest_periodic = _blank(periodic_row.get("report_nm"))
        latest_periodic_date = _blank(periodic_row.get("rcept_dt"))

    return {
        "source_status": "OpenDART Connected" if not disclosures.attrs.get("is_fallback", True) else "OpenDART Fallback",
        "latest_disclosure": _blank(latest.get("report_nm")),
        "latest_periodic_report": latest_periodic,
        "latest_key_report": _blank(key_reports.iloc[0].get("report_nm")) if not key_reports.empty else "조회 불가",
        "last_90_days_count": last_90,
        "periodic_update_status": periodic_status,
        "latest_report_date_available": latest_periodic_date,
    }


def ecos_source_status(rates: pd.DataFrame) -> str:
    message = str(rates.attrs.get("status_message", ""))
    if rates.empty:
        return "ECOS Missing API Key" if "key" in message.lower() else "ECOS Fallback"
    if rates.attrs.get("is_fallback", True):
        return "ECOS Missing API Key" if "key" in message.lower() else "ECOS Fallback"
    return "ECOS Connected"


def summarize_ecos_insights(rates: pd.DataFrame) -> dict[str, object]:
    if rates.empty:
        return {
            "source_status": ecos_source_status(rates),
            "latest_rate": None,
            "latest_date": "조회 불가",
            "recent_direction": "조회 불가",
            "scenario_base_rate": None,
            "shock_table": pd.DataFrame(columns=["Scenario", "Shock bp", "Scenario rate"]),
        }

    data = rates.sort_values("date").copy()
    latest = data.iloc[-1]
    latest_rate = float(latest["market_rate_pct"])
    if len(data) >= 2:
        previous_rate = float(data.iloc[-2]["market_rate_pct"])
        if latest_rate > previous_rate:
            direction = "최근 관측치 기준 상승"
        elif latest_rate < previous_rate:
            direction = "최근 관측치 기준 하락"
        else:
            direction = "최근 관측치 기준 보합"
    else:
        direction = "추세 판단을 위한 관측치 부족"

    shock_table = pd.DataFrame(
        [
            {"Scenario": "Base", "Shock bp": 0, "Scenario rate": latest_rate},
            {"Scenario": "+50bp", "Shock bp": 50, "Scenario rate": latest_rate + 0.50},
            {"Scenario": "+100bp", "Shock bp": 100, "Scenario rate": latest_rate + 1.00},
            {"Scenario": "+150bp", "Shock bp": 150, "Scenario rate": latest_rate + 1.50},
        ]
    )

    return {
        "source_status": ecos_source_status(rates),
        "latest_rate": latest_rate,
        "latest_date": _blank(latest.get("date")),
        "recent_direction": direction,
        "scenario_base_rate": latest_rate,
        "shock_table": shock_table,
    }


def calculate_manual_real_scenario(
    real_reit_name: str,
    total_assets: float,
    total_debt: float,
    annual_noi: float,
    dividend_amount: float,
    floating_debt_pct: float,
    average_coupon_pct: float,
    near_term_debt_pct: float,
    rate_shock_bp: int,
    rent_change_pct: float,
    asset_value_change_pct: float,
    include_tax_effect: bool,
    base_market_rate_pct: float | None = None,
) -> dict[str, object]:
    near_term_debt = total_debt * near_term_debt_pct / 100
    long_term_debt = max(total_debt - near_term_debt, 0)
    tax_impact_pct = 1.0 if include_tax_effect else 0.0

    reit = pd.Series(
        {
            "reit_name": real_reit_name,
            "annual_noi_krw_bn": annual_noi,
            "annual_ffo_krw_bn": annual_noi * 0.75,
            "dividend_payout_krw_bn": dividend_amount,
            "gross_asset_value_krw_bn": total_assets,
            "cash_balance_krw_bn": max(annual_noi * 0.20, 1),
            "occupancy_pct": 97.0,
            "wale_years": 4.5,
        }
    )
    assets = pd.DataFrame({"reit_id": ["manual"], "noi_krw_bn": [annual_noi], "capex_need_pct": [5.0]})
    debt = pd.DataFrame(
        [
            {
                "reit_id": "manual",
                "maturity_year": 2027,
                "principal_krw_bn": near_term_debt,
                "coupon_pct": average_coupon_pct,
                "floating_rate_pct": floating_debt_pct,
            },
            {
                "reit_id": "manual",
                "maturity_year": 2031,
                "principal_krw_bn": long_term_debt,
                "coupon_pct": average_coupon_pct,
                "floating_rate_pct": floating_debt_pct,
            },
        ]
    )
    scenario = run_scenario(
        reit,
        assets,
        debt,
        rate_shock_bp=rate_shock_bp,
        rent_change_pct=rent_change_pct,
        asset_value_change_pct=asset_value_change_pct,
        tax_impact_pct=tax_impact_pct,
        base_market_rate_pct=base_market_rate_pct or average_coupon_pct,
    )
    scenario["user_input_ltv_pct"] = total_debt / max(total_assets, 1) * 100
    scenario["user_input_interest_expense_krw_bn"] = total_debt * average_coupon_pct / 100
    scenario["user_input_refinancing_pressure"] = scenario["refinancing_status"]
    scenario["user_input_label"] = "사용자 입력 기반 예비 시뮬레이션"
    return scenario
