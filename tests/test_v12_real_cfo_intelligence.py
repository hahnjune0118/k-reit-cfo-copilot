from __future__ import annotations

import pandas as pd

from modules.account_mapper import build_financial_metric_table, extract_financial_metric, match_account
from modules.macro_assumptions import build_rate_scenarios, calculate_credit_spread_proxy
from modules.real_data_loader import load_real_reit_master
from modules.real_data_pipeline import build_metric_with_source, build_real_data_bundle
from modules.real_reit_analytics import build_real_reit_dashboard_model
from modules.real_reit_risk_model import build_component, calculate_overall_from_components
from modules.source_confidence import build_metric, build_source_inventory


def test_v12_metric_wrapper_has_required_source_schema() -> None:
    metric = build_metric("total_assets", 1_000, "KRW", "OpenDART financial statement API", "High", calculation_method="account mapping")

    assert {
        "value",
        "unit",
        "source",
        "source_type",
        "confidence",
        "as_of",
        "calculation_method",
        "warning",
    }.issubset(metric)
    assert metric["source_type"] == "OpenDART API"
    assert metric["confidence"] == "High"


def test_v12_account_mapper_handles_korean_reit_accounts() -> None:
    frame = pd.DataFrame(
        [
            {"account_nm": "자산총계", "thstrm_amount": "1,000"},
            {"account_nm": "부채총계", "thstrm_amount": "450"},
            {"account_nm": "현금 및 현금성자산", "thstrm_amount": "120"},
            {"account_nm": "영업활동현금흐름", "thstrm_amount": "80"},
        ]
    )

    assert match_account("자산총계") == "total_assets"
    assert match_account("현금 및 현금성자산") == "cash_and_equivalents"
    assert extract_financial_metric(frame, "operating_cash_flow")["value"] == 80
    table = build_financial_metric_table(frame)
    assert {"total_assets", "total_liabilities", "cash_and_equivalents", "operating_cash_flow"}.issubset(
        set(table["mapped_metric"])
    )


def test_v12_real_bundle_without_api_key_marks_company_financials_not_available(monkeypatch) -> None:
    import modules.real_data_pipeline as pipeline

    monkeypatch.setattr(pipeline, "collect_market_data", lambda selected, force_refresh=False: {"metrics": {}, "source": "test", "trading_date": "", "warnings": []})
    monkeypatch.setattr(pipeline, "collect_reit_association_data", lambda selected: {"source": "test association", "source_urls": [], "warnings": []})
    monkeypatch.setattr(pipeline, "collect_company_ir_data", lambda selected: {"source": "test ir", "source_urls": [], "warnings": []})

    bundle = build_real_data_bundle(load_real_reit_master().iloc[0], api_keys={"dart": ""})
    required_financials = [
        "total_assets",
        "total_liabilities",
        "total_equity",
        "total_debt",
        "cash",
        "revenue",
        "operating_income",
        "net_income",
        "interest_expense",
    ]

    for metric_name in required_financials:
        metric = bundle["financials"][metric_name]
        assert metric["value"] is None
        assert metric["confidence"] == "Not Available"
        assert metric["source"] == "OpenDART API key missing"
        assert metric["source_type"] == "Not Available"
    assert "DART_API_KEY missing: OpenDART financial statement extraction skipped." in bundle["warnings"]


def test_v12_risk_model_supports_partial_and_full_scores() -> None:
    partial = calculate_overall_from_components(
        [
            build_component("Leverage", 40),
            build_component("Liquidity", 30),
            build_component("Interest Rate", 55),
            build_component("Refinancing", None),
        ]
    )
    full = calculate_overall_from_components([build_component(f"Component {idx}", 50) for idx in range(5)])

    assert partial["score_type"] == "Partial"
    assert full["score_type"] == "Full"


def test_v12_macro_credit_spread_and_scenarios() -> None:
    spread = calculate_credit_spread_proxy({"value": 3.0}, {"value": 4.4})
    scenarios = build_rate_scenarios(base_rate=3.5, credit_spread=1.2)

    assert spread["value"] == 1.4000000000000004
    assert {"Base Case", "Rate +50bp", "Rate +100bp", "Credit Spread +50bp", "Combined Stress", "Downside Macro", "Upside Macro"}.issubset(
        set(scenarios["Scenario"])
    )


def test_v12_master_data_has_api_first_fields() -> None:
    master = load_real_reit_master()
    required = {
        "real_reit_name",
        "display_name",
        "stock_code",
        "corp_code",
        "market",
        "sector",
        "sponsor",
        "amc",
        "listing_date",
        "homepage_url",
        "ir_url",
        "dart_corp_name",
        "notes",
    }

    assert required.issubset(master.columns)
    assert {"SK리츠", "롯데리츠", "ESR켄달스퀘어리츠"}.issubset(set(master["real_reit_name"]))


def test_v12_dashboard_model_does_not_use_sample_values(monkeypatch) -> None:
    import modules.real_mode_analytics as analytics

    empty = pd.DataFrame(columns=["report_nm", "rcept_dt", "report_type", "rcept_no", "freshness_days"])
    empty.attrs["is_fallback"] = True
    empty.attrs["status_message"] = "test fallback"
    scenarios = build_rate_scenarios(base_rate=3.5, credit_spread=1.2)
    bundle = {
        "selected_reit_name": "테스트 REIT",
        "ticker": "000000.KS",
        "collection_timestamp": "2026-07-06T00:00:00+00:00",
        "financials": {
            "total_assets": build_metric_with_source("total_assets", None, "KRW", "OpenDART API key missing", "Not Available", as_of=None),
            "total_debt": build_metric_with_source("total_debt", None, "KRW", "OpenDART API key missing", "Not Available", as_of=None),
        },
        "market_data": {},
        "macro_data": {
            "base_rate": build_metric("base_rate", 3.5, "%", "Fallback Assumption", "Low"),
            "refinancing_spread": build_metric("refinancing_spread", 1.2, "%", "Fallback Assumption", "Low"),
            "refinancing_rate_assumption": build_metric("refinancing_rate_assumption", 4.7, "%", "Fallback Assumption", "Low"),
            "scenarios": scenarios,
        },
        "reit_specific": {},
        "disclosures": [],
        "disclosure_frame": empty,
        "parsed_tables": {"opendart_accounts": [], "report_evidence_snippets": []},
        "data_sources": [{"source": "OpenDART financial statement API", "status": "Not Available", "as_of": None, "warnings": []}],
        "missing_metrics": ["total_assets", "total_debt"],
        "warnings": [],
        "force_refresh": False,
    }

    monkeypatch.setattr(analytics, "build_real_data_bundle", lambda selected, force_refresh=False: bundle)
    model = build_real_reit_dashboard_model(load_real_reit_master().iloc[0], user_inputs={})
    source_text = " ".join(str(value) for value in model["collected_metrics"]["Source"])

    assert "sample_reits.csv" not in source_text
    assert model["risk_model"]["score_type"] in {"Limited", "Partial", "Full"}


def test_v12_source_inventory_is_dataframe() -> None:
    inventory = build_source_inventory(
        {
            "data_sources": [
                {"source": "OpenDART financial statement API", "status": "High", "as_of": "2026", "warnings": []},
                {"source": "ECOS API", "status": "Low", "as_of": "2026", "warnings": ["fallback"]},
            ]
        }
    )

    assert {"Source", "Source Type", "Status", "As of", "Warnings"}.issubset(inventory.columns)

