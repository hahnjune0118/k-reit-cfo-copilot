
"""
Real API Mode components for K-REIT CFO Copilot v10.

This module intentionally keeps Real API Mode conservative:
- factual OpenDART / ECOS data
- user-input hypothetical scenario
- no investment opinion
- no credit judgment
- no fabricated risk flags for real listed REITs
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def get_data_availability_matrix() -> pd.DataFrame:
    """Return v10 Data Availability Matrix."""
    rows = [
        {
            "Metric": "??? / ticker",
            "Source": "Real REIT master / KRX / OpenDART",
            "API availability": "?? ??",
            "Automation level": "High",
            "Manual validation required?": "No",
            "Notes": "?? REIT master data? ?? ??",
        },
        {
            "Metric": "OpenDART ?? ??",
            "Source": "OpenDART",
            "API availability": "??",
            "Automation level": "High",
            "Manual validation required?": "No",
            "Notes": "???, ???, ???? ?? ??",
        },
        {
            "Metric": "?? ????",
            "Source": "OpenDART",
            "API availability": "??",
            "Automation level": "High",
            "Manual validation required?": "Low",
            "Notes": "?????, ?????, ????? ?? ??",
        },
        {
            "Metric": "???? / ????",
            "Source": "ECOS",
            "API availability": "??",
            "Automation level": "High",
            "Manual validation required?": "No",
            "Notes": "Scenario Engine? ?? ???? ?? ??",
        },
        {
            "Metric": "?? / ????",
            "Source": "KRX / external market data",
            "API availability": "?? ??",
            "Automation level": "Medium",
            "Manual validation required?": "Low",
            "Notes": "v10??? roadmap ?? ??? ?? ???? ??",
        },
        {
            "Metric": "FFO / AFFO",
            "Source": "????? / IR ?? / ????",
            "API availability": "???",
            "Automation level": "Low",
            "Manual validation required?": "Yes",
            "Notes": "REIT? ??? ???? ?? ??",
        },
        {
            "Metric": "WALE",
            "Source": "????? ?? / IR ?? / ????",
            "API availability": "???",
            "Automation level": "Low",
            "Manual validation required?": "Yes",
            "Notes": "??? ??? ?? ??? ?? ??",
        },
        {
            "Metric": "??? ???",
            "Source": "????? ?? / ?? ??? ??",
            "API availability": "???",
            "Automation level": "Low",
            "Manual validation required?": "Yes",
            "Notes": "?? ??? ? ?? ?? ?? ??",
        },
        {
            "Metric": "??? NOI",
            "Source": "????? / ????? / ????",
            "API availability": "???",
            "Automation level": "Low",
            "Manual validation required?": "Yes",
            "Notes": "??? ????? ?? ?? ??",
        },
        {
            "Metric": "?? ?? ??",
            "Source": "????? ?? / ?? ?? ??",
            "API availability": "?? ??",
            "Automation level": "Medium",
            "Manual validation required?": "Yes",
            "Notes": "?? ?? ?? ? ?? ?? ?? ??",
        },
        {
            "Metric": "????",
            "Source": "?? ?? / ?? ????",
            "API availability": "??",
            "Automation level": "Low",
            "Manual validation required?": "Yes",
            "Notes": "?? ??, ??, ???, ??? ? ?? ?? ??",
        },
        {
            "Metric": "Investor Q&A",
            "Source": "?? / IR / ??? ?? / ?? LLM",
            "API availability": "?? ??",
            "Automation level": "Medium",
            "Manual validation required?": "Yes",
            "Notes": "?? v10? rule-based?? ?? LLM API ???",
        },
    ]
    return pd.DataFrame(rows)


def data_availability_matrix() -> pd.DataFrame:
    """Backward-compatible alias."""
    return get_data_availability_matrix()


def render_data_availability_matrix(
    matrix: pd.DataFrame | None = None,
    title: str = "Data Availability Matrix",
    **kwargs: Any,
) -> pd.DataFrame:
    """Render v10 Data Availability Matrix."""
    if matrix is None:
        matrix = get_data_availability_matrix()

    st.markdown(f"### {title}")
    st.caption(
        "?? API? ??? ??? ???, ??? ??? ??? ???, "
        "?? ???? ?? manual validation? ??? ???? ?????."
    )
    st.dataframe(matrix, use_container_width=True)
    st.info(
        """
        ? Matrix? Real API Mode? ?? ?????.

        OpenDART?ECOS? ?? ??? factual data?,
        REIT? ????? ?? ?? ?? ????? ??? ??? ?????.
        """
    )
    return matrix


def render_real_mode_cfo_interpretation(
    selected_reit=None,
    disclosure_data=None,
    market_rate_data=None,
    manual_scenario=None,
    disclosures=None,
    rates=None,
    scenario=None,
    **kwargs: Any,
) -> None:
    """Render conservative CFO interpretation box for Real API Mode."""
    if disclosures is not None and disclosure_data is None:
        disclosure_data = disclosures

    if rates is not None and market_rate_data is None:
        market_rate_data = rates

    if scenario is not None and manual_scenario is None:
        manual_scenario = scenario

    st.markdown("### CFO ?? ??")

    st.info(
        """
        Real API Mode? OpenDART?ECOS ? ?? API? ?? ??? ?? ???
        ???? ?? ??? ???? ???? ???.

        ? ??? ?? ??? ?? ?? ??, ?? ??, ??? ??? ??? ???? ????.
        """
    )

    if selected_reit is not None:
        try:
            reit_name = (
                selected_reit.get("real_reit_name")
                or selected_reit.get("reit_name")
                or selected_reit.get("name")
                or "?? REIT"
            )
        except AttributeError:
            reit_name = str(selected_reit)

        st.markdown(f"**?? REIT:** {reit_name}")

    st.markdown(
        """
        #### ?? ??

        - OpenDART ?? ?? ?? ??? ?? ??? ?? ???? ???? ?? factual data???.
        - ECOS ?? ?? ???? Scenario Engine? ???? ???? ??? ? ????.
        - ??? ??? ?? ?????? ???? ?? ????, ?? API??? ??? ??? ????.
        - ??? FFO, AFFO, WALE, ??? ???, ??? NOI, ?? ?? ??? ????? ?? ?? ?? ?? ?? ?? ??? ?????.
        """
    )

    if manual_scenario is not None:
        st.warning(
            """
            ?? ???? manual scenario ??? ???? ??? ??? ?? ?? ????????.

            ?? ?? ??, ?? ??, ?? ??, ???? ?? ?? ???? ????? ? ???.
            """
        )


def render_real_mode_disclaimer(**kwargs: Any) -> None:
    st.warning(
        """
        Real API Mode? OpenDART?ECOS ? ?? API? ?? ??? ?? ???
        ???? ?? ??? ???? ???? ???.

        ? ??? ?? ??? ?? ?? ??, ?? ??, ??? ??? ??? ???? ????.
        """
    )


def render_opendart_disclosure_monitor(disclosures=None, disclosure_data=None, selected_reit=None, **kwargs: Any):
    """Render OpenDART disclosure monitor with graceful fallback."""
    data = disclosures if disclosures is not None else disclosure_data

    st.markdown("### OpenDART ?? ???")

    if selected_reit is not None:
        try:
            name = selected_reit.get("real_reit_name") or selected_reit.get("reit_name") or selected_reit.get("name")
            if name:
                st.caption(f"?? REIT: {name}")
        except AttributeError:
            st.caption(f"?? REIT: {selected_reit}")

    if data is None:
        st.info("OpenDART ?? ???? ??? API fallback ?????.")
        return None

    if isinstance(data, pd.DataFrame):
        st.dataframe(data, use_container_width=True)
        return data

    try:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        return df
    except Exception:
        st.write(data)
        return data


def render_ecos_market_rate_panel(rates=None, market_rate_data=None, **kwargs: Any):
    """Render ECOS market rate panel with graceful fallback."""
    data = rates if rates is not None else market_rate_data

    st.markdown("### ECOS ?? ???")

    if data is None:
        st.info("ECOS ?? ???? ??? API fallback ?????.")
        return None

    if isinstance(data, pd.DataFrame):
        st.dataframe(data, use_container_width=True)
        return data

    if isinstance(data, dict):
        cols = st.columns(min(3, max(1, len(data))))
        for idx, (key, value) in enumerate(data.items()):
            cols[idx % len(cols)].metric(str(key), value)
        return data

    st.write(data)
    return data


def render_real_mode_manual_scenario_bridge(**kwargs: Any):
    """Render a conservative placeholder for user-input based real mode scenario."""
    st.markdown("### Real Mode ??? ?? ?? ?? ?????")
    st.caption(
        "? ??? ??? ???? ???? ? ?? ???????, "
        "?? API??? ??? ??? ????."
    )
    st.info("?? ????? ?? Scenario Engine ?? ??? ?? ??? ??? ?? ?????.")
    return None


def render_real_mode_data_quality_status(**kwargs: Any):
    """Render external data quality status for Real API Mode."""
    st.markdown("### Real API Mode ??? ?? ??")
    st.info(
        """
        OpenDART?ECOS ?? ??, fallback ??, manual validation ?? ??? ?????.
        FFO, AFFO, WALE, ??? ???, ??? NOI, ?? ?? ??? ?? ??? ?????.
        """
    )
    return None


def render_real_mode_dashboard_summary(**kwargs: Any):
    """Render simple real mode dashboard summary."""
    st.markdown("### Real API Mode Dashboard Summary")
    st.info("?? ?? REIT? ???? factual public data? ??? ?? ?? ?????? ?????.")
    return None


def _fallback_renderer(*args: Any, **kwargs: Any):
    """Fallback renderer for legacy imports during v10 stabilization."""
    st.info(
        """
        Real API Mode ?? ???????.

        ?? v10 ??? ????? ?? API ?? factual data?
        ??? ?? ?? ?? ?????? ?????.
        """
    )
    return None


def __getattr__(name: str):
    """
    Compatibility fallback.

    Allows legacy page imports such as render_xxx from this module
    without crashing the Streamlit app during v10 stabilization.
    """
    if name.startswith("render_"):
        return _fallback_renderer
    raise AttributeError(f"module 'modules.real_mode_components' has no attribute {name!r}")


__all__ = [
    "get_data_availability_matrix",
    "data_availability_matrix",
    "render_data_availability_matrix",
    "render_real_mode_cfo_interpretation",
    "render_real_mode_disclaimer",
    "render_opendart_disclosure_monitor",
    "render_ecos_market_rate_panel",
    "render_real_mode_manual_scenario_bridge",
    "render_real_mode_data_quality_status",
    "render_real_mode_dashboard_summary",
]

# --- ASCII-safe override for Korean Data Availability Matrix ---

def get_data_availability_matrix():
    import pandas as pd

    rows = [
        {
            "Metric": "\ud68c\uc0ac\uba85 / ticker",
            "Source": "Real REIT master / KRX / OpenDART",
            "API availability": "\ubd80\ubd84 \uac00\ub2a5",
            "Automation level": "High",
            "Manual validation required?": "No",
            "Notes": "\uc0c1\uc7a5 REIT master data\ub85c \uad00\ub9ac \uac00\ub2a5",
        },
        {
            "Metric": "OpenDART \uacf5\uc2dc \ubaa9\ub85d",
            "Source": "OpenDART",
            "API availability": "\uac00\ub2a5",
            "Automation level": "High",
            "Manual validation required?": "No",
            "Notes": "\uacf5\uc2dc\uba85, \uc811\uc218\uc77c, \uc811\uc218\ubc88\ud638 \uc870\ud68c \uac00\ub2a5",
        },
        {
            "Metric": "\ucd5c\uadfc \uc815\uae30\uacf5\uc2dc",
            "Source": "OpenDART",
            "API availability": "\uac00\ub2a5",
            "Automation level": "High",
            "Manual validation required?": "Low",
            "Notes": "\uc0ac\uc5c5\ubcf4\uace0\uc11c, \ubc18\uae30\ubcf4\uace0\uc11c, \ubd84\uae30\ubcf4\uace0\uc11c \uc2dd\ubcc4 \uac00\ub2a5",
        },
        {
            "Metric": "\uae30\uc900\uae08\ub9ac / \uc2dc\uc7a5\uae08\ub9ac",
            "Source": "ECOS",
            "API availability": "\uac00\ub2a5",
            "Automation level": "High",
            "Manual validation required?": "No",
            "Notes": "Scenario Engine\uc758 \uae08\ub9ac \uac00\uc815\uc73c\ub85c \ud65c\uc6a9 \uac00\ub2a5",
        },
        {
            "Metric": "\uc8fc\uac00 / \uc2dc\uac00\ucd1d\uc561",
            "Source": "KRX / external market data",
            "API availability": "\ubd80\ubd84 \uac00\ub2a5",
            "Automation level": "Medium",
            "Manual validation required?": "Low",
            "Notes": "v10\uc5d0\uc11c\ub294 roadmap \ub610\ub294 \uc81c\ud55c\uc801 \uc5f0\ub3d9 \ub300\uc0c1\uc73c\ub85c \ud45c\uc2dc",
        },
        {
            "Metric": "FFO / AFFO",
            "Source": "\uc0ac\uc5c5\ubcf4\uace0\uc11c / IR \uc790\ub8cc / \ub0b4\ubd80\uc790\ub8cc",
            "API availability": "\uc81c\ud55c\uc801",
            "Automation level": "Low",
            "Manual validation required?": "Yes",
            "Notes": "REIT\ubcc4 \uc0b0\uc2dd\uacfc \uc870\uc815\ud56d\ubaa9 \ud655\uc778 \ud544\uc694",
        },
        {
            "Metric": "WALE",
            "Source": "\uc0ac\uc5c5\ubcf4\uace0\uc11c \uc8fc\uc11d / IR \uc790\ub8cc / \ub0b4\ubd80\uc790\ub8cc",
            "API availability": "\uc81c\ud55c\uc801",
            "Automation level": "Low",
            "Manual validation required?": "Yes",
            "Notes": "\uc790\uc0b0\ubcc4 \uc784\ub300\ucc28 \ub9cc\uae30 \ub370\uc774\ud130 \ud655\uc778 \ud544\uc694",
        },
        {
            "Metric": "\uc784\ucc28\uc778 \uc9d1\uc911\ub3c4",
            "Source": "\uc0ac\uc5c5\ubcf4\uace0\uc11c \uc8fc\uc11d / \ub0b4\ubd80 \uc784\ub300\ucc28 \uc790\ub8cc",
            "API availability": "\uc81c\ud55c\uc801",
            "Automation level": "Low",
            "Manual validation required?": "Yes",
            "Notes": "\uc8fc\uc694 \uc784\ucc28\uc778 \ubc0f \ub9e4\ucd9c \ube44\uc911 \ud655\uc778 \ud544\uc694",
        },
        {
            "Metric": "\uc790\uc0b0\ubcc4 NOI",
            "Source": "\uc0ac\uc5c5\ubcf4\uace0\uc11c / \uc6b4\uc6a9\ubcf4\uace0\uc11c / \ub0b4\ubd80\uc790\ub8cc",
            "API availability": "\uc81c\ud55c\uc801",
            "Automation level": "Low",
            "Manual validation required?": "Yes",
            "Notes": "\uc790\uc0b0\ubcc4 \uc218\uc775\u00b7\ube44\uc6a9 \ubc30\ubd84 \ud655\uc778 \ud544\uc694",
        },
        {
            "Metric": "\ucc28\uc785 \ub9cc\uae30 \uad6c\uc870",
            "Source": "\uc0ac\uc5c5\ubcf4\uace0\uc11c \uc8fc\uc11d / \ucc28\uc785 \uc57d\uc815 \uc790\ub8cc",
            "API availability": "\ubd80\ubd84 \uac00\ub2a5",
            "Automation level": "Medium",
            "Manual validation required?": "Yes",
            "Notes": "\uacf5\uc2dc \uc8fc\uc11d \ud30c\uc2f1 \ubc0f \ucc28\uc785 \uc870\uac74 \uac80\uc99d \ud544\uc694",
        },
        {
            "Metric": "\uc138\uae08\ud6a8\uacfc",
            "Source": "\uc138\ubc95 \uac80\ud1a0 / \ub0b4\ubd80 \uac70\ub798\uc790\ub8cc",
            "API availability": "\ubd88\uac00",
            "Automation level": "Low",
            "Manual validation required?": "Yes",
            "Notes": "\uc790\uc0b0 \ub9e4\uac01, \ubc30\ub2f9, \ubc95\uc778\uc138, \uc9c0\ubc29\uc138 \ub4f1 \ubcc4\ub3c4 \uac80\ud1a0 \ud544\uc694",
        },
        {
            "Metric": "Investor Q&A",
            "Source": "\uacf5\uc2dc / IR / \uc0ac\uc6a9\uc790 \uc785\ub825 / \ud5a5\ud6c4 LLM",
            "API availability": "\ubd80\ubd84 \uac00\ub2a5",
            "Automation level": "Medium",
            "Manual validation required?": "Yes",
            "Notes": "\ud604\uc7ac v10\uc740 rule-based\uc774\uba70 \uc678\ubd80 LLM API \ubbf8\uc0ac\uc6a9",
        },
    ]

    return pd.DataFrame(rows)


def data_availability_matrix():
    return get_data_availability_matrix()

# --- end ASCII-safe override ---
