from __future__ import annotations

import pandas as pd


FOCUS_LABELS = {
    "dividend": "배당 지속 가능성",
    "refinancing": "refinancing risk",
    "asset_value": "자산가치 하락",
    "investor": "Investor communication",
}

DIVIDEND_STATUS_KO = {
    "Resilient": "Resilient",
    "Defensible": "Defensible",
    "Watch": "Watch",
    "Pressure": "Pressure",
}

RISK_TIER_KO = {
    "High": "High",
    "Medium": "Medium",
    "Low": "Low",
}


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
        "dividend": (
            f"현재 scenario 기준 dividend coverage는 **{_fmt(scenario['dividend_coverage'], 2)}x**이며 "
            f"배당 profile은 **{DIVIDEND_STATUS_KO.get(scenario['dividend_status'], scenario['dividend_status'])}** 구간으로 평가됩니다."
        ),
        "refinancing": (
            f"향후 24개월 내 만기 도래 debt는 전체 debt의 **{_fmt(scenario['near_term_debt_pct'])}%**이며 "
            f"refinancing Risk Score는 **{_fmt(scenario['refinancing_risk_score'], 0)}/100**입니다."
        ),
        "asset_value": (
            f"자산가치 shock 반영 후 stressed LTV는 **{_fmt(scenario['stressed_ltv_pct'])}%**입니다. "
            "lender threshold와 investor sensitivity를 함께 점검해야 합니다."
        ),
        "investor": (
            "management narrative는 금리와 valuation pressure를 설명하는 데서 끝나지 않고 "
            "debt action, asset action, tax leakage, dividend policy를 하나의 bridge로 연결해야 합니다."
        ),
    }.get(
        focus,
        "이번 scenario는 cash flow, debt, disclosure가 동시에 압박받는 복합 리스크를 보여줍니다.",
    )

    asset_sentence = "sample data 기준으로 즉시 강조해야 할 자산 concentration issue는 제한적입니다."
    if top_asset is not None:
        asset_sentence = (
            f"가장 높은 asset Risk Score는 **{top_asset['asset_name']}**입니다 "
            f"({RISK_TIER_KO.get(top_asset['risk_tier'], top_asset['risk_tier'])} risk, "
            f"{_fmt(top_asset['asset_risk_score'], 0)}/100). "
            "주요 driver는 tenant concentration, WALE, occupancy, capex 지표입니다."
        )

    flag_sentence = "현재 sample data에는 open disclosure flag가 표시되지 않습니다."
    if top_flag is not None:
        flag_sentence = (
            f"우선 점검할 disclosure flag는 **{top_flag['area']}**입니다: {top_flag['flag']} "
            f"권고 action: {top_flag['recommended_action']}."
        )

    return f"""
### CFO Briefing Memo - {reit_name}

**Scenario:** {scenario['scenario_label']}

**Executive view:** {focus_sentence}

**Cash-flow bridge:** tax-adjusted cash flow는 **KRW {_fmt(scenario['tax_adjusted_cash_flow_krw_bn'])}bn**으로 추정됩니다. rent impact **KRW {_fmt(scenario['rent_delta_krw_bn'])}bn**, interest/refinancing impact **KRW {_fmt(scenario['interest_delta_krw_bn'])}bn**, tax impact **KRW {_fmt(scenario['tax_delta_krw_bn'])}bn**을 반영한 결과입니다.

**Risk driver:** {asset_sentence}

**Disclosure readiness:** {flag_sentence}

**Recommended CFO actions**

1. 24개월 내 maturity에 대한 refinancing timetable과 lender status를 확정합니다.
2. 배당 guidance는 headline NOI가 아니라 tax-adjusted cash-flow coverage 기준으로 설명합니다.
3. 금리, rent, valuation, tax drag, management action을 연결한 investor bridge를 준비합니다.
4. open disclosure flag를 structured data field로 전환해 AI-generated reporting의 governance 기반을 만듭니다.
"""


def generate_investor_qa(
    reit_name: str,
    focus: str,
    scenario: dict,
    asset_scores: pd.DataFrame,
    flags: pd.DataFrame,
) -> str:
    top_asset = _top_asset(asset_scores)
    asset_name = top_asset["asset_name"] if top_asset is not None else "portfolio"
    top_flag = _top_flag(flags)
    disclosure_topic = top_flag["area"] if top_flag is not None else "disclosure controls"

    return f"""
### Investor Q&A Draft - {reit_name}

**Q1. 이번 scenario에서 배당은 얼마나 민감합니까?**  
현재 assumption 기준 dividend coverage는 **{_fmt(scenario['dividend_coverage'], 2)}x**입니다. 단순 임대수익이 아니라 rent movement, interest cost, refinancing exposure, tax impact를 반영한 tax-adjusted cash flow 기준으로 설명하는 것이 적절합니다.

**Q2. 투자자에게 전달해야 할 refinancing message는 무엇입니까?**  
near-term maturity는 **KRW {_fmt(scenario['near_term_debt_krw_bn'])}bn**이며 전체 debt의 **{_fmt(scenario['near_term_debt_pct'])}%**입니다. 이미 협의 중인 debt와 market-rate timing에 노출된 debt를 분리해 설명해야 합니다.

**Q3. 어떤 asset risk를 먼저 설명해야 합니까?**  
우선 설명할 asset은 **{asset_name}**입니다. tenant concentration, occupancy, WALE, capex needs를 먼저 설명한 뒤 해당 운영 지표가 cash-flow resilience와 어떻게 연결되는지 제시합니다.

**Q4. 자산가치 하락 압력은 어떻게 대응하고 있습니까?**  
선택한 asset-value shock 기준 stressed LTV는 **{_fmt(scenario['stressed_ltv_pct'])}%**입니다. covenant headroom, refinancing alternative, capital allocation 변화 여부를 함께 설명하는 답변이 필요합니다.

**Q5. 투자자 신뢰를 높이기 위해 가장 먼저 개선할 disclosure topic은 무엇입니까?**  
현재 우선순위 topic은 **{disclosure_topic}**입니다. 반복되는 Investor Q&A가 structured data, approved definition, repeatable scenario output에 기반한다는 점을 보여주는 것이 중요합니다.
"""
