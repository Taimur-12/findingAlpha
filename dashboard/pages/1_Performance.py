"""Performance analytics page."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from data.loader import (
    STARTING_CAPITAL,
    build_equity_curve,
    drawdown_series,
    load_both_states,
    load_trades,
    trade_metrics,
)

st.set_page_config(page_title="Performance · Finding Alpha", layout="wide")

from data.source import data_source_selector
data_source_selector()
st_autorefresh(interval=60_000, key="perf_refresh")

GREEN  = "#3FB950"
RED    = "#F85149"
AMBER  = "#D29922"
BLUE   = "#58A6FF"
PURPLE = "#BC8CFF"
GREY   = "#6E7681"

PLOT_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#E6EDF3"),
    margin=dict(l=0, r=0, t=24, b=0),
)

st.markdown("""
<style>
.section-header { color:#8B949E; font-size:11px; font-weight:600;
    letter-spacing:.1em; text-transform:uppercase;
    margin:24px 0 8px 0; border-bottom:1px solid #30363D; padding-bottom:6px; }
.metric-box { background:#161B22; border:1px solid #30363D;
    border-radius:8px; padding:14px 18px; }
</style>""", unsafe_allow_html=True)

st.title("📊 Performance")

s1, s2    = load_both_states()
trades_df = load_trades()

if trades_df.empty:
    st.info("No closed trades yet — come back after the first simulation run completes.")
    st.stop()

st.caption(
    f"📌 Showing **{len(trades_df)} simulation trades** from paper/sim/ — "
    f"last bar {s2['last_bar_ts'][:10]}. These are historical replay results, not live trading."
)

# ── Summary metrics ─────────────────────────────────────────────────────────────
all_m = trade_metrics(trades_df)
pd_m  = trade_metrics(trades_df[trades_df["strategy_id"] == "prev_day_breakdown_v1"])
sc_m  = trade_metrics(trades_df[trades_df["strategy_id"] == "short_composite_v1"])

col1, col2, col3, col4, col5, col6 = st.columns(6)
metrics = [
    ("Trades", f"{all_m['count']}"),
    ("Win Rate",  f"{all_m['win_rate']:.1f}%"),
    ("Expectancy", f"{all_m['expectancy_r']:+.3f}R"),
    ("Profit Factor", f"{all_m['profit_factor']:.2f}"),
    ("Net P&L", f"${all_m['net_pnl']:+,.2f}"),
    ("Total Fees", f"${all_m['total_fees']:,.2f}"),
]
for col, (label, value) in zip([col1, col2, col3, col4, col5, col6], metrics):
    with col:
        st.metric(label, value)

st.divider()

# ── Equity + Drawdown ──────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Equity Curve &amp; Drawdown</div>", unsafe_allow_html=True)

curve_df = build_equity_curve(trades_df, starting=float(STARTING_CAPITAL))
combined = curve_df[curve_df["strategy"] == "combined"].sort_values("exit_ts")

if not combined.empty:
    start_eq = float(STARTING_CAPITAL) * 2
    x_all = [combined["exit_ts"].iloc[0] - pd.Timedelta(hours=1)] + list(combined["exit_ts"])
    y_all = [start_eq] + list(combined["equity"])

    # Rolling peak for proper drawdown shading
    y_series  = pd.Series(y_all)
    roll_peak = y_series.cummax().tolist()

    fig = go.Figure()

    # Drawdown fill: rolling peak trace (invisible line) + equity fills down to it
    fig.add_trace(go.Scatter(
        x=x_all, y=roll_peak,
        line=dict(width=0), showlegend=False, name="_peak",
        hoverinfo="skip",
    ))
    # Equity line with fill back to the peak trace
    fig.add_trace(go.Scatter(
        x=x_all, y=y_all,
        mode="lines+markers",
        name="Combined equity",
        line=dict(color=GREEN, width=2),
        marker=dict(size=5),
        fill="tonexty",
        fillcolor="rgba(248,81,73,0.12)",
    ))

    # Per-strategy curves
    for sid, colour, name in [
        ("prev_day_breakdown_v1", BLUE, "prev_day_breakdown_v1"),
        ("short_composite_v1", PURPLE, "short_composite_v1"),
    ]:
        sub = curve_df[curve_df["strategy"] == sid].sort_values("exit_ts")
        if sub.empty:
            continue
        s_eq = float(STARTING_CAPITAL)
        xs = [sub["exit_ts"].iloc[0] - pd.Timedelta(hours=1)] + list(sub["exit_ts"])
        ys = [s_eq] + list(sub["equity"])
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers", name=name,
            line=dict(color=colour, width=1.5, dash="dot"),
            marker=dict(size=4),
        ))

    fig.add_hline(y=float(STARTING_CAPITAL), line_dash="dash",
                  line_color=GREY, annotation_text="$10k starting",
                  annotation_position="bottom right")

    fig.update_layout(
        height=320, hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(gridcolor="#30363D"),
        yaxis=dict(tickprefix="$", gridcolor="#30363D"),
        **PLOT_LAYOUT,
    )
    st.plotly_chart(fig, use_container_width=True)

# ── R-Multiple Distribution ────────────────────────────────────────────────────
st.markdown("<div class='section-header'>R-Multiple Distribution</div>", unsafe_allow_html=True)

col_l, col_r = st.columns([2, 1])
with col_l:
    r_vals = trades_df["r_multiple"].dropna()
    colours = [GREEN if r >= 0 else RED for r in r_vals]

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=list(range(len(r_vals))),
        y=list(r_vals),
        marker_color=colours,
        name="Trade R",
        hovertemplate="Trade %{x}: %{y:.3f}R<extra></extra>",
    ))
    fig2.add_hline(y=0, line_color=GREY, line_width=1)
    fig2.add_hline(y=float(trades_df["r_multiple"].mean()),
                   line_dash="dash", line_color=AMBER,
                   annotation_text=f"Avg {trades_df['r_multiple'].mean():+.3f}R",
                   annotation_position="top right")
    fig2.update_layout(
        height=260, showlegend=False,
        xaxis=dict(title="Trade #", gridcolor="#30363D"),
        yaxis=dict(title="R Multiple", gridcolor="#30363D"),
        **{k: v for k, v in PLOT_LAYOUT.items() if k not in ("xaxis", "yaxis")},
    )
    st.plotly_chart(fig2, use_container_width=True)

with col_r:
    st.markdown("<div class='section-header'>By Exit Reason</div>", unsafe_allow_html=True)
    exit_stats = trades_df.groupby("exit_reason").agg(
        Count=("net_pnl", "count"),
        Avg_R=("r_multiple", "mean"),
        Net_PnL=("net_pnl", "sum"),
    ).reset_index()
    exit_stats["Avg_R"]    = exit_stats["Avg_R"].apply(lambda x: f"{x:+.3f}R")
    exit_stats["Net_PnL"]  = exit_stats["Net_PnL"].apply(lambda x: f"${x:+,.2f}")
    exit_stats.columns     = ["Exit Reason", "Count", "Avg R", "Net P&L"]
    st.dataframe(exit_stats, use_container_width=True, hide_index=True)

# ── Monthly P&L Calendar ───────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Monthly P&amp;L</div>", unsafe_allow_html=True)

trades_df["month"] = trades_df["exit_ts"].dt.strftime("%Y-%m")
monthly = trades_df.groupby("month").agg(
    Trades=("net_pnl", "count"),
    Net_PnL=("net_pnl", "sum"),
    Win_Rate=("is_win", lambda x: x.mean() * 100),
    Avg_R=("r_multiple", "mean"),
).reset_index()
monthly.columns = ["Month", "Trades", "Net P&L ($)", "Win Rate (%)", "Avg R"]
monthly["Net P&L ($)"]  = monthly["Net P&L ($)"].round(2)
monthly["Win Rate (%)"] = monthly["Win Rate (%)"].round(1)
monthly["Avg R"]        = monthly["Avg R"].round(3)

st.dataframe(
    monthly.sort_values("Month", ascending=False),
    use_container_width=True,
    hide_index=True,
)

# ── Per-Strategy Breakdown ─────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Strategy Breakdown</div>", unsafe_allow_html=True)

def strategy_table(m: dict, name: str, colour: str) -> None:
    st.markdown(f"<div style='color:{colour}; font-weight:700; margin-bottom:6px'>{name}</div>",
                unsafe_allow_html=True)
    rows = {
        "Trades":          str(m["count"]),
        "Win rate":        f"{m['win_rate']:.1f}%",
        "Expectancy":      f"{m['expectancy_r']:+.3f}R",
        "Profit factor":   f"{m['profit_factor']:.2f}" if m["profit_factor"] != float("inf") else "∞",
        "Net P&L":         f"${m['net_pnl']:+,.2f}",
        "Total fees":      f"${m['total_fees']:,.2f}",
        "Avg hold (h)":    f"{m['avg_hold_hours']:.1f}",
        "Best trade":      f"{m['max_r_win']:+.3f}R",
        "Worst trade":     f"{m['max_r_loss']:+.3f}R",
    }
    df_rows = pd.DataFrame(rows.items(), columns=["Metric", "Value"])
    st.dataframe(df_rows, use_container_width=True, hide_index=True)

ca, cb = st.columns(2)
with ca:
    strategy_table(pd_m, "prev_day_breakdown_v1", BLUE)
with cb:
    strategy_table(sc_m, "short_composite_v1", PURPLE)
