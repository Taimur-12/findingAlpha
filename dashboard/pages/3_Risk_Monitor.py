"""Risk monitor page — gauges, circuit breaker, drawdown."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from data.loader import (
    STARTING_CAPITAL,
    drawdown_series,
    build_equity_curve,
    load_both_states,
    load_trades,
    trade_metrics,
)

st.set_page_config(page_title="Risk Monitor · Finding Alpha", layout="wide")

from data.source import data_source_selector
data_source_selector()
st_autorefresh(interval=30_000, key="risk_refresh")

GREEN  = "#3FB950"
RED    = "#F85149"
AMBER  = "#D29922"
BLUE   = "#58A6FF"
GREY   = "#6E7681"

st.markdown("""
<style>
.section-header { color:#8B949E; font-size:11px; font-weight:600;
    letter-spacing:.1em; text-transform:uppercase;
    margin:24px 0 8px 0; border-bottom:1px solid #30363D; padding-bottom:6px; }
.risk-card { background:#161B22; border:1px solid #30363D;
    border-radius:8px; padding:16px 20px; }
</style>""", unsafe_allow_html=True)

st.title("⚠️ Risk Monitor")

s1, s2    = load_both_states()
trades_df = load_trades()

DAILY_LOSS_LIMIT    = 3.0    # %
MAX_DRAWDOWN_LIMIT  = 10.0   # %
MAX_HEAT_LIMIT      = 6.0    # %
CB_LOSS_THRESHOLD   = 5      # consecutive losses

# Per-strategy risk metrics
def risk_metrics(state: dict, name: str):
    eq     = state["equity"]
    peak   = state["peak_equity"]
    daily  = state["daily_start_equity"]
    start  = float(STARTING_CAPITAL)

    dd_pct    = (eq - peak) / peak * 100 if peak else 0
    daily_pct = (eq - daily) / daily * 100 if daily else 0
    heat_pct  = 0.0  # single-position system: either 0% or risk_pct (~0.25%)
    if state.get("open_position"):
        heat_pct = 0.25

    return {
        "name":         name,
        "equity":       eq,
        "daily_pct":    daily_pct,
        "drawdown_pct": dd_pct,
        "heat_pct":     heat_pct,
        "cb":           state["circuit_breaker"],
    }

r1 = risk_metrics(s1, "prev_day_breakdown_v1")
r2 = risk_metrics(s2, "short_composite_v1")

# ── Circuit Breaker ────────────────────────────────────────────────────────────
cb_active = r1["cb"] or r2["cb"]
st.markdown("<div class='section-header'>Circuit Breaker</div>", unsafe_allow_html=True)

if cb_active:
    st.markdown(f"""
    <div style='background:{RED}22; border:2px solid {RED}; border-radius:8px;
                padding:20px; text-align:center; margin-bottom:16px;'>
        <div style='color:{RED}; font-size:28px; font-weight:700'>🚨 CIRCUIT BREAKER ACTIVE</div>
        <div style='color:#E6EDF3; margin-top:8px'>All new entries are blocked.
            Resets at next daily open (00:00 UTC).</div>
    </div>""", unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div style='background:{GREEN}11; border:1px solid {GREEN}44; border-radius:8px;
                padding:16px; text-align:center; margin-bottom:16px;'>
        <div style='color:{GREEN}; font-size:20px; font-weight:700'>● CIRCUIT BREAKER: INACTIVE</div>
        <div style='color:#8B949E; margin-top:4px'>Trading is permitted on all strategies</div>
    </div>""", unsafe_allow_html=True)

# ── Risk Gauges ────────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Risk Gauges (per strategy)</div>", unsafe_allow_html=True)

def gauge_fig(current: float, limit: float, title: str, unit: str = "%") -> go.Figure:
    pct_used = min(abs(current) / abs(limit) * 100, 100)
    bar_col = GREEN if pct_used < 60 else (AMBER if pct_used < 85 else RED)

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=abs(current),
        title={"text": title, "font": {"color": "#8B949E", "size": 13}},
        number={"suffix": unit, "prefix": "-" if current < 0 else "",
                "font": {"color": "#E6EDF3", "size": 24}},
        gauge={
            "axis": {"range": [0, abs(limit)], "tickcolor": "#8B949E",
                     "tickfont": {"color": "#8B949E", "size": 10}},
            "bar": {"color": bar_col},
            "bgcolor": "#161B22",
            "bordercolor": "#30363D",
            "steps": [
                {"range": [0, abs(limit) * 0.6],  "color": "#1C2128"},
                {"range": [abs(limit) * 0.6, abs(limit) * 0.85], "color": "#2D1F0B"},
                {"range": [abs(limit) * 0.85, abs(limit)],       "color": "#2D0D0D"},
            ],
            "threshold": {"line": {"color": RED, "width": 3},
                          "thickness": 0.8, "value": abs(limit)},
        },
    ))
    fig.update_layout(
        height=220, margin=dict(l=10, r=10, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E6EDF3"),
    )
    return fig

for label, r in [("prev_day_breakdown_v1", r1), ("short_composite_v1", r2)]:
    slug = label.replace("_", "")
    st.markdown(f"**{label}**")
    ga, gb, gc = st.columns(3)
    with ga:
        st.plotly_chart(
            gauge_fig(r["daily_pct"], DAILY_LOSS_LIMIT, "Daily Loss"),
            use_container_width=True,
            key=f"gauge_daily_{slug}",
        )
    with gb:
        st.plotly_chart(
            gauge_fig(r["drawdown_pct"], MAX_DRAWDOWN_LIMIT, "Drawdown"),
            use_container_width=True,
            key=f"gauge_dd_{slug}",
        )
    with gc:
        st.plotly_chart(
            gauge_fig(r["heat_pct"], MAX_HEAT_LIMIT, "Portfolio Heat"),
            use_container_width=True,
            key=f"gauge_heat_{slug}",
        )

# ── Drawdown Timeline ──────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Drawdown History</div>", unsafe_allow_html=True)

if not trades_df.empty:
    import pandas as pd
    curve_df = build_equity_curve(trades_df, starting=float(STARTING_CAPITAL))
    combined = curve_df[curve_df["strategy"] == "combined"].sort_values("exit_ts")

    if not combined.empty:
        start_eq = float(STARTING_CAPITAL) * 2
        x_all = [combined["exit_ts"].iloc[0] - pd.Timedelta(hours=1)] + list(combined["exit_ts"])
        y_all = pd.Series([start_eq] + list(combined["equity"]))
        dd    = drawdown_series(y_all)

        fig_dd = go.Figure()
        fig_dd.add_trace(go.Scatter(
            x=x_all, y=list(dd),
            fill="tozeroy",
            fillcolor="rgba(248,81,73,0.2)",
            line=dict(color=RED, width=1.5),
            name="Drawdown %",
        ))
        fig_dd.add_hline(y=-DAILY_LOSS_LIMIT, line_dash="dot",
                         line_color=AMBER, annotation_text="Daily loss limit",
                         annotation_position="bottom right")
        fig_dd.add_hline(y=-MAX_DRAWDOWN_LIMIT, line_dash="dot",
                         line_color=RED, annotation_text="Max drawdown limit",
                         annotation_position="bottom right")
        fig_dd.update_layout(
            height=250,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E6EDF3"),
            margin=dict(l=0, r=0, t=8, b=0),
            xaxis=dict(gridcolor="#30363D"),
            yaxis=dict(gridcolor="#30363D", ticksuffix="%"),
        )
        st.plotly_chart(fig_dd, use_container_width=True)
else:
    st.info("No trade history yet for drawdown chart.")

# ── Risk Parameter Reference ───────────────────────────────────────────────────
st.markdown("<div class='section-header'>Risk Parameter Reference</div>", unsafe_allow_html=True)

import pandas as pd
params = pd.DataFrame([
    ["Risk per trade",      "0.25%",  f"${float(STARTING_CAPITAL)*0.0025:,.2f} on $10k"],
    ["Daily loss limit",    f"-{DAILY_LOSS_LIMIT}%",   "Blocks all new entries until next day"],
    ["Max drawdown limit",  f"-{MAX_DRAWDOWN_LIMIT}%", "Blocks all new entries"],
    ["Max portfolio heat",  f"{MAX_HEAT_LIMIT}%",     "Max open risk across all positions"],
    ["Circuit breaker",     "5 consecutive losses",   "Auto-resets daily at 00:00 UTC"],
    ["Max positions",       "1 per strategy",          "2 total — each strategy runs independently"],
    ["Min notional",        "$100",                   "Bybit minimum order gate"],
], columns=["Parameter", "Limit", "Effect"])

st.dataframe(params, use_container_width=True, hide_index=True)
