from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd


SOURCE_TYPES = {
    "OpenDART API",
    "OpenDART Parsed",
    "ECOS API",
    "KRX / Market Data",
    "KAREIT / REIT Association",
    "Company IR",
    "Local Cache",
    "Inferred Proxy",
    "Fallback Assumption",
    "Not Available",
}

CONFIDENCE_LEVELS = {"High", "Medium", "Low", "Not Available"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_confidence(confidence: str | None) -> str:
    value = str(confidence or "").strip()
    lower_map = {item.lower(): item for item in CONFIDENCE_LEVELS}
    return lower_map.get(value.lower(), "Not Available")


def infer_source_type(source: str | None, fallback: str = "Not Available") -> str:
    text = str(source or "").casefold()
    if "opendart" in text and ("parser" in text or "parsed" in text or "report" in text or "원문" in text):
        return "OpenDART Parsed"
    if "opendart" in text or "dart" in text:
        return "OpenDART API"
    if "ecos" in text:
        return "ECOS API"
    if "krx" in text or "pykrx" in text or "market data" in text or "stooq" in text:
        return "KRX / Market Data"
    if "kareit" in text or "리츠협회" in text or "association" in text:
        return "KAREIT / REIT Association"
    if "company ir" in text or "ir public" in text:
        return "Company IR"
    if "cache" in text:
        return "Local Cache"
    if "proxy" in text or "calculated" in text or "inferred" in text:
        return "Inferred Proxy"
    if "fallback" in text or "assumption" in text or "local macro" in text:
        return "Fallback Assumption"
    if fallback in SOURCE_TYPES:
        return fallback
    return "Not Available"


def build_metric(
    name: str,
    value: Any,
    unit: str = "",
    source: str = "Not Available",
    confidence: str = "Not Available",
    *,
    source_type: str | None = None,
    as_of: str | None = None,
    calculation_method: str = "",
    warning: str = "",
    note: str = "",
) -> dict[str, Any]:
    normalized_confidence = normalize_confidence(confidence)
    resolved_source_type = source_type if source_type in SOURCE_TYPES else infer_source_type(source)
    resolved_as_of = as_of if as_of is not None else now_iso()
    return {
        "name": name,
        "value": value,
        "unit": unit,
        "source": source,
        "source_type": resolved_source_type,
        "confidence": normalized_confidence,
        "as_of": resolved_as_of,
        "calculation_method": calculation_method,
        "warning": warning,
        "note": note,
        "data_source": source,
        "confidence_level": normalized_confidence,
    }


def not_available_metric(
    name: str,
    unit: str = "",
    *,
    source: str = "Not Available",
    note: str = "",
    warning: str = "",
    as_of: str | None = None,
) -> dict[str, Any]:
    return build_metric(
        name,
        None,
        unit,
        source,
        "Not Available",
        source_type="Not Available",
        as_of=as_of,
        calculation_method="Not calculated because source data is unavailable.",
        note=note,
        warning=warning or note,
    )


def normalize_metric(metric: Any, default_name: str = "") -> dict[str, Any]:
    if not isinstance(metric, dict):
        return not_available_metric(default_name or "metric")
    source = str(metric.get("source") or metric.get("data_source") or "Not Available")
    return build_metric(
        str(metric.get("name") or default_name or "metric"),
        metric.get("value"),
        str(metric.get("unit") or ""),
        source,
        str(metric.get("confidence") or metric.get("confidence_level") or "Not Available"),
        source_type=metric.get("source_type") if metric.get("source_type") in SOURCE_TYPES else infer_source_type(source),
        as_of=metric.get("as_of"),
        calculation_method=str(metric.get("calculation_method") or metric.get("method") or ""),
        warning=str(metric.get("warning") or ""),
        note=str(metric.get("note") or ""),
    )


def metric_value(metric: Any) -> Any:
    return metric.get("value") if isinstance(metric, dict) else None


def metric_source(metric: Any, fallback: str = "Not Available") -> str:
    if not isinstance(metric, dict):
        return fallback
    return str(metric.get("source") or metric.get("data_source") or fallback)


def metric_source_type(metric: Any, fallback: str = "Not Available") -> str:
    if not isinstance(metric, dict):
        return fallback
    value = str(metric.get("source_type") or "").strip()
    return value if value in SOURCE_TYPES else infer_source_type(metric_source(metric, fallback), fallback=fallback)


def metric_confidence(metric: Any) -> str:
    if not isinstance(metric, dict):
        return "Not Available"
    return normalize_confidence(str(metric.get("confidence") or metric.get("confidence_level") or "Not Available"))


def source_badge_text(metric_or_source: Any) -> str:
    if isinstance(metric_or_source, dict):
        return metric_source_type(metric_or_source)
    return infer_source_type(str(metric_or_source))


def confidence_badge_text(metric: Any) -> str:
    return metric_confidence(metric)


def metric_to_row(metric_name: str, metric: Any) -> dict[str, Any]:
    normalized = normalize_metric(metric, metric_name)
    value = normalized["value"]
    return {
        "Metric": metric_name,
        "Value": value,
        "Unit": normalized["unit"],
        "Source": normalized["source"],
        "Source Type": normalized["source_type"],
        "Confidence": normalized["confidence"],
        "As of": normalized["as_of"],
        "Calculation Method": normalized["calculation_method"],
        "Warning": normalized["warning"] or normalized["note"],
        "Status": "수집됨" if value is not None else "미확보",
    }


def flatten_metric_sections(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    for section_name in ("financials", "market_data", "macro_data", "reit_specific"):
        section = bundle.get(section_name, {})
        if not isinstance(section, dict):
            continue
        for key, value in section.items():
            if isinstance(value, dict) and ("value" in value or "confidence" in value or "source" in value):
                metrics[key] = normalize_metric(value, key)
    return metrics


def build_collected_metrics_table(bundle_or_metrics: dict[str, Any]) -> pd.DataFrame:
    if any(key in bundle_or_metrics for key in ("financials", "market_data", "macro_data", "reit_specific")):
        metrics = flatten_metric_sections(bundle_or_metrics)
    else:
        metrics = {key: normalize_metric(value, key) for key, value in bundle_or_metrics.items()}
    rows = [metric_to_row(key, metric) for key, metric in sorted(metrics.items())]
    return pd.DataFrame(rows)


def build_source_inventory(bundle: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for source in bundle.get("data_sources", []) if isinstance(bundle, dict) else []:
        warnings = source.get("warnings", []) if isinstance(source, dict) else []
        rows.append(
            {
                "Source": source.get("source", ""),
                "Source Type": infer_source_type(source.get("source", "")),
                "Status": source.get("status", "Not Available"),
                "As of": source.get("as_of", ""),
                "Warnings": "; ".join(str(item) for item in warnings if item),
            }
        )
    if rows:
        return pd.DataFrame(rows)

    metrics = flatten_metric_sections(bundle)
    seen: dict[str, dict[str, Any]] = {}
    for metric in metrics.values():
        source = metric_source(metric)
        seen.setdefault(
            source,
            {
                "Source": source,
                "Source Type": metric_source_type(metric),
                "Status": metric_confidence(metric),
                "As of": metric.get("as_of", ""),
                "Warnings": metric.get("warning", ""),
            },
        )
    return pd.DataFrame(seen.values())


def confidence_distribution(metrics_or_bundle: dict[str, Any]) -> pd.DataFrame:
    if any(key in metrics_or_bundle for key in ("financials", "market_data", "macro_data", "reit_specific")):
        metrics = flatten_metric_sections(metrics_or_bundle)
    else:
        metrics = metrics_or_bundle
    counts: dict[str, int] = {level: 0 for level in ["High", "Medium", "Low", "Not Available"]}
    for metric in metrics.values():
        counts[metric_confidence(metric)] = counts.get(metric_confidence(metric), 0) + 1
    return pd.DataFrame([{"Confidence": key, "Metric Count": value} for key, value in counts.items()])

