from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import streamlit as st

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - python-dotenv is listed in requirements.
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / ".env"

if load_dotenv is not None:
    load_dotenv(ENV_PATH)


DART_KEY_NAMES = ("OPENDART_API_KEY", "DART_API_KEY", "OPEN_DART_API_KEY")
ECOS_KEY_NAMES = ("ECOS_API_KEY", "BOK_ECOS_API_KEY")


def _from_streamlit_secrets(names: Iterable[str]) -> str | None:
    try:
        secrets = st.secrets
    except Exception:
        return None

    for name in names:
        try:
            value = secrets.get(name)
        except Exception:
            value = None
        if value:
            return str(value).strip()

    for group_name in ("api_keys", "apis", "external_api"):
        try:
            group = secrets.get(group_name, {})
        except Exception:
            group = {}
        if not hasattr(group, "get"):
            continue
        for name in names:
            value = group.get(name)
            if value:
                return str(value).strip()
    return None


def _from_env(names: Iterable[str]) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip()
    return None


def get_dart_api_key() -> str | None:
    return _from_streamlit_secrets(DART_KEY_NAMES) or _from_env(DART_KEY_NAMES)


def get_ecos_api_key() -> str | None:
    return _from_streamlit_secrets(ECOS_KEY_NAMES) or _from_env(ECOS_KEY_NAMES)


def has_dart_api_key() -> bool:
    return bool(get_dart_api_key())


def has_ecos_api_key() -> bool:
    return bool(get_ecos_api_key())

