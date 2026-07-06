from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
VERSION_FILE = BASE_DIR / "VERSION.md"
SAMPLE_MODE = "Demo / Sample Mode"
REAL_API_MODE = "Real API Mode"

INDEXED_PAGE_LABELS = [
    "0. App",
    "1. 고객 Pain Point",
    "2. CFO Executive Dashboard",
    "3. Scenario Engine",
    "4. 자산 및 차입 리스크",
    "5. AI Memo & Investor Q&A",
    "6. 데이터 품질 · AI Readiness",
]


def get_app_version() -> str:
    if not VERSION_FILE.exists():
        return "v12"

    for line in VERSION_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("Current version:"):
            return stripped.split(":", 1)[1].strip()
    return "v12"


APP_VERSION = get_app_version()


def setup_page(page_title: str, subtitle: str | None = None) -> None:
    st.set_page_config(page_title=page_title, page_icon="KR", layout="wide")
    inject_global_css()
    render_sidebar_version()
    render_data_mode_selector()
    render_global_real_reit_selector()
    render_global_real_assumption_inputs()
    render_sidebar_api_status()
    render_sidebar_disclaimer()
    render_sidebar_module_index()
    st.title(page_title)
    if subtitle:
        st.caption(subtitle)


def render_sidebar_version() -> None:
    st.sidebar.markdown("---")
    st.sidebar.caption(f"현재 버전: {APP_VERSION}")


def render_data_mode_selector() -> str:
    mode = st.sidebar.radio(
        "Data Mode",
        [REAL_API_MODE, SAMPLE_MODE],
        index=0,
        key="data_mode",
        help="Real API Mode는 공개 API와 source-tagged metrics 중심, Demo / Sample Mode는 fictional sample data 기반 end-to-end 데모입니다.",
    )
    return str(mode)


def real_reit_selector_options(master: Any | None = None) -> list[str]:
    if master is None:
        try:
            from modules.real_data_loader import load_real_reit_master

            master = load_real_reit_master()
        except Exception:
            return ["선택 REIT"]

    if hasattr(master, "columns") and "real_reit_name" in master.columns:
        names = [str(name).strip() for name in master["real_reit_name"].tolist()]
    else:
        names = [str(item).strip() for item in master]

    return [name for name in names if name] or ["선택 REIT"]


def render_global_real_reit_selector() -> str | None:
    if get_data_mode() != REAL_API_MODE:
        return None

    options = real_reit_selector_options()
    selected = st.sidebar.selectbox(
        "Real REIT 선택",
        options,
        index=0,
        key="selected_real_reit_name",
        help="회사명만 표시합니다. ticker와 corp_code는 내부 식별 정보로만 사용합니다.",
    )
    return str(selected)


def get_sidebar_selected_real_reit_name(default: str | None = None) -> str | None:
    return st.session_state.get("selected_real_reit_name", default)


def render_global_real_assumption_inputs() -> None:
    if get_data_mode() != REAL_API_MODE:
        return

    if st.sidebar.button("Refresh real data", key="refresh_real_data_button", help="OpenDART, ECOS, market/public data cache를 새로고침합니다."):
        st.session_state["force_refresh_real_data"] = True
        try:
            st.cache_data.clear()
        except Exception:
            pass
        st.sidebar.success("Real data cache를 새로고침했습니다.")

    with st.sidebar.expander("Real Mode 수동 보완값", expanded=False):
        st.caption("먼저 자동 수집을 시도하고, 확인되지 않는 항목만 선택적으로 보완합니다. 0은 미입력으로 처리합니다.")
        st.number_input("총자산 (억 원)", min_value=0.0, value=0.0, step=100.0, key="real_total_assets_eok")
        st.number_input("총차입금 (억 원)", min_value=0.0, value=0.0, step=100.0, key="real_total_debt_eok")
        st.number_input("연간 NOI (억 원)", min_value=0.0, value=0.0, step=10.0, key="real_annual_noi_eok")
        st.number_input("연간 배당금 (억 원)", min_value=0.0, value=0.0, step=10.0, key="real_dividend_eok")
        st.number_input("변동금리 차입 비중 (%)", min_value=0.0, max_value=100.0, value=0.0, step=5.0, key="real_floating_debt_pct")
        st.number_input("1~2년 만기도래 차입 비중 (%)", min_value=0.0, max_value=100.0, value=0.0, step=5.0, key="real_near_term_debt_pct")
        st.number_input("평균 조달금리 (%)", min_value=0.0, max_value=20.0, value=0.0, step=0.1, key="real_average_coupon_pct")


def get_real_mode_user_inputs() -> dict[str, float | None]:
    def _eok_to_krw(key: str) -> float | None:
        value = float(st.session_state.get(key, 0.0) or 0.0)
        return value * 100_000_000 if value > 0 else None

    def _pct_or_none(key: str) -> float | None:
        value = float(st.session_state.get(key, 0.0) or 0.0)
        return value if value > 0 else None

    return {
        "total_assets_krw": _eok_to_krw("real_total_assets_eok"),
        "total_debt_krw": _eok_to_krw("real_total_debt_eok"),
        "annual_noi_krw": _eok_to_krw("real_annual_noi_eok"),
        "dividend_krw": _eok_to_krw("real_dividend_eok"),
        "floating_debt_pct": _pct_or_none("real_floating_debt_pct"),
        "near_term_debt_pct": _pct_or_none("real_near_term_debt_pct"),
        "average_coupon_pct": _pct_or_none("real_average_coupon_pct"),
    }


def get_data_mode() -> str:
    return str(st.session_state.get("data_mode", REAL_API_MODE))


def is_real_api_mode() -> bool:
    return get_data_mode() == REAL_API_MODE


def is_sample_mode() -> bool:
    return get_data_mode() == SAMPLE_MODE


def render_sidebar_disclaimer() -> None:
    st.sidebar.markdown("---")
    if is_real_api_mode():
        st.sidebar.caption(
            "Real API Mode는 OpenDART·ECOS 등 공개 API로 조회 가능한 사실 정보와 사용자가 직접 입력한 "
            "가정만을 기반으로 합니다. 본 화면은 실제 기업에 대한 투자 의견, 신용 판단, 부정적 리스크 평가를 "
            "제공하지 않습니다."
        )
    else:
        st.sidebar.caption(
            "Demo / Sample Mode: 회사명, 수치, Risk Score, 공시 신호는 모두 fictional sample data입니다. "
            "실제 기업 재무상태, 공시 내용 또는 투자판단을 나타내지 않습니다."
        )


def render_sidebar_api_status() -> None:
    try:
        from modules.api_clients.config import has_dart_api_key, has_ecos_api_key
    except Exception:
        return

    dart_ready = has_dart_api_key()
    ecos_ready = has_ecos_api_key()
    dart_status = "Key configured" if dart_ready else "Sample fallback"
    ecos_status = "Key configured" if ecos_ready else "Sample fallback"
    fallback_status = "예" if not (dart_ready and ecos_ready) else "API 시도"

    with st.sidebar.expander("External API 상태", expanded=False):
        st.caption(f"OpenDART 연결 상태: {dart_status}")
        st.caption(f"ECOS 연결 상태: {ecos_status}")
        st.caption(f"Sample data fallback 여부: {fallback_status}")
        st.caption("API key는 UI에 표시하지 않습니다.")


def render_sidebar_module_index() -> None:
    st.sidebar.markdown("---")
    with st.sidebar.expander("Dashboard 구성", expanded=False):
        for label in INDEXED_PAGE_LABELS:
            st.caption(label)


def inject_global_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #17202a;
            --muted: #667085;
            --line: #d9e1e8;
            --paper: #ffffff;
            --mist: #f5f7fa;
            --teal: #007c89;
            --navy: #263b5e;
            --amber: #b76e00;
            --coral: #c94f4f;
        }
        .stApp {
            background: linear-gradient(180deg, #f7f9fb 0%, #ffffff 42%);
            color: var(--ink);
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        section[data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--line);
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 8px 20px rgba(23, 32, 42, 0.04);
        }
        div[data-testid="stMetricLabel"] {
            color: var(--muted);
        }
        .consulting-hero {
            border: 1px solid var(--line);
            border-left: 5px solid var(--teal);
            border-radius: 8px;
            background: #ffffff;
            padding: 22px 24px;
            margin: 8px 0 18px 0;
            box-shadow: 0 10px 24px rgba(38, 59, 94, 0.06);
        }
        .eyebrow {
            color: var(--teal);
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .hero-title {
            color: var(--ink);
            font-size: 1.45rem;
            font-weight: 750;
            margin-bottom: 8px;
        }
        .hero-body {
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.5;
        }
        .signal-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--paper);
            padding: 16px;
            min-height: 132px;
            box-shadow: 0 8px 20px rgba(23, 32, 42, 0.04);
        }
        .signal-card strong {
            color: var(--ink);
        }
        .signal-label {
            color: var(--muted);
            font-size: 0.82rem;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 8px;
        }
        .signal-value {
            color: var(--ink);
            font-size: 1.35rem;
            font-weight: 760;
            margin-bottom: 6px;
        }
        .signal-detail {
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.35;
        }
        .tag-high, .tag-medium, .tag-low {
            display: inline-block;
            border-radius: 6px;
            padding: 2px 8px;
            color: #ffffff;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .tag-high { background: var(--coral); }
        .tag-medium { background: var(--amber); }
        .tag-low { background: var(--teal); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(eyebrow: str, title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="consulting-hero">
            <div class="eyebrow">{eyebrow}</div>
            <div class="hero-title">{title}</div>
            <div class="hero-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def signal_card(label: str, value: str, detail: str) -> None:
    st.markdown(
        f"""
        <div class="signal-card">
            <div class="signal-label">{label}</div>
            <div class="signal-value">{value}</div>
            <div class="signal-detail">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def risk_tag(risk_tier: str) -> str:
    normalized = risk_tier.lower()
    css = "tag-low"
    if normalized == "high":
        css = "tag-high"
    elif normalized == "medium":
        css = "tag-medium"
    return f'<span class="{css}">{risk_tier}</span>'


def _badge(text: str, background: str, color: str = "#ffffff") -> str:
    return (
        f"<span style='display:inline-block;background:{background};color:{color};"
        "border-radius:6px;padding:2px 8px;font-size:0.76rem;font-weight:700;"
        "margin-right:4px;white-space:nowrap;'>"
        f"{text}</span>"
    )


def risk_badge(level: str | None) -> str:
    label = str(level or "Not Available")
    colors = {
        "Low": "#007c89",
        "Moderate": "#667085",
        "Watch": "#b76e00",
        "Elevated": "#b76e00",
        "High": "#c94f4f",
        "Not Available": "#98a2b3",
    }
    return _badge(label, colors.get(label, "#98a2b3"))


def source_badge(source_type: str | None) -> str:
    label = str(source_type or "Not Available")
    colors = {
        "OpenDART API": "#263b5e",
        "OpenDART Parsed": "#4c6f91",
        "ECOS API": "#007c89",
        "KRX / Market Data": "#5a5f73",
        "KAREIT / REIT Association": "#667085",
        "Company IR": "#667085",
        "Local Cache": "#7a6f5a",
        "Inferred Proxy": "#b76e00",
        "Fallback Assumption": "#8a6f3d",
        "Not Available": "#98a2b3",
    }
    return _badge(label, colors.get(label, "#98a2b3"))


def confidence_badge(confidence: str | None) -> str:
    label = str(confidence or "Not Available")
    colors = {
        "High": "#007c89",
        "Medium": "#4c6f91",
        "Low": "#b76e00",
        "Not Available": "#98a2b3",
        "Not available": "#98a2b3",
    }
    return _badge(label, colors.get(label, "#98a2b3"))


def metric_card(label: str, value: str, detail: str = "", badges: str = "") -> None:
    st.markdown(
        f"""
        <div class="signal-card">
            <div class="signal-label">{label}</div>
            <div class="signal-value">{value}</div>
            <div class="signal-detail">{badges}</div>
            <div class="signal-detail">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def cfo_alert_card(priority: int, severity: str, title: str, why: str, action: str, source: str, confidence: str) -> None:
    st.markdown(
        f"""
        <div class="consulting-hero">
            <div class="eyebrow">Alert #{priority} · {risk_badge(severity)} {confidence_badge(confidence)}</div>
            <div class="hero-title">{title}</div>
            <div class="hero-body">
                <strong>왜 중요한가</strong><br>{why}<br><br>
                <strong>권고 액션</strong><br>{action}<br><br>
                {source_badge(source)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _compact_number(value: float, digits: int = 1) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{round(value):,.0f}"
    return f"{value:,.{digits}f}".rstrip("0").rstrip(".")


def format_krw(value: float | int | None, unit: str = "KRW", compact: bool = True) -> str:
    if value is None:
        return "데이터 없음"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return "데이터 없음"

    if unit.lower() in {"krw_bn", "krw bn", "bn"}:
        amount *= 1_000_000_000
    elif unit.lower() in {"krw_m", "krw m", "m"}:
        amount *= 1_000_000

    if amount != amount:
        return "데이터 없음"

    sign = "-" if amount < 0 else ""
    amount = abs(amount)

    if amount >= 1_000_000_000_000:
        return f"{sign}{_compact_number(amount / 1_000_000_000_000, 1)}조 원"
    if amount >= 100_000_000:
        return f"{sign}{_compact_number(amount / 100_000_000, 1)}억 원"
    return f"{sign}{_compact_number(amount / 10_000, 0)}만 원"


def format_krw_bn(value: float | int | None, digits: int = 0) -> str:
    return format_krw(value, unit="KRW_BN")


def format_pct(value: float, digits: int = 1) -> str:
    return f"{value:,.{digits}f}%"
