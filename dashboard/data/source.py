"""Sidebar selector for sim vs live data source. Persists via st.session_state."""

import streamlit as st


def data_source_selector() -> str:
    """Render a sidebar radio that controls whether loader.py reads paper/sim/ or paper/live/.

    Call at the top of every page. Returns the current selection.
    """
    if "data_source" not in st.session_state:
        st.session_state.data_source = "sim"

    with st.sidebar:
        st.markdown("### Data source")
        choice = st.radio(
            "Display data from:",
            options=["sim", "live"],
            format_func=lambda x: "📊 Simulation (paper/sim/)" if x == "sim" else "🛰 Live testnet (paper/live/)",
            key="data_source",
            label_visibility="collapsed",
        )
        if choice == "sim":
            st.caption("Historical replay seeded in `paper/sim/`. Use for shareholder demo.")
        else:
            st.caption("Real Bybit testnet activity from `paper/live/`. Trigger cycles on the Live Trading page.")
        st.divider()
    return choice


def source_label() -> tuple[str, str, str]:
    """Return (mode_label, banner_text, banner_colour_hex) for the current source."""
    src = st.session_state.get("data_source", "sim")
    if src == "live":
        return (
            "LIVE TESTNET",
            "LIVE BYBIT TESTNET DATA — orders placed against api-testnet.bybit.com. "
            "No real money. Equity/P&L reflect testnet activity from <code>paper/live/</code>.",
            "#58A6FF",
        )
    return (
        "SIMULATION",
        "SIMULATED DATA — NOT LIVE PERFORMANCE. "
        "Equity, P&amp;L, and trades below are from historical replay seeded in "
        "<code>paper/sim/</code>, not real trading.",
        "#BC8CFF",
    )
