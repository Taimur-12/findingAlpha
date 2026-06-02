# Phase 3 — Data Quality Report

Generated: 2026-05-27  
Data range: 2025-11-28 to 2026-05-27 (approx. 6 months)

---

## Dataset Summary

| Venue | Symbol | Timeframe | Rows | Date range |
|---|---|---|---|---|
| Bybit | BTCUSDT | 1h | 4,321 | 2025-11-28 to 2026-05-27 |
| Bybit | BTCUSDT | 15m | 17,246 | 2025-11-28 to 2026-05-27 |
| Bybit | BTCUSDT | funding | 541 | 2025-11-28 to 2026-05-27 |
| Bybit | BTCUSDT | OI (1h) | 4,321 | 2025-11-28 to 2026-05-27 |
| Binance | BTCUSDT | 1h | ~4,320 | 2025-11-28 to 2026-05-27 |
| Binance | BTCUSDT | 15m | ~17,240 | 2025-11-28 to 2026-05-27 |
| Binance | BTCUSDT | funding | ~541 | 2025-11-28 to 2026-05-27 |
| Binance | BTCUSDT | OI (1h) | ~720 | Last ~30 days only |

---

## Bybit 1h Candles — Quality Check

Quality check run via `check_candles(candles_1h, "1h")` from `finding_alpha.data.quality`:

| Check | Result |
|---|---|
| Gap count | **0** |
| Duplicate timestamps | **0** |
| Zero-volume bars | **0** |

**Conclusion**: Bybit 1h candle data is complete with no gaps, no duplicates, and no zero-volume bars across the full 6-month dataset. Suitable for production-quality backtesting.

---

## Known Data Limitations

### Binance OI History Cap
Binance `/fapi/v1/openInterestHist` endpoint retains only approximately 30 days of open interest history. The `startTime` parameter is rejected — pagination must be done backward using `endTime` only.

**Impact**: Binance OI data is limited to the most recent ~30 days. This data is used as a cross-venue reference feature only. Bybit OI (full 6 months) is the primary OI source.

### Funding Rate Cadence
Bybit funding settles every 8 hours. The 541 rows in the funding dataset represent 8-hour settlements from 2025-11-28 to 2026-05-27. This is the expected count for a 6-month period (182 days × 3 settlements/day ≈ 546 rows, slightly less accounting for exact start/end alignment).

### Candle Finality (Live Data Note)
Historical candles fetched via REST are always complete. In live trading (Phase 8), the Bybit WebSocket `confirm` field must be checked before processing a candle. Unconfirmed (in-progress) candles must be ignored to prevent look-ahead.

---

## Normalization Applied

All candle data is normalized to a standard schema before storage:
- `open_time`: UTC datetime, timezone-aware
- `open`, `high`, `low`, `close`: stored as Decimal strings, coerced to float for computation
- `volume`: float
- Venue and symbol fields added to every row

Funding data normalized to:
- `funding_time`: UTC datetime
- `funding_rate`: float

OI data normalized to:
- `open_time`: UTC datetime
- `open_interest_value`: float (USDT-denominated)

---

## Storage Format

Data stored as Parquet files under `data/` (gitignored):

```
data/bybit/BTCUSDT/1h/candles.parquet
data/bybit/BTCUSDT/15m/candles.parquet
data/bybit/BTCUSDT/funding.parquet
data/bybit/BTCUSDT/open_interest_1h.parquet
data/binance/BTCUSDT/1h/candles.parquet
data/binance/BTCUSDT/15m/candles.parquet
data/binance/BTCUSDT/funding.parquet
data/binance/BTCUSDT/open_interest_1h.parquet
```

Each directory contains a `metadata.json` with fetch timestamp and row count.

---

## Re-fetch Instructions

To update the dataset to the current date:

```bash
conda activate finding_alpha
python notebooks/phase3_fetch_data.py
```

The script fetches from the last stored timestamp forward, appending new rows.
