from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import requests
import streamlit as st

from modules.api_clients.config import get_ecos_api_key, has_ecos_api_key


ECOS_BASE_URL = "https://ecos.bok.or.kr/api/StatisticSearch"
DEFAULT_RATE_STAT_CODE = "722Y001"
DEFAULT_RATE_ITEM_CODE = "0101000"
MARKET_RATE_COLUMNS = ["date", "market_rate_pct", "stat_code", "item_code", "source"]


def sample_interest_rate_series(message: str = "ECOS API unavailable; using sample market rate data.") -> pd.DataFrame:
    end = pd.Timestamp.today().normalize()
    dates = pd.bdate_range(end=end, periods=30)
    values = [3.45 + (idx % 5) * 0.01 for idx in range(len(dates))]
    frame = pd.DataFrame(
        {
            "date": dates,
            "market_rate_pct": values,
            "stat_code": DEFAULT_RATE_STAT_CODE,
            "item_code": DEFAULT_RATE_ITEM_CODE,
            "source": "sample",
        }
    )
    frame.attrs["source"] = "sample"
    frame.attrs["api_connected"] = False
    frame.attrs["is_fallback"] = True
    frame.attrs["status_message"] = message
    return frame


def _empty_ecos_frame(message: str) -> pd.DataFrame:
    frame = pd.DataFrame(columns=MARKET_RATE_COLUMNS)
    frame.attrs["source"] = "ECOS API"
    frame.attrs["api_connected"] = False
    frame.attrs["is_fallback"] = True
    frame.attrs["status_message"] = message
    return frame


@st.cache_data(show_spinner=False, ttl=60 * 60)
def fetch_ecos_stat(
    stat_code: str,
    item_code: str,
    start_period: str,
    end_period: str,
    cycle: str = "D",
) -> pd.DataFrame:
    if not has_ecos_api_key():
        return _empty_ecos_frame("ECOS API key missing.")

    url = (
        f"{ECOS_BASE_URL}/{get_ecos_api_key()}/json/kr/1/1000/"
        f"{stat_code}/{cycle}/{start_period}/{end_period}/{item_code}"
    )
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return _empty_ecos_frame("ECOS API request failed.")

    stat_payload = payload.get("StatisticSearch")
    if not isinstance(stat_payload, dict):
        return _empty_ecos_frame("ECOS API response did not include StatisticSearch rows.")

    rows = stat_payload.get("row", [])
    if not rows:
        return _empty_ecos_frame("ECOS API response was empty.")

    frame = pd.DataFrame(rows)
    if "TIME" not in frame or "DATA_VALUE" not in frame:
        return _empty_ecos_frame("ECOS API response schema was not recognized.")

    frame["date"] = pd.to_datetime(frame["TIME"], errors="coerce")
    frame["market_rate_pct"] = pd.to_numeric(frame["DATA_VALUE"], errors="coerce")
    frame["stat_code"] = stat_code
    frame["item_code"] = item_code
    frame["source"] = "ECOS API"
    frame = frame.dropna(subset=["date", "market_rate_pct"])
    frame = frame[MARKET_RATE_COLUMNS].sort_values("date").reset_index(drop=True)
    frame.attrs["source"] = "ECOS API"
    frame.attrs["api_connected"] = not frame.empty
    frame.attrs["is_fallback"] = frame.empty
    frame.attrs["status_message"] = "ECOS interest rate series loaded." if not frame.empty else "ECOS rate series was empty."
    return frame


def fetch_interest_rate_series() -> pd.DataFrame:
    end = date.today()
    start = end - timedelta(days=120)
    result = fetch_ecos_stat(
        DEFAULT_RATE_STAT_CODE,
        DEFAULT_RATE_ITEM_CODE,
        start.strftime("%Y%m%d"),
        end.strftime("%Y%m%d"),
        cycle="D",
    )
    if result.empty or result.attrs.get("is_fallback", True):
        return sample_interest_rate_series(result.attrs.get("status_message", "ECOS API unavailable."))
    return result

