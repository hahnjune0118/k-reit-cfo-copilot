from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import re
from typing import Any

import requests


BASE_DIR = Path(__file__).resolve().parents[1]
CACHE_DIR = BASE_DIR / "data" / "cache" / "reit_external"
USER_AGENT = "K-REIT-CFO-Copilot/12 (+portfolio prototype; contact via app owner)"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _selected_value(selected_reit: Any, key: str, default: str = "") -> str:
    try:
        value = selected_reit.get(key, default)
    except AttributeError:
        return default
    if value is None:
        return default
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _cache_file(url: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{sha256(url.encode('utf-8')).hexdigest()}.html"


def safe_fetch_url(url: str, timeout: int = 5) -> dict[str, Any]:
    """Fetch a public page with a short timeout and local cache fallback."""

    cache_path = _cache_file(url)
    if cache_path.exists():
        try:
            cached = cache_path.read_text(encoding="utf-8", errors="ignore")
            if cached.strip():
                return {
                    "url": url,
                    "success": True,
                    "from_cache": True,
                    "status_code": None,
                    "retrieval_timestamp": _now_iso(),
                    "text": cached,
                    "warning": "",
                }
        except OSError:
            pass

    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        return {
            "url": url,
            "success": False,
            "from_cache": False,
            "status_code": getattr(getattr(exc, "response", None), "status_code", None),
            "retrieval_timestamp": _now_iso(),
            "text": "",
            "warning": f"외부 REIT 자료 수집 실패: {exc.__class__.__name__}",
        }

    response.encoding = response.encoding or "utf-8"
    text = response.text
    try:
        cache_path.write_text(text, encoding="utf-8")
    except OSError:
        pass
    return {
        "url": url,
        "success": True,
        "from_cache": False,
        "status_code": response.status_code,
        "retrieval_timestamp": _now_iso(),
        "text": text,
        "warning": "",
    }


def _extract_links(html: str, base_url: str, keywords: list[str]) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for match in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, flags=re.I | re.S):
        href = re.sub(r"\s+", " ", match.group(1)).strip()
        label = re.sub(r"<[^>]+>", " ", match.group(2))
        label = re.sub(r"\s+", " ", label).strip()
        combined = f"{label} {href}".casefold()
        if not any(keyword.casefold() in combined for keyword in keywords):
            continue
        if href.startswith("/"):
            href = base_url.rstrip("/") + href
        links.append({"title": label or href, "url": href})
    return links[:10]


def collect_reit_association_data(selected_reit: Any, allow_network: bool = False) -> dict[str, Any]:
    """Collect KAREIT / association-style public links when network collection is enabled.

    The function intentionally does not fabricate REIT metrics. If a stable source URL is not configured
    or the request fails, it returns warnings and empty result lists.
    """

    reit_name = _selected_value(selected_reit, "real_reit_name", "선택 REIT")
    result: dict[str, Any] = {
        "source": "KAREIT / 리츠협회 public pages",
        "retrieval_timestamp": _now_iso(),
        "selected_reit_name": reit_name,
        "investment_report_links": [],
        "business_report_links": [],
        "asset_information": [],
        "dividend_information": [],
        "debt_information": [],
        "source_urls": [],
        "warnings": [],
    }

    if not allow_network:
        result["warnings"].append("외부 리츠 자료 수집은 기본 실행에서 생략되었으며, Refresh real data 실행 시 재시도할 수 있습니다.")
        return result

    candidate_urls = [
        "https://www.kareit.or.kr/",
    ]
    for url in candidate_urls:
        fetched = safe_fetch_url(url)
        result["source_urls"].append(
            {
                "url": url,
                "success": fetched["success"],
                "from_cache": fetched["from_cache"],
                "retrieval_timestamp": fetched["retrieval_timestamp"],
            }
        )
        if not fetched["success"]:
            result["warnings"].append(fetched["warning"])
            continue

        links = _extract_links(
            fetched["text"],
            url,
            ["리츠", "투자보고서", "사업보고서", "배당", "자산", "REIT", reit_name],
        )
        result["investment_report_links"].extend(
            link for link in links if any(keyword in link["title"] for keyword in ["투자", "운용", "IR"])
        )
        result["business_report_links"].extend(
            link for link in links if any(keyword in link["title"] for keyword in ["사업", "보고서", "공시"])
        )
        result["asset_information"].extend(link for link in links if "자산" in link["title"])
        result["dividend_information"].extend(link for link in links if "배당" in link["title"])
        result["debt_information"].extend(link for link in links if any(keyword in link["title"] for keyword in ["차입", "금리", "만기"]))

    return result


def collect_company_ir_data(selected_reit: Any, allow_network: bool = False) -> dict[str, Any]:
    reit_name = _selected_value(selected_reit, "real_reit_name", "선택 REIT")
    ir_url = _selected_value(selected_reit, "ir_url", "")
    result: dict[str, Any] = {
        "source": "Company IR public page",
        "retrieval_timestamp": _now_iso(),
        "selected_reit_name": reit_name,
        "portfolio_links": [],
        "presentation_links": [],
        "dividend_links": [],
        "financing_links": [],
        "source_urls": [],
        "warnings": [],
    }

    if not ir_url:
        result["warnings"].append("회사 IR URL이 Real REIT master에 없어 자동 IR scraping을 수행하지 않았습니다.")
        return result
    if not allow_network:
        result["warnings"].append("회사 IR scraping은 기본 실행에서 생략되었으며, Refresh real data 실행 시 재시도할 수 있습니다.")
        return result

    fetched = safe_fetch_url(ir_url)
    result["source_urls"].append(
        {
            "url": ir_url,
            "success": fetched["success"],
            "from_cache": fetched["from_cache"],
            "retrieval_timestamp": fetched["retrieval_timestamp"],
        }
    )
    if not fetched["success"]:
        result["warnings"].append(fetched["warning"])
        return result

    links = _extract_links(
        fetched["text"],
        ir_url,
        ["IR", "Investor", "Presentation", "배당", "자산", "차입", "금리", "만기", "포트폴리오"],
    )
    result["portfolio_links"] = [link for link in links if any(k in link["title"] for k in ["자산", "포트폴리오"])]
    result["presentation_links"] = [link for link in links if any(k.casefold() in link["title"].casefold() for k in ["IR", "Presentation", "자료"])]
    result["dividend_links"] = [link for link in links if "배당" in link["title"]]
    result["financing_links"] = [link for link in links if any(k in link["title"] for k in ["차입", "금리", "만기"])]
    return result
