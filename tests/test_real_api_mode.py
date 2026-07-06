from __future__ import annotations

import inspect
from pathlib import Path

from modules.real_data_loader import load_real_disclosure_data, load_real_market_rate_data, load_real_reit_master
from modules.real_mode_components import (
    get_data_availability_matrix,
    render_data_availability_matrix,
    render_real_mode_cfo_interpretation,
)
from modules.real_insights import (
    calculate_manual_real_scenario,
    data_availability_matrix,
    summarize_disclosure_insights,
    summarize_ecos_insights,
)


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
