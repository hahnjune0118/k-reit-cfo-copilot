from __future__ import annotations

from pathlib import Path

import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
VERSION_FILE = BASE_DIR / "VERSION.md"
SAMPLE_MODE = "Sample Mode"
REAL_API_MODE = "Real API Mode"


def get_app_version() -> str:
    if not VERSION_FILE.exists():
        return "v10"

    for line in VERSION_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("Current version:"):
            return stripped.split(":", 1)[1].strip()
    return "v10"


APP_VERSION = get_app_version()


def setup_page(page_title: str, subtitle: str | None = None) -> None:
    st.set_page_config(page_title=page_title, page_icon="KR", layout="wide")
    inject_global_css()
    render_sidebar_version()
    render_data_mode_selector()
    render_sidebar_api_status()
    render_sidebar_disclaimer()
    st.title(page_title)
    if subtitle:
        st.caption(subtitle)


def render_sidebar_version() -> None:
    st.sidebar.markdown("---")
    st.sidebar.caption(f"현재 버전: {APP_VERSION}")


def render_data_mode_selector() -> str:
    mode = st.sidebar.radio(
        "Data Mode",
        [SAMPLE_MODE, REAL_API_MODE],
        index=0,
        key="data_mode",
        help="Sample Mode는 fictional data 기반 end-to-end demo, Real API Mode는 공개 API 기반 factual data 조회입니다.",
    )
    return str(mode)


def get_data_mode() -> str:
    return str(st.session_state.get("data_mode", SAMPLE_MODE))


def is_real_api_mode() -> bool:
    return get_data_mode() == REAL_API_MODE


def is_sample_mode() -> bool:
    return get_data_mode() == SAMPLE_MODE


def render_sidebar_disclaimer() -> None:
    st.sidebar.markdown("---")
    if is_real_api_mode():
        st.sidebar.caption(
            "Real API Mode: OpenDART/ECOS 공개 API factual data와 사용자 입력 가정만 표시합니다. "
            "검증되지 않은 부정적 Risk Score, 투자 의견, 신용 판단은 제공하지 않습니다."
        )
    else:
        st.sidebar.caption(
            "Sample Mode: 회사명, 수치, Risk Score, 공시 신호는 모두 fictional sample data입니다. "
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

    st.sidebar.markdown("### External API")
    st.sidebar.caption(f"OpenDART 연결 상태: {dart_status}")
    st.sidebar.caption(f"ECOS 연결 상태: {ecos_status}")
    st.sidebar.caption(f"Sample data fallback 여부: {fallback_status}")
    st.sidebar.caption("API key는 UI에 표시하지 않습니다.")


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


def format_krw_bn(value: float, digits: int = 0) -> str:
    return f"KRW {value:,.{digits}f}bn"


def format_pct(value: float, digits: int = 1) -> str:
    return f"{value:,.{digits}f}%"
