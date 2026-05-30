"""Full trade log with filters and export."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from data.loader import load_trades, trade_metrics

st.set_page_config(page_title="Trade Log · Finding Alpha", layout="wide")

from data.source import data_source_selector
data_source_selector()

GREEN  = "#3FB950"
RED    = "#F85149"
AMBER  = "#D29922"
BLUE   = "#58A6FF"
PURPLE = "#BC8CFF"
GREY   = "#6E7681"

st.markdown("""
<style>
.section-header { color:#8B949E; font-size:11px; font-weight:600;
    letter-spacing:.1em; text-transform:uppercase;
    margin:24px 0 8px 0; border-bottom:1px solid #30363D; padding-bottom:6px; }
</style>""", unsafe_allow_html=True)

st.title("📋 Trade Log")

trades_df = load_trades()

if trades_df.empty:
    st.info("No completed trades yet.")
    st.stop()

# ── Filters ────────────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Filters</div>", unsafe_allow_html=True)

f1, f2, f3, f4 = st.columns(4)

with f1:
    strategies = ["All"] + sorted(trades_df["strategy_id"].unique().tolist())
    sel_strat  = st.selectbox("Strategy", strategies)

with f2:
    exit_reasons = ["All"] + sorted(trades_df["exit_reason"].unique().tolist())
    sel_exit     = st.selectbox("Exit reason", exit_reasons)

with f3:
    sel_result = st.selectbox("Result", ["All", "Wins only", "Losses only"])

with f4:
    min_date = trades_df["entry_ts"].dt.date.min()
    max_date = trades_df["entry_ts"].dt.date.max()
    date_range = st.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

# Apply filters
filtered = trades_df.copy()

if sel_strat != "All":
    filtered = filtered[filtered["strategy_id"] == sel_strat]

if sel_exit != "All":
    filtered = filtered[filtered["exit_reason"] == sel_exit]

if sel_result == "Wins only":
    filtered = filtered[filtered["is_win"]]
elif sel_result == "Losses only":
    filtered = filtered[~filtered["is_win"]]

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_d, end_d = date_range
    filtered = filtered[
        (filtered["entry_ts"].dt.date >= start_d) &
        (filtered["entry_ts"].dt.date <= end_d)
    ]

# ── Filtered summary ───────────────────────────────────────────────────────────
m = trade_metrics(filtered)

s1, s2, s3, s4, s5 = st.columns(5)
s1.metric("Trades",         f"{m['count']}")
s2.metric("Win Rate",       f"{m['win_rate']:.1f}%" if m["count"] else "—")
s3.metric("Expectancy",     f"{m['expectancy_r']:+.3f}R" if m["count"] else "—")
s4.metric("Net P&L",        f"${m['net_pnl']:+,.2f}" if m["count"] else "—")
s5.metric("Total Fees",     f"${m['total_fees']:,.2f}" if m["count"] else "—")

# ── Trade table ────────────────────────────────────────────────────────────────
st.markdown(f"<div class='section-header'>Trades ({len(filtered)} shown)</div>",
            unsafe_allow_html=True)

if filtered.empty:
    st.info("No trades match the current filters.")
else:
    display = filtered.sort_values("exit_ts", ascending=False).copy()

    display["#"]         = range(len(display), 0, -1)
    display["Entry Time"] = display["entry_ts"].dt.strftime("%Y-%m-%d %H:%M")
    display["Exit Time"]  = display["exit_ts"].dt.strftime("%Y-%m-%d %H:%M")
    display["Strategy"]   = display["strategy_id"]
    display["Side"]       = display["side"].str.upper()
    display["Entry $"]    = display["entry_price"].apply(lambda x: f"${x:,.2f}")
    display["Exit $"]     = display["exit_price"].apply(lambda x: f"${x:,.2f}")
    display["Qty"]        = display["quantity"].apply(lambda x: f"{x:.3f}")
    display["Gross P&L"]  = display["gross_pnl"].apply(lambda x: f"${x:+,.2f}")
    display["Fees"]       = display["total_fees"].apply(lambda x: f"${x:,.2f}")
    display["Net P&L"]    = display["net_pnl"].apply(lambda x: f"${x:+,.2f}")
    display["R"]          = display["r_multiple"].apply(lambda x: f"{x:+.3f}")
    display["Hold (h)"]   = display["hold_hours"].apply(lambda x: f"{x:.1f}")
    display["Exit"]       = display["exit_reason"]
    display["Result"]     = display["is_win"].apply(lambda w: "✓ WIN" if w else "✗ LOSS")

    cols = ["#", "Entry Time", "Exit Time", "Strategy", "Side",
            "Entry $", "Exit $", "Qty", "Gross P&L", "Fees",
            "Net P&L", "R", "Hold (h)", "Exit", "Result"]

    st.dataframe(
        display[cols].reset_index(drop=True),
        use_container_width=True,
        height=500,
        column_config={
            "#":        st.column_config.NumberColumn(width="small"),
            "Result":   st.column_config.TextColumn(width="small"),
            "R":        st.column_config.TextColumn(width="small"),
            "Hold (h)": st.column_config.TextColumn(width="small"),
        },
    )

    # ── CSV export ─────────────────────────────────────────────────────────────
    st.markdown("<div class='section-header'>Export</div>", unsafe_allow_html=True)
    export_df = filtered[[
        "entry_ts", "exit_ts", "strategy_id", "symbol", "side",
        "entry_price", "exit_price", "quantity",
        "gross_pnl", "total_fees", "net_pnl",
        "initial_risk_amount", "r_multiple", "exit_reason",
    ]].copy()
    export_df["entry_ts"] = export_df["entry_ts"].dt.strftime("%Y-%m-%d %H:%M:%S")
    export_df["exit_ts"]  = export_df["exit_ts"].dt.strftime("%Y-%m-%d %H:%M:%S")

    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download CSV",
        data=csv_bytes,
        file_name="finding_alpha_trades.csv",
        mime="text/csv",
    )

    # ── Per-trade detail expander ──────────────────────────────────────────────
    st.markdown("<div class='section-header'>Trade Detail Inspector</div>",
                unsafe_allow_html=True)
    st.caption("Select a trade index to inspect full details.")

    idx = st.number_input(
        "Trade # (from table above)",
        min_value=1,
        max_value=len(filtered),
        value=1,
        step=1,
    )
    row = filtered.sort_values("exit_ts", ascending=False).iloc[idx - 1]

    pnl_col = GREEN if row["net_pnl"] >= 0 else RED
    sign    = "+" if row["net_pnl"] >= 0 else ""

    st.markdown(f"""
    <div style='background:#161B22; border:1px solid #30363D; border-radius:8px;
                padding:18px 22px; font-size:14px;'>
        <div style='font-size:16px; font-weight:700; margin-bottom:12px; color:#E6EDF3'>
            Trade #{idx} — {row["strategy_id"]}
            <span style='color:{pnl_col}; margin-left:12px'>{sign}${row["net_pnl"]:,.2f}
                ({row["r_multiple"]:+.3f}R)</span>
        </div>
        <table style='width:100%; border-collapse:collapse'>
            <tr><td style='color:#8B949E; padding:4px 8px 4px 0; width:40%'>Signal ID</td>
                <td style='font-family:monospace; font-size:12px'>{row["signal_id"]}</td></tr>
            <tr><td style='color:#8B949E; padding:4px 8px 4px 0'>Symbol / Side</td>
                <td>{row["symbol"]} {row["side"].upper()}</td></tr>
            <tr><td style='color:#8B949E; padding:4px 8px 4px 0'>Entry</td>
                <td>${float(row["entry_price"]):,.2f} at {str(row["entry_ts"])[:16]} UTC</td></tr>
            <tr><td style='color:#8B949E; padding:4px 8px 4px 0'>Exit</td>
                <td>${float(row["exit_price"]):,.2f} at {str(row["exit_ts"])[:16]} UTC</td></tr>
            <tr><td style='color:#8B949E; padding:4px 8px 4px 0'>Quantity</td>
                <td>{float(row["quantity"]):.4f} BTC</td></tr>
            <tr><td style='color:#8B949E; padding:4px 8px 4px 0'>Hold time</td>
                <td>{row["hold_hours"]:.1f} hours</td></tr>
            <tr><td style='color:#8B949E; padding:4px 8px 4px 0'>Gross P&L</td>
                <td>${float(row["gross_pnl"]):+,.2f}</td></tr>
            <tr><td style='color:#8B949E; padding:4px 8px 4px 0'>Fees</td>
                <td>-${float(row["total_fees"]):,.2f}</td></tr>
            <tr><td style='color:#8B949E; padding:4px 8px 4px 0'>Net P&L</td>
                <td style='color:{pnl_col}; font-weight:600'>{sign}${float(row["net_pnl"]):,.2f}</td></tr>
            <tr><td style='color:#8B949E; padding:4px 8px 4px 0'>Risk at entry</td>
                <td>${float(row["initial_risk_amount"]):,.2f}</td></tr>
            <tr><td style='color:#8B949E; padding:4px 8px 4px 0'>R multiple</td>
                <td style='color:{pnl_col}; font-weight:600'>{float(row["r_multiple"]):+.3f}R</td></tr>
            <tr><td style='color:#8B949E; padding:4px 8px 4px 0'>Exit reason</td>
                <td>{row["exit_reason"]}</td></tr>
        </table>
    </div>""", unsafe_allow_html=True)
