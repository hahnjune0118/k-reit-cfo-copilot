from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
MACRO_ASSUMPTIONS_FILE = BASE_DIR / "data" / "macro_assumptions.csv"


def load_macro_assumptions() -> pd.DataFrame:
    if not MACRO_ASSUMPTIONS_FILE.exists():
        return _fallback_macro_assumptions()

    frame = pd.read_csv(MACRO_ASSUMPTIONS_FILE)
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame["is_actual"] = frame["is_actual"].astype(str).str.lower().isin(["true", "1", "yes"])
    frame["is_forecast"] = frame["is_forecast"].astype(str).str.lower().isin(["true", "1", "yes"])
    frame.attrs["source"] = "local macro_assumptions.csv"
    frame.attrs["status_message"] = "BOK/ECOS actual rate와 KDI/IMF/OECD-style 수동 전망 가정을 함께 사용합니다."
    return frame


def _fallback_macro_assumptions() -> pd.DataFrame:
    rows = [
        {
            "source": "Model assumption",
            "metric": "BOK base rate",
            "date": "2026-07-01",
            "value": 3.50,
            "unit": "%",
            "scenario": "base",
            "note": "local fallback assumption",
            "is_actual": False,
            "is_forecast": False,
        },
        {
            "source": "Model assumption",
            "metric": "REIT refinancing spread proxy",
            "date": "2026-07-01",
            "value": 1.35,
            "unit": "%",
            "scenario": "base",
            "note": "local fallback spread assumption",
            "is_actual": False,
            "is_forecast": False,
        },
    ]
    frame = pd.DataFrame(rows)
    frame.attrs["source"] = "fallback macro assumptions"
    frame.attrs["status_message"] = "macro_assumptions.csv를 찾지 못해 local fallback assumption을 사용합니다."
    return frame


def _latest_metric_value(assumptions: pd.DataFrame, metric: str, scenario: str | None = None) -> float | None:
    data = assumptions[assumptions["metric"].str.lower() == metric.lower()].copy()
    if scenario is not None:
        data = data[data["scenario"].str.lower() == scenario.lower()]
    if data.empty:
        return None
    data["date_parsed"] = pd.to_datetime(data["date"], errors="coerce")
    latest = data.sort_values("date_parsed").iloc[-1]
    return float(latest["value"]) if pd.notna(latest["value"]) else None


def get_base_rate_assumption(market_rate_data: pd.DataFrame | None = None) -> dict[str, object]:
    if market_rate_data is not None and not market_rate_data.empty and "market_rate_pct" in market_rate_data.columns:
        latest = market_rate_data.sort_values("date").iloc[-1]
        return {
            "rate_pct": float(latest["market_rate_pct"]),
            "date": str(latest.get("date", "조회 불가")),
            "source": "ECOS actual" if not market_rate_data.attrs.get("is_fallback", True) else "ECOS fallback",
            "basis": "API-sourced real data" if not market_rate_data.attrs.get("is_fallback", True) else "market/forecast assumption data",
            "is_fallback": bool(market_rate_data.attrs.get("is_fallback", True)),
        }

    assumptions = load_macro_assumptions()
    value = _latest_metric_value(assumptions, "BOK base rate", "base") or 3.50
    return {
        "rate_pct": value,
        "date": "2026-07-01",
        "source": "local macro assumption",
        "basis": "수동 관리 가정",
        "is_fallback": True,
    }


def get_credit_spread_assumption(assumptions: pd.DataFrame | None = None) -> dict[str, object]:
    assumptions = load_macro_assumptions() if assumptions is None else assumptions
    value = _latest_metric_value(assumptions, "credit spread proxy", "base")
    if value is None:
        value = _latest_metric_value(assumptions, "REIT refinancing spread proxy", "base") or 1.25
    return {
        "spread_pct": float(value),
        "source": "Market proxy / local assumption",
        "basis": "수동 관리 가정",
    }


def get_refinancing_rate_assumption(
    market_rate_data: pd.DataFrame | None = None,
    assumptions: pd.DataFrame | None = None,
) -> dict[str, object]:
    assumptions = load_macro_assumptions() if assumptions is None else assumptions
    base = get_base_rate_assumption(market_rate_data)
    spread = get_refinancing_rate_spread(assumptions)
    return {
        "base_rate_pct": float(base["rate_pct"]),
        "refinancing_spread_pct": spread,
        "refinancing_rate_pct": float(base["rate_pct"]) + spread,
        "source": f"{base['source']} + refinancing spread assumption",
        "basis": "market/forecast assumption data",
        "is_fallback": bool(base["is_fallback"]),
    }


def get_refinancing_rate_spread(assumptions: pd.DataFrame | None = None) -> float:
    assumptions = load_macro_assumptions() if assumptions is None else assumptions
    return float(_latest_metric_value(assumptions, "REIT refinancing spread proxy", "base") or 1.35)


def build_rate_scenarios(
    market_rate_data: pd.DataFrame | None = None,
    assumptions: pd.DataFrame | None = None,
) -> pd.DataFrame:
    assumptions = load_macro_assumptions() if assumptions is None else assumptions
    base = get_base_rate_assumption(market_rate_data)
    refi_spread = get_refinancing_rate_spread(assumptions)
    credit_spread = get_credit_spread_assumption(assumptions)["spread_pct"]

    rows = [
        {
            "Scenario": "Base",
            "기준금리": float(base["rate_pct"]),
            "credit spread": credit_spread,
            "refinancing spread": refi_spread,
            "Scenario 기준금리": float(base["rate_pct"]) + refi_spread,
            "Source": base["source"],
            "Basis": base["basis"],
        },
        {
            "Scenario": "Downside",
            "기준금리": float(base["rate_pct"]) + 0.60,
            "credit spread": credit_spread + 0.35,
            "refinancing spread": refi_spread + 0.45,
            "Scenario 기준금리": float(base["rate_pct"]) + 0.60 + refi_spread + 0.45,
            "Source": "KDI/IMF/OECD-style local outlook assumption",
            "Basis": "전망치 기반 가정",
        },
        {
            "Scenario": "Upside",
            "기준금리": max(float(base["rate_pct"]) - 0.40, 0),
            "credit spread": max(credit_spread - 0.20, 0),
            "refinancing spread": max(refi_spread - 0.25, 0),
            "Scenario 기준금리": max(float(base["rate_pct"]) - 0.40, 0) + max(refi_spread - 0.25, 0),
            "Source": "KDI/IMF/OECD-style local outlook assumption",
            "Basis": "전망치 기반 가정",
        },
    ]
    return pd.DataFrame(rows)


def _metric(
    name: str,
    value: Any,
    unit: str,
    source: str,
    confidence: str,
    note: str = "",
    as_of: str | None = None,
) -> dict[str, object]:
    return {
        "name": name,
        "value": value,
        "unit": unit,
        "source": source,
        "data_source": source,
        "confidence": confidence,
        "confidence_level": confidence,
        "as_of": as_of or "2026-07-01",
        "note": note,
    }


def collect_ecos_rates(api_key: str | None = None) -> dict[str, object]:
    del api_key
    try:
        from modules.api_clients.ecos_client import fetch_interest_rate_series

        rates = fetch_interest_rate_series()
    except Exception:
        rates = pd.DataFrame()
        rates.attrs["is_fallback"] = True
        rates.attrs["status_message"] = "ECOS 금리 데이터를 조회하지 못해 fallback macro assumption을 사용합니다."

    base = get_base_rate_assumption(rates)
    confidence = "High" if not bool(base.get("is_fallback", True)) else "Low"
    return {
        "series": rates,
        "base_rate": _metric(
            "base_rate",
            base.get("rate_pct"),
            "%",
            str(base.get("source", "ECOS fallback")),
            confidence,
            str(base.get("basis", "ECOS 기준 금리 데이터는 Scenario Engine 기준금리 가정으로 활용됩니다.")),
            as_of=str(base.get("date", "2026-07-01")),
        ),
        "status_message": rates.attrs.get("status_message", ""),
    }


def collect_credit_spread_proxy(api_key: str | None = None) -> dict[str, object]:
    del api_key
    assumptions = load_macro_assumptions()
    spread = _latest_metric_value(assumptions, "credit spread proxy", "base")
    source = "local macro_assumptions.csv"
    note = "Corporate bond yield proxy와 treasury yield proxy의 차이를 우선 사용하고, 없으면 수동 관리 spread proxy를 사용합니다."
    if spread is None:
        spread = _latest_metric_value(assumptions, "REIT refinancing spread proxy", "base")
        source = "fallback macro assumption"
        note = "정확한 ECOS corporate bond / treasury spread series가 없어서 REIT refinancing spread proxy를 사용합니다."
    return _metric(
        "credit_spread_proxy",
        float(spread or 0.0),
        "%",
        source,
        "Low",
        note,
    )


def build_refinancing_rate_assumption(
    base_rate: dict[str, object] | float | None,
    treasury_yield: dict[str, object] | float | None,
    credit_spread: dict[str, object] | float | None,
) -> dict[str, object]:
    del treasury_yield

    def _value(item: dict[str, object] | float | None) -> float | None:
        if isinstance(item, dict):
            value = item.get("value")
        else:
            value = item
        try:
            return None if value is None else float(value)
        except (TypeError, ValueError):
            return None

    base = _value(base_rate)
    spread = _value(credit_spread)
    if base is None or spread is None:
        return _metric(
            "refinancing_rate_assumption",
            None,
            "%",
            "macro assumption layer",
            "Not available",
            "기준금리 또는 credit spread proxy가 없어 refinancing rate assumption을 계산하지 못했습니다.",
        )
    return _metric(
        "refinancing_rate_assumption",
        base + spread,
        "%",
        "ECOS / macro assumption layer",
        "Low",
        "기준금리와 credit spread proxy를 단순 합산한 refinancing rate proxy입니다.",
    )


def build_macro_rate_environment(api_key: str | None = None) -> dict[str, object]:
    assumptions = load_macro_assumptions()
    ecos = collect_ecos_rates(api_key)
    base_rate = ecos["base_rate"]

    treasury = _metric(
        "treasury_yield",
        _latest_metric_value(assumptions, "government bond yield proxy", "base"),
        "%",
        "local macro_assumptions.csv",
        "Low",
        "ECOS 세부 series 연결 전까지 수동 관리 국고채 금리 proxy입니다.",
    )
    credit_spread = collect_credit_spread_proxy(api_key)
    corporate_value = None
    if treasury.get("value") is not None and credit_spread.get("value") is not None:
        corporate_value = float(treasury["value"]) + float(credit_spread["value"])
    corporate = _metric(
        "corporate_bond_yield",
        corporate_value,
        "%",
        "macro proxy calculation",
        "Low" if corporate_value is not None else "Not available",
        "국고채 proxy와 credit spread proxy를 합산한 corporate bond yield proxy입니다.",
    )
    refinancing_spread = _metric(
        "refinancing_spread",
        get_refinancing_rate_spread(assumptions),
        "%",
        "local macro_assumptions.csv",
        "Low",
        "상장 REIT debt refinancing spread assumption입니다.",
    )
    refinancing_rate = build_refinancing_rate_assumption(base_rate, treasury, refinancing_spread)
    scenarios = build_rate_scenarios(ecos["series"], assumptions)

    return {
        "base_rate": base_rate,
        "treasury_yield": treasury,
        "corporate_bond_yield": corporate,
        "credit_spread_proxy": credit_spread,
        "refinancing_spread": refinancing_spread,
        "refinancing_rate_assumption": refinancing_rate,
        "scenarios": scenarios,
        "status_message": ecos.get("status_message", ""),
    }
