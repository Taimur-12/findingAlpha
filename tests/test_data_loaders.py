"""
Phase 3 data layer tests.

Covers: loader parsing, normalizer, quality checks, storage round-trip, replay.
HTTP calls are mocked — no live network required.
"""

import json
import tempfile
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from finding_alpha.data.normalizer import normalize_candles, normalize_funding, normalize_open_interest
from finding_alpha.data.quality import check_candles
from finding_alpha.data.storage import save_candles, load_candles, save_funding, load_funding
from finding_alpha.data.replay_loader import load_candles_to_matrix


# ── Helpers ────────────────────────────────────────────────────────────────────

START = datetime(2025, 11, 1, 0, 0, 0, tzinfo=timezone.utc)
END = datetime(2025, 11, 1, 1, 0, 0, tzinfo=timezone.utc)


def _bybit_klines_response(candles: list) -> dict:
    return {"retCode": 0, "retMsg": "OK", "result": {"category": "linear", "symbol": "BTCUSDT", "list": candles}}


def _binance_klines_response(candles: list) -> list:
    return candles


def _make_mock_http(json_return):
    mock_resp = MagicMock()
    mock_resp.json.return_value = json_return
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def _make_candles_df(venue: str = "bybit") -> pd.DataFrame:
    """Build a minimal normalised candle DataFrame."""
    now = pd.Timestamp("2025-11-01 00:00:00", tz="UTC")
    rows = []
    for i in range(4):
        t = now + pd.Timedelta(minutes=15 * i)
        rows.append({
            "venue": venue,
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "open_time": t,
            "close_time": t + pd.Timedelta(minutes=15) - pd.Timedelta(milliseconds=1),
            "open": "70000",
            "high": "70100",
            "low": "69900",
            "close": "70050",
            "volume": "5.5",
            "quote_volume": "385000",
            "is_final": True,
        })
    return pd.DataFrame(rows)


# ── Bybit loader (mocked HTTP) ─────────────────────────────────────────────────

class TestBybitLoader:
    def test_fetch_candles_parses_response(self):
        # 4 candles in reverse order (newest first)
        # Timestamps: 2025-11-01 00:45, 00:30, 00:15, 00:00 UTC
        raw_candles = [
            ["1761957900000", "70100", "70200", "70050", "70150", "5.5", "385825"],
            ["1761957000000", "70000", "70100", "69950", "70100", "4.2", "294000"],
            ["1761956100000", "69900", "70000", "69850", "70000", "6.1", "427000"],
            ["1761955200000", "69800", "69900", "69750", "69900", "3.8", "266220"],
        ]

        # oldest_ts == start_ms → loop breaks after a single page
        resp = _make_mock_http(_bybit_klines_response(raw_candles))

        with patch("finding_alpha.data.bybit_loader.httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            instance.get.return_value = resp

            from finding_alpha.data.bybit_loader import fetch_candles
            df = fetch_candles("BTCUSDT", "15m", START, END)

        # Should be sorted ascending
        assert df["open_time"].is_monotonic_increasing
        assert df["venue"].iloc[0] == "bybit"
        assert df["symbol"].iloc[0] == "BTCUSDT"
        assert df["timeframe"].iloc[0] == "15m"
        assert df["is_final"].all()
        # Price values preserved as strings
        assert isinstance(df["close"].iloc[0], str)

    def test_fetch_candles_returns_empty_on_no_data(self):
        empty_resp = _make_mock_http(_bybit_klines_response([]))

        with patch("finding_alpha.data.bybit_loader.httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            instance.get.return_value = empty_resp

            from finding_alpha.data.bybit_loader import fetch_candles
            df = fetch_candles("BTCUSDT", "15m", START, END)

        assert df.empty

    def test_fetch_candles_rejects_unknown_timeframe(self):
        from finding_alpha.data.bybit_loader import fetch_candles
        with pytest.raises(ValueError):
            fetch_candles("BTCUSDT", "5m", START, END)

    def test_fetch_funding_parses_response(self):
        raw = [
            {"symbol": "BTCUSDT", "fundingRate": "0.0001", "fundingRateTimestamp": "1730415900000"},
            {"symbol": "BTCUSDT", "fundingRate": "-0.0002", "fundingRateTimestamp": "1730386800000"},
        ]
        resp = _make_mock_http({"retCode": 0, "retMsg": "OK", "result": {"list": raw}})
        empty = _make_mock_http({"retCode": 0, "retMsg": "OK", "result": {"list": []}})

        with patch("finding_alpha.data.bybit_loader.httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            instance.get.side_effect = [resp, empty]

            from finding_alpha.data.bybit_loader import fetch_funding
            df = fetch_funding("BTCUSDT", START, END)

        assert list(df.columns) == ["venue", "symbol", "funding_time", "funding_rate"]
        assert df["venue"].iloc[0] == "bybit"
        assert df["funding_time"].is_monotonic_increasing


# ── Binance loader (mocked HTTP) ───────────────────────────────────────────────

class TestBinanceLoader:
    def test_fetch_candles_parses_response(self):
        # Binance returns chronological order
        # Timestamps: 2025-11-01 00:00 and 00:15 UTC
        raw = [
            [1761955200000, "69800", "69900", "69750", "69900", "3.8",
             1761956099999, "266220", 150, "1.9", "133110", "0"],
            [1761956100000, "69900", "70000", "69850", "70000", "6.1",
             1761956999999, "427000", 200, "3.0", "210000", "0"],
        ]
        resp = _make_mock_http(raw)

        with patch("finding_alpha.data.binance_loader.httpx.Client") as MockClient:
            instance = MockClient.return_value.__enter__.return_value
            # Fewer than 1500 rows → loop stops after first page
            instance.get.return_value = resp

            from finding_alpha.data.binance_loader import fetch_candles
            df = fetch_candles("BTCUSDT", "15m", START, END)

        assert df["venue"].iloc[0] == "binance"
        assert df["open_time"].is_monotonic_increasing
        assert df["is_final"].all()
        assert isinstance(df["close"].iloc[0], str)

    def test_fetch_candles_rejects_unknown_timeframe(self):
        from finding_alpha.data.binance_loader import fetch_candles
        with pytest.raises(ValueError):
            fetch_candles("BTCUSDT", "5m", START, END)


# ── Normalizer ─────────────────────────────────────────────────────────────────

class TestNormalizer:
    def test_normalize_candles_preserves_rows(self):
        df = _make_candles_df()
        result = normalize_candles(df)
        assert len(result) == 4
        assert list(result.columns) == [
            "venue", "symbol", "timeframe", "open_time", "close_time",
            "open", "high", "low", "close", "volume", "quote_volume", "is_final",
        ]

    def test_normalize_candles_removes_duplicates(self):
        df = _make_candles_df()
        # Add a duplicate row
        dup = df.iloc[[0]].copy()
        df = pd.concat([df, dup], ignore_index=True)
        result = normalize_candles(df)
        assert len(result) == 4  # duplicate removed

    def test_normalize_candles_sorts_ascending(self):
        df = _make_candles_df()
        df = df.iloc[::-1].reset_index(drop=True)  # reverse order
        result = normalize_candles(df)
        assert result["open_time"].is_monotonic_increasing

    def test_normalize_candles_empty_df(self):
        from finding_alpha.data.normalizer import CANDLE_COLUMNS
        df = pd.DataFrame(columns=CANDLE_COLUMNS)
        result = normalize_candles(df)
        assert result.empty

    def test_normalize_funding(self):
        rows = [
            {"venue": "bybit", "symbol": "BTCUSDT",
             "funding_time": pd.Timestamp("2025-11-01 08:00:00", tz="UTC"),
             "funding_rate": "0.0001"},
            {"venue": "bybit", "symbol": "BTCUSDT",
             "funding_time": pd.Timestamp("2025-11-01 00:00:00", tz="UTC"),
             "funding_rate": "-0.0002"},
        ]
        df = pd.DataFrame(rows)
        result = normalize_funding(df)
        assert result["funding_time"].is_monotonic_increasing
        assert isinstance(result["funding_rate"].iloc[0], str)


# ── Quality checks ─────────────────────────────────────────────────────────────

class TestQuality:
    def test_no_issues_on_clean_data(self):
        df = _make_candles_df()
        report = check_candles(df, "15m")
        assert report["total_candles"] == 4
        assert report["gap_count"] == 0
        assert report["total_missing"] == 0
        assert report["duplicate_times"] == []
        assert report["zero_volume_times"] == []

    def test_detects_gap(self):
        df = _make_candles_df()
        # Remove the second candle → gap of 2 intervals
        df = df.drop(index=1).reset_index(drop=True)
        report = check_candles(df, "15m")
        assert report["gap_count"] == 1
        assert report["gaps"][0]["missing_candles"] == 1

    def test_detects_duplicate(self):
        df = _make_candles_df()
        dup = df.iloc[[0]].copy()
        df = pd.concat([df, dup], ignore_index=True)
        report = check_candles(df, "15m")
        assert len(report["duplicate_times"]) == 1

    def test_detects_zero_volume(self):
        df = _make_candles_df()
        df.loc[2, "volume"] = "0"
        report = check_candles(df, "15m")
        assert len(report["zero_volume_times"]) == 1

    def test_empty_df_returns_zeros(self):
        df = pd.DataFrame()
        report = check_candles(df, "15m")
        assert report["total_candles"] == 0
        assert report["gaps"] == []

    def test_rejects_unknown_timeframe(self):
        df = _make_candles_df()
        with pytest.raises(ValueError):
            check_candles(df, "5m")


# ── Storage round-trip ─────────────────────────────────────────────────────────

class TestStorage:
    def test_save_and_load_candles(self):
        df = _make_candles_df()
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            path = save_candles(df, base, "bybit", "BTCUSDT", "15m")
            assert path.exists()
            loaded = load_candles(base, "bybit", "BTCUSDT", "15m")
            assert len(loaded) == 4
            assert loaded["symbol"].iloc[0] == "BTCUSDT"

    def test_metadata_written(self):
        df = _make_candles_df()
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            save_candles(df, base, "bybit", "BTCUSDT", "15m", {"quality": {"gap_count": 0}})
            meta_path = base / "bybit" / "BTCUSDT" / "15m" / "metadata.json"
            assert meta_path.exists()
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            assert meta["total_candles"] == 4
            assert meta["quality"]["gap_count"] == 0

    def test_load_missing_raises(self):
        from finding_alpha.data.storage import load_candles
        with pytest.raises(FileNotFoundError):
            load_candles(Path("/nonexistent"), "bybit", "BTCUSDT", "15m")

    def test_save_and_load_funding(self):
        rows = [
            {"venue": "bybit", "symbol": "BTCUSDT",
             "funding_time": pd.Timestamp("2025-11-01 00:00:00", tz="UTC"),
             "funding_rate": "0.0001"},
        ]
        df = pd.DataFrame(rows)
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            save_funding(df, base, "bybit", "BTCUSDT")
            loaded = load_funding(base, "bybit", "BTCUSDT")
            assert len(loaded) == 1
            assert loaded["funding_rate"].iloc[0] == "0.0001"


# ── Replay loader ──────────────────────────────────────────────────────────────

class TestReplayLoader:
    def test_candles_become_events_in_matrix(self):
        df = _make_candles_df()
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            save_candles(df, base, "bybit", "BTCUSDT", "15m")
            log = load_candles_to_matrix(base, "bybit", "BTCUSDT", "15m")

        assert log.event_count() == 4
        latest = log.latest_candle("bybit", "BTCUSDT", "15m")
        assert latest is not None
        assert latest.close == Decimal("70050")
        assert latest.is_final is True

    def test_replay_uses_existing_log(self):
        from finding_alpha.matrix import MatrixEventLog
        df = _make_candles_df()
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            save_candles(df, base, "bybit", "BTCUSDT", "15m")
            existing_log = MatrixEventLog()
            log = load_candles_to_matrix(base, "bybit", "BTCUSDT", "15m", log=existing_log)
        assert log is existing_log
        assert log.event_count() == 4
