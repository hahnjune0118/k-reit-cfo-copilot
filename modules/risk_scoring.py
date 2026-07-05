from __future__ import annotations

import numpy as np
import pandas as pd

from modules.scenario_engine import CURRENT_YEAR, classify_risk, debt_profile, run_scenario


SEVERITY_SCORE = {"Low": 1, "Medium": 2, "High": 3}
RISK_WEIGHTS = {
    "Refinancing Risk": 0.30,
    "Dividend Sustainability": 0.25,
    "Asset Risk": 0.20,
    "Disclosure Quality": 0.15,
    "AI Readiness": 0.10,
}
READINESS_WEIGHTS = {
    "Data Availability": 0.20,
    "Data Consistency": 0.20,
    "KPI Standardization": 0.15,
    "Scenario Capability": 0.20,
    "Tax-Finance Integration": 0.15,
    "AI Use Case Readiness": 0.10,
}


def score_assets(assets: pd.DataFrame) -> pd.DataFrame:
    scored = assets.copy()
    scored["occupancy_risk"] = np.clip((100 - scored["occupancy_pct"]) * 5, 0, 25)
    scored["wale_risk"] = np.clip((5.5 - scored["wale_years"]) * 8, 0, 28)
    scored["tenant_concentration_risk"] = np.clip(scored["top_tenant_share_pct"] * 0.38, 0, 30)
    scored["capex_risk"] = np.clip(scored["capex_need_pct"] * 1.5, 0, 18)
    scored["asset_risk_score"] = np.clip(
        scored["occupancy_risk"]
        + scored["wale_risk"]
        + scored["tenant_concentration_risk"]
        + scored["capex_risk"],
        0,
        100,
    )
    scored["risk_tier"] = scored["asset_risk_score"].apply(classify_risk)
    return scored.sort_values("asset_risk_score", ascending=False)


def refinancing_risk_table(
    reits: pd.DataFrame,
    debt: pd.DataFrame,
    current_year: int = CURRENT_YEAR,
) -> pd.DataFrame:
    rows = []
    for _, reit in reits.iterrows():
        reit_debt = debt[debt["reit_id"] == reit["reit_id"]]
        profile = debt_profile(reit_debt, current_year=current_year)
        score = np.clip(
            (profile["near_term_debt_pct"] * 0.55)
            + (profile["floating_rate_pct"] * 0.25)
            + (float(reit["ltv_pct"]) - 40) * 1.4
            + max(profile["weighted_coupon_pct"] - 3.8, 0) * 8,
            0,
            100,
        )
        rows.append(
            {
                "reit_id": reit["reit_id"],
                "reit_name": reit["reit_name"],
                "total_debt_krw_bn": profile["total_debt_krw_bn"],
                "near_term_debt_krw_bn": profile["near_term_debt_krw_bn"],
                "near_term_debt_pct": profile["near_term_debt_pct"],
                "floating_rate_pct": profile["floating_rate_pct"],
                "weighted_coupon_pct": profile["weighted_coupon_pct"],
                "ltv_pct": float(reit["ltv_pct"]),
                "refinancing_risk_score": float(score),
                "risk_tier": classify_risk(score),
            }
        )
    return pd.DataFrame(rows).sort_values("refinancing_risk_score", ascending=False)


def debt_maturity_wall(debt: pd.DataFrame) -> pd.DataFrame:
    wall = (
        debt.groupby(["reit_id", "maturity_year"], as_index=False)["principal_krw_bn"]
        .sum()
        .sort_values(["maturity_year", "reit_id"])
    )
    return wall


def disclosure_flag_summary(flags: pd.DataFrame) -> pd.DataFrame:
    flagged = flags.copy()
    flagged["severity_score"] = flagged["severity"].map(SEVERITY_SCORE).fillna(1)
    return (
        flagged.groupby("reit_id", as_index=False)
        .agg(
            open_flags=("flag_id", "count"),
            high_flags=("severity", lambda x: int((x == "High").sum())),
            avg_severity=("severity_score", "mean"),
        )
        .sort_values(["high_flags", "open_flags"], ascending=False)
    )


def readiness_score(readiness: pd.DataFrame, flags: pd.DataFrame | None = None) -> pd.DataFrame:
    scores = (
        readiness.groupby("reit_id", as_index=False)
        .agg(ai_readiness_score=("score", "mean"))
    )
    if flags is not None and not flags.empty:
        summary = disclosure_flag_summary(flags)[["reit_id", "high_flags", "open_flags"]]
        scores = scores.merge(summary, on="reit_id", how="left").fillna({"high_flags": 0, "open_flags": 0})
        scores["ai_readiness_score"] = np.clip(
            scores["ai_readiness_score"] - scores["high_flags"] * 0.10 - scores["open_flags"] * 0.02,
            0,
            5,
        )
    return scores.sort_values("ai_readiness_score", ascending=False)


def readiness_interpretation(score: float) -> str:
    if score >= 3.8:
        return "Strong"
    if score >= 3.0:
        return "Moderate"
    return "Needs Improvement"


def weighted_readiness_score(readiness: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float | str]]:
    scored = readiness.copy()
    scored["weight"] = scored["dimension"].map(READINESS_WEIGHTS).fillna(0.0)
    weight_sum = scored["weight"].sum()
    if weight_sum == 0:
        scored["weight"] = 1 / max(len(scored), 1)
    else:
        scored["weight"] = scored["weight"] / weight_sum
    scored["weighted_score"] = scored["score"] * scored["weight"]
    weighted_score = float(scored["weighted_score"].sum())
    diagnostic = {
        "weighted_score": weighted_score,
        "weighted_score_pct": weighted_score / 5 * 100,
        "interpretation": readiness_interpretation(weighted_score),
    }
    return scored.sort_values("score"), diagnostic


def data_quality_flags(
    reit: pd.Series,
    assets: pd.DataFrame,
    debt: pd.DataFrame,
    flags: pd.DataFrame,
    readiness: pd.DataFrame,
) -> pd.DataFrame:
    data_availability = readiness.loc[readiness["dimension"] == "Data Availability", "score"]
    data_consistency = readiness.loc[readiness["dimension"] == "Data Consistency", "score"]
    scenario_capability = readiness.loc[readiness["dimension"] == "Scenario Capability", "score"]

    missing_score = float(data_availability.iloc[0]) if not data_availability.empty else 0.0
    consistency_score = float(data_consistency.iloc[0]) if not data_consistency.empty else 0.0
    scenario_score = float(scenario_capability.iloc[0]) if not scenario_capability.empty else 0.0
    high_flags = int((flags["severity"] == "High").sum()) if not flags.empty else 0
    open_flags = int(len(flags))

    asset_yield = float(assets["noi_krw_bn"].sum() / max(assets["asset_value_krw_bn"].sum(), 1) * 100)
    debt_cost_gap = float(abs(debt["coupon_pct"].mean() - reit["avg_debt_cost_pct"])) if not debt.empty else 0.0

    rows = [
        {
            "flag_type": "Missing data",
            "status": "High" if missing_score < 3.0 else "Watch" if missing_score < 3.8 else "Low",
            "evidence": f"Data Availability score {missing_score:.1f}/5",
            "impact": "필수 asset, debt, tax field가 누락되면 AI Memo와 Scenario Engine의 신뢰도가 낮아집니다.",
            "action": "필수 data dictionary와 source owner를 지정합니다.",
        },
        {
            "flag_type": "Inconsistent values",
            "status": "High" if consistency_score < 3.0 or debt_cost_gap > 0.4 else "Watch" if consistency_score < 3.8 else "Low",
            "evidence": f"Data Consistency score {consistency_score:.1f}/5, debt cost gap {debt_cost_gap:.1f}%p",
            "impact": "KPI definition이 다르면 CFO Dashboard와 IR narrative가 서로 다른 숫자를 말할 수 있습니다.",
            "action": "FFO, AFFO, LTV, debt cost, occupancy definition을 표준화합니다.",
        },
        {
            "flag_type": "Unusual movement",
            "status": "High" if asset_yield < 3.5 or asset_yield > 6.0 else "Watch" if scenario_score < 3.2 else "Low",
            "evidence": f"portfolio NOI yield {asset_yield:.1f}%, Scenario Capability score {scenario_score:.1f}/5",
            "impact": "비정상적 movement를 설명하지 못하면 investor Q&A와 valuation narrative가 약해집니다.",
            "action": "NOI, rent, valuation movement에 대한 threshold 기반 review rule을 설정합니다.",
        },
        {
            "flag_type": "Manual review required",
            "status": "High" if high_flags > 0 else "Watch" if open_flags > 0 else "Low",
            "evidence": f"open disclosure flags {open_flags}, high-severity flags {high_flags}",
            "impact": "manual review 항목이 남아 있으면 AI-generated output의 approval risk가 커집니다.",
            "action": "High severity flag부터 owner, target date, approval status를 부여합니다.",
        },
    ]
    return pd.DataFrame(rows)


def readiness_roadmap(readiness: pd.DataFrame, quality_flags: pd.DataFrame) -> pd.DataFrame:
    weakest = readiness.sort_values("score").head(2)["dimension"].tolist()
    high_flags = quality_flags[quality_flags["status"] == "High"]["flag_type"].tolist()
    watch_flags = quality_flags[quality_flags["status"] == "Watch"]["flag_type"].tolist()

    short_focus = ", ".join(high_flags or watch_flags or ["source data validation"])
    weakest_focus = ", ".join(weakest or ["KPI Standardization"])

    return pd.DataFrame(
        [
            {
                "horizon": "단기 개선 과제",
                "priority": "0-3개월",
                "initiative": f"{short_focus} 항목을 우선 정리하고 필수 data owner를 지정",
                "expected_impact": "Data Quality flag를 줄이고 Dashboard 숫자 신뢰도를 확보",
            },
            {
                "horizon": "중기 개선 과제",
                "priority": "3-6개월",
                "initiative": f"{weakest_focus} 영역의 KPI dictionary와 scenario workflow 표준화",
                "expected_impact": "CFO, AMC, IR팀이 같은 metric으로 의사결정 가능",
            },
            {
                "horizon": "장기 AX 전환 과제",
                "priority": "6-12개월",
                "initiative": "AI Memo, Investor Q&A, disclosure workflow에 approval governance와 audit trail 구축",
                "expected_impact": "AI Readiness를 실제 AX operating model로 확장",
            },
        ]
    )


def attention_label(score: float) -> str:
    if score >= 65:
        return "High"
    if score >= 35:
        return "Watch"
    return "Low"


def attention_scores(
    reit: pd.Series,
    assets: pd.DataFrame,
    debt: pd.DataFrame,
    flags: pd.DataFrame,
    readiness: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, float | str]]:
    scenario = run_scenario(reit, assets, debt)
    asset_scores = score_assets(assets)
    ready = readiness_score(readiness, flags)
    ai_ready_score = float(ready["ai_readiness_score"].iloc[0]) if not ready.empty else 0.0

    high_flags = int((flags["severity"] == "High").sum()) if not flags.empty else 0
    open_flags = int(len(flags))
    avg_asset_risk = float(asset_scores.head(3)["asset_risk_score"].mean()) if not asset_scores.empty else 0.0

    refinancing_risk = float(scenario["refinancing_risk_score"])
    dividend_risk = float(np.clip(100 - scenario["dividend_sustainability_score"], 0, 100))
    asset_risk = float(np.clip(avg_asset_risk, 0, 100))
    disclosure_quality_risk = float(np.clip(high_flags * 35 + open_flags * 12, 0, 100))
    ai_readiness_risk = float(np.clip((5 - ai_ready_score) * 20, 0, 100))

    rows = [
        {
            "category": "Refinancing Risk",
            "score": refinancing_risk,
            "label": attention_label(refinancing_risk),
            "why": "near-term maturity와 floating-rate exposure가 금리 충격 시 현금흐름과 차입 비용을 동시에 압박합니다.",
            "action": "24개월 내 maturity별 lender status, term sheet, refinancing timetable을 확인합니다.",
        },
        {
            "category": "Dividend Sustainability",
            "score": dividend_risk,
            "label": attention_label(dividend_risk),
            "why": "dividend coverage가 약해지면 투자자 신뢰와 배당 guidance의 방어력이 낮아집니다.",
            "action": "FFO/AFFO bridge, dividend buffer, cash balance 활용 가능성을 함께 점검합니다.",
        },
        {
            "category": "Asset Risk",
            "score": asset_risk,
            "label": attention_label(asset_risk),
            "why": "asset-level occupancy, WALE, tenant concentration, capex risk가 NOI와 valuation narrative를 좌우합니다.",
            "action": "상위 risk asset의 lease rollover, capex plan, tenant renewal probability를 확인합니다.",
        },
        {
            "category": "Disclosure Quality",
            "score": disclosure_quality_risk,
            "label": attention_label(disclosure_quality_risk),
            "why": "disclosure flag가 많거나 severity가 높으면 Investor Q&A와 management narrative의 일관성이 약해집니다.",
            "action": "High severity flag부터 source data, owner, target date를 지정해 정리합니다.",
        },
        {
            "category": "AI Readiness",
            "score": ai_readiness_risk,
            "label": attention_label(ai_readiness_risk),
            "why": "Data Quality와 KPI standardization이 낮으면 AI Memo와 Investor Q&A 자동화가 확장되기 어렵습니다.",
            "action": "source-of-truth field, KPI dictionary, approval workflow를 우선 정의합니다.",
        },
    ]

    category_df = pd.DataFrame(rows)
    overall_score = float(
        sum(row["score"] * RISK_WEIGHTS[row["category"]] for row in rows)
    )
    overall = {
        "overall_score": overall_score,
        "overall_label": attention_label(overall_score),
        "dividend_coverage": float(scenario["dividend_coverage"]),
        "dividend_buffer_krw_bn": float(scenario["dividend_buffer_krw_bn"]),
        "ai_readiness_score": ai_ready_score,
        "open_flags": open_flags,
        "high_flags": high_flags,
    }
    return category_df.sort_values("score", ascending=False), overall


def top_cfo_alerts(category_scores: pd.DataFrame, limit: int = 3) -> pd.DataFrame:
    alerts = category_scores.sort_values("score", ascending=False).head(limit).copy()
    alerts["alert_rank"] = range(1, len(alerts) + 1)
    return alerts[["alert_rank", "category", "score", "label", "why", "action"]]


def executive_signal_table(
    reits: pd.DataFrame,
    assets: pd.DataFrame,
    debt: pd.DataFrame,
    readiness: pd.DataFrame,
    flags: pd.DataFrame,
) -> pd.DataFrame:
    scenarios = []
    for _, reit in reits.iterrows():
        scenario = run_scenario(
            reit,
            assets[assets["reit_id"] == reit["reit_id"]],
            debt[debt["reit_id"] == reit["reit_id"]],
        )
        scenarios.append(
            {
                "reit_id": reit["reit_id"],
                "reit_name": reit["reit_name"],
                "dividend_coverage": scenario["dividend_coverage"],
                "dividend_status": scenario["dividend_status"],
                "tax_adjusted_cash_flow_krw_bn": scenario["tax_adjusted_cash_flow_krw_bn"],
            }
        )
    scenario_df = pd.DataFrame(scenarios)
    refi = refinancing_risk_table(reits, debt)[["reit_id", "refinancing_risk_score", "risk_tier"]]
    ready = readiness_score(readiness, flags)
    flag_summary = disclosure_flag_summary(flags)[["reit_id", "open_flags", "high_flags"]]

    return (
        scenario_df.merge(refi, on="reit_id", how="left")
        .merge(ready[["reit_id", "ai_readiness_score"]], on="reit_id", how="left")
        .merge(flag_summary, on="reit_id", how="left")
        .fillna({"open_flags": 0, "high_flags": 0})
        .sort_values("refinancing_risk_score", ascending=False)
    )
