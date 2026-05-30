"""
Data loader for the Finding Alpha dashboard.
All functions return plain dicts / DataFrames — no domain types leak into the UI layer.
Paths are relative to the project root (parent of dashboard/).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

import pandas as pd

# ── Project root ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]

PREV_DAY_STATE   = ROOT / "paper/sim/state.json"
COMPOSITE_STATE  = ROOT / "paper/sim/composite/state.json"
PREV_DAY_TRADES  = ROOT / "paper/sim/trades.jsonl"
COMPOSITE_TRADES = ROOT / "paper/sim/composite/trades.jsonl"
PREV_DAY_MATRIX  = ROOT / "paper/sim/matrix.jsonl"
COMPOSITE_MATRIX = ROOT / "paper/sim/composite/matrix.jsonl"
ADVISORY_PATH    = ROOT / "advisory.json"
ADVISORY_LOG     = ROOT / "paper/advisory_log.jsonl"

STARTING_CAPITAL = Decimal("10000")
STRATEGY_LABELS  = {
    "prev_day_breakdown_v1": "prev_day_breakdown_v1",
    "short_composite_v1":    "short_composite_v1",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(json.loads(line))
    return lines


def _read_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _dec(val) -> float:
    return float(Decimal(str(val)))


# ── State ─────────────────────────────────────────────────────────────────────

def load_state(path: Path) -> dict:
    raw = _read_json(path) or {}
    return {
        "equity":               _dec(raw.get("equity", STARTING_CAPITAL)),
        "peak_equity":          _dec(raw.get("peak_equity", STARTING_CAPITAL)),
        "daily_start_equity":   _dec(raw.get("daily_start_equity", STARTING_CAPITAL)),
        "daily_date":           raw.get("daily_date", ""),
        "open_position":        raw.get("open_position"),
        "pending_entry":        raw.get("pending_entry"),
        "last_bar_ts":          raw.get("last_processed_bar_ts", ""),
        "circuit_breaker":      raw.get("circuit_breaker_active", False),
    }


def load_both_states() -> tuple[dict, dict]:
    return load_state(PREV_DAY_STATE), load_state(COMPOSITE_STATE)


def combined_equity(s1: dict, s2: dict) -> float:
    """Sum of both strategy equities (they each start at STARTING_CAPITAL)."""
    return s1["equity"] + s2["equity"]


def combined_starting() -> float:
    return float(STARTING_CAPITAL) * 2


# ── Trades ────────────────────────────────────────────────────────────────────

def load_trades() -> pd.DataFrame:
    rows = []
    for path in (PREV_DAY_TRADES, COMPOSITE_TRADES):
        rows.extend(_read_jsonl(path))
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Numeric coercions
    for col in ("entry_price", "exit_price", "quantity", "gross_pnl",
                "total_fees", "net_pnl", "initial_risk_amount", "r_multiple"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Timestamps
    df["entry_ts"] = pd.to_datetime(df["entry_ts"], utc=True)
    df["exit_ts"]  = pd.to_datetime(df["exit_ts"],  utc=True)

    # Derived columns
    df["hold_hours"] = (df["exit_ts"] - df["entry_ts"]).dt.total_seconds() / 3600
    df["is_win"]     = df["net_pnl"] > 0

    df.sort_values("exit_ts", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def build_equity_curve(df: pd.DataFrame, starting: float = 10000.0) -> pd.DataFrame:
    """Build per-strategy and combined equity curves from trade history."""
    if df.empty:
        return pd.DataFrame()

    curves = []
    for sid, group in df.groupby("strategy_id", sort=False):
        g = group.sort_values("exit_ts").copy()
        g["cumulative_pnl"] = g["net_pnl"].cumsum()
        g["equity"]         = starting + g["cumulative_pnl"]
        g["strategy"]       = sid
        curves.append(g[["exit_ts", "equity", "strategy"]])

    # Combined (sum both strategies starting from 2×starting)
    combined = df.sort_values("exit_ts").copy()
    combined["cumulative_pnl"] = combined["net_pnl"].cumsum()
    combined["equity"]         = float(STARTING_CAPITAL) * 2 + combined["cumulative_pnl"]
    combined["strategy"]       = "combined"
    curves.append(combined[["exit_ts", "equity", "strategy"]])

    return pd.concat(curves, ignore_index=True)


def trade_metrics(df: pd.DataFrame) -> dict:
    """Compute summary metrics for a trade DataFrame."""
    if df.empty:
        return {
            "count": 0, "win_rate": 0.0, "expectancy_r": 0.0,
            "profit_factor": 0.0, "net_pnl": 0.0, "total_fees": 0.0,
            "avg_hold_hours": 0.0, "max_r_win": 0.0, "max_r_loss": 0.0,
        }
    wins  = df[df["is_win"]]
    loses = df[~df["is_win"]]
    gross_wins  = wins["gross_pnl"].sum()
    gross_loses = abs(loses["gross_pnl"].sum())
    return {
        "count":          len(df),
        "win_rate":       len(wins) / len(df) * 100,
        "expectancy_r":   df["r_multiple"].mean(),
        "profit_factor":  gross_wins / gross_loses if gross_loses > 0 else float("inf"),
        "net_pnl":        df["net_pnl"].sum(),
        "total_fees":     df["total_fees"].sum(),
        "avg_hold_hours": df["hold_hours"].mean(),
        "max_r_win":      df["r_multiple"].max(),
        "max_r_loss":     df["r_multiple"].min(),
    }


def drawdown_series(equity: pd.Series) -> pd.Series:
    """Return drawdown % from rolling peak for each equity value."""
    rolling_peak = equity.cummax()
    return (equity - rolling_peak) / rolling_peak * 100


# ── Advisory ──────────────────────────────────────────────────────────────────

def load_advisory() -> dict:
    raw = _read_json(ADVISORY_PATH) or {}
    now = datetime.now(timezone.utc)

    expires_str = raw.get("expires_at", "")
    expires_dt  = None
    if expires_str:
        try:
            expires_dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
        except ValueError:
            pass

    is_expired = (expires_dt is None) or (expires_dt <= now)
    hours_left = None
    if expires_dt and not is_expired:
        hours_left = (expires_dt - now).total_seconds() / 3600

    return {
        "exists":           bool(raw),
        "is_expired":       is_expired,
        "hours_left":       hours_left,
        "as_of":            raw.get("as_of", ""),
        "expires_at":       expires_str,
        "trade_policy":     raw.get("trade_policy", "normal"),
        "risk_scalar":      float(raw.get("confidence_multiplier", 1.0)),
        "summary":          raw.get("one_sentence_summary", ""),
        "event_type":       raw.get("event_type", "none"),
        "severity":         float(raw.get("severity", 0)),
        "allowed_strategies": raw.get("allowed_strategies", []),
        "reason_codes":     raw.get("reason_codes", []),
        "model_id":         raw.get("model_id", ""),
    }


def load_advisory_log() -> pd.DataFrame:
    rows = _read_jsonl(ADVISORY_LOG)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "as_of" in df.columns:
        df["as_of"] = pd.to_datetime(df["as_of"], utc=True, errors="coerce")
    if "expires_at" in df.columns:
        df["expires_at"] = pd.to_datetime(df["expires_at"], utc=True, errors="coerce")
    if "confidence_multiplier" in df.columns:
        df["confidence_multiplier"] = pd.to_numeric(df["confidence_multiplier"], errors="coerce")
    return df.sort_values("as_of", ascending=False).reset_index(drop=True) if "as_of" in df.columns else df


# ── Market context from matrix ────────────────────────────────────────────────

def load_market_context() -> dict:
    """Return the latest FeatureSnapshot and RegimeState from composite matrix."""
    last_snap   = None
    last_regime = None

    for path in (COMPOSITE_MATRIX, PREV_DAY_MATRIX):
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = d.get("_type", "")
                if t == "FeatureSnapshot":
                    last_snap = d
                elif t == "RegimeState":
                    last_regime = d
        break  # composite has both; no need for fallback usually

    snap = last_snap or {}
    reg  = last_regime or {}

    def fval(key, default=None):
        v = snap.get(key, default)
        try:
            return float(v) if v is not None else default
        except (TypeError, ValueError):
            return default

    return {
        "regime":           reg.get("regime", "unknown"),
        "regime_confidence": float(reg.get("confidence", 0)),
        "regime_ts":        reg.get("classified_at", ""),
        "close":            fval("close"),
        "ema_20":           fval("ema_20"),
        "ema_50":           fval("ema_50"),
        "ema_200":          fval("ema_200"),
        "rsi_14":           fval("rsi_14"),
        "adx_14":           fval("adx_14"),
        "atr_14":           fval("atr_14"),
        "atr_percentile":   fval("atr_percentile"),
        "bb_bandwidth":     fval("bb_bandwidth"),
        "bb_bandwidth_percentile": fval("bb_bandwidth_percentile"),
        "volume_z_score":   fval("volume_z_score"),
        "funding_rate":     fval("funding_rate"),
        "funding_z_score":  fval("funding_z_score"),
        "oi_z_score":       fval("oi_z_score"),
        "ts":               snap.get("ts", ""),
    }


# ── System health ─────────────────────────────────────────────────────────────

def system_health(s1: dict, s2: dict, advisory: dict) -> dict:
    now = datetime.now(timezone.utc)

    def staleness_hours(bar_ts_str: str) -> Optional[float]:
        if not bar_ts_str:
            return None
        try:
            ts = datetime.fromisoformat(bar_ts_str.replace("Z", "+00:00"))
            return (now - ts).total_seconds() / 3600
        except ValueError:
            return None

    stale1 = staleness_hours(s1["last_bar_ts"])
    stale2 = staleness_hours(s2["last_bar_ts"])

    def status(hours):
        if hours is None:
            return "offline"
        if hours > 4:
            return "stale"
        if hours > 2:
            return "warning"
        return "ok"

    adv_status = "expired" if advisory["is_expired"] else (
        "expiring" if (advisory["hours_left"] or 99) < 2 else "ok"
    )

    return {
        "runner1_stale_h":  stale1,
        "runner1_status":   status(stale1),
        "runner2_stale_h":  stale2,
        "runner2_status":   status(stale2),
        "advisory_status":  adv_status,
        "advisory_hours_left": advisory["hours_left"],
        "circuit_breaker":  s1["circuit_breaker"] or s2["circuit_breaker"],
    }
