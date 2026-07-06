from __future__ import annotations

from typing import Any

import pandas as pd

from modules.api_clients.config import get_dart_api_key
from modules.real_data_pipeline import collect_opendart_disclosures, collect_opendart_financials


def has_api_key(api_key: str | None = None) -> bool:
    key = get_dart_api_key() if api_key is None else api_key
    return bool(str(key or "").strip())


def fetch_financial_statement_metrics(
    selected_reit: Any,
    api_key: str | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    key = get_dart_api_key() if api_key is None else api_key
    return collect_opendart_financials(selected_reit, api_key=str(key or ""), force_refresh=force_refresh)


def fetch_disclosure_list(selected_reit: Any, api_key: str | None = None) -> pd.DataFrame:
    key = get_dart_api_key() if api_key is None else api_key
    return collect_opendart_disclosures(selected_reit, api_key=str(key or ""))


def latest_periodic_disclosure(disclosures: pd.DataFrame) -> dict[str, Any]:
    if disclosures.empty:
        return {"report_nm": "조회 불가", "rcept_dt": "", "rcept_no": "", "source": "OpenDART API"}
    data = disclosures.copy()
    if "report_type" in data.columns:
        periodic = data[data["report_type"].isin(["사업보고서", "반기보고서", "분기보고서", "1분기보고서", "3분기보고서"])]
        if not periodic.empty:
            data = periodic
    row = data.iloc[0]
    return {
        "report_nm": str(row.get("report_nm", "")),
        "rcept_dt": str(row.get("rcept_dt", "")),
        "rcept_no": str(row.get("rcept_no", "")),
        "source": "OpenDART API",
    }

