from pathlib import Path

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


def reit_options(reits: pd.DataFrame) -> list[str]:
    return reits.sort_values("reit_name")["reit_name"].tolist()


def reit_id_from_name(reits: pd.DataFrame, reit_name: str) -> str:
    match = reits.loc[reits["reit_name"] == reit_name, "reit_id"]
    if match.empty:
        raise ValueError(f"Unknown REIT name: {reit_name}")
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
