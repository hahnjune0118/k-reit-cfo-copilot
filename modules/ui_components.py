from __future__ import annotations

from pathlib import Path

import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
VERSION_FILE = BASE_DIR / "VERSION.md"


def get_app_version() -> str:
    if not VERSION_FILE.exists():
        return "v02"

    for line in VERSION_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("Current version:"):
            return stripped.split(":", 1)[1].strip()
    return "v02"


APP_VERSION = get_app_version()


def setup_page(page_title: str, subtitle: str | None = None) -> None:
    st.set_page_config(page_title=page_title, page_icon="KR", layout="wide")
    inject_global_css()
    render_sidebar_version()
    st.title(page_title)
    if subtitle:
        st.caption(subtitle)


def render_sidebar_version() -> None:
    st.sidebar.markdown("---")
    st.sidebar.caption(f"현재 버전: {APP_VERSION}")


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
