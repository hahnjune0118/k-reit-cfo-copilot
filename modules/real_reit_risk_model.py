from __future__ import annotations

from typing import Any

import pandas as pd


COMPONENTS = [
    "Leverage",
    "Liquidity",
    "Interest Rate",
    "Refinancing",
    "Dividend Sustainability",
    "Market Signal",
    "Disclosure Freshness",
    "Data Quality",
]


def _level(score: float | None) -> str:
    if score is None:
        return "Not Available"
    if score >= 75:
        return "High"
    if score >= 55:
        return "Elevated"
    if score >= 35:
        return "Moderate"
    return "Low"


def _clip(score: float | None) -> float | None:
    if score is None:
        return None
    return max(min(float(score), 100.0), 0.0)


def build_component(
    name: str,
    score: float | None,
    *,
    source: str = "Not Available",
    confidence: str = "Not Available",
    explanation: str = "",
    recommended_action: str = "",
) -> dict[str, Any]:
    clipped = _clip(score)
    return {
        "component": name,
        "score": clipped,
        "level": _level(clipped),
        "source": source,
        "confidence": confidence,
        "explanation": explanation,
        "recommended_cfo_action": recommended_action,
    }


def score_type_from_available_count(count: int) -> str:
    if count >= 5:
        return "Full"
    if count >= 3:
        return "Partial"
    return "Limited"


def calculate_overall_from_components(components: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [item for item in components if item.get("score") is not None]
    if not scored:
        return {
            "overall_score": None,
            "overall_level": "Not Available",
            "score_type": "Limited",
            "components": components,
            "top_drivers": [],
            "cfo_actions": ["필수 재무제표, 시장, 공시 데이터를 먼저 수집해야 합니다."],
        }
    score = sum(float(item["score"]) for item in scored) / len(scored)
    drivers = sorted(scored, key=lambda item: float(item["score"]), reverse=True)[:3]
    actions = [item["recommended_cfo_action"] for item in drivers if item.get("recommended_cfo_action")]
    return {
        "overall_score": score,
        "overall_level": _level(score),
        "score_type": score_type_from_available_count(len(scored)),
        "components": components,
        "top_drivers": drivers,
        "cfo_actions": actions,
    }


def components_to_frame(components: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(components)

