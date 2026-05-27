# Bybit Order Semantics Report

Phase 1 deliverable. Documents Bybit USDT linear perpetuals order behavior relevant to simulation and live execution.

---

## Venue

Bybit USDT linear perpetuals — V5 API (`/v5/` endpoints).  
Symbol in scope: `BTCUSDT`.  
Contract type: linear, USDT-margined, perpetual (no expiry).

---

## Order Types Used

| Order Type | Use case | Fill price |
|---|---|---|
| `limit` | Entry | At or better than limit price |
| `stop_market` | Stop loss | Market fill at trigger, subject to slippage |
| `limit` (reduce_only) | Take profit | At or better than limit price |

---

## Fill Semantics

### Limit Entry
- Posted to the book as a maker order.
- Fills when the market trades through the limit price (ask ≤ limit for longs, bid ≥ limit for shorts).
- Fee: maker rate = 0.02% (2 bps).
- In simulation: conservative assumption — long fills when `candle.low ≤ entry_price`, short when `candle.high ≥ entry_price`. Fill price = limit price (no adverse slippage on maker fills).

### Stop Market (Stop Loss)
- Triggered when mark price reaches `trigger_price`.
- Executes as market order after trigger → taker fee applies.
- Fee: taker rate = 0.055% (5.5 bps).
- Slippage modeled at 0.05% (5 bps) adverse on fill vs. trigger price.
- In simulation: long stop fills when `candle.low ≤ stop_price`, fill at `stop_price × (1 - 5 bps)`.

### Take Profit Limit (Reduce-Only)
- Posted as a limit order with `reduce_only=True`.
- Fills when market reaches the TP price.
- Fee: maker rate = 0.02% (2 bps).
- In simulation: long TP fills when `candle.high ≥ tp_price`, fill at `tp_price`.

### Same-Candle Ambiguity
When both stop and TP could have filled within the same bar (candle.low ≤ stop AND candle.high ≥ TP), simulation resolves conservatively — **stop loss wins**. This matches the worst-case fill ordering and avoids overstating performance.

---

## Candle Finality

Bybit kline REST endpoint returns closed candles only when `confirm = true` on the WebSocket feed or when the current timestamp is past the candle's close time.

- **Simulation**: Uses completed historical candles — no look-ahead possible.
- **Live data (Phase 8 note)**: Must verify `confirm` field before processing a bar. Incomplete bars must be ignored.

---

## Funding Rate

- Settled every 8 hours at 00:00, 08:00, 16:00 UTC.
- Rate applied to open notional: `funding_cost = qty × entry_price × funding_rate`.
- Positive rate = longs pay shorts; negative rate = shorts pay longs.
- In simulation: funding accumulated per completed 8-hour period within the hold window.
- Data source: Bybit `/v5/market/funding/history` endpoint.

---

## Open Interest

- Available as 1h snapshots via `/v5/market/open-interest`.
- Used as a regime/context feature (OI delta z-score), not as a trading signal directly.
- Full 6-month history available on Bybit (Binance OI limited to ~30 days).

---

## Leverage and Margin

- Account type: unified margin (UMA) or isolated margin.
- v1 design: isolated margin per symbol, leverage set by `PortfolioConfig.max_leverage` (default 10×).
- Bybit enforces minimum order size: 0.001 BTC (1 lot = 0.001 BTC for BTCUSDT).
- Minimum notional: ~$10 USDT at standard BTC prices.
- Quantity precision: 3 decimal places (0.001 BTC minimum increment).
- Price precision: 2 decimal places ($0.01 per tick).

---

## Fee Summary

| Action | Fee type | Rate |
|---|---|---|
| Limit entry (maker) | Maker | 0.02% |
| Stop loss exit (taker) | Taker | 0.055% |
| TP exit (maker) | Maker | 0.02% |
| Market entry (taker) | Taker | 0.055% |

Round-trip fee on a stop-loss exit: 0.02% + 0.055% = 0.075%.  
Round-trip fee on a TP exit: 0.02% + 0.02% = 0.04%.

---

## Testnet

- Bybit testnet: `testnet.bybit.com` — full V5 API compatibility.
- NautilusTrader Bybit adapter supports testnet via config flag.
- Phase 10 will validate order flow against testnet before live capital.
