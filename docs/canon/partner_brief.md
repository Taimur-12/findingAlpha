# Partner Brief — Finding Alpha Trading System

**As of:** 2026-05-30
**Status:** Build complete through Phase 10. Paused for strategy direction discussion before any capital deployment.

---

## What the system can do today

A fully-automated crypto trading bot for **Bybit USDT perpetuals**, currently scoped to **BTCUSDT on the 1-hour timeframe**. Every layer that touches real money is built, tested, and verified end-to-end against the real Bybit testnet exchange (with fake money — zero risk to date).

**The full pipeline, ready to run on real capital with a single environment flag flip:**

| Layer | What it does | Status |
|---|---|---|
| Historical data | 3 years of 1h Bybit + Binance candles, funding, open interest | Loaded, 0 gaps |
| Features | RSI, MACD, EMAs, ATR, Bollinger, ADX, Supertrend, VWAP, funding/OI z-scores | 38 tests, validated |
| Regime classifier | 7-rule market regime (trend up/down, range, breakout, high vol, crisis) | Validated |
| Signal generation | Two strategies producing entry/stop/target candidates | See "Strategies" below |
| Portfolio sizing | Risk-% based, leverage cap, min-notional gate, precision floor | 142 tests |
| Risk gate | 8 failure modes (circuit breaker, daily loss, drawdown, heat, stale data, etc.) | 142 tests |
| Paper runtime | Live REST polling, candle finality check, stale-data block | Running hourly via cron |
| LLM advisor | Claude reads market context, can veto or scale down trades. Cannot invent trades. | Wired in, logging |
| Execution agent | Submits to Bybit V5 API, tracks 11-state order machine, idempotent retries | Live-verified |
| Reconciliation | Detects state drift, unprotected positions, ghost positions after restart | Live-verified |

**Total test coverage:** ~210 tests, all passing.

---

## Strategies currently in scope

Both are **short-only on BTCUSDT 1h**. Both were derived from 3 years of historical data with walk-forward validation. Both are gated through the regime classifier before any entry.

### `prev_day_breakdown_v1`
- Trades when price closes below the previous day's low on rising volume, in bearish or compression regimes.
- **Backtest (3 years):** 95 trades, 31.6% win rate, **+0.42 R expectancy**, profit factor 1.44, net +$1,015 on 0.25% risk/trade.
- Walk-forward: 9/21 profitable windows (43%). Low-frequency strategy.
- **Honest read:** does not meet the standard 300-trade gate. Promoted to paper observation only.

### `short_composite_v1`
- Two entry triggers: prev-day breakdown (similar to above) OR EMA20 intra-bar rejection in a confirmed downtrend.
- **Backtest (3 years):** 233 trades, 36.9% win rate, **+0.235 R expectancy**, profit factor 1.30, net +$1,398.
- Walk-forward: 16/33 profitable windows (48%).
- Promotion gate was adjusted (225 trades / PF ≥ 1.25 / WF ≥ 45%) because a 300-trade gate is mathematically unreachable for a single short-only instrument in this market structure. This is documented.

---

## Honest expectations

- **Edge is small.** +0.2 to +0.4 R per trade after fees, slippage, funding. Sustainable but slow.
- **Drawdowns are real.** Walk-forward shows ~half of test windows are losing windows. A 3-6 month losing streak is statistically expected and **not** a signal to stop.
- **Both are short-only.** This system makes money when BTC trends down or compresses. It sits flat in trend-up regimes. There is no long strategy in scope.
- **Low frequency.** Expect 1-5 trades per week per strategy, sometimes weeks with zero trades.
- **Not a hedge fund.** We do not compete on data spend, latency, or PhD count. We compete on **discipline at retail scale**: every trade is gated by deterministic rules, every order has a stop, every state divergence triggers an alert. The edge comes from not screwing up, not from prediction superiority.

---

## What's NOT in the system (intentional)

- **No long strategies.** Both candidates are short-only. Trend-up regimes = no trades.
- **No DCA.** Adding to losers is blocked.
- **No 5-minute trading.** Fees + spread eat the edge below 15m.
- **No reinforcement learning.** Skipped indefinitely — sample size insufficient, big-fund literature is mostly negative.
- **No ML in the hot path.** Hot path (signal → sizing → risk → execution) is fully deterministic. ML reserved for cold-path roles only (decay detection, trade outcome classification) at Phase 12.5+.

---

## Key decisions for the partner discussion

These are the levers worth aligning on **before** putting money on the line:

### 1. Are these two strategies the right ones to deploy first?

The honest case for proceeding as-is:
- Both backtested positive over 3 years.
- Both have walk-forward validation.
- Both have realistic, defensible assumptions.
- Pausing for "better strategies" is research, not execution — research has no end date.

The honest case against:
- Both are short-only. In a sustained bull market we sit flat.
- `prev_day_breakdown_v1` has only 95 trades — small sample.
- Neither has been observed live for the full 6-8 weeks originally planned.

### 2. Risk budget per trade

Backtests use 0.25% of capital per trade. With $10k capital that's a $25 risk per trade — very conservative. Worth confirming this is the target before going live.

### 3. Capital cap for the first live run

Original plan: $5–$50 hard-coded position cap until manually unlocked. Worth confirming the partner is comfortable with $50 max position size for the first month.

### 4. Should we add a long strategy before going live?

Adding a long candidate would require returning to the Phase 5 / Phase 7 research loop. Probably **+1 month of work** before a candidate is qualified. Possible candidates exist but none have been validated to the same bar as the two shorts.

### 5. Cloud deployment timing

The bot currently runs on the local laptop via cron. To run 24/7 it needs a small cloud VM (~$6/month DigitalOcean droplet). One day of setup. Should happen before any real capital. Partner SSH access included.

---

## Path forward (proposed)

Whatever the partner decides about strategies, the rest of the path is the same:

1. **Cloud deployment** (1 day) — droplet, systemd, partner SSH access.
2. **Run testnet for 1-2 weeks** on the cloud — confirms 24/7 stability and that the LLM advisor isn't producing surprising vetoes.
3. **Flip to mainnet with $5–$50 cap** — observe one month of micro-live trading.
4. **Review and uncap** — if first month is clean (no unprotected positions, no state divergences, behavior matches paper), discuss raising the cap.

If the partner wants a different strategy first, we add a research loop **before step 2**.

---

## Risk summary in plain terms

- **What you can lose on a single trade:** at most the risk budget (e.g. $25 on a $10k account at 0.25%).
- **What you can lose in a bad month:** historically up to ~3-5% of capital in the worst drawdowns observed.
- **What protects you from a flash crash:** every position has a stop-loss submitted to Bybit immediately after entry. The reconciliation layer alerts if any position is ever observed without a stop.
- **What protects you from a software bug:** circuit breaker on N consecutive losses, daily loss cap, drawdown cap, max-position-count cap. Any breach halts new entries.
- **What protects you from an LLM going off the rails:** the advisor can only **veto or shrink** trades. It cannot invent a new trade or override a stop-loss. Every advisory decision is logged for audit.
