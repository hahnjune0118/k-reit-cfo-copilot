from __future__ import annotations

import re
from typing import Any

import pandas as pd

from modules.source_confidence import build_metric, not_available_metric


ACCOUNT_MAP: dict[str, list[str]] = {
    "total_assets": ["자산총계", "자산 총계", "Total assets", "Assets"],
    "total_liabilities": ["부채총계", "부채 총계", "Total liabilities", "Liabilities"],
    "total_equity": ["자본총계", "자본 총계", "Total equity", "Equity"],
    "current_assets": ["유동자산", "유동자산합계", "Current assets"],
    "noncurrent_assets": ["비유동자산", "비유동자산합계", "Non-current assets", "Noncurrent assets"],
    "current_liabilities": ["유동부채", "유동부채합계", "Current liabilities"],
    "noncurrent_liabilities": ["비유동부채", "비유동부채합계", "Non-current liabilities", "Noncurrent liabilities"],
    "cash_and_equivalents": ["현금및현금성자산", "현금 및 현금성자산", "Cash and cash equivalents"],
    "cash": ["현금", "Cash"],
    "short_term_debt": ["단기차입금", "유동성장기차입금", "Short-term borrowings", "Current borrowings"],
    "long_term_debt": ["장기차입금", "Long-term borrowings", "Non-current borrowings"],
    "borrowings": ["차입금", "Borrowings"],
    "bonds_payable": ["사채", "회사채", "Bonds payable"],
    "revenue": ["매출액", "영업수익", "수익", "Revenue", "Operating revenue"],
    "rental_income": ["임대수익", "임대료수익", "임대료", "Rental income", "Rental revenue"],
    "operating_income": ["영업이익", "Operating income", "Profit from operations"],
    "net_income": ["당기순이익", "분기순이익", "반기순이익", "Net income", "Profit for the period"],
    "finance_cost": ["금융비용", "이자비용", "Finance costs", "Interest expense"],
    "interest_expense": ["이자비용", "Interest expense"],
    "operating_cash_flow": ["영업활동현금흐름", "영업활동으로 인한 현금흐름", "Cash flows from operating activities"],
    "dividend_amount": ["배당금", "현금배당", "Dividends", "Dividend"],
}


def normalize_account_name(name: Any) -> str:
    text = str(name or "").casefold()
    text = re.sub(r"[\s()\[\]{}ㆍ·,._\-_/\\]+", "", text)
    return text


def match_account(account_name: Any) -> str | None:
    normalized = normalize_account_name(account_name)
    if not normalized:
        return None
    candidates: list[tuple[int, str, str]] = []
    for canonical, aliases in ACCOUNT_MAP.items():
        for alias in aliases:
            alias_norm = normalize_account_name(alias)
            if alias_norm:
                candidates.append((len(alias_norm), canonical, alias_norm))
    for _, canonical, alias_norm in sorted(candidates, reverse=True):
        if alias_norm in normalized or normalized in alias_norm:
            return canonical
    return None


def _clean_number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"[^0-9.\-]", "", text)
    if text in {"", "-", ".", "-."}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return -number if negative else number


def _amount_column(frame: pd.DataFrame) -> str:
    for column in ["thstrm_amount", "thstrm_add_amount", "frmtrm_amount", "amount", "value"]:
        if column in frame.columns:
            return column
    return ""


def extract_financial_metric(
    frame: pd.DataFrame,
    metric_name: str,
    *,
    source: str = "OpenDART financial statement API",
    as_of: str | None = None,
) -> dict[str, Any]:
    if frame.empty:
        return not_available_metric(metric_name, "KRW", source="OpenDART API", note="OpenDART 재무제표 계정 데이터가 비어 있습니다.", as_of=as_of)
    if "account_nm" not in frame.columns:
        return not_available_metric(metric_name, "KRW", source="OpenDART API", note="account_nm 컬럼이 없어 계정 매핑을 수행하지 못했습니다.", as_of=as_of)
    amount_column = _amount_column(frame)
    if not amount_column:
        return not_available_metric(metric_name, "KRW", source="OpenDART API", note="금액 컬럼이 없어 계정 금액을 추출하지 못했습니다.", as_of=as_of)

    for _, row in frame.iterrows():
        account_name = str(row.get("account_nm", ""))
        if match_account(account_name) != metric_name:
            continue
        amount = _clean_number(row.get(amount_column))
        if amount is None:
            continue
        return build_metric(
            metric_name,
            amount,
            "KRW",
            source,
            "High",
            source_type="OpenDART API",
            as_of=as_of,
            calculation_method=f"OpenDART account_nm '{account_name}' mapped to {metric_name}.",
            note=f"계정명 '{account_name}' 기준으로 매핑했습니다.",
        )

    return not_available_metric(
        metric_name,
        "KRW",
        source="OpenDART API",
        note=f"{metric_name}에 대응되는 OpenDART 계정을 찾지 못했습니다.",
        as_of=as_of,
    )


def build_financial_metric_table(frame: pd.DataFrame, *, as_of: str | None = None) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if frame.empty or "account_nm" not in frame.columns:
        return pd.DataFrame(columns=["account_nm", "mapped_metric", "amount", "confidence", "source"])
    amount_column = _amount_column(frame)
    for _, row in frame.iterrows():
        mapped = match_account(row.get("account_nm"))
        amount = _clean_number(row.get(amount_column)) if amount_column else None
        if mapped is None:
            continue
        rows.append(
            {
                "account_nm": row.get("account_nm"),
                "mapped_metric": mapped,
                "amount": amount,
                "confidence": "High" if amount is not None else "Not Available",
                "source": "OpenDART financial statement API",
                "as_of": as_of,
            }
        )
    return pd.DataFrame(rows)
