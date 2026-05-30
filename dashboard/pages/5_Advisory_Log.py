"""LLM Advisory log page."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from data.loader import load_advisory, load_advisory_log

st.set_page_config(page_title="Advisory Log · Finding Alpha", layout="wide")

from data.source import data_source_selector
data_source_selector()
st_autorefresh(interval=60_000, key="adv_refresh")

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
.adv-card { background:#161B22; border:1px solid #30363D;
    border-radius:8px; padding:16px 20px; margin-bottom:8px; }
</style>""", unsafe_allow_html=True)

st.title("🤖 Advisory Log")

advisory     = load_advisory()
advisory_log = load_advisory_log()

# ── Current advisory ───────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Current Advisory</div>", unsafe_allow_html=True)

POL_COLOURS = {
    "normal":              GREEN,
    "reduce_size":         AMBER,
    "block_new_entries":   RED,
    "close_risk_positions": RED,
}
pol_col = POL_COLOURS.get(advisory["trade_policy"], GREY)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class='adv-card'>
        <div style='color:#8B949E; font-size:11px; text-transform:uppercase'>Policy</div>
        <div style='color:{pol_col}; font-size:22px; font-weight:700; margin-top:4px'>
            {advisory["trade_policy"].upper().replace("_"," ")}</div>
    </div>""", unsafe_allow_html=True)
with c2:
    rs = advisory["risk_scalar"]
    rs_col = GREEN if rs >= 1.0 else (AMBER if rs >= 0.5 else RED)
    st.markdown(f"""<div class='adv-card'>
        <div style='color:#8B949E; font-size:11px; text-transform:uppercase'>Risk Scalar</div>
        <div style='color:{rs_col}; font-size:22px; font-weight:700; margin-top:4px'>
            {rs:.2f}×</div>
    </div>""", unsafe_allow_html=True)
with c3:
    ev = advisory["event_type"]
    ev_col = RED if ev not in ("none", "") else GREY
    st.markdown(f"""<div class='adv-card'>
        <div style='color:#8B949E; font-size:11px; text-transform:uppercase'>Event Type</div>
        <div style='color:{ev_col}; font-size:18px; font-weight:700; margin-top:4px'>
            {ev.upper()}</div>
    </div>""", unsafe_allow_html=True)
with c4:
    hl = advisory["hours_left"]
    exp_col = RED if advisory["is_expired"] else (AMBER if (hl or 99) < 4 else GREEN)
    hl_str  = f"{hl:.1f}h left" if hl is not None else "EXPIRED"
    st.markdown(f"""<div class='adv-card'>
        <div style='color:#8B949E; font-size:11px; text-transform:uppercase'>Validity</div>
        <div style='color:{exp_col}; font-size:18px; font-weight:700; margin-top:4px'>
            {hl_str}</div>
        <div style='color:#8B949E; font-size:12px; margin-top:2px'>
            {advisory["expires_at"][:16].replace("T"," ")} UTC</div>
    </div>""", unsafe_allow_html=True)

if advisory["summary"]:
    st.markdown(f"""
    <div style='background:#161B22; border-left:3px solid {pol_col};
                border-radius:0 8px 8px 0; padding:14px 18px; margin:12px 0;
                color:#E6EDF3; font-size:14px; line-height:1.6;'>
        <span style='color:#8B949E; font-size:11px; text-transform:uppercase;
                     font-weight:600; display:block; margin-bottom:6px'>Summary</span>
        "{advisory["summary"]}"
        <div style='color:#8B949E; font-size:12px; margin-top:8px'>
            Model: {advisory["model_id"]} · Generated: {advisory["as_of"][:16].replace("T"," ")} UTC
        </div>
    </div>""", unsafe_allow_html=True)

if advisory["allowed_strategies"]:
    st.warning(f"**Restricted strategies:** Only {', '.join(advisory['allowed_strategies'])} allowed")
else:
    st.markdown("<span style='color:#8B949E; font-size:13px'>All strategies permitted</span>",
                unsafe_allow_html=True)

if advisory["reason_codes"]:
    st.markdown(f"**Reason codes:** `{'`, `'.join(advisory['reason_codes'])}`")

# ── Advisory history ───────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Advisory History</div>", unsafe_allow_html=True)

if not advisory_log.empty:
    display = advisory_log.copy()

    def fmt_as_of(row):
        if "as_of" in row and row["as_of"] is not None:
            try:
                return str(row["as_of"])[:16].replace("T", " ") + " UTC"
            except Exception:
                pass
        return "—"

    def fmt_policy(row):
        p = row.get("trade_policy", "—")
        return str(p).upper().replace("_", " ")

    def fmt_scalar(row):
        v = row.get("confidence_multiplier")
        if v is None:
            return "—"
        try:
            return f"{float(v):.2f}×"
        except Exception:
            return str(v)

    table_rows = []
    for _, row in display.iterrows():
        table_rows.append({
            "Date (UTC)":  fmt_as_of(row),
            "Policy":      fmt_policy(row),
            "Risk Scalar": fmt_scalar(row),
            "Event":       row.get("event_type", "—"),
            "Model":       row.get("model_id", "—"),
            "Summary":     str(row.get("one_sentence_summary", ""))[:120],
        })

    import pandas as pd
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
else:
    st.info("Advisory log is empty. The advisory runner needs to be scheduled daily (06:00 UTC).")
    st.markdown("""
**To run the advisory manually:**
```bash
python notebooks/phase9_advisory_runner.py
```

**To schedule it in cron (Linux VM):**
```
0 6 * * * cd /home/ubuntu/findingAlpha && python notebooks/phase9_advisory_runner.py
```
    """)

# ── About the advisory ─────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>How the Advisory Works</div>", unsafe_allow_html=True)

st.markdown("""
The LLM advisory is a **daily read-only risk check** powered by Claude. It runs once per day,
reads recent trade performance and market context, and returns a structured decision.

**What the advisory CAN do:**
- Set `trade_policy = normal` → full trading permitted
- Set `trade_policy = reduce_size` → risk_scalar < 1.0 (sizes down positions)
- Set `trade_policy = block_new_entries` → no new entries today
- Restrict to specific strategies via `allowed_strategies`

**What the advisory CANNOT do:**
- Invent new trade signals (hot path is deterministic)
- Override or move stop-loss orders
- Raise risk_scalar above 1.0 (ceiling enforced in code)
- Access live order book or real-time price feeds

**Failure mode:** If the advisory file is missing, malformed, or expired,
the system defaults to `normal / 1.0×` — it never blocks trading due to advisory failure.

**Advisory inputs (as of current build):**
- Recent paper trade R-multiples
- Previous advisory decision

**Planned improvements (Phase 13.5):**
- Current BTC price and ATR %
- Funding rate and open interest
- Trade post-mortem summaries
- Macro calendar events
""")
