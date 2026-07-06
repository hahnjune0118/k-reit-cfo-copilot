from __future__ import annotations

import pytest

from modules.data_loader import load_all_data
from modules.risk_scoring import refinancing_risk_table
from modules.scenario_engine import run_scenario


def test_refinancing_risk_table_matches_run_scenario_baseline() -> None:
    data = load_all_data()
    refi = refinancing_risk_table(data["reits"], data["debt"], data["assets"])

    for _, reit in data["reits"].iterrows():
        reit_id = reit["reit_id"]
        assets = data["assets"][data["assets"]["reit_id"] == reit_id]
        debt = data["debt"][data["debt"]["reit_id"] == reit_id]
        scenario = run_scenario(
            reit,
            assets,
            debt,
            rate_shock_bp=0,
            rent_change_pct=0.0,
            asset_value_change_pct=0.0,
            tax_impact_pct=0.0,
        )
        table_score = float(refi.loc[refi["reit_id"] == reit_id, "refinancing_risk_score"].iloc[0])

        assert table_score == pytest.approx(float(scenario["refinancing_risk_score"]))


def test_refinancing_risk_table_preserves_expected_columns() -> None:
    data = load_all_data()
    refi = refinancing_risk_table(data["reits"], data["debt"], data["assets"])

    expected_columns = {
        "reit_id",
        "reit_name",
        "total_debt_krw_bn",
        "near_term_debt_krw_bn",
        "near_term_debt_pct",
        "floating_rate_pct",
        "weighted_coupon_pct",
        "ltv_pct",
        "refinancing_risk_score",
        "risk_tier",
    }
    assert expected_columns.issubset(refi.columns)
    assert len(refi) == len(data["reits"])
