from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO, StringIO
import json
from pathlib import Path
import re
import time
from typing import Any
import zipfile

import pandas as pd
import requests

from modules.api_clients.config import get_dart_api_key
from modules.macro_assumptions import build_macro_rate_environment
from modules.account_mapper import match_account
from modules.source_confidence import build_metric, infer_source_type, not_available_metric


BASE_DIR = Path(__file__).resolve().parents[1]
CACHE_DIR = BASE_DIR / "data" / "cache"
DART_BASE_URL = "https://opendart.fss.or.kr/api"
USER_AGENT = "K-REIT-CFO-Copilot/12 (+portfolio prototype)"

FINANCIAL_REPORT_CODES = {
    "11011": "사업보고서",
    "11012": "반기보고서",
    "11013": "1분기보고서",
    "11014": "3분기보고서",
}

PERIODIC_REPORT_TYPES = ["사업보고서", "반기보고서", "분기보고서", "1분기보고서", "3분기보고서"]

ACCOUNT_ALIASES: dict[str, list[str]] = {
    "total_assets": ["자산총계", "자산 총계", "Total assets"],
    "total_liabilities": ["부채총계", "부채 총계", "Total liabilities"],
    "total_equity": ["자본총계", "자본 총계", "Total equity"],
    "current_assets": ["유동자산", "유동자산합계", "Current assets"],
    "noncurrent_assets": ["비유동자산", "비유동자산합계", "Non-current assets", "Noncurrent assets"],
    "revenue": ["매출액", "영업수익", "수익", "Revenue", "Operating revenue"],
    "rental_income": ["임대수익", "임대료수익", "임대료", "Rental income", "Rental revenue"],
    "operating_income": ["영업이익", "Operating income"],
    "net_income": ["당기순이익", "분기순이익", "반기순이익", "Net income"],
    "cash_and_equivalents": ["현금및현금성자산", "현금 및 현금성자산", "Cash and cash equivalents"],
    "short_term_debt": ["단기차입금", "유동성장기차입금", "Short-term borrowings"],
    "long_term_debt": ["장기차입금", "Long-term borrowings"],
    "borrowings": ["차입금", "Borrowings"],
    "bonds_payable": ["사채", "Bonds payable"],
    "current_liabilities": ["유동부채", "유동부채합계", "Current liabilities"],
    "noncurrent_liabilities": ["비유동부채", "비유동부채합계", "Non-current liabilities", "Noncurrent liabilities"],
    "finance_cost": ["금융비용", "이자비용", "Finance costs", "Interest expense"],
    "interest_expense": ["이자비용", "금융비용", "Interest expense", "Finance costs"],
    "operating_cash_flow": ["영업활동현금흐름", "영업활동으로 인한 현금흐름", "Cash flows from operating activities"],
    "dividend_amount": ["배당금", "현금배당", "Dividends", "Dividend"],
}

REQUIRED_METRICS = [
    "total_assets",
    "total_liabilities",
    "total_equity",
    "current_assets",
    "noncurrent_assets",
    "total_debt",
    "cash",
    "cash_and_equivalents",
    "revenue",
    "rental_income",
    "operating_income",
    "net_income",
    "interest_expense",
    "finance_cost",
    "operating_cash_flow",
    "short_term_debt",
    "long_term_debt",
    "borrowings",
    "bonds_payable",
    "current_liabilities",
    "noncurrent_liabilities",
    "latest_price",
    "market_cap",
    "base_rate",
    "treasury_yield",
    "corporate_bond_yield",
    "credit_spread_proxy",
    "ffo",
    "affo",
    "wale",
    "tenant_concentration",
    "asset_level_noi",
    "debt_maturity_wall",
    "dividend_amount",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _selected_value(selected_reit: Any, key: str, default: str = "") -> str:
    try:
        value = selected_reit.get(key, default)
    except AttributeError:
        return default
    if value is None or pd.isna(value):
        return default
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _cache_path(group: str, key: str, suffix: str) -> Path:
    directory = CACHE_DIR / group
    directory.mkdir(parents=True, exist_ok=True)
    digest = sha256(key.encode("utf-8")).hexdigest()
    return directory / f"{digest}.{suffix}"


def _read_json_cache(path: Path, ttl_seconds: int = 60 * 60) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - float(payload.get("_cached_at", 0)) > ttl_seconds:
            return None
        return payload.get("data")
    except (OSError, ValueError, TypeError):
        return None


def _write_json_cache(path: Path, data: dict[str, Any]) -> None:
    try:
        path.write_text(json.dumps({"_cached_at": time.time(), "data": data}, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _read_binary_cache(path: Path, ttl_seconds: int = 60 * 60 * 24) -> bytes | None:
    if not path.exists():
        return None
    if time.time() - path.stat().st_mtime > ttl_seconds:
        return None
    try:
        return path.read_bytes()
    except OSError:
        return None


def _write_binary_cache(path: Path, data: bytes) -> None:
    try:
        path.write_bytes(data)
    except OSError:
        pass


def _cached_get_json(url: str, params: dict[str, Any], cache_group: str, cache_key: str, force_refresh: bool = False) -> dict[str, Any]:
    cache_file = _cache_path(cache_group, cache_key, "json")
    if not force_refresh:
        cached = _read_json_cache(cache_file)
        if cached is not None:
            return cached

    try:
        response = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=15)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return {}

    _write_json_cache(cache_file, payload)
    return payload


def _cached_get_bytes(url: str, params: dict[str, Any], cache_group: str, cache_key: str, force_refresh: bool = False) -> bytes:
    cache_file = _cache_path(cache_group, cache_key, "bin")
    if not force_refresh:
        cached = _read_binary_cache(cache_file)
        if cached is not None:
            return cached

    try:
        response = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=20)
        response.raise_for_status()
    except requests.RequestException:
        return b""

    _write_binary_cache(cache_file, response.content)
    return response.content


def build_metric_with_source(
    name: str,
    value: Any,
    unit: str,
    source: str,
    confidence: str,
    note: str | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    return build_metric(
        name,
        value,
        unit,
        source,
        confidence,
        source_type=infer_source_type(source),
        as_of=as_of or _now_iso(),
        calculation_method=note or "",
        note=note or "",
    )


def _missing_metric(name: str, unit: str = "KRW", note: str = "") -> dict[str, Any]:
    return not_available_metric(
        name,
        unit,
        source="Not Available",
        note=note or "자동 수집 시도 후 미확보",
        as_of=None,
    )


def _missing_financial_metric(
    name: str,
    source: str = "자동 수집 시도 후 미확보",
    note: str = "OpenDART 재무제표 API에서 아직 확보되지 않았습니다.",
    as_of: str | None = None,
) -> dict[str, Any]:
    metric = build_metric_with_source(name, None, "KRW", source, "Not available", note)
    metric["as_of"] = as_of
    metric["source_type"] = "Not Available"
    metric["calculation_method"] = "Not calculated because OpenDART financial statement source data is unavailable."
    metric["warning"] = note
    return metric


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


def _normalize_account_name(name: str) -> str:
    return re.sub(r"[\s()\[\]·ㆍ_-]+", "", str(name).casefold())


def map_opendart_account_name(account_name: str) -> str | None:
    mapped = match_account(account_name)
    if mapped:
        return mapped
    normalized = _normalize_account_name(account_name)
    for canonical, aliases in ACCOUNT_ALIASES.items():
        for alias in aliases:
            if _normalize_account_name(alias) in normalized or normalized in _normalize_account_name(alias):
                return canonical
    return None


def _resolve_corp_code(selected_reit: Any) -> tuple[str, str, list[str]]:
    warnings: list[str] = []
    corp_code = _selected_value(selected_reit, "corp_code")
    corp_name = _selected_value(selected_reit, "real_reit_name") or _selected_value(selected_reit, "corp_name")
    if corp_code:
        return corp_code, corp_name, warnings

    try:
        from modules.api_clients.dart_client import find_corp_by_name

        matches = find_corp_by_name(corp_name)
    except Exception as exc:
        warnings.append(f"OpenDART corp_code lookup 실패: {exc.__class__.__name__}")
        return "", corp_name, warnings

    if matches.empty:
        warnings.append("OpenDART corp_code를 찾지 못했습니다.")
        return "", corp_name, warnings

    first = matches.iloc[0]
    return str(first.get("corp_code", "")).strip(), str(first.get("corp_name", corp_name)).strip(), warnings


def _default_financial_metrics(
    source: str = "자동 수집 시도 후 미확보",
    note: str = "OpenDART 재무제표 API에서 아직 확보되지 않았습니다.",
    as_of: str | None = None,
) -> dict[str, dict[str, Any]]:
    return {
        key: _missing_financial_metric(key, source=source, note=note, as_of=as_of)
        for key in [
            "total_assets",
            "total_liabilities",
            "total_equity",
            "current_assets",
            "noncurrent_assets",
            "revenue",
            "rental_income",
            "operating_income",
            "net_income",
            "cash",
            "cash_and_equivalents",
            "short_term_debt",
            "long_term_debt",
            "borrowings",
            "bonds_payable",
            "current_liabilities",
            "noncurrent_liabilities",
            "interest_expense",
            "finance_cost",
            "operating_cash_flow",
            "total_debt",
        ]
    }


def _extract_financial_metrics_from_frame(frame: pd.DataFrame, source_note: str, as_of: str) -> dict[str, dict[str, Any]]:
    metrics = _default_financial_metrics()
    decisions: dict[str, str] = {}

    if frame.empty or "account_nm" not in frame.columns:
        return metrics

    amount_column = next(
        (column for column in ["thstrm_amount", "thstrm_add_amount", "frmtrm_amount"] if column in frame.columns),
        "",
    )
    if not amount_column:
        return metrics

    for _, row in frame.iterrows():
        account_name = str(row.get("account_nm", "")).strip()
        canonical = map_opendart_account_name(account_name)
        if not canonical:
            continue
        amount = _clean_number(row.get(amount_column))
        if amount is None:
            continue
        current = metrics.get(canonical, {})
        if current.get("value") is None:
            decisions[canonical] = account_name
            metrics[canonical] = build_metric_with_source(
                canonical,
                amount,
                "KRW",
                "OpenDART financial statement API",
                "High",
                f"{source_note}; account_nm='{account_name}' 매핑",
                as_of=as_of,
            )

    debt_parts = [
        metrics["short_term_debt"]["value"],
        metrics["long_term_debt"]["value"],
        metrics["bonds_payable"]["value"],
    ]
    if any(value is not None for value in debt_parts):
        total = sum(float(value or 0) for value in debt_parts)
        metrics["total_debt"] = build_metric_with_source(
            "total_debt",
            total,
            "KRW",
            "OpenDART financial statement API",
            "Medium",
            "단기차입금, 장기차입금, 사채 계정 합산 proxy입니다.",
            as_of=as_of,
        )
    elif metrics["borrowings"]["value"] is not None:
        metrics["total_debt"] = build_metric_with_source(
            "total_debt",
            metrics["borrowings"]["value"],
            "KRW",
            "OpenDART financial statement API",
            "Medium",
            f"차입금 계정 기반 proxy입니다. 매핑: {decisions.get('borrowings', '차입금')}",
            as_of=as_of,
        )

    if metrics["cash_and_equivalents"]["value"] is not None:
        metrics["cash"] = {
            **metrics["cash_and_equivalents"],
            "name": "cash",
            "note": f"{metrics['cash_and_equivalents'].get('note', '')} cash alias.",
        }
    if metrics["finance_cost"]["value"] is not None:
        metrics["interest_expense"] = {
            **metrics["finance_cost"],
            "name": "interest_expense",
            "note": f"{metrics['finance_cost'].get('note', '')} interest_expense alias.",
        }

    return metrics


def collect_opendart_financials(selected_reit: Any, api_key: str | None = None, force_refresh: bool = False) -> dict[str, Any]:
    api_key_text = "" if api_key is None else str(api_key).strip()
    missing_key_message = "DART_API_KEY missing: OpenDART financial statement extraction skipped."
    missing_key_note = "DART_API_KEY가 없어 OpenDART 재무제표 데이터를 수집하지 못했습니다."
    if not api_key_text:
        return {
            "metrics": _default_financial_metrics(
                source="OpenDART API key missing",
                note=missing_key_note,
                as_of=None,
            ),
            "raw_accounts": [],
            "corp_code": _selected_value(selected_reit, "corp_code"),
            "corp_name": _selected_value(selected_reit, "real_reit_name") or _selected_value(selected_reit, "corp_name"),
            "source": "OpenDART API key missing",
            "confidence": "Not available",
            "as_of": None,
            "warnings": [missing_key_message],
        }

    corp_code, corp_name, lookup_warnings = _resolve_corp_code(selected_reit)
    result: dict[str, Any] = {
        "metrics": _default_financial_metrics(),
        "raw_accounts": [],
        "corp_code": corp_code,
        "corp_name": corp_name,
        "source": "OpenDART financial statement API",
        "confidence": "Not available",
        "as_of": _now_iso(),
        "warnings": lookup_warnings,
    }

    if not corp_code:
        result["warnings"].append("corp_code가 없어 OpenDART 재무제표 API를 호출하지 않았습니다.")
        return result

    current_year = datetime.now().year
    for year in range(current_year - 1, current_year - 5, -1):
        for report_code, report_label in FINANCIAL_REPORT_CODES.items():
            for fs_div in ["CFS", "OFS"]:
                payload = _cached_get_json(
                    f"{DART_BASE_URL}/fnlttSinglAcntAll.json",
                    {
                        "crtfc_key": api_key_text,
                        "corp_code": corp_code,
                        "bsns_year": str(year),
                        "reprt_code": report_code,
                        "fs_div": fs_div,
                    },
                    "opendart",
                    f"financials:{corp_code}:{year}:{report_code}:{fs_div}",
                    force_refresh=force_refresh,
                )
                if str(payload.get("status", "")) != "000" or not payload.get("list"):
                    continue

                frame = pd.DataFrame(payload["list"])
                source_note = f"{year} {report_label} {fs_div}"
                result["raw_accounts"] = frame.to_dict("records")
                result["metrics"] = _extract_financial_metrics_from_frame(frame, source_note, as_of=f"{year}")
                result["confidence"] = "High"
                result["as_of"] = f"{year}"
                result["warnings"] = lookup_warnings
                return result

    result["warnings"].append("OpenDART 재무제표 API에서 사용 가능한 계정 데이터를 찾지 못했습니다.")
    return result


def collect_opendart_disclosures(selected_reit: Any, api_key: str | None = None) -> pd.DataFrame:
    if api_key is not None and not str(api_key).strip():
        frame = pd.DataFrame()
        frame.attrs["is_fallback"] = True
        frame.attrs["api_connected"] = False
        frame.attrs["source"] = "OpenDART API key missing"
        frame.attrs["status_message"] = "DART_API_KEY missing: OpenDART disclosure list extraction skipped."
        return frame

    try:
        from modules.real_data_loader import load_real_disclosure_data

        disclosures = load_real_disclosure_data(selected_reit)
    except Exception as exc:
        disclosures = pd.DataFrame()
        disclosures.attrs["is_fallback"] = True
        disclosures.attrs["api_connected"] = False
        disclosures.attrs["source"] = "OpenDART API"
        disclosures.attrs["status_message"] = f"OpenDART 공시 목록 조회 실패: {exc.__class__.__name__}"
        return disclosures

    if not disclosures.empty and "report_type" in disclosures.columns:
        priority = disclosures["report_type"].isin(PERIODIC_REPORT_TYPES + ["주요사항보고서", "투자설명서"])
        disclosures = pd.concat([disclosures[priority], disclosures[~priority]], ignore_index=True)
    return disclosures


def _strip_report_markup(raw_text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw_text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _decode_report_payload(payload: bytes) -> str:
    if not payload:
        return ""
    chunks: list[str] = []
    try:
        with zipfile.ZipFile(BytesIO(payload)) as zip_file:
            for name in zip_file.namelist():
                if name.lower().endswith((".xml", ".html", ".htm", ".txt")):
                    raw = zip_file.read(name)
                    chunks.append(raw.decode("utf-8", errors="ignore"))
    except zipfile.BadZipFile:
        chunks.append(payload.decode("utf-8", errors="ignore"))
    return _strip_report_markup(" ".join(chunks))


def _evidence_snippets(text: str, keywords: list[str], window: int = 120) -> list[dict[str, str]]:
    snippets: list[dict[str, str]] = []
    lowered = text.casefold()
    for keyword in keywords:
        start = lowered.find(keyword.casefold())
        if start < 0:
            continue
        begin = max(start - window, 0)
        end = min(start + len(keyword) + window, len(text))
        snippets.append({"keyword": keyword, "snippet": text[begin:end].strip()})
    return snippets[:20]


def _extract_amount_from_snippets(snippets: list[dict[str, str]], metric_name: str) -> dict[str, Any]:
    for item in snippets:
        snippet = item["snippet"]
        match = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?)\s*(조원|억원|백만원|천원|원)?", snippet)
        if not match:
            continue
        number = _clean_number(match.group(1))
        if number is None:
            continue
        unit = match.group(2) or ""
        multiplier = 1.0
        if unit == "조원":
            multiplier = 1_000_000_000_000
        elif unit == "억원":
            multiplier = 100_000_000
        elif unit == "백만원":
            multiplier = 1_000_000
        elif unit == "천원":
            multiplier = 1_000
        elif not unit and number < 10_000:
            return _missing_metric(metric_name, "KRW", "공시 원문에서 숫자는 발견했지만 단위를 확정하지 못했습니다.")
        return build_metric_with_source(
            metric_name,
            number * multiplier,
            "KRW",
            "OpenDART report parser",
            "Low",
            f"keyword='{item['keyword']}' 주변 문맥에서 추출한 예비값입니다.",
        )
    return _missing_metric(metric_name, "KRW", "공시 원문 keyword는 확인했으나 구조화 수치 추출은 제한적입니다.")


def parse_reit_specific_metrics(report_text: str, tables: Any = None) -> dict[str, Any]:
    del tables
    keywords = [
        "차입",
        "차입금",
        "단기차입금",
        "장기차입금",
        "사채",
        "만기",
        "이자율",
        "금리",
        "담보",
        "투자부동산",
        "임대수익",
        "임대료",
        "임차인",
        "배당",
        "FFO",
        "AFFO",
        "운용수익",
        "자산보유현황",
        "부동산투자회사",
        "투자보고서",
        "자산관리회사",
        "AMC",
        "WALE",
    ]
    snippets = _evidence_snippets(report_text, keywords)
    text = report_text or ""

    metrics = {
        "rental_revenue": _extract_amount_from_snippets(
            [item for item in snippets if item["keyword"] in {"임대수익", "임대료", "운용수익"}],
            "rental_revenue",
        ),
        "dividend_amount": _extract_amount_from_snippets(
            [item for item in snippets if item["keyword"] == "배당"],
            "dividend_amount",
        ),
        "ffo": _extract_amount_from_snippets([item for item in snippets if item["keyword"] == "FFO"], "ffo"),
        "affo": _extract_amount_from_snippets([item for item in snippets if item["keyword"] == "AFFO"], "affo"),
        "asset_level_noi": _missing_metric("asset_level_noi", "KRW", "자산별 NOI는 공시 원문에서 구조화 추출하지 못했습니다."),
        "tenant_concentration": _missing_metric("tenant_concentration", "%", "임차인 집중도는 공시 원문에서 구조화 추출하지 못했습니다."),
        "wale": _missing_metric("wale", "years", "WALE는 공시 원문에서 구조화 추출하지 못했습니다."),
        "debt_maturity_wall": _missing_metric("debt_maturity_wall", "KRW", "차입 만기 표는 공시 원문에서 구조화 추출하지 못했습니다."),
    }

    wale_match = re.search(r"WALE[^0-9]{0,30}([0-9]+(?:\.[0-9]+)?)", text, flags=re.I)
    if wale_match:
        metrics["wale"] = build_metric_with_source(
            "wale",
            float(wale_match.group(1)),
            "years",
            "OpenDART report parser",
            "Low",
            "WALE keyword 주변 숫자 추출값입니다.",
        )

    concentration_match = re.search(r"(임차인|tenant)[^%]{0,80}([0-9]+(?:\.[0-9]+)?)\s*%", text, flags=re.I)
    if concentration_match:
        metrics["tenant_concentration"] = build_metric_with_source(
            "tenant_concentration",
            float(concentration_match.group(2)),
            "%",
            "OpenDART report parser",
            "Low",
            "임차인 keyword 주변 비율 추출값입니다.",
        )

    return {
        "metrics": metrics,
        "evidence_snippets": snippets,
        "parser_note": "공시 원문 keyword 기반 예비 parser입니다. 구조화 표 검증 전에는 manual validation을 권장합니다.",
    }


def download_and_parse_opendart_report(selected_reit: Any, api_key: str | None = None, force_refresh: bool = False) -> dict[str, Any]:
    api_key_text = "" if api_key is None else str(api_key).strip()
    result: dict[str, Any] = {
        "metrics": parse_reit_specific_metrics("")["metrics"],
        "report_text_available": False,
        "rcept_no": "",
        "report_name": "",
        "evidence_snippets": [],
        "source": "OpenDART report parser",
        "confidence": "Not available",
        "warnings": [],
    }
    if not api_key_text:
        result["warnings"].append("DART_API_KEY missing: OpenDART report parser skipped.")
        return result

    disclosures = collect_opendart_disclosures(selected_reit, api_key_text)
    if disclosures.empty:
        result["warnings"].append("최근 공시 목록이 없어 보고서 원문 parser를 실행하지 않았습니다.")
        return result

    data = disclosures.copy()
    if "report_type" in data.columns:
        periodic = data[data["report_type"].isin(PERIODIC_REPORT_TYPES)]
        if not periodic.empty:
            data = periodic
    latest = data.iloc[0]
    rcept_no = str(latest.get("rcept_no", "")).strip()
    report_name = str(latest.get("report_nm", "")).strip()
    if not rcept_no:
        result["warnings"].append("공시 접수번호가 없어 보고서 원문 parser를 실행하지 않았습니다.")
        return result

    payload = _cached_get_bytes(
        f"{DART_BASE_URL}/document.xml",
        {"crtfc_key": api_key_text, "rcept_no": rcept_no},
        "opendart",
        f"report:{rcept_no}",
        force_refresh=force_refresh,
    )
    text = _decode_report_payload(payload)
    if not text:
        result["warnings"].append("OpenDART 보고서 원문을 내려받거나 해석하지 못했습니다.")
        return result

    parsed = parse_reit_specific_metrics(text)
    result.update(
        {
            "metrics": parsed["metrics"],
            "report_text_available": True,
            "rcept_no": rcept_no,
            "report_name": report_name,
            "evidence_snippets": parsed["evidence_snippets"],
            "confidence": "Low" if parsed["evidence_snippets"] else "Not available",
            "parser_note": parsed["parser_note"],
        }
    )
    return result


def collect_market_data(selected_reit: Any, force_refresh: bool = False) -> dict[str, Any]:
    ticker = _selected_value(selected_reit, "ticker")
    result: dict[str, Any] = {
        "metrics": {
            "latest_price": _missing_metric("latest_price", "KRW", "KRX/public market data에서 주가를 확보하지 못했습니다."),
            "market_cap": _missing_metric("market_cap", "KRW", "KRX/public market data에서 시가총액을 확보하지 못했습니다."),
            "fifty_two_week_high": _missing_metric("fifty_two_week_high", "KRW"),
            "fifty_two_week_low": _missing_metric("fifty_two_week_low", "KRW"),
            "recent_return": _missing_metric("recent_return", "%"),
        },
        "source": "KRX/public market data",
        "trading_date": "",
        "warnings": [],
    }
    if not ticker:
        result["warnings"].append("ticker가 없어 market data 수집을 수행하지 않았습니다.")
        return result

    krx_ticker = ticker.split(".")[0]
    end = pd.Timestamp.today().normalize()
    start = end - pd.Timedelta(days=370)

    try:
        from pykrx import stock  # type: ignore

        ohlcv = stock.get_market_ohlcv_by_date(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), krx_ticker)
        market_cap = stock.get_market_cap_by_date(start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), krx_ticker)
        if not ohlcv.empty:
            latest = ohlcv.dropna().iloc[-1]
            close_column = "종가" if "종가" in ohlcv.columns else ohlcv.columns[0]
            latest_price = float(latest[close_column])
            prices = pd.to_numeric(ohlcv[close_column], errors="coerce").dropna()
            result["trading_date"] = str(ohlcv.index[-1].date())
            result["metrics"]["latest_price"] = build_metric_with_source(
                "latest_price", latest_price, "KRW", "pykrx / KRX market data", "Medium", as_of=result["trading_date"]
            )
            if not prices.empty:
                result["metrics"]["fifty_two_week_high"] = build_metric_with_source(
                    "fifty_two_week_high", float(prices.max()), "KRW", "pykrx / KRX market data", "Medium", as_of=result["trading_date"]
                )
                result["metrics"]["fifty_two_week_low"] = build_metric_with_source(
                    "fifty_two_week_low", float(prices.min()), "KRW", "pykrx / KRX market data", "Medium", as_of=result["trading_date"]
                )
                result["metrics"]["recent_return"] = build_metric_with_source(
                    "recent_return",
                    (float(prices.iloc[-1]) / float(prices.iloc[0]) - 1) * 100,
                    "%",
                    "pykrx / KRX market data",
                    "Medium",
                    "최근 약 1년 가격 변화율입니다.",
                    as_of=result["trading_date"],
                )
        if not market_cap.empty:
            cap_column = "시가총액" if "시가총액" in market_cap.columns else market_cap.columns[0]
            result["metrics"]["market_cap"] = build_metric_with_source(
                "market_cap",
                float(market_cap.iloc[-1][cap_column]),
                "KRW",
                "pykrx / KRX market data",
                "Medium",
                as_of=str(market_cap.index[-1].date()),
            )
        return result
    except Exception as exc:
        result["warnings"].append(f"pykrx market data 수집 실패 또는 pykrx 미설치: {exc.__class__.__name__}")

    stooq_symbol = f"{krx_ticker}.kr"
    url = f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d"
    try:
        payload = _cached_get_bytes(url, {}, "krx", f"stooq:{stooq_symbol}", force_refresh=force_refresh)
        if not payload:
            raise ValueError("Stooq response was empty")
        frame = pd.read_csv(StringIO(payload.decode("utf-8", errors="ignore")))
        if frame.empty or "Close" not in frame.columns:
            raise ValueError("Stooq response was empty")
        frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
        frame["Close"] = pd.to_numeric(frame["Close"], errors="coerce")
        frame = frame.dropna(subset=["Date", "Close"]).sort_values("Date")
        if frame.empty:
            raise ValueError("Stooq response did not include usable prices")
        latest = frame.iloc[-1]
        result["trading_date"] = str(latest["Date"].date())
        prices = frame["Close"]
        result["metrics"]["latest_price"] = build_metric_with_source(
            "latest_price", float(latest["Close"]), "KRW", "Stooq public market data", "Low", as_of=result["trading_date"]
        )
        result["metrics"]["fifty_two_week_high"] = build_metric_with_source(
            "fifty_two_week_high", float(prices.max()), "KRW", "Stooq public market data", "Low", as_of=result["trading_date"]
        )
        result["metrics"]["fifty_two_week_low"] = build_metric_with_source(
            "fifty_two_week_low", float(prices.min()), "KRW", "Stooq public market data", "Low", as_of=result["trading_date"]
        )
        result["metrics"]["recent_return"] = build_metric_with_source(
            "recent_return",
            (float(prices.iloc[-1]) / float(prices.iloc[0]) - 1) * 100,
            "%",
            "Stooq public market data",
            "Low",
            "KRX 공식 API가 아닌 public market data fallback입니다.",
            as_of=result["trading_date"],
        )
    except Exception as exc:
        result["warnings"].append(f"public market data fallback 수집 실패: {exc.__class__.__name__}")
    return result


def collect_reit_association_data(selected_reit: Any) -> dict[str, Any]:
    try:
        from modules.reit_external_scrapers import collect_reit_association_data as _collect

        return _collect(selected_reit, allow_network=False)
    except Exception as exc:
        return {
            "source": "KAREIT / 리츠협회 public pages",
            "retrieval_timestamp": _now_iso(),
            "warnings": [f"외부 리츠 자료 수집 실패: {exc.__class__.__name__}"],
            "source_urls": [],
        }


def collect_company_ir_data(selected_reit: Any) -> dict[str, Any]:
    try:
        from modules.reit_external_scrapers import collect_company_ir_data as _collect

        return _collect(selected_reit, allow_network=False)
    except Exception as exc:
        return {
            "source": "Company IR public page",
            "retrieval_timestamp": _now_iso(),
            "warnings": [f"회사 IR 자료 수집 실패: {exc.__class__.__name__}"],
            "source_urls": [],
        }


def _metric_value(metric: dict[str, Any] | None) -> Any:
    if not isinstance(metric, dict):
        return None
    return metric.get("value")


def _resolve_dart_key_for_bundle(api_keys: dict[str, str] | None) -> tuple[str, bool]:
    if api_keys is None:
        key = get_dart_api_key() or ""
        key = str(key).strip()
        return key, bool(key)

    for name in ("dart", "DART_API_KEY", "OPENDART_API_KEY", "OPEN_DART_API_KEY"):
        if name in api_keys:
            key = str(api_keys.get(name) or "").strip()
            return key, bool(key)
    return "", False


def build_real_data_bundle(selected_reit: Any, api_keys: dict[str, str] | None = None, force_refresh: bool = False) -> dict[str, Any]:
    reit_name = _selected_value(selected_reit, "real_reit_name", "선택 REIT")
    ticker = _selected_value(selected_reit, "ticker")
    dart_key, has_valid_dart_key = _resolve_dart_key_for_bundle(api_keys)

    financials = collect_opendart_financials(selected_reit, api_key=dart_key, force_refresh=force_refresh)
    disclosures = collect_opendart_disclosures(selected_reit, api_key=dart_key if has_valid_dart_key else "")
    report = download_and_parse_opendart_report(selected_reit, api_key=dart_key if has_valid_dart_key else "", force_refresh=force_refresh)
    market = collect_market_data(selected_reit, force_refresh=force_refresh)
    macro = build_macro_rate_environment()
    association = collect_reit_association_data(selected_reit)
    company_ir = collect_company_ir_data(selected_reit)

    reit_specific = report["metrics"].copy()
    missing_metrics: list[str] = []
    for key in REQUIRED_METRICS:
        metric = None
        if key in financials["metrics"]:
            metric = financials["metrics"][key]
        elif key in market["metrics"]:
            metric = market["metrics"][key]
        elif key in macro:
            metric = macro[key]
        elif key in reit_specific:
            metric = reit_specific[key]
        if _metric_value(metric) is None:
            missing_metrics.append(key)

    data_sources = [
        {
            "source": "OpenDART financial statement API",
            "status": financials["confidence"],
            "as_of": financials["as_of"],
            "warnings": financials["warnings"],
        },
        {
            "source": "OpenDART disclosure list",
            "status": "High" if not disclosures.empty and not disclosures.attrs.get("is_fallback", True) else "Not available",
            "as_of": _now_iso(),
            "warnings": [disclosures.attrs.get("status_message", "")],
        },
        {
            "source": "OpenDART report parser",
            "status": report["confidence"],
            "as_of": _now_iso(),
            "warnings": report["warnings"],
        },
        {
            "source": "KRX/public market data",
            "status": "Medium" if _metric_value(market["metrics"].get("latest_price")) is not None else "Not available",
            "as_of": market.get("trading_date", ""),
            "warnings": market["warnings"],
        },
        {
            "source": "ECOS / macro assumption layer",
            "status": macro.get("base_rate", {}).get("confidence", "Not available"),
            "as_of": macro.get("base_rate", {}).get("as_of", ""),
            "warnings": [macro.get("status_message", "")],
        },
        {
            "source": association.get("source", "KAREIT / 리츠협회 public pages"),
            "status": "Low" if association.get("source_urls") else "Not available",
            "as_of": association.get("retrieval_timestamp", ""),
            "warnings": association.get("warnings", []),
        },
        {
            "source": company_ir.get("source", "Company IR public page"),
            "status": "Low" if company_ir.get("source_urls") else "Not available",
            "as_of": company_ir.get("retrieval_timestamp", ""),
            "warnings": company_ir.get("warnings", []),
        },
    ]

    warnings: list[str] = []
    for source in data_sources:
        for warning in source.get("warnings", []):
            if warning:
                warnings.append(str(warning))

    return {
        "selected_reit_name": reit_name,
        "ticker": ticker,
        "collection_timestamp": _now_iso(),
        "financials": financials["metrics"],
        "market_data": market["metrics"],
        "macro_data": macro,
        "reit_specific": reit_specific,
        "disclosures": disclosures.to_dict("records") if isinstance(disclosures, pd.DataFrame) else [],
        "disclosure_frame": disclosures,
        "parsed_tables": {
            "opendart_accounts": financials["raw_accounts"],
            "report_evidence_snippets": report["evidence_snippets"],
            "association_sources": association.get("source_urls", []),
            "company_ir_sources": company_ir.get("source_urls", []),
        },
        "data_sources": data_sources,
        "missing_metrics": missing_metrics,
        "warnings": warnings,
        "force_refresh": force_refresh,
    }
