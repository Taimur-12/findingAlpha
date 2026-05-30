"""Live status page — system health, position card, market context, advisory."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from data.loader import (
    load_advisory,
    load_both_states,
    load_market_context,
    system_health,
)

st.set_page_config(page_title="Live Status · Finding Alpha", layout="wide")

from data.source import data_source_selector
data_source_selector()
st_autorefresh(interval=30_000, key="status_refresh")

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
.status-card { background:#161B22; border:1px solid #30363D;
    border-radius:8px; padding:16px 20px; margin-bottom:8px; }
.pos-card { background:#161B22; border-radius:8px; padding:18px 22px; }
</style>""", unsafe_allow_html=True)

st.title("🟢 Live Status")

s1, s2   = load_both_states()
advisory = load_advisory()
market   = load_market_context()
health   = system_health(s1, s2, advisory)
now      = datetime.now(timezone.utc)

# ── Data freshness banner ──────────────────────────────────────────────────────
stale_h = health["runner1_stale_h"] or health["runner2_stale_h"]
if stale_h and stale_h > 2:
    days = stale_h / 24
    st.warning(
        f"⚠ Market data is **{days:.1f} days stale** (last bar: {s2['last_bar_ts'][:10]}). "
        f"The market context below reflects conditions as of that timestamp, not current live prices. "
        f"Start the cron job or cloud deployment to get live data."
    )

# ── System Health Panel ────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>System Health</div>", unsafe_allow_html=True)

STATUS_DOT = {
    "ok":       (GREEN, "● RUNNING"),
    "warning":  (AMBER, "● WARNING"),
    "stale":    (RED,   "● STALE"),
    "offline":  (GREY,  "● OFFLINE"),
    "expired":  (RED,   "● EXPIRED"),
    "expiring": (AMBER, "● EXPIRING"),
}

def health_row(label: str, status: str, detail: str) -> str:
    """Single-line HTML — no leading whitespace or blank lines to confuse the Markdown parser."""
    colour, dot_label = STATUS_DOT.get(status, (GREY, "● UNKNOWN"))
    return (
        f"<div style='display:flex;justify-content:space-between;align-items:center;"
        f"padding:10px 0;border-bottom:1px solid #21262D;'>"
        f"<span style='color:#E6EDF3;font-weight:500'>{label}</span>"
        f"<span><span style='color:{colour};font-weight:600'>{dot_label}</span>"
        f"<span style='color:#8B949E;font-size:13px;margin-left:12px'>{detail}</span>"
        f"</span></div>"
    )

def stale_str(hours):
    if hours is None:
        return "never seen"
    if hours < 1:
        return f"{int(hours*60)}m ago"
    return f"{hours:.1f}h ago"

runner1_detail = f"prev_day_breakdown_v1 — last bar {stale_str(health['runner1_stale_h'])}"
runner2_detail = f"short_composite_v1 — last bar {stale_str(health['runner2_stale_h'])}"

adv_hl = health["advisory_hours_left"]
if adv_hl is not None:
    adv_detail = f"Expires in {adv_hl:.1f}h"
elif health["advisory_status"] == "expired":
    adv_detail = "EXPIRED — advisory not current"
else:
    adv_detail = "No advisory file"

circuit_str = "TRIPPED — no new entries" if health["circuit_breaker"] else "Inactive"
circuit_status = "stale" if health["circuit_breaker"] else "ok"

# Build entire card as one compact string — blank lines inside an unsafe_allow_html block
# cause the Markdown parser to exit HTML mode and render subsequent tags as plain text.
_rows = (
    health_row("Runner 1 (prev_day)", health["runner1_status"], runner1_detail)
    + health_row("Runner 2 (composite)", health["runner2_status"], runner2_detail)
    + health_row("LLM Advisory", health["advisory_status"], adv_detail)
    + health_row("Circuit Breaker", circuit_status, circuit_str)
)
st.markdown(
    f"<div class='status-card'>{_rows}</div>",
    unsafe_allow_html=True,
)

# ── Circuit breaker banner ─────────────────────────────────────────────────────
if health["circuit_breaker"]:
    st.error("⚠ CIRCUIT BREAKER ACTIVE — Daily loss limit reached. No new trades until reset.")

# ── Position Cards ─────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Open Positions</div>", unsafe_allow_html=True)

pc1, pc2 = st.columns(2)

def render_position_card(col, state: dict, label: str, colour: str) -> None:
    pos = state.get("open_position") or state.get("pending_entry")
    with col:
        if pos is None:
            st.markdown(f"""
            <div class='pos-card' style='border:1px solid #30363D; text-align:center; min-height:160px;'>
                <div style='color:{colour}; font-weight:700; margin-bottom:12px'>{label}</div>
                <div style='color:#8B949E; font-size:22px; margin:24px 0'>NO OPEN POSITION</div>
                <div style='color:#6E7681; font-size:13px'>Strategy slot: AVAILABLE</div>
            </div>""", unsafe_allow_html=True)
        else:
            entry_p = pos.get("entry_price", pos.get("limit_price", "?"))
            stop_p  = pos.get("stop_price", "?")
            tp_p    = pos.get("target_price", "?")
            side    = pos.get("side", "?").upper()
            qty     = pos.get("quantity", "?")
            entry_ts = pos.get("entry_ts", pos.get("filled_at", ""))[:16].replace("T", " ")

            border_col = GREEN if side == "LONG" else RED
            st.markdown(f"""
            <div class='pos-card' style='border:1px solid {border_col}55;'>
                <div style='color:{colour}; font-weight:700; margin-bottom:10px'>{label}</div>
                <div style='color:{border_col}; font-size:18px; font-weight:700'>
                    {side} BTCUSDT</div>
                <table style='width:100%; font-size:13px; margin-top:10px; border-collapse:collapse'>
                    <tr><td style='color:#8B949E; padding:2px 0'>Entry</td>
                        <td style='text-align:right'>${float(entry_p):,.2f} — {entry_ts} UTC</td></tr>
                    <tr><td style='color:#8B949E; padding:2px 0'>Stop loss</td>
                        <td style='text-align:right; color:{RED}'>${float(stop_p):,.2f}</td></tr>
                    <tr><td style='color:#8B949E; padding:2px 0'>Take profit</td>
                        <td style='text-align:right; color:{GREEN}'>${float(tp_p):,.2f}</td></tr>
                    <tr><td style='color:#8B949E; padding:2px 0'>Quantity</td>
                        <td style='text-align:right'>{qty} BTC</td></tr>
                </table>
            </div>""", unsafe_allow_html=True)

render_position_card(pc1, s1, "prev_day_breakdown_v1", BLUE)
render_position_card(pc2, s2, "short_composite_v1", PURPLE)

# ── Market Context ─────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Market Context — BTCUSDT 1H</div>", unsafe_allow_html=True)

if market["ts"]:
    ts_str = market["ts"][:16].replace("T", " ") + " UTC"
else:
    ts_str = "No data"

REGIME_COLOURS = {
    "trend_up":         GREEN,
    "trend_down":       RED,
    "range":            BLUE,
    "breakout_pending": AMBER,
    "high_volatility":  AMBER,
    "crisis":           RED,
    "unknown":          GREY,
}
reg_colour = REGIME_COLOURS.get(market["regime"], GREY)
conf_pct   = market["regime_confidence"] * 100

mc1, mc2 = st.columns(2)

with mc1:
    close   = market["close"]
    ema20   = market["ema_20"]
    ema50   = market["ema_50"]
    ema200  = market["ema_200"]
    rsi14   = market["rsi_14"]
    adx14   = market["adx_14"]
    atr14   = market["atr_14"]
    atr_pct = market["atr_percentile"]
    fund    = market["funding_rate"]
    fund_z  = market["funding_z_score"]
    vol_z   = market["volume_z_score"]

    def fmt(v, prefix="", suffix="", decimals=2):
        if v is None:
            return "—"
        return f"{prefix}{v:,.{decimals}f}{suffix}"

    def fmt_pct(v, decimals=4):
        """Format a raw decimal funding/rate as a percentage string."""
        if v is None:
            return "—"
        return f"{v * 100:.{decimals}f}%"

    def ema_stack():
        if close and ema20 and ema50 and ema200:
            if close < ema20 < ema50 < ema200:
                return f"<span style='color:{RED}'>bearish (20 &lt; 50 &lt; 200)</span>"
            if close > ema20 > ema50 > ema200:
                return f"<span style='color:{GREEN}'>bullish (20 &gt; 50 &gt; 200)</span>"
        return "<span style='color:#8B949E'>mixed</span>"

    atr_pct_str = f"p{atr_pct:.0f}" if atr_pct is not None else "—"

    st.markdown(f"""
    <div class='status-card'>
        <div style='margin-bottom:6px; color:#8B949E; font-size:12px'>As of {ts_str}</div>
        <table style='width:100%; border-collapse:collapse; font-size:14px'>
            <tr><td style='color:#8B949E; padding:4px 0'>Regime</td>
                <td style='text-align:right'>
                    <span style='color:{reg_colour}; font-weight:700'>{market["regime"]}</span>
                    <span style='color:#8B949E; font-size:12px'> ({conf_pct:.0f}% conf)</span></td></tr>
            <tr><td style='color:#8B949E; padding:4px 0'>Price</td>
                <td style='text-align:right; font-weight:600'>{fmt(close, "$")}</td></tr>
            <tr><td style='color:#8B949E; padding:4px 0'>EMA stack</td>
                <td style='text-align:right'>{ema_stack()}</td></tr>
            <tr><td style='color:#8B949E; padding:4px 0'>RSI (14)</td>
                <td style='text-align:right'>{fmt(rsi14, decimals=1)}</td></tr>
            <tr><td style='color:#8B949E; padding:4px 0'>ADX (14)</td>
                <td style='text-align:right'>{fmt(adx14, decimals=1)}</td></tr>
            <tr><td style='color:#8B949E; padding:4px 0'>ATR (14)</td>
                <td style='text-align:right'>{fmt(atr14, "$")} ({atr_pct_str})</td></tr>
            <tr><td style='color:#8B949E; padding:4px 0'>Funding rate</td>
                <td style='text-align:right'>{fmt_pct(fund)} (z={fmt(fund_z,"","",2)})</td></tr>
            <tr><td style='color:#8B949E; padding:4px 0'>Volume z-score</td>
                <td style='text-align:right'>{fmt(vol_z,"","",2)}</td></tr>
        </table>
    </div>""", unsafe_allow_html=True)

# ── LLM Advisory Detail ────────────────────────────────────────────────────────
with mc2:
    st.markdown("<div class='section-header'>LLM Advisory</div>", unsafe_allow_html=True)

    pol = advisory["trade_policy"]
    POL_COLOURS = {"normal": GREEN, "reduce_size": AMBER,
                   "block_new_entries": RED, "close_risk_positions": RED}
    pol_col = POL_COLOURS.get(pol, GREY)

    adv_exp_col = RED if advisory["is_expired"] else (
        AMBER if (advisory["hours_left"] or 99) < 4 else GREEN
    )
    expires_str = advisory["expires_at"][:16].replace("T", " ") + " UTC" if advisory["expires_at"] else "—"

    st.markdown(f"""
    <div class='status-card'>
        <table style='width:100%; border-collapse:collapse; font-size:14px'>
            <tr><td style='color:#8B949E; padding:4px 0'>Policy</td>
                <td style='text-align:right; color:{pol_col}; font-weight:700'>
                    {pol.upper().replace("_"," ")}</td></tr>
            <tr><td style='color:#8B949E; padding:4px 0'>Risk scalar</td>
                <td style='text-align:right; font-weight:600'>
                    {advisory["risk_scalar"]:.2f}×</td></tr>
            <tr><td style='color:#8B949E; padding:4px 0'>Event type</td>
                <td style='text-align:right'>{advisory["event_type"]}</td></tr>
            <tr><td style='color:#8B949E; padding:4px 0'>Generated</td>
                <td style='text-align:right'>{advisory["as_of"][:16].replace("T"," ")} UTC</td></tr>
            <tr><td style='color:#8B949E; padding:4px 0'>Expires</td>
                <td style='text-align:right; color:{adv_exp_col}'>{expires_str}</td></tr>
            <tr><td style='color:#8B949E; padding:4px 0'>Model</td>
                <td style='text-align:right; font-size:12px'>{advisory["model_id"]}</td></tr>
        </table>
        <div style='margin-top:12px; padding:10px; background:#0D1117; border-radius:6px;
                    color:#E6EDF3; font-size:13px; font-style:italic; line-height:1.5'>
            "{advisory["summary"] or "No summary available."}"
        </div>
    </div>""", unsafe_allow_html=True)

    if advisory["reason_codes"]:
        st.markdown(f"**Reason codes:** {', '.join(advisory['reason_codes'])}")
    if advisory["allowed_strategies"]:
        st.markdown(f"**Allowed strategies:** {', '.join(advisory['allowed_strategies'])}")
    else:
        st.markdown("<span style='color:#8B949E; font-size:13px'>All strategies allowed</span>",
                    unsafe_allow_html=True)
