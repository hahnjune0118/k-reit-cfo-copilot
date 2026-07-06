from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
REAL_REIT_MASTER_FILE = DATA_DIR / "real_reit_master.csv"


REAL_DISCLOSURE_COLUMNS = [
    "real_reit_name",
    "ticker",
    "corp_code",
    "corp_name",
    "report_nm",
    "rcept_dt",
    "report_type",
    "rcept_no",
    "disclosure_link",
    "corp_cls",
    "flr_nm",
    "freshness_days",
    "freshness_indicator",
    "is_key_report",
]


@st.cache_data(show_spinner=False)
def load_real_reit_master() -> pd.DataFrame:
    master = pd.read_csv(REAL_REIT_MASTER_FILE, dtype=str).fillna("")
    master.attrs["source"] = "real_reit_master.csv"
    master.attrs["is_fallback"] = False
    master.attrs["status_message"] = "Real REIT master loaded from local portfolio data."
    return master


def get_selected_real_reit(real_reit_name: str | None = None) -> pd.Series:
    master = load_real_reit_master()
    if master.empty:
        raise ValueError("real_reit_master.csv is empty.")
    if real_reit_name is None:
        return master.iloc[0]
    match = master[master["real_reit_name"] == real_reit_name]
    if match.empty:
        raise ValueError(f"Unknown real REIT name: {real_reit_name}")
    return match.iloc[0]


def _empty_real_disclosure_frame(message: str, source: str = "OpenDART API") -> pd.DataFrame:
    frame = pd.DataFrame(columns=REAL_DISCLOSURE_COLUMNS)
    frame.attrs["source"] = source
    frame.attrs["api_connected"] = False
    frame.attrs["is_fallback"] = True
    frame.attrs["status_message"] = message
    return frame


def _has_dart_key() -> bool:
    try:
        from modules.api_clients.config import has_dart_api_key

        return has_dart_api_key()
    except Exception:
        return False


def _lookup_corp_code(real_reit_name: str) -> tuple[str, str]:
    try:
        from modules.api_clients.dart_client import find_corp_by_name

        matches = find_corp_by_name(real_reit_name)
    except Exception:
        return "", ""

    if matches.empty:
        return "", ""

    first = matches.iloc[0]
    return str(first.get("corp_code", "")).strip(), str(first.get("corp_name", "")).strip()


def _fetch_disclosures(corp_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    try:
        from modules.api_clients.dart_client import fetch_disclosure_list

        return fetch_disclosure_list(corp_code, start_date, end_date)
    except Exception:
        return _empty_real_disclosure_frame("OpenDART client unavailable; disclosure request skipped.")


def classify_report_type(report_name: str) -> str:
    text = str(report_name)
    if "사업보고서" in text:
        return "사업보고서"
    if "반기보고서" in text:
        return "반기보고서"
    if "분기보고서" in text:
        return "분기보고서"
    if "주요사항보고서" in text:
        return "주요사항보고서"
    if "투자설명서" in text:
        return "투자설명서"
    return "기타 공시"


def _freshness_indicator(days: float | int | None) -> str:
    if days is None or pd.isna(days):
        return "조회 불가"
    days = int(days)
    if days <= 30:
        return "Fresh"
    if days <= 90:
        return "Watch"
    return "Stale"


def _parse_api_date(value: str | None, default: date) -> date:
    if not value:
        return default
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return parsed.date()


def load_real_disclosure_data(
    real_reit: pd.Series | dict[str, str],
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    name = str(real_reit.get("real_reit_name", "")).strip()
    ticker = str(real_reit.get("ticker", "")).strip()
    corp_code = str(real_reit.get("corp_code", "")).strip()

    if not _has_dart_key():
        return _empty_real_disclosure_frame("OpenDART API key가 없어 실제 공시 목록을 조회하지 않았습니다.")

    corp_name = ""
    if not corp_code:
        corp_code, corp_name = _lookup_corp_code(name)
    if not corp_code:
        return _empty_real_disclosure_frame("OpenDART corp_code를 찾지 못해 실제 공시 목록을 조회하지 않았습니다.")

    end = _parse_api_date(end_date, date.today())
    start = _parse_api_date(start_date, end - timedelta(days=365))
    disclosures = _fetch_disclosures(corp_code, start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))

    if disclosures.empty:
        return _empty_real_disclosure_frame(
            disclosures.attrs.get("status_message", "OpenDART 공시 응답이 비어 있습니다.")
        )

    result = disclosures.copy()
    result["real_reit_name"] = name
    result["ticker"] = ticker
    result["corp_code"] = corp_code
    result["corp_name"] = result.get("corp_name", corp_name)
    result["report_type"] = result["report_nm"].apply(classify_report_type)
    result["disclosure_link"] = result["rcept_no"].apply(
        lambda value: f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={value}" if str(value).strip() else ""
    )
    result["rcept_dt_parsed"] = pd.to_datetime(result["rcept_dt"], errors="coerce", format="%Y%m%d")
    today = pd.Timestamp.today().normalize()
    result["freshness_days"] = (today - result["rcept_dt_parsed"]).dt.days
    result["freshness_indicator"] = result["freshness_days"].apply(_freshness_indicator)
    result["is_key_report"] = result["report_type"].isin(["사업보고서", "반기보고서", "분기보고서", "주요사항보고서", "투자설명서"])
    result = result.sort_values("rcept_dt", ascending=False)

    result.attrs["source"] = "OpenDART API"
    result.attrs["api_connected"] = True
    result.attrs["is_fallback"] = False
    result.attrs["status_message"] = "OpenDART 공시 목록을 조회했습니다."
    return result[REAL_DISCLOSURE_COLUMNS]


def load_real_market_rate_data(use_api: bool = True) -> pd.DataFrame:
    from modules.data_loader import load_market_rate_data

    return load_market_rate_data(use_api=use_api)
