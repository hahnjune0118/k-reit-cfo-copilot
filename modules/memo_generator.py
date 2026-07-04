from __future__ import annotations

import pandas as pd


def _fmt(value: float, digits: int = 1) -> str:
    return f"{value:,.{digits}f}"


def _top_asset(asset_scores: pd.DataFrame) -> pd.Series | None:
    if asset_scores.empty:
        return None
    return asset_scores.sort_values("asset_risk_score", ascending=False).iloc[0]


def _top_flag(flags: pd.DataFrame) -> pd.Series | None:
    if flags.empty:
        return None
    severity_order = {"High": 3, "Medium": 2, "Low": 1}
    ordered = flags.copy()
    ordered["_severity_order"] = ordered["severity"].map(severity_order).fillna(0)
    return ordered.sort_values(["_severity_order", "flag_id"], ascending=False).iloc[0]


def generate_cfo_memo(
    reit_name: str,
    focus: str,
    scenario: dict,
    asset_scores: pd.DataFrame,
    flags: pd.DataFrame,
) -> str:
    top_asset = _top_asset(asset_scores)
    top_flag = _top_flag(flags)

    focus_sentence = {
        "Dividend sustainability": (
            f"Dividend coverage is {_fmt(scenario['dividend_coverage'], 2)}x, "
            f"placing the distribution profile in **{scenario['dividend_status']}** territory."
        ),
        "Refinancing risk": (
            f"Near-term maturities represent {_fmt(scenario['near_term_debt_pct'])}% of debt, "
            f"with a refinancing risk score of {_fmt(scenario['refinancing_risk_score'], 0)}/100."
        ),
        "Asset value decline": (
            f"The stressed LTV moves to {_fmt(scenario['stressed_ltv_pct'])}%, "
            f"which should be tested against lender and investor thresholds."
        ),
        "Investor communication": (
            "The management narrative should explain the bridge from market pressure "
            "to controllable actions on debt, assets, tax leakage, and dividends."
        ),
    }.get(focus, "The scenario highlights a combined pressure point across cash flow, debt, and disclosure.")

    asset_sentence = "No material asset concentration issue was detected in the sample data."
    if top_asset is not None:
        asset_sentence = (
            f"The highest-ranked asset risk is **{top_asset['asset_name']}** "
            f"({top_asset['risk_tier']} risk, {_fmt(top_asset['asset_risk_score'], 0)}/100), "
            f"driven by tenant concentration, WALE, occupancy, and capex indicators."
        )

    flag_sentence = "No open disclosure flag is currently shown in the sample data."
    if top_flag is not None:
        flag_sentence = (
            f"The most urgent disclosure flag is **{top_flag['area']}**: {top_flag['flag']} "
            f"Recommended action: {top_flag['recommended_action']}."
        )

    return f"""
### CFO Briefing Memo - {reit_name}

**Scenario:** {scenario['scenario_label']}

**Executive view:** {focus_sentence}

**Cash-flow bridge:** tax-adjusted cash flow is estimated at **KRW {_fmt(scenario['tax_adjusted_cash_flow_krw_bn'])}bn**, after a rent impact of **KRW {_fmt(scenario['rent_delta_krw_bn'])}bn**, an interest/refinancing impact of **KRW {_fmt(scenario['interest_delta_krw_bn'])}bn**, and a tax impact of **KRW {_fmt(scenario['tax_delta_krw_bn'])}bn**.

**Risk driver:** {asset_sentence}

**Disclosure readiness:** {flag_sentence}

**Recommended CFO actions**

1. Confirm the refinancing timetable for maturities inside the next 24 months.
2. Align dividend guidance with tax-adjusted cash-flow coverage rather than headline NOI alone.
3. Prepare a concise investor bridge explaining rates, rents, valuation, tax drag, and management actions.
4. Convert open disclosure flags into structured data fields before scaling AI-generated reporting.
"""


def generate_investor_qa(
    reit_name: str,
    focus: str,
    scenario: dict,
    asset_scores: pd.DataFrame,
    flags: pd.DataFrame,
) -> str:
    top_asset = _top_asset(asset_scores)
    asset_name = top_asset["asset_name"] if top_asset is not None else "the portfolio"
    top_flag = _top_flag(flags)
    disclosure_topic = top_flag["area"] if top_flag is not None else "disclosure controls"

    return f"""
### Investor Q&A Draft - {reit_name}

**Q1. How sensitive is the dividend to the selected scenario?**  
Dividend coverage is estimated at **{_fmt(scenario['dividend_coverage'], 2)}x** under the current assumptions. Management can explain the dividend position through tax-adjusted cash flow, not just rental income, because the bridge includes rent movement, interest cost, refinancing exposure, and tax impact.

**Q2. What is the key refinancing message for investors?**  
Near-term maturities equal **KRW {_fmt(scenario['near_term_debt_krw_bn'])}bn** or **{_fmt(scenario['near_term_debt_pct'])}%** of debt. The investor message should separate debt already under negotiation from debt exposed to market-rate timing.

**Q3. Which asset risk should investors understand first?**  
The first asset to explain is **{asset_name}**. The narrative should focus on tenant concentration, occupancy, WALE, and capex needs, then connect those operating facts to cash-flow resilience.

**Q4. How should management address asset value pressure?**  
Under the selected asset-value shock, stressed LTV is **{_fmt(scenario['stressed_ltv_pct'])}%**. A credible answer should describe covenant headroom, refinancing alternatives, and whether valuation pressure changes capital allocation.

**Q5. What disclosure improvement would most improve confidence?**  
The current priority topic is **{disclosure_topic}**. Management should show that recurring investor questions are backed by structured data, approved definitions, and repeatable scenario outputs.
"""
