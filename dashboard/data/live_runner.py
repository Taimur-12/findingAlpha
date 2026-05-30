"""
Live-mode trading helper for the dashboard.

Wraps `run_once` with a per-strategy `PaperRuntimeConfig` pointed at
`paper/live/...` so a Streamlit button can trigger a real testnet cycle
without touching `paper/sim/`.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from finding_alpha.execution.bybit_client import BybitClient, BybitClientConfig
from finding_alpha.paper.live_execution import query_position_state
from finding_alpha.paper.runtime import PaperRuntimeConfig, run_once

LIVE_DIR = ROOT / "paper" / "live"
PREV_DAY_DIR = LIVE_DIR
COMPOSITE_DIR = LIVE_DIR / "composite"

STRATEGIES = [
    ("prev_day_breakdown_v1", PREV_DAY_DIR),
    ("short_composite_v1", COMPOSITE_DIR),
]


def _build_cfg(strategy_id: str, paper_dir: Path) -> PaperRuntimeConfig:
    return PaperRuntimeConfig(
        symbol="BTCUSDT",
        timeframe="1h",
        venue="bybit",
        lookback_bars=300,
        funding_days=14,
        oi_days=14,
        strategy_id=strategy_id,
        initial_equity=10_000,
        risk_pct="0.0025",
        max_hold_minutes=720,
        maker_fee_bps="2.0",
        taker_fee_bps="5.5",
        stop_slippage_bps="10",
        qty_precision=3,
        min_notional=10,
        max_leverage=10,
        daily_loss_limit_pct="0.03",
        max_drawdown_pct="0.10",
        paper_dir=paper_dir,
        execution_mode="live",
    )


def env_ready() -> tuple[bool, str]:
    """Return (ok, message) describing whether testnet keys are loadable."""
    load_dotenv(ROOT / ".env", override=False)
    try:
        cfg = BybitClientConfig.from_env()
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    if "testnet" not in cfg.base_url:
        return False, f"BYBIT_LIVE_MODE points to {cfg.base_url}, not testnet"
    return True, f"testnet keys loaded ({cfg.base_url})"


def run_cycle() -> list[dict]:
    """Run a live cycle for both strategies. Returns one result dict per strategy."""
    load_dotenv(ROOT / ".env", override=False)
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    COMPOSITE_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for sid, pdir in STRATEGIES:
        cfg = _build_cfg(sid, pdir)
        try:
            result = run_once(cfg)
            result["strategy_id"] = sid
            result["ok"] = True
        except Exception as exc:
            result = {
                "strategy_id": sid,
                "ok": False,
                "status": "exception",
                "error": f"{type(exc).__name__}: {exc}",
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        results.append(result)
    return results


def _read_jsonl_tail(path: Path, n: int) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows[-n:]


def load_live_state(strategy_dir: Path) -> dict:
    state_path = strategy_dir / "state.json"
    if not state_path.exists():
        return {"exists": False}
    with open(state_path, encoding="utf-8") as f:
        raw = json.load(f)
    return {
        "exists": True,
        "equity": float(Decimal(str(raw.get("equity", "10000")))),
        "peak_equity": float(Decimal(str(raw.get("peak_equity", "10000")))),
        "last_bar_ts": raw.get("last_processed_bar_ts", ""),
        "open_position": raw.get("open_position"),
        "pending_entry": raw.get("pending_entry"),
        "live_plan_ref": raw.get("live_plan_ref"),
        "circuit_breaker": raw.get("circuit_breaker_active", False),
    }


def load_live_trades() -> pd.DataFrame:
    rows: list[dict] = []
    for _sid, pdir in STRATEGIES:
        p = pdir / "trades.jsonl"
        if p.exists():
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for col in ("entry_price", "exit_price", "quantity", "gross_pnl",
                "total_fees", "net_pnl", "initial_risk_amount", "r_multiple"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "entry_ts" in df.columns:
        df["entry_ts"] = pd.to_datetime(df["entry_ts"], utc=True)
    if "exit_ts" in df.columns:
        df["exit_ts"] = pd.to_datetime(df["exit_ts"], utc=True)
    if "exit_ts" in df.columns:
        df.sort_values("exit_ts", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def latest_matrix_events(strategy_dir: Path, n: int = 8) -> list[dict]:
    return _read_jsonl_tail(strategy_dir / "matrix.jsonl", n)


def exchange_position_snapshot(symbol: str = "BTCUSDT") -> dict:
    """Independently query Bybit testnet for current position. Returns size/side/mark."""
    load_dotenv(ROOT / ".env", override=False)
    try:
        client = BybitClient(BybitClientConfig.from_env())
        size, side, mark = query_position_state(client, symbol)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": True,
        "size": float(size),
        "side": side or "flat",
        "mark_price": float(mark) if mark is not None else None,
    }
