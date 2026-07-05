from pathlib import Path
from datetime import date, timedelta

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"


@st.cache_data(show_spinner=False)
def _load_csv(file_name: str) -> pd.DataFrame:
    path = DATA_DIR / file_name
    return pd.read_csv(path)


def load_reits() -> pd.DataFrame:
    return _load_csv("sample_reits.csv")


def load_assets() -> pd.DataFrame:
    return _load_csv("sample_assets.csv")


def load_debt() -> pd.DataFrame:
    return _load_csv("sample_debt.csv")


def load_disclosure_flags() -> pd.DataFrame:
    return _load_csv("sample_disclosure_flags.csv")


def load_readiness() -> pd.DataFrame:
    return _load_csv("sample_readiness.csv")


def load_all_data() -> dict[str, pd.DataFrame]:
    return {
        "reits": load_reits(),
        "assets": load_assets(),
        "debt": load_debt(),
        "flags": load_disclosure_flags(),
        "readiness": load_readiness(),
    }


def _attach_source_attrs(
    frame: pd.DataFrame,
    source: str,
    api_connected: bool,
    is_fallback: bool,
    status_message: str,
) -> pd.DataFrame:
    frame.attrs["source"] = source
    frame.attrs["api_connected"] = api_connected
    frame.attrs["is_fallback"] = is_fallback
    frame.attrs["status_message"] = status_message
    return frame


def _has_dart_api_key() -> bool:
    try:
        from modules.api_clients.config import has_dart_api_key

        return has_dart_api_key()
    except Exception:
        return False


def _sample_interest_rate_series(message: str = "API unavailable; using sample market rate data.") -> pd.DataFrame:
    try:
        from modules.api_clients.ecos_client import sample_interest_rate_series

        return sample_interest_rate_series(message)
    except Exception:
        end = pd.Timestamp.today().normalize()
        dates = pd.bdate_range(end=end, periods=30)
        frame = pd.DataFrame(
            {
                "date": dates,
                "market_rate_pct": [3.45 + (idx % 5) * 0.01 for idx in range(len(dates))],
                "stat_code": "sample",
                "item_code": "sample",
                "source": "sample",
            }
        )
        return _attach_source_attrs(
            frame,
            "sample",
            api_connected=False,
            is_fallback=True,
            status_message=message,
        )


def _fetch_interest_rate_series() -> pd.DataFrame:
    try:
        from modules.api_clients.ecos_client import fetch_interest_rate_series

        return fetch_interest_rate_series()
    except Exception:
        return _sample_interest_rate_series("ECOS client unavailable; using sample market rate data.")


def _find_corp_by_name(company_name: str) -> pd.DataFrame:
    try:
        from modules.api_clients.dart_client import find_corp_by_name

        return find_corp_by_name(company_name)
    except Exception:
        frame = pd.DataFrame(columns=["corp_code", "corp_name", "stock_code", "modify_date"])
        return _attach_source_attrs(
            frame,
            "sample",
            api_connected=False,
            is_fallback=True,
            status_message="OpenDART client unavailable; company mapping skipped.",
        )


def _fetch_disclosure_list(corp_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    try:
        from modules.api_clients.dart_client import fetch_disclosure_list

        return fetch_disclosure_list(corp_code, start_date, end_date)
    except Exception:
        frame = pd.DataFrame()
        return _attach_source_attrs(
            frame,
            "sample",
            api_connected=False,
            is_fallback=True,
            status_message="OpenDART client unavailable; disclosure API skipped.",
        )


def load_reit_master_data(use_api: bool = True) -> pd.DataFrame:
    master = load_reits().copy()
    if not use_api or not _has_dart_api_key():
        return _attach_source_attrs(
            master,
            "sample",
            api_connected=False,
            is_fallback=True,
            status_message="OpenDART API key missing; using sample REIT master data.",
        )

    matched_rows = []
    for _, reit in master.iterrows():
        matches = _find_corp_by_name(str(reit["reit_name"]))
        if not matches.empty:
            first = matches.iloc[0]
            matched_rows.append(
                {
                    "reit_id": reit["reit_id"],
                    "dart_corp_code": first.get("corp_code", ""),
                    "dart_corp_name": first.get("corp_name", ""),
                    "dart_stock_code": first.get("stock_code", ""),
                }
            )

    if not matched_rows:
        return _attach_source_attrs(
            master,
            "sample",
            api_connected=False,
            is_fallback=True,
            status_message="OpenDART company mapping unavailable; using sample REIT master data.",
        )

    mapped = master.merge(pd.DataFrame(matched_rows), on="reit_id", how="left")
    return _attach_source_attrs(
        mapped,
        "sample + OpenDART mapping",
        api_connected=True,
        is_fallback=False,
        status_message="Sample REIT master data enriched with OpenDART company mapping where available.",
    )


def load_market_rate_data(use_api: bool = True) -> pd.DataFrame:
    if not use_api:
        return _sample_interest_rate_series("API disabled; using sample market rate data.")
    return _fetch_interest_rate_series()


def load_disclosure_data(use_api: bool = True) -> pd.DataFrame:
    sample_flags = load_disclosure_flags().copy()
    if not use_api or not _has_dart_api_key():
        return _attach_source_attrs(
            sample_flags,
            "sample",
            api_connected=False,
            is_fallback=True,
            status_message="OpenDART API key missing; using sample disclosure flags.",
        )

    end = date.today()
    start = end - timedelta(days=365)
    disclosures = []
    for _, reit in load_reits().iterrows():
        matches = _find_corp_by_name(str(reit["reit_name"]))
        if matches.empty:
            continue
        corp_code = str(matches.iloc[0].get("corp_code", ""))
        fetched = _fetch_disclosure_list(corp_code, start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
        if fetched.empty:
            continue
        fetched = fetched.copy()
        fetched["reit_id"] = reit["reit_id"]
        disclosures.append(fetched)

    if not disclosures:
        return _attach_source_attrs(
            sample_flags,
            "sample",
            api_connected=False,
            is_fallback=True,
            status_message="OpenDART disclosure data unavailable; using sample disclosure flags.",
        )

    result = pd.concat(disclosures, ignore_index=True)
    return _attach_source_attrs(
        result,
        "OpenDART API",
        api_connected=True,
        is_fallback=False,
        status_message="OpenDART disclosure list loaded for matched REIT companies.",
    )


def reit_options(reits: pd.DataFrame | None = None) -> list[str]:
    source = load_reits() if reits is None else reits
    return source.sort_values("reit_name")["reit_name"].tolist()


def reit_id_from_name(reits_or_name: pd.DataFrame | str, reit_name: str | None = None) -> str:
    if reit_name is None:
        reits = load_reits()
        name = str(reits_or_name)
    else:
        reits = reits_or_name
        name = reit_name

    if not isinstance(reits, pd.DataFrame):
        raise TypeError("reit_id_from_name expects reit_id_from_name(name) or reit_id_from_name(reits, name).")

    match = reits.loc[reits["reit_name"] == name, "reit_id"]
    if match.empty:
        raise ValueError(f"Unknown REIT name: {name}")
    return str(match.iloc[0])


def filter_by_reit(df: pd.DataFrame, reit_id: str) -> pd.DataFrame:
    return df[df["reit_id"] == reit_id].copy()


def selected_reit_package(reit_name: str) -> dict[str, pd.DataFrame]:
    data = load_all_data()
    reit_id = reit_id_from_name(data["reits"], reit_name)
    return {
        "reit_id": reit_id,
        "reit": filter_by_reit(data["reits"], reit_id).iloc[0],
        "assets": filter_by_reit(data["assets"], reit_id),
        "debt": filter_by_reit(data["debt"], reit_id),
        "flags": filter_by_reit(data["flags"], reit_id),
        "readiness": filter_by_reit(data["readiness"], reit_id),
        "all": data,
    }
