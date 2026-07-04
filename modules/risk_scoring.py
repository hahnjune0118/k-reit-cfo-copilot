from __future__ import annotations

import numpy as np
import pandas as pd

from modules.scenario_engine import CURRENT_YEAR, classify_risk, debt_profile, run_scenario


SEVERITY_SCORE = {"Low": 1, "Medium": 2, "High": 3}


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
