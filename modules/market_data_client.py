from __future__ import annotations

from typing import Any

import pandas as pd

from modules.real_data_pipeline import collect_market_data
from modules.source_confidence import build_collected_metrics_table, not_available_metric


MARKET_METRICS = [
    "latest_price",
    "market_cap",
    "shares_outstanding",
    "return_1m",
    "return_3m",
    "return_ytd",
    "fifty_two_week_high",
    "fifty_two_week_low",
    "volume",
]


def collect_reit_market_data(selected_reit: Any, force_refresh: bool = False) -> dict[str, Any]:
    result = collect_market_data(selected_reit, force_refresh=force_refresh)
    metrics = result.setdefault("metrics", {})
    for key in MARKET_METRICS:
        metrics.setdefault(
            key,
            not_available_metric(
                key,
                "KRW" if key not in {"return_1m", "return_3m", "return_ytd"} else "%",
                source="KRX / Market Data",
                note="KRX/public market data에서 아직 수집하지 못했습니다.",
                as_of=None,
            ),
        )
    result["metrics"] = metrics
    result.setdefault("source", "KRX / Market Data")
    return result


def build_market_metric_table(selected_reit: Any, force_refresh: bool = False) -> pd.DataFrame:
    result = collect_reit_market_data(selected_reit, force_refresh=force_refresh)
    return build_collected_metrics_table(result.get("metrics", {}))

