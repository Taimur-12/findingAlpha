"""Finding Alpha — Dashboard entry point (Overview page)."""

import sys
from pathlib import Path

# Make sure the project src is importable if needed
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from data.loader import (
    STARTING_CAPITAL,
    build_equity_curve,
    combined_equity,
    combined_starting,
    drawdown_series,
    load_advisory,
    load_both_states,
    load_market_context,
    load_trades,
    system_health,
    trade_metrics,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Finding Alpha",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Auto-refresh every 60 seconds
st_autorefresh(interval=60_000, key="overview_refresh")

# ── Load data ─────────────────────────────────────────────────────────────────
s1, s2     = load_both_states()
trades_df  = load_trades()
advisory   = load_advisory()
market     = load_market_context()
health     = system_health(s1, s2, advisory)

# ── Colour helpers ─────────────────────────────────────────────────────────────
GREEN  = "#3FB950"
RED    = "#F85149"
AMBER  = "#D29922"
BLUE   = "#58A6FF"
PURPLE = "#BC8CFF"
GREY   = "#6E7681"

def pnl_colour(val: float) -> str:
    return GREEN if val > 0 else (RED if val < 0 else GREY)

def status_dot(status: str) -> str:
    colours = {"ok": GREEN, "warning": AMBER, "stale": RED,
               "offline": GREY, "expired": RED, "expiring": AMBER}
    c = colours.get(status, GREY)
    labels = {"ok": "RUNNING", "warning": "WARNING", "stale": "STALE",
              "offline": "OFFLINE", "expired": "EXPIRED", "expiring": "EXPIRING"}
    return f'<span style="color:{c}">●</span> {labels.get(status, status.upper())}'

def policy_colour(policy: str) -> str:
    return {"normal": GREEN, "reduce_size": AMBER,
            "block_new_entries": RED, "close_risk_positions": RED}.get(policy, GREY)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.kpi-card {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 8px;
    padding: 18px 22px;
    margin: 4px 0;
}
.kpi-label { color: #8B949E; font-size: 12px; font-weight: 600;
             letter-spacing: 0.08em; text-transform: uppercase; }
.kpi-value { font-size: 32px; font-weight: 700; line-height: 1.2; }
.kpi-sub   { color: #8B949E; font-size: 13px; margin-top: 4px; }
.section-header { color: #8B949E; font-size: 11px; font-weight: 600;
                  letter-spacing: 0.1em; text-transform: uppercase;
                  margin: 24px 0 8px 0; border-bottom: 1px solid #30363D;
                  padding-bottom: 6px; }
.strat-card {
    background: #161B22; border: 1px solid #30363D;
    border-radius: 8px; padding: 16px 20px;
}
.trade-row-win  { background-color: rgba(63,185,80,0.06); }
.trade-row-loss { background-color: rgba(248,81,73,0.06); }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
mode_label = "SIMULATION"
mode_colour = PURPLE

h1, h2 = st.columns([3, 1])
with h1:
    st.markdown(f"# 📈 Finding Alpha")
    st.markdown(f"Systematic Crypto Trading · BTCUSDT 1H · Bybit")
with h2:
    st.markdown(f"""
    <div style='text-align:right; padding-top:8px'>
        <span style='background:{mode_colour}22; color:{mode_colour};
                     border:1px solid {mode_colour}55; border-radius:4px;
                     padding:4px 10px; font-size:13px; font-weight:600;'>
            ● {mode_label}
        </span>
        <div style='color:#8B949E; font-size:12px; margin-top:6px'>
            Last bar: {s2["last_bar_ts"][:10] if s2["last_bar_ts"] else "—"}
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Simulated-data banner (unmissable) ──────────────────────────────────────────
st.markdown(f"""
<div style='background:{AMBER}1A; border:1px solid {AMBER}; border-radius:8px;
            padding:12px 18px; margin-bottom:12px; display:flex; align-items:center;'>
    <span style='font-size:20px; margin-right:12px'>⚠</span>
    <div style='color:#E6EDF3; font-size:14px; line-height:1.5'>
        <strong style='color:{AMBER}; letter-spacing:0.04em'>SIMULATED DATA — NOT LIVE PERFORMANCE.</strong>
        Equity, P&amp;L, and trades below are from historical replay seeded in
        <code>paper/sim/</code>, not real trading. No capital is deployed. The live
        paper runners start flat until 24/7 cloud operation begins.
    </div>
</div>
""", unsafe_allow_html=True)

# ── Staleness warning ──────────────────────────────────────────────────────────
stale_h = health.get("runner1_stale_h") or health.get("runner2_stale_h")
if stale_h and stale_h > 2:
    days = stale_h / 24
    st.warning(
        f"⚠ Data is **{days:.1f} days stale** — last bar {s2['last_bar_ts'][:10]}. "
        f"Stats reflect simulation replay data, not live market prices. "
        f"Deploy to cloud and start the cron job for live updates."
    )

# ── KPI Strip ──────────────────────────────────────────────────────────────────
combined_eq  = combined_equity(s1, s2)
combined_st  = combined_starting()
total_return = combined_eq - combined_st
total_ret_pct = total_return / combined_st * 100

# Daily P&L — combined
daily_pnl = (s1["equity"] - s1["daily_start_equity"]) + (s2["equity"] - s2["daily_start_equity"])
daily_pnl_pct = daily_pnl / combined_st * 100

# Drawdown — worst of the two
dd1 = (s1["equity"] - s1["peak_equity"]) / s1["peak_equity"] * 100 if s1["peak_equity"] else 0
dd2 = (s2["equity"] - s2["peak_equity"]) / s2["peak_equity"] * 100 if s2["peak_equity"] else 0
max_dd = min(dd1, dd2)

# Status
if health["circuit_breaker"]:
    sys_status, sys_label, sys_colour = "●", "CIRCUIT BREAKER", RED
elif health["runner1_status"] in ("stale", "offline") or health["runner2_status"] in ("stale", "offline"):
    sys_status, sys_label, sys_colour = "●", "DATA STALE", AMBER
else:
    sys_status, sys_label, sys_colour = "●", "OPERATIONAL", GREEN

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Account Equity</div>
        <div class='kpi-value' style='color:#E6EDF3'>${combined_eq:,.2f}</div>
        <div class='kpi-sub'>Combined (2 strategies)</div>
    </div>""", unsafe_allow_html=True)

with k2:
    ret_col = pnl_colour(total_return)
    sign = "+" if total_return >= 0 else ""
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Total Return</div>
        <div class='kpi-value' style='color:{ret_col}'>{sign}${total_return:,.2f}</div>
        <div class='kpi-sub' style='color:{ret_col}'>{sign}{total_ret_pct:.2f}% since start</div>
    </div>""", unsafe_allow_html=True)

with k3:
    dpnl_col = pnl_colour(daily_pnl)
    dsign = "+" if daily_pnl >= 0 else ""
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Today's P&L</div>
        <div class='kpi-value' style='color:{dpnl_col}'>{dsign}${daily_pnl:,.2f}</div>
        <div class='kpi-sub' style='color:{dpnl_col}'>{dsign}{daily_pnl_pct:.2f}% today</div>
    </div>""", unsafe_allow_html=True)

with k4:
    dd_col = RED if max_dd < -5 else (AMBER if max_dd < -2 else GREEN)
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Max Drawdown</div>
        <div class='kpi-value' style='color:{dd_col}'>{max_dd:.1f}%</div>
        <div class='kpi-sub'>From peak equity</div>
    </div>""", unsafe_allow_html=True)

with k5:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>System Status</div>
        <div class='kpi-value' style='color:{sys_colour}; font-size:22px'>{sys_status} {sys_label}</div>
        <div class='kpi-sub'>Auto-refreshes every 60s</div>
    </div>""", unsafe_allow_html=True)

# ── Equity Curve ───────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Equity Curve</div>", unsafe_allow_html=True)

if not trades_df.empty:
    curve_df = build_equity_curve(trades_df, starting=float(STARTING_CAPITAL))
    time_options = {"1M": 30, "3M": 90, "ALL": 9999}
    time_sel = st.radio("Range", list(time_options.keys()), horizontal=True, index=2, key="eq_range")
    cutoff_days = time_options[time_sel]
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=cutoff_days)

    fig = go.Figure()

    strat_colours = {
        "prev_day_breakdown_v1": BLUE,
        "short_composite_v1":    PURPLE,
        "combined":              GREEN,
    }
    strat_names = {
        "prev_day_breakdown_v1": "prev_day_breakdown_v1",
        "short_composite_v1":    "short_composite_v1",
        "combined":              "Combined",
    }

    for sid, colour in strat_colours.items():
        sub = curve_df[curve_df["strategy"] == sid]
        sub = sub[sub["exit_ts"] >= cutoff]
        if sub.empty:
            continue

        # Starting point
        start_eq = float(STARTING_CAPITAL) * (2 if sid == "combined" else 1)
        x_vals = [sub["exit_ts"].iloc[0] - pd.Timedelta(hours=1)] + list(sub["exit_ts"])
        y_vals = [start_eq] + list(sub["equity"])

        fig.add_trace(go.Scatter(
            x=x_vals, y=y_vals,
            mode="lines+markers" if sid != "combined" else "lines",
            name=strat_names[sid],
            line=dict(color=colour, width=2 if sid == "combined" else 1.5,
                      dash="solid" if sid == "combined" else "dot"),
            marker=dict(size=6),
        ))

    # Starting capital reference line
    fig.add_hline(y=float(STARTING_CAPITAL), line_dash="dash",
                  line_color=GREY, annotation_text="Starting Capital (per strategy)",
                  annotation_position="bottom right")

    fig.update_layout(
        height=340,
        margin=dict(l=0, r=0, t=8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E6EDF3"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        xaxis=dict(gridcolor="#30363D", showgrid=True),
        yaxis=dict(gridcolor="#30363D", showgrid=True, tickprefix="$"),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No closed trades yet. Equity curve will appear once trades complete.")

# ── Strategy Performance Cards ─────────────────────────────────────────────────
st.markdown("<div class='section-header'>Strategy Performance</div>", unsafe_allow_html=True)

c1, c2 = st.columns(2)

for col, sid, state, label, colour in [
    (c1, "prev_day_breakdown_v1", s1, "prev_day_breakdown_v1", BLUE),
    (c2, "short_composite_v1",    s2, "short_composite_v1",    PURPLE),
]:
    strat_trades = trades_df[trades_df["strategy_id"] == sid] if not trades_df.empty else pd.DataFrame()
    m = trade_metrics(strat_trades)
    eq = state["equity"]
    pnl = eq - float(STARTING_CAPITAL)
    pnl_pct = pnl / float(STARTING_CAPITAL) * 100
    pnl_col = pnl_colour(pnl)
    sign = "+" if pnl >= 0 else ""

    win_pct = f"{m['win_rate']:.0f}%" if m["count"] else "—"
    exp_r   = f"{m['expectancy_r']:+.3f}R" if m["count"] else "—"
    pf      = f"{m['profit_factor']:.2f}" if m["count"] else "—"

    with col:
        st.markdown(f"""
        <div class='strat-card'>
            <div style='color:{colour}; font-weight:700; font-size:15px; margin-bottom:12px;
                        border-bottom:1px solid #30363D; padding-bottom:8px;'>{label}</div>
            <table style='width:100%; border-collapse:collapse; font-size:14px;'>
                <tr><td style='color:#8B949E; padding:3px 0'>Equity</td>
                    <td style='text-align:right; color:{pnl_col}; font-weight:600'>
                        ${eq:,.2f} ({sign}{pnl_pct:.2f}%)</td></tr>
                <tr><td style='color:#8B949E; padding:3px 0'>Trades</td>
                    <td style='text-align:right; font-weight:600'>{m['count']}</td></tr>
                <tr><td style='color:#8B949E; padding:3px 0'>Win rate</td>
                    <td style='text-align:right; font-weight:600'>{win_pct}</td></tr>
                <tr><td style='color:#8B949E; padding:3px 0'>Avg expectancy</td>
                    <td style='text-align:right; font-weight:600'>{exp_r}</td></tr>
                <tr><td style='color:#8B949E; padding:3px 0'>Profit factor</td>
                    <td style='text-align:right; font-weight:600'>{pf}</td></tr>
                <tr><td style='color:#8B949E; padding:3px 0'>Net P&L</td>
                    <td style='text-align:right; color:{pnl_col}; font-weight:600'>
                        {sign}${m['net_pnl']:,.2f}</td></tr>
            </table>
            <div style='margin-top:10px; font-size:12px; color:{BLUE}'>● MONITORING (simulation)</div>
        </div>""", unsafe_allow_html=True)

# ── Recent Trades ──────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Recent Trades</div>", unsafe_allow_html=True)

if not trades_df.empty:
    recent = trades_df.sort_values("exit_ts", ascending=False).head(10).copy()
    recent["Date"] = recent["exit_ts"].dt.strftime("%Y-%m-%d %H:%M UTC")
    recent["Strategy"] = recent["strategy_id"]
    recent["Entry $"] = recent["entry_price"].apply(lambda x: f"${x:,.2f}")
    recent["Exit $"]  = recent["exit_price"].apply(lambda x: f"${x:,.2f}")
    recent["P&L"]     = recent["net_pnl"].apply(lambda x: f"{'+'if x>=0 else ''}{x:,.2f}")
    recent["R"]       = recent["r_multiple"].apply(lambda x: f"{'+'if x>=0 else ''}{x:.3f}R")
    recent["Exit"]    = recent["exit_reason"]
    recent["✓"]       = recent["is_win"].apply(lambda w: "✓" if w else "✗")

    display_cols = ["Date", "Strategy", "Entry $", "Exit $", "P&L", "R", "Exit", "✓"]
    st.dataframe(
        recent[display_cols].reset_index(drop=True),
        use_container_width=True,
        height=350,
        column_config={
            "P&L": st.column_config.TextColumn("Net P&L"),
            "R":   st.column_config.TextColumn("R Multiple"),
            "✓":   st.column_config.TextColumn("Result"),
        },
    )
else:
    st.info("No completed trades yet.")

# ── Advisory snapshot ──────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>LLM Advisory</div>", unsafe_allow_html=True)

a1, a2, a3 = st.columns(3)
pol_col = policy_colour(advisory["trade_policy"])
with a1:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Trade Policy</div>
        <div class='kpi-value' style='color:{pol_col}; font-size:20px'>
            {advisory["trade_policy"].upper().replace("_", " ")}</div>
    </div>""", unsafe_allow_html=True)

with a2:
    rs = advisory["risk_scalar"]
    rs_col = GREEN if rs >= 1.0 else (AMBER if rs >= 0.5 else RED)
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Risk Scalar</div>
        <div class='kpi-value' style='color:{rs_col}'>{rs:.2f}×</div>
        <div class='kpi-sub'>{"Full sizing" if rs >= 1.0 else f"{rs*100:.0f}% of normal"}</div>
    </div>""", unsafe_allow_html=True)

with a3:
    adv_col = RED if advisory["is_expired"] else (AMBER if (advisory["hours_left"] or 99) < 4 else GREEN)
    hl = advisory["hours_left"]
    hl_str = f"{hl:.1f}h remaining" if hl is not None else "EXPIRED"
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Advisory Expires</div>
        <div class='kpi-value' style='color:{adv_col}; font-size:20px'>{hl_str}</div>
        <div class='kpi-sub'>{advisory["as_of"][:16].replace("T"," ")} UTC</div>
    </div>""", unsafe_allow_html=True)

if advisory["summary"]:
    st.markdown(f"""
    <div style='background:#161B22; border:1px solid #30363D; border-radius:8px;
                padding:14px 18px; margin-top:8px; color:#E6EDF3; font-size:14px;
                font-style:italic;'>
        "{advisory["summary"]}"
        <div style='color:#8B949E; font-size:12px; margin-top:6px'>
            — {advisory["model_id"]}
        </div>
    </div>""", unsafe_allow_html=True)
