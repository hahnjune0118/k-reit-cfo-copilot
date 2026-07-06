from __future__ import annotations

import inspect
from pathlib import Path

import pandas as pd

from modules.real_data_loader import load_real_disclosure_data, load_real_market_rate_data, load_real_reit_master
from modules.macro_assumptions import collect_credit_spread_proxy
from modules.real_data_pipeline import (
    build_metric_with_source,
    build_real_data_bundle,
    map_opendart_account_name,
)
from modules.real_mode_analytics import (
    AUTO_COLLECTION_MISSING,
    CALC_LIMITED,
    USER_OVERRIDE,
    build_real_mode_analysis,
    build_real_reit_debt_maturity_wall,
    build_real_reit_data_confidence_report,
    calculate_real_reit_risk_score,
)
from modules.real_mode_components import (
    get_data_availability_matrix,
    render_ecos_market_rate_panel,
    render_data_availability_matrix,
    render_real_mode_cfo_interpretation,
)
from modules.real_insights import (
    calculate_manual_real_scenario,
    data_availability_matrix,
    summarize_disclosure_insights,
    summarize_ecos_insights,
)
from modules.ui_components import INDEXED_PAGE_LABELS, format_krw, real_reit_selector_options


def _empty_disclosures() -> pd.DataFrame:
    frame = pd.DataFrame(columns=["report_nm", "rcept_dt", "report_type", "rcept_no", "freshness_days"])
    frame.attrs["is_fallback"] = True
    frame.attrs["status_message"] = "test fallback"
    return frame


def _metric(name: str, value, unit: str = "KRW", source: str = "test source", confidence: str = "Medium"):
    return build_metric_with_source(name, value, unit, source, confidence)


def _fake_bundle(financials: dict | None = None, market_data: dict | None = None, missing_metrics: list[str] | None = None):
    scenarios = pd.DataFrame(
        [
            {"Scenario": "Base", "기준금리": 3.5, "credit spread": 1.1, "refinancing spread": 1.3, "Scenario 기준금리": 4.8, "Source": "test", "Basis": "test macro"},
            {"Scenario": "Downside", "기준금리": 4.1, "credit spread": 1.4, "refinancing spread": 1.7, "Scenario 기준금리": 5.8, "Source": "test", "Basis": "test macro"},
            {"Scenario": "Upside", "기준금리": 3.1, "credit spread": 0.9, "refinancing spread": 1.1, "Scenario 기준금리": 4.2, "Source": "test", "Basis": "test macro"},
        ]
    )
    return {
        "selected_reit_name": "테스트 REIT",
        "ticker": "000000.KS",
        "collection_timestamp": "2026-07-06T00:00:00+00:00",
        "financials": financials or {},
        "market_data": market_data or {},
        "macro_data": {
            "base_rate": _metric("base_rate", 3.5, "%", "ECOS fallback", "Low"),
            "refinancing_spread": _metric("refinancing_spread", 1.35, "%", "macro assumption", "Low"),
            "refinancing_rate_assumption": _metric("refinancing_rate_assumption", 4.85, "%", "ECOS / macro assumption layer", "Low"),
            "scenarios": scenarios,
        },
        "reit_specific": {},
        "disclosures": [],
        "disclosure_frame": _empty_disclosures(),
        "parsed_tables": {"opendart_accounts": [], "report_evidence_snippets": []},
        "data_sources": [{"source": "test source", "status": "Low", "as_of": "2026", "warnings": []}],
        "missing_metrics": missing_metrics or [],
        "warnings": [],
        "force_refresh": False,
    }


def test_v11_format_krw_uses_korean_units() -> None:
    assert format_krw(50_000_000) == "5,000만 원"
    assert format_krw(1_000_000_000) == "10억 원"
    assert format_krw(100_000_000_000) == "1,000억 원"
    assert format_krw(1_200_000_000_000) == "1.2조 원"
    assert format_krw(None) == "데이터 없음"
    assert "bn" not in format_krw(1_000_000_000)


def test_v11_indexed_sidebar_labels_exist() -> None:
    assert INDEXED_PAGE_LABELS == [
        "0. App",
        "1. 고객 Pain Point",
        "2. CFO Executive Dashboard",
        "3. Scenario Engine",
        "4. 자산 및 차입 리스크",
        "5. AI Memo & Investor Q&A",
        "6. 데이터 품질 · AI Readiness",
    ]


def test_v11_real_reit_selector_options_are_company_names_only() -> None:
    options = real_reit_selector_options(load_real_reit_master())

    assert "SK리츠" in options
    assert "롯데리츠" in options
    assert "ESR켄달스퀘어리츠" in options
    assert all(".KS" not in option for option in options)
    assert all("corp_code" not in option for option in options)


def test_real_reit_master_loads() -> None:
    master = load_real_reit_master()

    assert len(master) >= 5
    assert {"real_reit_name", "ticker", "corp_code", "notes"}.issubset(master.columns)
    assert master["real_reit_name"].notna().all()


def test_real_mode_disclosure_fallback_without_api_key(monkeypatch) -> None:
    import modules.real_data_loader as real_data_loader

    monkeypatch.setattr(real_data_loader, "_has_dart_key", lambda: False)
    master = load_real_reit_master()
    result = load_real_disclosure_data(master.iloc[0])

    assert result.empty
    assert result.attrs["is_fallback"] is True
    assert result.attrs["api_connected"] is False
    assert "severity" not in result.columns
    assert "decision_risk" not in result.columns


def test_real_market_rate_fallback_without_api() -> None:
    rates = load_real_market_rate_data(use_api=False)

    assert not rates.empty
    assert "market_rate_pct" in rates.columns
    assert rates.attrs["is_fallback"] is True


def test_real_mode_cfo_interpretation_import_and_signature() -> None:
    signature = inspect.signature(render_real_mode_cfo_interpretation)

    assert "selected_reit" in signature.parameters
    assert "disclosure_data" in signature.parameters
    assert "market_rate_data" in signature.parameters
    assert "manual_scenario" in signature.parameters
    assert "disclosures" in signature.parameters
    assert "rates" in signature.parameters
    assert "scenario" in signature.parameters
    assert any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values())


def test_real_mode_data_availability_imports_and_signature() -> None:
    signature = inspect.signature(render_data_availability_matrix)

    assert "matrix" in signature.parameters
    assert "title" in signature.parameters
    assert any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values())


def test_real_mode_components_data_availability_matrix_required_metrics() -> None:
    matrix = get_data_availability_matrix()
    required_metrics = [
        "회사명 / ticker",
        "OpenDART 공시 목록",
        "최근 정기공시",
        "기준금리 / 시장금리",
        "주가 / 시가총액",
        "FFO / AFFO",
        "WALE",
        "임차인 집중도",
        "자산별 NOI",
        "차입 만기 구조",
        "세금효과",
        "Investor Q&A",
    ]

    assert matrix["Metric"].tolist() == required_metrics
    assert {"Metric", "Source", "API availability", "Automation level", "Manual validation required?", "Notes"}.issubset(
        matrix.columns
    )


def test_v11_ecos_panel_is_simplified() -> None:
    source = inspect.getsource(render_ecos_market_rate_panel)

    assert "plotly_chart" not in source
    assert "ECOS source status" not in source
    assert "ECOS 금리 요약" in source


def test_v11_1_metric_wrapper_always_has_source_and_confidence() -> None:
    metric = build_metric_with_source("total_assets", 1_000, "KRW", "OpenDART financial statement API", "High")

    assert metric["value"] == 1_000
    assert metric["unit"] == "KRW"
    assert metric["source"] == "OpenDART financial statement API"
    assert metric["data_source"] == "OpenDART financial statement API"
    assert metric["confidence"] == "High"
    assert metric["confidence_level"] == "High"
    assert "as_of" in metric


def test_v11_1_opendart_account_mapper_matches_korean_names() -> None:
    assert map_opendart_account_name("자산총계") == "total_assets"
    assert map_opendart_account_name("부채 총계") == "total_liabilities"
    assert map_opendart_account_name("현금 및 현금성자산") == "cash_and_equivalents"
    assert map_opendart_account_name("금융비용") == "finance_cost"


def test_v11_1_credit_spread_proxy_calculates_from_assumption_layer() -> None:
    spread = collect_credit_spread_proxy()

    assert spread["name"] == "credit_spread_proxy"
    assert spread["value"] is not None
    assert float(spread["value"]) >= 0
    assert spread["confidence"] in {"Low", "Medium", "High"}


def test_v11_1_real_data_pipeline_returns_bundle_without_api_keys(monkeypatch) -> None:
    import modules.real_data_pipeline as pipeline

    monkeypatch.setattr(pipeline, "collect_market_data", lambda selected, force_refresh=False: {"metrics": {}, "source": "test", "trading_date": "", "warnings": []})
    monkeypatch.setattr(pipeline, "collect_reit_association_data", lambda selected: {"source": "test association", "source_urls": [], "warnings": []})
    monkeypatch.setattr(pipeline, "collect_company_ir_data", lambda selected: {"source": "test ir", "source_urls": [], "warnings": []})

    selected = load_real_reit_master().iloc[0]
    bundle = build_real_data_bundle(selected, api_keys={"dart": ""})

    assert bundle["selected_reit_name"] == selected["real_reit_name"]
    assert {"financials", "market_data", "macro_data", "reit_specific", "data_sources", "missing_metrics"}.issubset(bundle)
    assert isinstance(bundle["missing_metrics"], list)
    assert bundle["financials"]["total_assets"]["confidence"] == "Not Available"


def test_v11_1_risk_score_calculates_with_at_least_four_components(monkeypatch) -> None:
    import modules.real_mode_analytics as analytics

    financials = {
        "total_assets": _metric("total_assets", 2_000_000_000_000, source="OpenDART financial statement API", confidence="High"),
        "total_debt": _metric("total_debt", 900_000_000_000, source="OpenDART financial statement API", confidence="Medium"),
        "cash_and_equivalents": _metric("cash_and_equivalents", 120_000_000_000, source="OpenDART financial statement API", confidence="High"),
        "finance_cost": _metric("finance_cost", 38_000_000_000, source="OpenDART financial statement API", confidence="High"),
        "operating_income": _metric("operating_income", 100_000_000_000, source="OpenDART financial statement API", confidence="High"),
        "short_term_debt": _metric("short_term_debt", 250_000_000_000, source="OpenDART financial statement API", confidence="Medium"),
    }
    market = {
        "recent_return": _metric("recent_return", -4.0, "%", "public market data", "Low"),
    }
    monkeypatch.setattr(analytics, "build_real_data_bundle", lambda selected, force_refresh=False: _fake_bundle(financials=financials, market_data=market))

    analysis = build_real_mode_analysis(load_real_reit_master().iloc[0], user_inputs={"dividend_krw": 60_000_000_000})

    assert analysis["score"]["risk_score_display"] != CALC_LIMITED
    assert analysis["score"]["scored_categories"] >= 4


def test_v11_1_risk_score_limited_with_fewer_than_four_components() -> None:
    indicators = pd.DataFrame(
        [
            {"Category": "macro", "Risk Score": 40, "Confidence": "Low"},
            {"Category": "market", "Risk Score": None, "Confidence": "Not available"},
        ]
    )

    score = calculate_real_reit_risk_score(indicators)

    assert score["risk_score_display"] == CALC_LIMITED
    assert score["scored_categories"] == 1


def test_v11_1_debt_maturity_wall_proxy_uses_short_term_debt() -> None:
    financials = {
        "total_debt": _metric("total_debt", 1_000_000_000_000, source="OpenDART financial statement API", confidence="Medium"),
        "short_term_debt": _metric("short_term_debt", 300_000_000_000, source="OpenDART financial statement API", confidence="Medium"),
        "long_term_debt": _metric("long_term_debt", 700_000_000_000, source="OpenDART financial statement API", confidence="Medium"),
    }
    public_data = {"real_data_bundle": _fake_bundle(financials=financials)}

    wall = build_real_reit_debt_maturity_wall(load_real_reit_master().iloc[0], public_data)

    assert not wall.empty
    assert "0~1년" in set(wall["구간"])
    assert wall.loc[wall["구간"] == "0~1년", "금액"].iloc[0] == 300_000_000_000
    assert "proxy" in wall.attrs["status_message"]


def test_v11_1_real_mode_does_not_use_sample_mode_fictional_values(monkeypatch) -> None:
    import modules.real_mode_analytics as analytics

    monkeypatch.setattr(analytics, "build_real_data_bundle", lambda selected, force_refresh=False: _fake_bundle())
    analysis = build_real_mode_analysis(load_real_reit_master().iloc[0], user_inputs={})

    source_text = " ".join(str(value) for value in analysis["confidence_report"]["Source/Basis"])
    assert "fictional sample" not in source_text
    assert "sample_reits.csv" not in source_text


def test_v11_1_real_mode_risk_score_can_be_limited_after_collection_attempt(monkeypatch) -> None:
    import modules.real_mode_analytics as analytics

    monkeypatch.setattr(analytics, "build_real_data_bundle", lambda selected, force_refresh=False: _fake_bundle())
    selected = load_real_reit_master().iloc[0]
    analysis = build_real_mode_analysis(selected, user_inputs={})

    assert analysis["score"]["risk_score_display"] == CALC_LIMITED
    assert analysis["score"]["confidence_level"] in {"Low", "Not available"}
    assert AUTO_COLLECTION_MISSING in set(analysis["confidence_report"]["Source/Basis"])


def test_v11_1_real_mode_confidence_report_keeps_source_confidence_labels(monkeypatch) -> None:
    import modules.real_mode_analytics as analytics

    monkeypatch.setattr(analytics, "build_real_data_bundle", lambda selected, force_refresh=False: _fake_bundle())
    selected = load_real_reit_master().iloc[0]
    analysis = build_real_mode_analysis(
        selected,
        user_inputs={
            "total_assets_krw": 2_000_000_000_000,
            "total_debt_krw": 900_000_000_000,
            "annual_noi_krw": 90_000_000_000,
            "dividend_krw": 65_000_000_000,
            "floating_debt_pct": 40.0,
            "near_term_debt_pct": 35.0,
            "average_coupon_pct": 4.2,
        },
    )
    confidence = build_real_reit_data_confidence_report(analysis["metrics"])

    assert analysis["score"]["risk_score_display"] != CALC_LIMITED
    assert USER_OVERRIDE in set(confidence["Source/Basis"])
    assert "ECOS / macro assumption layer" in set(confidence["Source/Basis"]) or "macro assumption" in set(confidence["Source/Basis"])


def test_korean_ui_source_does_not_contain_repeated_question_mark_corruption() -> None:
    roots = [Path("app.py"), Path("pages"), Path("modules"), Path("README.md"), Path("CHANGELOG.md"), Path("VERSION.md")]
    patterns = ["?" * length for length in (2, 3, 4)]
    offenders: list[str] = []

    for root in roots:
        files = [root] if root.is_file() else list(root.rglob("*"))
        for file in files:
            if file.suffix not in {".py", ".md"}:
                continue
            if "__pycache__" in file.parts:
                continue
            text = file.read_text(encoding="utf-8")
            if any(pattern in text for pattern in patterns):
                offenders.append(str(file))

    assert offenders == []


def test_v10_data_availability_matrix_identifies_manual_validation_items() -> None:
    matrix = data_availability_matrix()

    expected_columns = {
        "Metric",
        "Source",
        "API availability",
        "Automation level",
        "Manual validation required?",
        "Notes",
    }
    assert expected_columns.issubset(matrix.columns)
    assert {"FFO / AFFO", "WALE", "임차인 집중도", "자산별 NOI", "차입 만기 구조", "Investor Q&A"}.issubset(
        set(matrix["Metric"])
    )
    manual_rows = matrix[matrix["Metric"].isin(["FFO / AFFO", "WALE", "임차인 집중도", "자산별 NOI"])]
    assert (manual_rows["Manual validation required?"] == "Yes").all()


def test_v10_manual_real_scenario_is_labeled_as_user_input_hypothetical() -> None:
    scenario = calculate_manual_real_scenario(
        real_reit_name="테스트 REIT",
        total_assets=3000,
        total_debt=1400,
        annual_noi=140,
        dividend_amount=95,
        floating_debt_pct=45,
        average_coupon_pct=4.2,
        near_term_debt_pct=45,
        rate_shock_bp=100,
        rent_change_pct=-2.0,
        asset_value_change_pct=-5.0,
        include_tax_effect=True,
        base_market_rate_pct=3.5,
    )

    assert scenario["user_input_label"] == "사용자 입력 기반 예비 시뮬레이션"
    assert scenario["user_input_ltv_pct"] > 0
    assert "user_input_interest_expense_krw_bn" in scenario
    assert "user_input_refinancing_pressure" in scenario
    assert "overall_risk_score" not in scenario


def test_v10_factual_insight_summaries_do_not_emit_investment_judgment() -> None:
    disclosures = load_real_disclosure_data(load_real_reit_master().iloc[0])
    disclosure_summary = summarize_disclosure_insights(disclosures)
    rate_summary = summarize_ecos_insights(load_real_market_rate_data(use_api=False))

    combined_text = " ".join(str(value) for value in {**disclosure_summary, **rate_summary}.values())
    blocked_terms = ["투자 의견", "신용 판단", "매도", "매수", "부정적 Risk Score"]

    assert all(term not in combined_text for term in blocked_terms)
