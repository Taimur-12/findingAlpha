"""
Phase 8 paper trading runner.

Usage:
    # Run once (check for new bars, process, exit):
    python notebooks/phase8_paper_runner.py --once

    # Poll continuously every 60 seconds (default):
    python notebooks/phase8_paper_runner.py

    # Custom poll interval:
    python notebooks/phase8_paper_runner.py --poll 120

    # Print current paper status without processing:
    python notebooks/phase8_paper_runner.py --status

All paper data is written to the paper/ directory under the project root:
    paper/state.json      — current account state
    paper/trades.jsonl    — append-only closed trade log
    paper/matrix.jsonl    — full Matrix event audit log

Frozen Phase 8 parameters (do not change during observation period):
    strategy:  prev_day_breakdown_v1
    symbol:    BTCUSDT
    timeframe: 1h
    risk/trade: 0.25%
    max_hold:  12h
    stop:      entry + 0.75 ATR
    target:    entry - 4.5 ATR
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure the package is importable when run as a script
_root = Path(__file__).resolve().parent.parent
if str(_root / "src") not in sys.path:
    sys.path.insert(0, str(_root / "src"))

from finding_alpha.paper.runtime import PaperRuntimeConfig, run_loop, run_once
from finding_alpha.paper.state import load_state

# ── Config (frozen for Phase 8 observation period) ────────────────────────────

PAPER_DIR = _root / "paper"

cfg = PaperRuntimeConfig(
    symbol="BTCUSDT",
    timeframe="1h",
    venue="bybit",
    lookback_bars=300,
    funding_days=14,
    oi_days=14,
    initial_equity=10_000,          # simulated 10 000 USDT
    risk_pct="0.0025",              # 0.25% per trade
    max_hold_minutes=720,           # 12h
    maker_fee_bps="2.0",
    taker_fee_bps="5.5",
    stop_slippage_bps="10",
    qty_precision=3,
    min_notional=10,
    max_leverage=10,
    daily_loss_limit_pct="0.03",
    max_drawdown_pct="0.10",
    paper_dir=PAPER_DIR,
)


# ── Status printer ─────────────────────────────────────────────────────────────

def print_status() -> None:
    state = load_state(cfg.state_path)
    trade_log = cfg.trade_log_path

    closed_trades: list[dict] = []
    if trade_log.exists():
        with open(trade_log, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    closed_trades.append(json.loads(line))

    wins = [t for t in closed_trades if float(t["net_pnl"]) > 0]
    win_rate = len(wins) / len(closed_trades) if closed_trades else 0.0
    total_pnl = sum(float(t["net_pnl"]) for t in closed_trades)

    print("=" * 60)
    print("  PHASE 8 PAPER STATUS")
    print("=" * 60)
    print(f"  As of:          {datetime.now(timezone.utc).isoformat()}")
    print(f"  Equity:         {state.equity} USDT")
    print(f"  Peak equity:    {state.peak_equity} USDT")
    drawdown = (state.peak_equity - state.equity) / state.peak_equity * 100 if state.peak_equity > 0 else 0
    print(f"  Drawdown:       {drawdown:.2f}%")
    print(f"  Total trades:   {len(closed_trades)}")
    print(f"  Win rate:       {win_rate:.1%}")
    print(f"  Net PnL:        {total_pnl:+.2f} USDT")
    print()
    if state.has_open_position():
        pos = state.open_position
        print(f"  OPEN POSITION: {pos.side} {pos.symbol}")
        print(f"    Entry:  {pos.entry_price}  Stop: {pos.stop_price}  Target: {pos.target_price}")
        print(f"    Qty:    {pos.quantity}  Notional: {pos.notional}")
        print(f"    Entry at: {pos.entry_ts.isoformat()}")
        print(f"    Expires:  {pos.max_exit_ts.isoformat()}")
    elif state.has_pending_entry():
        pe = state.pending_entry
        print(f"  PENDING ENTRY: {pe.side} @ {pe.entry_price}")
        print(f"    Signal bar: {pe.signal_bar_open_time.isoformat()}")
    else:
        print("  Position: flat")
    print()
    print(f"  Last bar processed: {state.last_processed_bar_ts}")
    print(f"  Circuit breaker:    {state.circuit_breaker_active}")
    print("=" * 60)

    if closed_trades:
        print()
        print("  RECENT TRADES (last 5):")
        for t in closed_trades[-5:]:
            r = float(t.get("r_multiple", 0))
            pnl = float(t["net_pnl"])
            print(f"    {t['exit_ts'][:19]}  {t['exit_reason']:15s}  R={r:+.2f}  PnL={pnl:+.2f}")


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 8 paper trading runner")
    parser.add_argument("--once", action="store_true", help="Run one pass and exit")
    parser.add_argument("--status", action="store_true", help="Print current status and exit")
    parser.add_argument("--poll", type=int, default=60, help="Poll interval in seconds (default 60)")
    args = parser.parse_args()

    if args.status:
        print_status()
        return

    if args.once:
        now = datetime.now(timezone.utc)
        result = run_once(cfg, now=now)
        print(json.dumps(result, indent=2, default=str))
        print()
        print_status()
        return

    run_loop(cfg, poll_seconds=args.poll)


if __name__ == "__main__":
    main()
