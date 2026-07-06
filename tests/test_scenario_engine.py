from __future__ import annotations

from numbers import Number

from modules.data_loader import load_all_data
from modules.scenario_engine import run_scenario


def test_run_scenario_for_all_sample_reits() -> None:
    data = load_all_data()

    for _, reit in data["reits"].iterrows():
        reit_id = reit["reit_id"]
        assets = data["assets"][data["assets"]["reit_id"] == reit_id]
        debt = data["debt"][data["debt"]["reit_id"] == reit_id]

        scenario = run_scenario(reit, assets, debt)

        assert isinstance(scenario["dividend_coverage"], Number)
        assert isinstance(scenario["refinancing_risk_score"], Number)
        assert 0 <= float(scenario["refinancing_risk_score"]) <= 100


def test_sample_data_uses_fictional_reit_ids_and_joins() -> None:
    data = load_all_data()
    expected_ids = {"reit_a", "reit_b", "reit_c"}

    assert set(data["reits"]["reit_id"]) == expected_ids
    assert set(data["assets"]["reit_id"]) == expected_ids
    assert set(data["debt"]["reit_id"]) == expected_ids
    assert set(data["flags"]["reit_id"]) == expected_ids
    assert set(data["readiness"]["reit_id"]) == expected_ids

    for table_name in ["assets", "debt", "flags", "readiness"]:
        joined = data[table_name].merge(data["reits"][["reit_id"]], on="reit_id", how="left", indicator=True)
        assert (joined["_merge"] == "both").all(), table_name

    assert set(data["reits"]["ticker"]) == {"999901.KS", "999902.KS", "999903.KS"}
    assert set(data["reits"]["reit_name"]) == {"Alpha Prime REIT", "Beta Retail REIT", "Gamma Logistics REIT"}
