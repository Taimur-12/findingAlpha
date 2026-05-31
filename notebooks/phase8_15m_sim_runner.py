"""
15m scalp simulation runner.

Replays historical Bybit 15m data through the paper runtime (same process_final_bar
used in live trading) to backtest ema_scalp_15m_v1.

Usage:
    python notebooks/phase8_15m_sim_runner.py --weeks 8
    python notebooks/phase8_15m_sim_runner.py --weeks 52

Output:
    paper/sim/scalp_15m/state.json
    paper/sim/scalp_15m/trades.jsonl
    paper/sim/scalp_15m/matrix.jsonl
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
_SIM_DIR  = _root / "paper" / "sim" / "scalp_15m"

LOOKBACK_BARS = 300
FUNDING_DAYS  = 14
OI_DAYS       = 14


def _to_ns_utc(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True).astype("datetime64[ns, UTC]")


def _load_candles() -> pd.DataFrame:
    path = _DATA_DIR / "bybit" / "BTCUSDT" / "15m" / "candles.parquet"
    if not path.exists():
        raise FileNotFoundError(
            f"No 15m candle data at {path}.\n"
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
    # Use 1h OI — merge_asof backward-fills onto 15m bars; stale threshold is 2h so this is fine.
    path = _DATA_DIR / "bybit" / "BTCUSDT" / "open_interest_1h.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["venue", "symbol", "timeframe", "ts", "open_interest"])
    df = pd.read_parquet(path)
    df["ts"] = _to_ns_utc(df["ts"])
    return df.sort_values("ts").reset_index(drop=True)


def _funding_window(funding_df: pd.DataFrame, bar_time: pd.Timestamp) -> pd.DataFrame:
    cutoff = bar_time + pd.Timedelta(minutes=15)
    start  = cutoff - pd.Timedelta(days=FUNDING_DAYS)
    mask = (funding_df["funding_time"] >= start) & (funding_df["funding_time"] <= cutoff)
    return funding_df[mask].reset_index(drop=True)


def _oi_window(oi_df: pd.DataFrame, bar_time: pd.Timestamp) -> pd.DataFrame:
    cutoff = bar_time + pd.Timedelta(minutes=15)
    start  = cutoff - pd.Timedelta(days=OI_DAYS)
    mask = (oi_df["ts"] >= start) & (oi_df["ts"] <= cutoff)
    return oi_df[mask].reset_index(drop=True)


def run_simulation(
    all_candles: pd.DataFrame,
    all_funding: pd.DataFrame,
    all_oi: pd.DataFrame,
    sim_start: pd.Timestamp,
    sim_end: pd.Timestamp,
) -> dict:
    _SIM_DIR.mkdir(parents=True, exist_ok=True)

    cfg = PaperRuntimeConfig(
        symbol="BTCUSDT",
        timeframe="15m",
        venue="bybit",
        lookback_bars=LOOKBACK_BARS,
        funding_days=FUNDING_DAYS,
        oi_days=OI_DAYS,
        strategy_id="ema_scalp_15m_v1",
        initial_equity=10_000,
        risk_pct="0.0025",
        max_hold_minutes=120,
        maker_fee_bps="2.0",
        taker_fee_bps="5.5",
        stop_slippage_bps="10",
        qty_precision=3,
        min_notional=10,
        max_leverage=10,
        daily_loss_limit_pct="0.03",
        max_drawdown_pct="0.10",
        paper_dir=_SIM_DIR,
    )

    for p in [cfg.state_path, cfg.trade_log_path, cfg.matrix_log_path]:
        if p.exists():
            p.unlink()

    state  = PaperState()
    matrix = MatrixEventLog(log_path=cfg.matrix_log_path)

    sim_bars = all_candles[
        (all_candles["open_time"] >= sim_start) &
        (all_candles["open_time"] <= sim_end)
    ].reset_index(drop=True)

    if sim_bars.empty:
        print("  No bars in simulation window. Check data availability.")
        return {}

    bars_processed = 0
    trades_closed  = 0

    for _, bar in sim_bars.iterrows():
        bar_time = bar["open_time"]

        # Simulated now: just after 15m bar finalized (15min + 61s grace)
        now = (bar_time + pd.Timedelta(seconds=961)).to_pydatetime()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        buf_mask = all_candles["open_time"] <= bar_time
        buffer   = all_candles[buf_mask].tail(LOOKBACK_BARS + 5).copy()

        funding_win = _funding_window(all_funding, bar_time)
        oi_win      = _oi_window(all_oi, bar_time)

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

    closed: list[dict] = []
    if cfg.trade_log_path.exists():
        with open(cfg.trade_log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    closed.append(json.loads(line))

    wins     = [t for t in closed if float(t["net_pnl"]) > 0]
    win_rate = len(wins) / len(closed) if closed else 0.0
    total_pnl = sum(float(t["net_pnl"]) for t in closed)
    avg_r    = sum(float(t.get("r_multiple", 0)) for t in closed) / len(closed) if closed else 0.0

    pf_wins  = sum(float(t["net_pnl"]) for t in wins)
    losses   = [t for t in closed if float(t["net_pnl"]) <= 0]
    pf_loss  = abs(sum(float(t["net_pnl"]) for t in losses))
    profit_factor = (pf_wins / pf_loss) if pf_loss > 0 else float("inf")

    exit_counts: dict[str, int] = {}
    for t in closed:
        r = t.get("exit_reason", "unknown")
        exit_counts[r] = exit_counts.get(r, 0) + 1

    return {
        "strategy_id": "ema_scalp_15m_v1",
        "sim_start": sim_start.isoformat(),
        "sim_end": sim_end.isoformat(),
        "bars_processed": bars_processed,
        "trades_closed": trades_closed,
        "win_rate": win_rate,
        "avg_r": avg_r,
        "profit_factor": profit_factor,
        "total_pnl": total_pnl,
        "final_equity": float(state.equity),
        "exit_breakdown": exit_counts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="15m scalp simulation runner")
    parser.add_argument("--weeks", type=int, default=8, help="Simulation window in weeks")
    args = parser.parse_args()

    print(f"Loading 15m data...")
    all_candles = _load_candles()
    all_funding = _load_funding()
    all_oi      = _load_oi()

    sim_end   = pd.Timestamp(all_candles["open_time"].max())
    sim_start = sim_end - pd.Timedelta(weeks=args.weeks)

    print(f"Running ema_scalp_15m_v1 | {args.weeks} weeks | "
          f"{sim_start.date()} to {sim_end.date()}")
    print(f"Total 15m bars available: {len(all_candles):,}")

    result = run_simulation(all_candles, all_funding, all_oi, sim_start, sim_end)

    if result:
        print()
        print("=" * 55)
        print("  15M SCALP SIM RESULTS")
        print("=" * 55)
        print(f"  Bars processed : {result['bars_processed']:,}")
        print(f"  Trades closed  : {result['trades_closed']}")
        print(f"  Win rate       : {result['win_rate']:.1%}")
        print(f"  Avg R          : {result['avg_r']:+.3f}")
        print(f"  Profit factor  : {result['profit_factor']:.2f}")
        print(f"  Net P&L        : {result['total_pnl']:+.2f} USDT")
        print(f"  Final equity   : {result['final_equity']:,.2f} USDT")
        print(f"  Exit breakdown : {result['exit_breakdown']}")
        print(f"  Output dir     : paper/sim/scalp_15m/")
        print("=" * 55)


if __name__ == "__main__":
    main()
