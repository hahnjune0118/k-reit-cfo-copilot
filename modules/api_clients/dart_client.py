from __future__ import annotations

from io import BytesIO
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import streamlit as st

from modules.api_clients.config import get_dart_api_key, has_dart_api_key


DART_BASE_URL = "https://opendart.fss.or.kr/api"
CORP_CODE_COLUMNS = ["corp_code", "corp_name", "stock_code", "modify_date"]
DISCLOSURE_COLUMNS = [
    "corp_code",
    "corp_name",
    "stock_code",
    "corp_cls",
    "report_nm",
    "rcept_no",
    "flr_nm",
    "rcept_dt",
    "rm",
]


def _empty_frame(columns: list[str], message: str, fallback: bool = True) -> pd.DataFrame:
    frame = pd.DataFrame(columns=columns)
    frame.attrs["source"] = "OpenDART API"
    frame.attrs["api_connected"] = False
    frame.attrs["is_fallback"] = fallback
    frame.attrs["status_message"] = message
    return frame


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def fetch_corp_code_zip() -> bytes:
    if not has_dart_api_key():
        return b""

    try:
        response = requests.get(
            f"{DART_BASE_URL}/corpCode.xml",
            params={"crtfc_key": get_dart_api_key()},
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException:
        return b""
    return response.content


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def load_corp_codes() -> pd.DataFrame:
    payload = fetch_corp_code_zip()
    if not payload:
        return _empty_frame(CORP_CODE_COLUMNS, "OpenDART API key missing or corp code request failed.")

    try:
        with zipfile.ZipFile(BytesIO(payload)) as zip_file:
            xml_name = next((name for name in zip_file.namelist() if name.lower().endswith(".xml")), "")
            if not xml_name:
                return _empty_frame(CORP_CODE_COLUMNS, "OpenDART corp code zip did not include XML.")
            xml_bytes = zip_file.read(xml_name)

        root = ET.fromstring(xml_bytes)
        rows = []
        for node in root.findall("list"):
            rows.append(
                {
                    "corp_code": (node.findtext("corp_code") or "").strip(),
                    "corp_name": (node.findtext("corp_name") or "").strip(),
                    "stock_code": (node.findtext("stock_code") or "").strip(),
                    "modify_date": (node.findtext("modify_date") or "").strip(),
                }
            )
        frame = pd.DataFrame(rows, columns=CORP_CODE_COLUMNS)
        frame.attrs["source"] = "OpenDART API"
        frame.attrs["api_connected"] = not frame.empty
        frame.attrs["is_fallback"] = frame.empty
        frame.attrs["status_message"] = "OpenDART corp code loaded." if not frame.empty else "OpenDART corp code was empty."
        return frame
    except (zipfile.BadZipFile, ET.ParseError, OSError):
        return _empty_frame(CORP_CODE_COLUMNS, "OpenDART corp code parse failed.")


def find_corp_by_name(company_name: str) -> pd.DataFrame:
    corp_codes = load_corp_codes()
    if corp_codes.empty or not company_name:
        return _empty_frame(CORP_CODE_COLUMNS, "OpenDART corp code unavailable or company name missing.")

    normalized = company_name.strip().casefold()
    corp_names = corp_codes["corp_name"].fillna("").str.casefold()
    exact = corp_codes[corp_names == normalized]
    if not exact.empty:
        return exact.reset_index(drop=True)

    contains = corp_codes[corp_names.str.contains(normalized, regex=False)]
    if contains.empty:
        compact = normalized.replace(" ", "")
        compact_names = corp_codes["corp_name"].fillna("").str.replace(" ", "", regex=False).str.casefold()
        contains = corp_codes[compact_names.str.contains(compact, regex=False)]

    result = contains.reset_index(drop=True)
    result.attrs["source"] = "OpenDART API"
    result.attrs["api_connected"] = not result.empty
    result.attrs["is_fallback"] = result.empty
    result.attrs["status_message"] = "OpenDART company match found." if not result.empty else "OpenDART company match not found."
    return result


@st.cache_data(show_spinner=False, ttl=60 * 15)
def fetch_disclosure_list(corp_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    if not has_dart_api_key() or not corp_code:
        return _empty_frame(DISCLOSURE_COLUMNS, "OpenDART API key missing or corp_code missing.")

    try:
        response = requests.get(
            f"{DART_BASE_URL}/list.json",
            params={
                "crtfc_key": get_dart_api_key(),
                "corp_code": corp_code,
                "bgn_de": start_date,
                "end_de": end_date,
                "page_no": 1,
                "page_count": 100,
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return _empty_frame(DISCLOSURE_COLUMNS, "OpenDART disclosure request failed.")

    status = str(payload.get("status", ""))
    if status != "000":
        message = payload.get("message") or "OpenDART disclosure response was empty."
        return _empty_frame(DISCLOSURE_COLUMNS, str(message))

    frame = pd.DataFrame(payload.get("list", []), columns=DISCLOSURE_COLUMNS)
    frame.attrs["source"] = "OpenDART API"
    frame.attrs["api_connected"] = not frame.empty
    frame.attrs["is_fallback"] = frame.empty
    frame.attrs["status_message"] = "OpenDART disclosure list loaded." if not frame.empty else "OpenDART disclosure list was empty."
    return frame

