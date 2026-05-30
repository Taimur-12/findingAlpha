"""Live Trading page — manually trigger a Bybit testnet cycle from the UI."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from data.live_runner import (
    COMPOSITE_DIR,
    PREV_DAY_DIR,
    env_ready,
    exchange_position_snapshot,
    latest_matrix_events,
    load_live_state,
    load_live_trades,
    run_cycle,
)

st.set_page_config(page_title="Live Trading · Finding Alpha", layout="wide")

GREEN = "#3FB950"
RED = "#F85149"
AMBER = "#D29922"
BLUE = "#58A6FF"
PURPLE = "#BC8CFF"
GREY = "#6E7681"

st.markdown(
    """
<style>
.section-header { color:#8B949E; font-size:11px; font-weight:600;
    letter-spacing:.1em; text-transform:uppercase;
    margin:24px 0 8px 0; border-bottom:1px solid #30363D; padding-bottom:6px; }
.kpi-card { background:#161B22; border:1px solid #30363D;
    border-radius:8px; padding:16px 20px; }
.kpi-label { color:#8B949E; font-size:12px; font-weight:600;
    letter-spacing:.08em; text-transform:uppercase; }
.kpi-value { font-size:24px; font-weight:700; }
.kpi-sub { color:#8B949E; font-size:12px; margin-top:4px; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🛰 Live Trading — Bybit Testnet")

# ── Testnet banner ────────────────────────────────────────────────────────────
st.markdown(
    f"""
<div style='background:{AMBER}1A; border:1px solid {AMBER}; border-radius:8px;
            padding:12px 18px; margin-bottom:12px;'>
    <strong style='color:{AMBER}'>⚠ BYBIT TESTNET — NO REAL MONEY.</strong>
    Orders go to <code>api-testnet.bybit.com</code>. State written to <code>paper/live/</code>
    (separate from <code>paper/sim/</code>). Both strategies trade on each cycle.
</div>
""",
    unsafe_allow_html=True,
)

# ── Env / key status ──────────────────────────────────────────────────────────
ok, env_msg = env_ready()
if not ok:
    st.error(f"Testnet credentials not ready: {env_msg}")
    st.info(
        "Make sure `.env` at the project root contains "
        "`BYBIT_TESTNET_API_KEY` and `BYBIT_TESTNET_API_SECRET`. "
        "Default mode is testnet; no extra env var needed."
    )
    st.stop()
else:
    st.success(f"✓ {env_msg}")

# ── Run button ────────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Trigger Cycle</div>", unsafe_allow_html=True)

if "live_running" not in st.session_state:
    st.session_state.live_running = False
if "last_results" not in st.session_state:
    st.session_state.last_results = None
if "last_run_ts" not in st.session_state:
    st.session_state.last_run_ts = None

col_btn, col_info = st.columns([1, 3])
with col_btn:
    clicked = st.button(
        "▶ RUN LIVE CYCLE NOW",
        disabled=st.session_state.live_running,
        type="primary",
        use_container_width=True,
    )
with col_info:
    if st.session_state.last_run_ts:
        delta = (datetime.now(timezone.utc) - st.session_state.last_run_ts).total_seconds()
        st.markdown(
            f"<div style='color:{GREY}; padding-top:8px'>"
            f"Last cycle: {st.session_state.last_run_ts.strftime('%Y-%m-%d %H:%M:%S UTC')} "
            f"({int(delta)}s ago)</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='color:{GREY}; padding-top:8px'>No cycles run yet this session.</div>",
            unsafe_allow_html=True,
        )

if clicked:
    st.session_state.live_running = True
    with st.spinner("Fetching market data, polling exchange, processing strategies…"):
        results = run_cycle()
    st.session_state.last_results = results
    st.session_state.last_run_ts = datetime.now(timezone.utc)
    st.session_state.live_running = False
    st.rerun()

# ── Last cycle results ────────────────────────────────────────────────────────
if st.session_state.last_results:
    st.markdown("<div class='section-header'>Last Cycle Result</div>", unsafe_allow_html=True)
    for r in st.session_state.last_results:
        colour = GREEN if r.get("ok") else RED
        status = r.get("status", "?")
        sid = r.get("strategy_id", "?")
        with st.container():
            st.markdown(
                f"<div class='kpi-card' style='margin-bottom:8px'>"
                f"<span style='color:{colour}; font-weight:700'>● {sid}</span>"
                f" — <code>{status}</code>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if r.get("error"):
                st.code(r["error"], language="text")
            else:
                detail_cols = [
                    "bars_processed", "trades_closed", "has_open_position",
                    "has_pending_entry", "equity", "last_bar",
                    "exchange_position_size", "exchange_position_side",
                ]
                shown = {k: r.get(k) for k in detail_cols if r.get(k) is not None}
                if shown:
                    st.json(shown, expanded=False)

# ── Live state snapshot ───────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Live State (paper/live/)</div>", unsafe_allow_html=True)

s_prev = load_live_state(PREV_DAY_DIR)
s_comp = load_live_state(COMPOSITE_DIR)

cols = st.columns(2)
for col, label, state, colour in [
    (cols[0], "prev_day_breakdown_v1", s_prev, BLUE),
    (cols[1], "short_composite_v1", s_comp, PURPLE),
]:
    with col:
        if not state.get("exists"):
            st.markdown(
                f"<div class='kpi-card'>"
                f"<div style='color:{colour}; font-weight:700; margin-bottom:8px'>{label}</div>"
                f"<div style='color:{GREY}'>No live state yet — click RUN to start.</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            continue
        eq = state["equity"]
        pnl = eq - 10_000
        pnl_pct = pnl / 10_000 * 100
        pnl_col = GREEN if pnl >= 0 else RED
        pos = "OPEN" if state.get("open_position") else (
            "PENDING" if state.get("pending_entry") else (
                "LIVE-REF" if state.get("live_plan_ref") else "FLAT"
            )
        )
        cb = "● CIRCUIT BREAKER" if state.get("circuit_breaker") else "● OK"
        cb_col = RED if state.get("circuit_breaker") else GREEN
        st.markdown(
            f"<div class='kpi-card'>"
            f"<div style='color:{colour}; font-weight:700; margin-bottom:8px'>{label}</div>"
            f"<table style='width:100%; font-size:13px'>"
            f"<tr><td style='color:#8B949E'>Equity</td>"
            f"<td style='text-align:right; color:{pnl_col}; font-weight:600'>"
            f"${eq:,.2f} ({'+' if pnl >= 0 else ''}{pnl_pct:.2f}%)</td></tr>"
            f"<tr><td style='color:#8B949E'>Position</td>"
            f"<td style='text-align:right; font-weight:600'>{pos}</td></tr>"
            f"<tr><td style='color:#8B949E'>Last bar</td>"
            f"<td style='text-align:right; font-size:12px'>{(state.get('last_bar_ts') or '—')[:16]}</td></tr>"
            f"<tr><td style='color:#8B949E'>Status</td>"
            f"<td style='text-align:right; color:{cb_col}; font-weight:600'>{cb}</td></tr>"
            f"</table>"
            f"</div>",
            unsafe_allow_html=True,
        )

# ── Exchange position (independent source of truth) ───────────────────────────
st.markdown(
    "<div class='section-header'>Exchange Position (live from Bybit)</div>",
    unsafe_allow_html=True,
)
ex = exchange_position_snapshot()
if not ex.get("ok"):
    st.error(f"Could not query exchange: {ex.get('error')}")
else:
    if ex["size"] == 0:
        st.markdown(
            f"<div class='kpi-card'><span style='color:{GREEN}; font-weight:700'>● FLAT</span>"
            f" — no open position on testnet.</div>",
            unsafe_allow_html=True,
        )
    else:
        side_col = GREEN if ex["side"] == "Buy" else RED
        st.markdown(
            f"<div class='kpi-card'>"
            f"<span style='color:{side_col}; font-weight:700'>● {ex['side'].upper()} {ex['size']}</span>"
            f" @ mark <strong>${ex['mark_price']:,.2f}</strong>"
            f"</div>",
            unsafe_allow_html=True,
        )

# ── Live trades ───────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Live Trades</div>", unsafe_allow_html=True)
trades_df = load_live_trades()
if trades_df.empty:
    st.info("No closed live trades yet.")
else:
    recent = trades_df.sort_values("exit_ts", ascending=False).head(20).copy()
    recent["Date"] = recent["exit_ts"].dt.strftime("%Y-%m-%d %H:%M UTC")
    recent["Strategy"] = recent["strategy_id"]
    recent["Entry $"] = recent["entry_price"].apply(lambda x: f"${x:,.2f}")
    recent["Exit $"] = recent["exit_price"].apply(lambda x: f"${x:,.2f}")
    recent["P&L"] = recent["net_pnl"].apply(lambda x: f"{'+' if x >= 0 else ''}{x:,.2f}")
    recent["R"] = recent["r_multiple"].apply(lambda x: f"{'+' if x >= 0 else ''}{x:.3f}R")
    recent["Exit"] = recent["exit_reason"]
    st.dataframe(
        recent[["Date", "Strategy", "Entry $", "Exit $", "P&L", "R", "Exit"]].reset_index(drop=True),
        use_container_width=True,
        height=300,
    )

# ── Recent matrix events per strategy ─────────────────────────────────────────
st.markdown("<div class='section-header'>Recent Matrix Events</div>", unsafe_allow_html=True)
ec1, ec2 = st.columns(2)
for col, label, pdir in [
    (ec1, "prev_day_breakdown_v1", PREV_DAY_DIR),
    (ec2, "short_composite_v1", COMPOSITE_DIR),
]:
    with col:
        st.caption(label)
        events = latest_matrix_events(pdir, n=8)
        if not events:
            st.markdown(f"<div style='color:{GREY}'>No events yet.</div>", unsafe_allow_html=True)
            continue
        for ev in reversed(events):
            etype = ev.get("_type", "?")
            ts = ev.get("detected_at") or ev.get("submitted_at") or ev.get("filled_at") or ""
            reason = ev.get("reason_code") or ev.get("detail") or ""
            st.markdown(
                f"<div style='font-size:12px; padding:4px 0; border-bottom:1px solid #21262D'>"
                f"<code>{etype}</code> "
                f"<span style='color:{GREY}'>{ts[:16]}</span><br>"
                f"<span style='color:#E6EDF3'>{reason}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

st.divider()
st.caption(
    "Click RUN at the top of each hour (just after :00) to process the freshly-closed bar. "
    "Each click: fetches latest candles, polls exchange, executes any open live plan, "
    "and submits new entries if a strategy fires. State and trades persist to paper/live/."
)
