"""
Load historical Parquet candles into a MatrixEventLog as CandleEvent objects.

Used to create a replay-ready event stream for backtesting in Phase 4+.
"""

from decimal import Decimal
from pathlib import Path

import pandas as pd

from finding_alpha.contracts import CandleEvent
from finding_alpha.matrix import MatrixEventLog
from .storage import load_candles


def load_candles_to_matrix(
    base_dir: Path,
    venue: str,
    symbol: str,
    timeframe: str,
    log: MatrixEventLog | None = None,
) -> MatrixEventLog:
    """Read a Parquet candle file and append every row as a CandleEvent.

    If log is None a fresh MatrixEventLog (in-memory only) is created.
    Returns the populated log.
    """
    if log is None:
        log = MatrixEventLog()

    df = load_candles(base_dir, venue, symbol, timeframe)

    for _, row in df.iterrows():
        event = CandleEvent(
            venue=str(row["venue"]),
            symbol=str(row["symbol"]),
            timeframe=str(row["timeframe"]),
            open_time=pd.Timestamp(row["open_time"]).to_pydatetime(),
            close_time=pd.Timestamp(row["close_time"]).to_pydatetime(),
            open=Decimal(str(row["open"])),
            high=Decimal(str(row["high"])),
            low=Decimal(str(row["low"])),
            close=Decimal(str(row["close"])),
            volume=Decimal(str(row["volume"])),
            quote_volume=Decimal(str(row["quote_volume"])),
            is_final=bool(row["is_final"]),
        )
        log.append(event)

    return log
