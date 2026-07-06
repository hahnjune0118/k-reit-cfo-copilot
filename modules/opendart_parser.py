from __future__ import annotations

from typing import Any

import pandas as pd

from modules.api_clients.config import get_dart_api_key
from modules.opendart_client import fetch_disclosure_list, latest_periodic_disclosure
from modules.real_data_pipeline import download_and_parse_opendart_report, parse_reit_specific_metrics as _pipeline_parse_reit_specific_metrics
from modules.source_confidence import not_available_metric


def get_latest_periodic_report(selected_reit: Any) -> dict[str, Any]:
    disclosures = fetch_disclosure_list(selected_reit)
    return latest_periodic_disclosure(disclosures)


def download_report_document(rcp_no: str, api_key: str | None = None) -> bytes:
    del rcp_no, api_key
    return b""


def extract_text_from_report(document: Any) -> str:
    if isinstance(document, bytes):
        return document.decode("utf-8", errors="ignore")
    return str(document or "")


def extract_tables_from_report(document: Any) -> list[pd.DataFrame]:
    del document
    return []


def _parsed_bundle_from_text(report_text: str) -> dict[str, Any]:
    parsed = _pipeline_parse_reit_specific_metrics(report_text)
    return {
        "metrics": parsed.get("metrics", {}),
        "source_snippets": parsed.get("evidence_snippets", []),
        "confidence": "Low" if parsed.get("evidence_snippets") else "Not Available",
        "parser_warnings": [parsed.get("parser_note", "")],
    }


def parse_debt_notes(document: Any) -> dict[str, Any]:
    text = extract_text_from_report(document)
    parsed = _parsed_bundle_from_text(text)
    return {
        "debt_maturity_wall": parsed["metrics"].get("debt_maturity_wall", not_available_metric("debt_maturity_wall", "KRW")),
        "source_snippets": parsed["source_snippets"],
        "confidence": parsed["confidence"],
        "parser_warnings": parsed["parser_warnings"],
    }


def parse_dividend_data(document: Any) -> dict[str, Any]:
    parsed = _parsed_bundle_from_text(extract_text_from_report(document))
    return {
        "dividend_amount": parsed["metrics"].get("dividend_amount", not_available_metric("dividend_amount", "KRW")),
        "source_snippets": parsed["source_snippets"],
        "confidence": parsed["confidence"],
        "parser_warnings": parsed["parser_warnings"],
    }


def parse_portfolio_assets(document: Any) -> dict[str, Any]:
    parsed = _parsed_bundle_from_text(extract_text_from_report(document))
    return {
        "asset_level_noi": parsed["metrics"].get("asset_level_noi", not_available_metric("asset_level_noi", "KRW")),
        "source_snippets": parsed["source_snippets"],
        "confidence": parsed["confidence"],
        "parser_warnings": parsed["parser_warnings"],
    }


def parse_rental_revenue(document: Any) -> dict[str, Any]:
    parsed = _parsed_bundle_from_text(extract_text_from_report(document))
    return {
        "rental_revenue": parsed["metrics"].get("rental_revenue", not_available_metric("rental_revenue", "KRW")),
        "source_snippets": parsed["source_snippets"],
        "confidence": parsed["confidence"],
        "parser_warnings": parsed["parser_warnings"],
    }


def parse_interest_rate_terms(document: Any) -> dict[str, Any]:
    parsed = _parsed_bundle_from_text(extract_text_from_report(document))
    return {
        "interest_rate_terms": not_available_metric(
            "interest_rate_terms",
            "%",
            source="OpenDART Parsed",
            note="공시 원문에서 금리 조건을 구조화하려면 추가 parser 검증이 필요합니다.",
        ),
        "source_snippets": parsed["source_snippets"],
        "confidence": parsed["confidence"],
        "parser_warnings": parsed["parser_warnings"],
    }


def parse_maturity_schedule(document: Any) -> dict[str, Any]:
    return parse_debt_notes(document)


def parse_reit_specific_metrics_from_report(selected_reit: Any, api_key: str | None = None, force_refresh: bool = False) -> dict[str, Any]:
    key = get_dart_api_key() if api_key is None else api_key
    return download_and_parse_opendart_report(selected_reit, api_key=str(key or ""), force_refresh=force_refresh)


def parse_reit_specific_metrics(document: Any, tables: Any = None) -> dict[str, Any]:
    del tables
    return _parsed_bundle_from_text(extract_text_from_report(document))
