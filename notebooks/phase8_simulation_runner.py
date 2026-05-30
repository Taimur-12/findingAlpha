"""
Phase 8 simulation runner.

Replays historical Bybit 1h data through the exact same paper runtime code
(process_final_bar) used in live paper trading. Results go to paper/sim/ and
paper/sim/composite/ so they never overwrite live paper state.

Purpose:
  - Confirm the paper runtime code behaves correctly (stop/TP/fill logic, state persistence)
  - Generate a trades.jsonl and equity curve to inspect before starting live observation
  - Verify signal frequency and behavior match backtest assumptions

Usage:
    python notebooks/phase8_simulation_runner.py --weeks 8
    python notebooks/phase8_simulation_runner.py --weeks 8 --strategy prev_day_breakdown_v1
    python notebooks/phase8_simulation_runner.py --weeks 8 --strategy short_composite_v1
    python notebooks/phase8_simulation_runner.py --weeks 8 --both   (default)

Output:
    paper/sim/state.json               -- prev_day_breakdown_v1 final state
    paper/sim/trades.jsonl             -- closed trades
    paper/sim/matrix.jsonl             -- full event log
    paper/sim/composite/state.json     -- short_composite_v1 final state
    paper/sim/composite/trades.jsonl
    paper/sim/composite/matrix.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

_root = Path(__file__).resolve().parent.parent
if str(_root / "src") not in sys.path:
    sys.path.insert(0, str(_root / "src"))

from finding_alpha.matrix.event_log import MatrixEventLog
from finding_alpha.paper.runtime import PaperRuntimeConfig, process_final_bar
from finding_alpha.paper.state import PaperState, append_trade_log, load_state, save_state

_DATA_DIR = _root / "data"
_SIM_DIR = _root / "paper" / "sim"
_SIM_COMPOSITE_DIR = _root / "paper" / "sim" / "composite"

LOOKBACK_BARS = 300
FUNDING_DAYS = 14
OI_DAYS = 14


def _to_ns_utc(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True).astype("datetime64[ns, UTC]")


def _load_candles() -> pd.DataFrame:
    path = _DATA_DIR / "bybit" / "BTCUSDT" / "1h" / "candles.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"No candle data at {path}.\n"
            "Run: FINDING_ALPHA_FETCH_DAYS=1095 python notebooks/phase7b_fetch_extended_bybit.py"
        )
    df = pd.read_parquet(path)
    df["open_time"] = _to_ns_utc(df["open_time"])
    return df.sort_values("open_time").reset_index(drop=True)


def _load_funding() -> pd.DataFrame:
    path = _DATA_DIR / "bybit" / "BTCUSDT" / "funding.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["venue", "symbol", "funding_time", "funding_rate"])
    df = pd.read_parquet(path)
    df["funding_time"] = _to_ns_utc(df["funding_time"])
    return df.sort_values("funding_time").reset_index(drop=True)


def _load_oi() -> pd.DataFrame:
    path = _DATA_DIR / "bybit" / "BTCUSDT" / "open_interest_1h.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["venue", "symbol", "timeframe", "ts", "open_interest"])
    df = pd.read_parquet(path)
    df["ts"] = _to_ns_utc(df["ts"])
    return df.sort_values("ts").reset_index(drop=True)


def _funding_window(funding_df: pd.DataFrame, bar_time: pd.Timestamp) -> pd.DataFrame:
    cutoff = bar_time + pd.Timedelta(hours=1)
    start = cutoff - pd.Timedelta(days=FUNDING_DAYS)
    mask = (funding_df["funding_time"] >= start) & (funding_df["funding_time"] <= cutoff)
    return funding_df[mask].reset_index(drop=True)


def _oi_window(oi_df: pd.DataFrame, bar_time: pd.Timestamp) -> pd.DataFrame:
    cutoff = bar_time + pd.Timedelta(hours=1)
    start = cutoff - pd.Timedelta(days=OI_DAYS)
    mask = (oi_df["ts"] >= start) & (oi_df["ts"] <= cutoff)
    return oi_df[mask].reset_index(drop=True)


def run_simulation(
    strategy_id: str,
    sim_dir: Path,
    all_candles: pd.DataFrame,
    all_funding: pd.DataFrame,
    all_oi: pd.DataFrame,
    sim_start: pd.Timestamp,
    sim_end: pd.Timestamp,
) -> dict:
    sim_dir.mkdir(parents=True, exist_ok=True)

    cfg = PaperRuntimeConfig(
        symbol="BTCUSDT",
        timeframe="1h",
        venue="bybit",
        lookback_bars=LOOKBACK_BARS,
        funding_days=FUNDING_DAYS,
        oi_days=OI_DAYS,
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
        paper_dir=sim_dir,
    )

    # Delete any existing sim state for clean run
    for p in [cfg.state_path, cfg.trade_log_path, cfg.matrix_log_path]:
        if p.exists():
            p.unlink()

    state = PaperState()
    matrix = MatrixEventLog(log_path=cfg.matrix_log_path)

    # All bars in simulation window
    sim_bars = all_candles[
        (all_candles["open_time"] >= sim_start) &
        (all_candles["open_time"] <= sim_end)
    ].reset_index(drop=True)

    if sim_bars.empty:
        print(f"  [{strategy_id}] No bars in simulation window. Check data availability.")
        return {}

    bars_processed = 0
    trades_closed = 0

    for _, bar in sim_bars.iterrows():
        bar_time = bar["open_time"]

        # Simulated "now": just after bar finalized (bar close + 61s grace)
        now = (bar_time + pd.Timedelta(seconds=3661)).to_pydatetime()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # Rolling candle buffer: last LOOKBACK_BARS up to and including this bar
        buf_mask = all_candles["open_time"] <= bar_time
        buffer = all_candles[buf_mask].tail(LOOKBACK_BARS + 5).copy()

        funding_win = _funding_window(all_funding, bar_time)
        oi_win = _oi_window(all_oi, bar_time)

        trade = process_final_bar(
            bar=bar,
            state=state,
            candle_buffer=buffer,
            funding_df=funding_win,
            oi_df=oi_win,
            matrix=matrix,
            cfg=cfg,
            now=now,
            is_catchup=False,
        )

        if trade is not None:
            append_trade_log(trade, cfg.trade_log_path)
            trades_closed += 1

        bars_processed += 1

    save_state(state, cfg.state_path)

    # Load trades for summary
    closed: list[dict] = []
    if cfg.trade_log_path.exists():
        with open(cfg.trade_log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    closed.append(json.loads(line))

    wins = [t for t in closed if float(t["net_pnl"]) > 0]
    win_rate = len(wins) / len(closed) if closed else 0.0
    total_pnl = sum(float(t["net_pnl"]) for t in closed)
    avg_r = sum(float(t.get("r_multiple", 0)) for t in closed) / len(closed) if closed else 0.0
    exit_counts: dict[str, int] = {}
    for t in closed:
        r = t.get("exit_reason", "unknown")
        exit_counts[r] = exit_counts.get(r, 0) + 1

    return {
        "strategy_id": strategy_id,
        "sim_start": sim_start.isoformat(),
        "sim_end": sim_end.isoformat(),
        "bars_processed": bars_processed,
        "trades_closed": trades_closed,
        "win_rate": win_rate,
        "avg_r": avg_r,
        "total_pnl": total_pnl,
        "final_equity": float(state.equity),
        "peak_equity": float(state.peak_equity),
        "max_drawdown_pct": float((state.peak_equity - state.equity) / state.peak_equity * 100) if state.peak_equity > 0 else 0.0,
        "exit_counts": exit_counts,
        "circuit_breaker": state.circuit_breaker_active,
    }


def _print_summary(result: dict) -> None:
    sid = result.get("strategy_id", "?")
    print()
    print("=" * 60)
    print(f"  SIMULATION RESULT — {sid}")
    print("=" * 60)
    print(f"  Period:         {result['sim_start'][:10]} → {result['sim_end'][:10]}")
    print(f"  Bars processed: {result['bars_processed']}")
    print(f"  Trades:         {result['trades_closed']}")
    print(f"  Win rate:       {result['win_rate']:.1%}")
    print(f"  Avg R:          {result['avg_r']:+.3f}")
    print(f"  Net PnL:        {result['total_pnl']:+.2f} USDT")
    print(f"  Final equity:   {result['final_equity']:.2f} USDT")
    print(f"  Peak equity:    {result['peak_equity']:.2f} USDT")
    print(f"  Max drawdown:   {result['max_drawdown_pct']:.2f}%")
    print(f"  Circuit breaker:{result['circuit_breaker']}")
    ec = result.get("exit_counts", {})
    if ec:
        print(f"  Exit breakdown: {ec}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 8 simulation runner (historical replay)")
    parser.add_argument("--weeks", type=int, default=8, help="How many weeks of history to simulate (default 8)")
    parser.add_argument("--strategy", type=str, default=None, help="Run one strategy only (prev_day_breakdown_v1 or short_composite_v1)")
    parser.add_argument("--both", action="store_true", default=True, help="Run both strategies (default)")
    args = parser.parse_args()

    print(f"Loading historical data from {_DATA_DIR} ...")
    all_candles = _load_candles()
    all_funding = _load_funding()
    all_oi = _load_oi()

    last_bar_time = all_candles["open_time"].max()
    sim_end = last_bar_time
    sim_start = sim_end - pd.Timedelta(weeks=args.weeks)

    print(f"Simulation window: {sim_start.date()} → {sim_end.date()} ({args.weeks} weeks)")
    print(f"Total candles available: {len(all_candles)}")
    print(f"Candles in window: {len(all_candles[(all_candles['open_time'] >= sim_start) & (all_candles['open_time'] <= sim_end)])}")
    print()

    strategies_to_run: list[tuple[str, Path]] = []

    if args.strategy == "prev_day_breakdown_v1":
        strategies_to_run = [("prev_day_breakdown_v1", _SIM_DIR)]
    elif args.strategy == "short_composite_v1":
        strategies_to_run = [("short_composite_v1", _SIM_COMPOSITE_DIR)]
    else:
        strategies_to_run = [
            ("prev_day_breakdown_v1", _SIM_DIR),
            ("short_composite_v1", _SIM_COMPOSITE_DIR),
        ]

    results = []
    for strategy_id, sim_dir in strategies_to_run:
        print(f"Running simulation: {strategy_id} → {sim_dir}")
        result = run_simulation(
            strategy_id=strategy_id,
            sim_dir=sim_dir,
            all_candles=all_candles,
            all_funding=all_funding,
            all_oi=all_oi,
            sim_start=sim_start,
            sim_end=sim_end,
        )
        if result:
            results.append(result)
            _print_summary(result)

    print()
    print("Simulation complete.")
    print(f"  prev_day_breakdown_v1 results: {_SIM_DIR}")
    print(f"  short_composite_v1 results:    {_SIM_COMPOSITE_DIR}")
    print()
    print("Compare these results to the backtest expectations in docs/current/phase8_paper_observation_guide.md")
    print("If behavior looks correct, proceed to live paper trading with the cron setup.")


if __name__ == "__main__":
    main()
