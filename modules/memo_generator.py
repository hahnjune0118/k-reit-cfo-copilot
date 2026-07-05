from __future__ import annotations

import pandas as pd


FOCUS_LABELS = {
    "dividend": "배당 안정성",
    "refinancing": "리파이낸싱 리스크",
    "asset_value": "자산가치 하락",
    "tenant": "임차인 리스크",
    "disclosure": "공시 품질",
}

FOCUS_TO_RISK_CATEGORY = {
    "dividend": "Dividend Sustainability",
    "refinancing": "Refinancing Risk",
    "asset_value": "Asset Risk",
    "tenant": "Asset Risk",
    "disclosure": "Disclosure Quality",
}


def _fmt(value: float, digits: int = 1) -> str:
    return f"{value:,.{digits}f}"


def _krw(value: float, digits: int = 1) -> str:
    return f"KRW {_fmt(value, digits)}bn"


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


def _risk_row(category_scores: pd.DataFrame | None, focus: str) -> pd.Series | None:
    if category_scores is None or category_scores.empty:
        return None
    category = FOCUS_TO_RISK_CATEGORY.get(focus)
    match = category_scores[category_scores["category"] == category]
    if match.empty:
        return None
    return match.iloc[0]


def _risk_summary(category_scores: pd.DataFrame | None, focus: str) -> str:
    row = _risk_row(category_scores, focus)
    if row is None:
        return "정량 Risk Score는 별도 Dashboard에서 확인 가능합니다."
    return f"{row['category']}는 {row['label']} 구간이며 Risk Score는 {_fmt(float(row['score']), 0)}/100입니다."


def _focus_context(focus: str, scenario: dict, asset_scores: pd.DataFrame, flags: pd.DataFrame) -> dict[str, str]:
    top_asset = _top_asset(asset_scores)
    top_flag = _top_flag(flags)
    asset_name = top_asset["asset_name"] if top_asset is not None else "portfolio"
    flag_area = top_flag["area"] if top_flag is not None else "공시 controls"

    contexts = {
        "dividend": {
            "summary": (
                f"배당 안정성 관점에서 dividend coverage는 {_fmt(scenario['dividend_coverage'], 2)}x, "
                f"dividend buffer는 {_krw(scenario['dividend_buffer_krw_bn'])}입니다."
            ),
            "risk": "AFFO estimate가 dividend payout을 충분히 방어하지 못하면 배당 guidance 신뢰도가 약화될 수 있습니다.",
            "question": "현재 금리와 임대료 scenario에서도 배당 안정성을 유지할 수 있습니까?",
            "caution": "확정 배당 guidance처럼 표현하지 말고, scenario assumption과 buffer 민감도를 함께 설명해야 합니다.",
        },
        "refinancing": {
            "summary": (
                f"near-term maturity는 {_krw(scenario['near_term_debt_krw_bn'], 0)}이며 "
                f"refinancing Risk Score는 {_fmt(scenario['refinancing_risk_score'], 0)}/100입니다."
            ),
            "risk": "금리 충격은 floating-rate debt와 near-term refinancing cost를 동시에 압박합니다.",
            "question": "향후 만기 도래 차입금의 refinancing plan은 충분히 확보되어 있습니까?",
            "caution": "lender 협의 상태와 market-rate timing을 구분해 설명해야 합니다.",
        },
        "asset_value": {
            "summary": (
                f"asset value shock 반영 후 stressed LTV는 {_fmt(scenario['stressed_ltv_pct'])}%이며 "
                f"base 대비 {_fmt(scenario['ltv_change_pctp'])}p 변동합니다."
            ),
            "risk": "자산가치 하락은 LTV, covenant headroom, capital allocation narrative에 영향을 줍니다.",
            "question": "자산가치 하락이 LTV와 배당가능성에 미치는 영향은 어느 정도입니까?",
            "caution": "valuation decline을 단일 숫자로 단정하지 말고 LTV range와 covenant headroom 중심으로 설명해야 합니다.",
        },
        "tenant": {
            "summary": f"임차인 리스크 관점에서 우선 설명할 asset은 {asset_name}입니다.",
            "risk": "tenant concentration, WALE, occupancy 변화는 NOI 안정성과 investor confidence에 직접 연결됩니다.",
            "question": "주요 tenant renewal과 occupancy 안정성에 대한 management view는 무엇입니까?",
            "caution": "개별 tenant 정보는 disclosure policy와 confidentiality를 고려해 portfolio-level language로 조정해야 합니다.",
        },
        "disclosure": {
            "summary": f"공시 품질 관점에서 우선 점검할 disclosure topic은 {flag_area}입니다.",
            "risk": "disclosure flag가 정리되지 않으면 Investor Q&A와 management narrative의 일관성이 약화됩니다.",
            "question": "투자자에게 반복적으로 설명해야 할 disclosure topic과 개선 일정은 무엇입니까?",
            "caution": "공시 개선 계획은 책임자, source data, target date가 있는 실행 항목으로 표현해야 합니다.",
        },
    }
    return contexts.get(focus, contexts["dividend"])


def generate_cfo_memo(
    reit_name: str,
    focus: str,
    scenario: dict,
    asset_scores: pd.DataFrame,
    flags: pd.DataFrame,
    category_scores: pd.DataFrame | None = None,
    overall: dict | None = None,
) -> str:
    context = _focus_context(focus, scenario, asset_scores, flags)
    top_asset = _top_asset(asset_scores)
    top_flag = _top_flag(flags)
    risk_summary = _risk_summary(category_scores, focus)
    overall_sentence = ""
    if overall:
        overall_sentence = f" Overall Risk Score는 {_fmt(float(overall['overall_score']), 0)}/100이며 label은 {overall['overall_label']}입니다."

    asset_sentence = "자산별 특이사항은 제한적입니다."
    if top_asset is not None:
        asset_sentence = (
            f"상위 asset risk는 {top_asset['asset_name']}이며 Asset Risk Score는 "
            f"{_fmt(float(top_asset['asset_risk_score']), 0)}/100입니다."
        )

    flag_sentence = "open disclosure flag는 제한적입니다."
    if top_flag is not None:
        flag_sentence = f"주요 disclosure flag는 {top_flag['area']}입니다. {top_flag['recommended_action']}"

    return f"""# CFO Briefing Memo - {reit_name}

## 핵심 요약
{context['summary']} {risk_summary}{overall_sentence}

## 주요 리스크
- {context['risk']}
- {asset_sentence}
- {flag_sentence}

## 배당가능성 영향
- AFFO estimate는 {_krw(scenario['affo_estimate_krw_bn'])}입니다.
- dividend coverage는 {_fmt(scenario['dividend_coverage'], 2)}x입니다.
- dividend buffer는 {_krw(scenario['dividend_buffer_krw_bn'])}이며, buffer가 축소될 경우 배당 policy와 cash reserve 사용 가능성을 함께 검토해야 합니다.

## 리파이낸싱 영향
- interest expense impact는 {_krw(scenario['interest_expense_impact_krw_bn'])}입니다.
- near-term maturity는 {_krw(scenario['near_term_debt_krw_bn'], 0)}이며 전체 debt의 {_fmt(scenario['near_term_debt_pct'])}%입니다.
- refinancing risk level은 {scenario['refinancing_status']}이며 Risk Score는 {_fmt(scenario['refinancing_risk_score'], 0)}/100입니다.

## 세금효과 고려사항
- tax impact는 {_krw(scenario['tax_delta_krw_bn'])}로 반영했습니다.
- v05 MVP에서는 tax drag를 단순 assumption으로 반영하므로, 실제 board memo에서는 taxable income, withholding, property tax, transaction tax를 별도 검토해야 합니다.

## CFO 권고 액션
1. focus topic인 {FOCUS_LABELS.get(focus, focus)}에 대해 board-level decision question을 먼저 확정합니다.
2. FFO/AFFO bridge와 dividend buffer sensitivity를 CFO Dashboard와 일치시킵니다.
3. refinancing timetable, lender status, covenant headroom을 최신화합니다.
4. Investor Q&A에 사용할 approved metric과 disclosure wording을 IR팀과 사전 합의합니다.
"""


def generate_investor_qa(
    reit_name: str,
    focus: str,
    scenario: dict,
    asset_scores: pd.DataFrame,
    flags: pd.DataFrame,
    category_scores: pd.DataFrame | None = None,
    overall: dict | None = None,
) -> str:
    context = _focus_context(focus, scenario, asset_scores, flags)
    risk_summary = _risk_summary(category_scores, focus)

    return f"""# Investor Q&A Draft - {reit_name}

## 예상 질문
{context['question']}

## 답변 초안
현재 scenario 기준으로 {context['summary']} {risk_summary}

management는 단순 NOI 변화만 보지 않고 FFO estimate, AFFO estimate, dividend buffer, LTV, refinancing Risk Score를 함께 검토하고 있습니다. 선택한 scenario에서 AFFO estimate는 {_krw(scenario['affo_estimate_krw_bn'])}, dividend buffer는 {_krw(scenario['dividend_buffer_krw_bn'])}, stressed LTV는 {_fmt(scenario['stressed_ltv_pct'])}%입니다.

리파이낸싱 측면에서는 near-term maturity {_krw(scenario['near_term_debt_krw_bn'], 0)}와 interest expense impact {_krw(scenario['interest_expense_impact_krw_bn'])}를 우선 관리하고 있으며, lender 협의 상황과 시장금리 변화를 반영해 funding plan을 업데이트할 예정입니다.

## 커뮤니케이션 유의사항
- {context['caution']}
- scenario output은 forecast가 아니라 sensitivity analysis로 표현해야 합니다.
- Investor Q&A에서는 숫자, assumption, management action을 한 문단 안에서 연결해 설명해야 합니다.
- 필요한 경우 공시 전 확인이 필요한 tenant, lender, tax detail은 portfolio-level 표현으로 조정합니다.
"""


def markdown_to_plain_text(markdown: str) -> str:
    replacements = {
        "# ": "",
        "## ": "",
        "### ": "",
        "**": "",
        "- ": "• ",
    }
    text = markdown
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text
