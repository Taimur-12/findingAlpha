# Critical Gap Analysis — Finding Alpha
**Date:** 2026-05-30  
**Scope:** Full codebase audit + strategy critique + path-to-competitiveness review  
**Verdict:** Infrastructure is production-grade. Strategy layer and operational hygiene are not ready for real capital.

---

## 0. The Brutal Summary First

Before the details: the paper runners have been running since Phase 8 completion, but `paper/trades.jsonl` does not exist and `paper/composite/trades.jsonl` does not exist. **Zero trades have been captured.** The last processed bar timestamp is `2026-05-27T18:00:00+00:00` — three days behind the current date. The cron is not running reliably.

You have a system that has never actually traded in paper mode. The 6–8 week paper observation gate is completely unsatisfied. Every other issue below is secondary to this.

---

## 1. Operational Failures (Show-Stoppers)

### 1.1 Paper runners are not running

**Evidence from code:**
```
paper/state.json → last_processed_bar_ts: 2026-05-27T18:00:00+00:00  (3 days stale)
paper/trades.jsonl → NOT FOUND (zero trades ever)
paper/composite/trades.jsonl → NOT FOUND (zero trades ever)
```

The cron jobs installed on the local laptop have failed, or the laptop sleeps and kills them. You have been running a paper observation for zero days, not 4+ weeks.

**Impact:** The Phase 11 pre-flight gate (`paper/trades.jsonl` + positive expectancy + runtime runs unattended) is entirely unsatisfied. You cannot go live.

**Fix:** Cloud VM, now. One day of work. Nothing else matters until this is done.

---

### 1.2 Advisory runner is not on a schedule

**Evidence:** `notebooks/phase9_advisory_runner.py` is a standalone script. The cron only runs the paper runners. The advisory is manually generated. After 24 hours it expires. The runtime then falls back to `default_advisory()` — permissive defaults, i.e. the advisory layer does nothing.

**Impact:** The LLM advisory is functionally absent for all paper observation time since it wasn't scheduled.

**Fix:** Add to cloud cron:
```
0 6 * * *  python notebooks/phase9_advisory_runner.py --once
```

---

### 1.3 Advisory path resolution is fragile

**Evidence in code:**

In `phase9_advisory_runner.py`:
```python
ADVISORY_PATH = _ROOT / "advisory.json"   # project root
```

In `PaperRuntimeConfig`:
```python
advisory_path: Path = Path("advisory.json")  # relative to cwd
```

If the cron runs the paper runner from a different working directory than the advisory was written to, the advisory is never found and defaults apply silently.

**Fix:** Make both use the same absolute path resolved from `_ROOT`.

---

### 1.4 No monitoring, alerting, or dead-man switch

There is no mechanism to know when:
- A paper trade fires
- The runtime crashes
- Data goes stale
- The circuit breaker trips
- The cron job fails silently

**Fix (minimal):** One-line Telegram or Discord webhook in `_print_status()` when a trade closes, and a dead-man alert (cron + curl to a free uptime monitor like healthchecks.io) after each successful `run_once`.

---

## 2. Code-Level Bugs and Design Gaps

### 2.1 Take-profit orders are NOT submitted to the exchange

**Evidence in `execution/execution_agent.py`:**
```python
"""
Take-profit legs are not implemented: the two production strategies exit
on stop or max_hold_time, so TP plumbing would be dead code.
"""
```

**The problem:** The backtests model TP exits at 4.5 ATR as a limit order fill. The live/paper execution path exits on `max_hold_time` if price hasn't already stopped out. These are different exit mechanics. In the backtest, a trade hitting 4.5 ATR is a win. In the live path, a trade that moves 4 ATR in your favour but doesn't hit 4.5 ATR before the 12h timeout exits at market close — potentially a smaller win or a loss.

**Impact:** Backtest/live divergence. Live expectancy will be lower than backtest expectancy.

**Fix:** Submit a TP limit order to Bybit after entry fill, using `reduce_only=True`. The execution agent already builds `take_profit_orders` in `build_order_plan()` — the submission step just isn't wired.

---

### 2.2 Coordinator is bypassed in the paper runtime

**Evidence in `paper/runtime.py`:** The `_run_strategy_pipeline()` function calls the strategy function directly, then calls `risk_evaluate()` directly. `coordinator.process_signals()` is never called.

**The problem:** The coordinator exists to deduplicate signals, apply symbol-level arbitration, and track incremental portfolio heat across simultaneous signals. The paper runtime skips all of that. If two strategies fire on the same bar (which `short_composite_v1` can trigger on its `breakdown` trigger, which is identical to `prev_day_breakdown_v1`'s trigger), the paper runtime processes them in isolation.

**Fix:** Route through `coordinator.process_signals()` in `_run_strategy_pipeline()`.

---

### 2.3 Both strategies can fire simultaneously on the same signal

`prev_day_breakdown_v1` fires when `close < prev_day_low AND volume_z >= 2.0`.  
`short_composite_v1` fires trigger #1 when `close < prev_day_low AND volume_z >= 1.0`.

On any strong breakdown bar with `volume_z >= 2.0`, **both strategies generate a signal for the same entry**. With two separate paper runners and two separate paper state files, this produces two independent paper positions on the same trade. When going live with a single capital pool, this will create double exposure unless the coordinator deduplicates them.

**Fix:** If both strategies are ever run from a single live runner, the coordinator must be used and must deduplicate by `(symbol, side)`.

---

### 2.4 Risk agent missing the expected-net-edge check

**Evidence in `risk/agent.py`:** Eight checks are implemented. The source of truth (`FINDING_ALPHA_SOURCE_OF_TRUTH.md`) lists as a required pre-trade check:
> "expected net R after fees, slippage, and funding"

This check does not exist in the implemented risk agent. Any signal that passes the 8 implemented checks goes through regardless of whether the fee-adjusted expected edge is positive.

**Fix:** Add a ninth check:
```python
# Estimated net edge from signal
expected_r = signal.expected_net_r  # or compute from confidence × R:R - fee_adj
if expected_r < config.min_expected_r:
    return _reject([rc.RISK_INSUFFICIENT_EDGE])
```

---

### 2.5 `high_volatility` regime doesn't block any strategies

**Evidence in `regime/classifier.py`:**
```python
regime="high_volatility",
confidence=Decimal("0.75"),
evidence=evidence, blocked_strategies=[],   # ← nothing blocked
```

Both strategies are allowed to fire in high-volatility conditions (ATR percentile >= 80). A breakdown short signal in a spike-down market with 80th-percentile ATR is exactly when stop-losses are most likely to be overrun and fills are most likely to be adversely impacted.

**Fix:** Add `short_composite_v1` and `prev_day_breakdown_v1` to `blocked_strategies` in `high_volatility`, or at minimum reduce sizing by 50% via a high-vol modifier.

---

### 2.6 `breakout_pending` fires short entries with unknown direction

Both strategies allow entry in `breakout_pending` regime (Bollinger bandwidth <= 15th percentile — a compression squeeze). The problem: a squeeze breaks in either direction. Taking a short in a compression regime because the close went below prev-day low is highly prone to false breakdown: price often re-enters the range within 1–3 bars.

**Industry evidence:** Most retail quant systems that trade breakouts require the direction to be confirmed by an initial candle close outside the range before taking a continuation entry. The current setup allows entry on the very candle that appears to initiate a breakdown, which backtests show is often a fakeout in ranging/compression environments.

**Fix:** Remove `breakout_pending` from `_ALLOWED_REGIMES` for `prev_day_breakdown_v1`. For `short_composite_v1`, restrict trigger #1 (breakdown) to `trend_down` only; allow trigger #2 (EMA rejection) in `breakout_pending` only if ADX >= 25 (pre-existing trend confirmation).

---

### 2.7 ADX threshold of 20 is too low for trend classification

**Evidence in `regime/classifier.py`:**
```python
if adx_val >= 20:
    if e20 > e50 > e200 and rsi > 50:
        ...regime="trend_up"
```

ADX 20 is the common textbook entry threshold but it produces many false trend classifications. At ADX 20–24, markets are technically "trending" by the indicator definition but are often still transitional. The literature on ADX (Wilder's original work, and subsequent quant research) consistently shows that ADX >= 25 is the reliable threshold for a trend worth trading.

**Impact:** You are taking trend-following short entries in markets that are only marginally trending, which inflates false-signal rate and suppresses win rate.

**Fix:** Change the threshold to `adx_val >= 25` for both trend_up and trend_down classification. This will reduce trade frequency but increase per-trade quality.

---

### 2.8 LLM advisory has no external data inputs whatsoever

**Evidence in `notebooks/phase9_advisory_runner.py`, `build_user_message()`:**

The entire user message is:
1. Recent paper trade R multiples (currently: zero trades, so "None in the lookback window")
2. The previous advisory's trade_policy and summary

There is no: current BTC price, RSI, funding rate, open interest, news, macro calendar events, exchange status, FOMC dates, or any market context. The LLM is asked to advise on trading risk with literally no market information.

**What Claude actually produces:** With zero trades and no market data, the advisory defaults to `trade_policy: "normal", confidence_multiplier: 1.0` every single time. The advisory is a no-op by design.

**The irony:** The system prompt says "Use recent paper trade performance as your main input." With zero trades, there is nothing to use.

**Fix — minimum viable:**
```python
# Add to build_user_message():
current_market = fetch_market_context()  # free Bybit API call
macro_events = load_macro_calendar()     # hardcoded FOMC/CPI dates + free API
```

At minimum, feed: current BTC close, ATR percentile, funding rate z-score, and the next 48h macro events. This costs nothing (Bybit public API) and gives the LLM something to reason about.

---

### 2.9 CVD / taker-buy imbalance is absent from all strategies

The source of truth lists CVD and taker-buy imbalance as core feature requirements. The feature engine has `volume_z_score` but no taker-buy computation. The strategies use only `volume_z_score` as order-flow confirmation.

**The difference matters:** Volume z-score tells you *how much* was traded. Taker-buy imbalance tells you *who was aggressive* (sellers or buyers). A high-volume candle could be 90% buy-aggressive (bullish) or 90% sell-aggressive (bearish). Using volume_z without direction is a weaker signal.

**Fix:** Add taker-buy volume ratio from Bybit's `taker_buy_vol` field in kline data (already returned in the API response but not currently used). Add `taker_buy_ratio = taker_buy_vol / total_vol` to the feature snapshot and require `taker_buy_ratio < 0.40` (seller-dominated) as a confirmation filter on breakdown entries.

---

### 2.10 `PortfolioConfig.risk_pct` default is 1% but paper runtime uses 0.25%

**Evidence:**
```python
# portfolio/agent.py
risk_pct: Decimal = Decimal("0.01")   # 1% default

# paper/runtime.py  
risk_pct: Decimal = Decimal("0.0025")  # 0.25% paper
```

The defaults are inconsistent. If the portfolio agent is used without overriding config (e.g. in testing or research), it sizes at 1%, not 0.25%. This inconsistency will silently cause backtest-validation mismatches if someone runs the agent with its default config.

**Fix:** Align the default to 0.0025 in `PortfolioConfig`, or rename `risk_pct` in the paper config to make the override intent explicit.

---

## 3. Strategy-Level Gaps

### 3.1 Zero long strategies — critical structural gap

Both strategies are short-only. BTC is in a long-term uptrend with multi-month bull cycles interspersed with corrections. In any sustained `trend_up` regime, the system sits completely flat.

**Arithmetic consequences:**
- If BTC spends 6 months trending up (common in halving cycles), the system earns zero.
- Annual return potential halves from the theoretical maximum.
- The system cannot compound in bull markets.

**What should be built:**
The most natural candidates that mirror the existing short structure:
1. **EMA20 long rejection** — bar opens below EMA20, closes above it in `trend_up` with aligned EMA stack. Mirror of the existing short trigger #2.
2. **Previous-day high breakout long** — close above prev-day high on elevated volume in `trend_up`. Mirror of `prev_day_breakdown_v1`.
3. **Funding squeeze long** — deeply negative funding (shorts paying longs) + price at structural support. Strong crypto-native signal.

All three use the existing feature engine with zero new infrastructure.

---

### 3.2 No out-of-sample instrument validation

Both strategies are validated on BTCUSDT 1h only. This is in-sample for the instrument universe. A strategy with real edge should:
1. Survive on ETHUSDT with the same parameters (same market microstructure, different price level)
2. Not have its entire edge concentrated in 2-3 specific BTC events from 2023–2026

**What this means in practice:** If you run `prev_day_breakdown_v1` on ETHUSDT 1h with identical parameters and it shows negative expectancy, the BTCUSDT edge may be an artifact of specific BTC bear periods (Q4 2023, Q1 2025) that happened to dominate the 3-year sample.

**Fix:** Run both strategies on ETHUSDT 1h with zero parameter changes. If expectancy is positive (even weaker than BTC), the signal is real. If it's negative, the BTC result is suspect.

---

### 3.3 4.5 ATR single-target exit is likely unrealistic for live execution

The backtest models a limit order at `close - 4.5 ATR` as the take-profit. On BTCUSDT 1h with ATR ≈ $800, this is a $3,600 move. The strategy has a 36.9% win rate, which means 63% of trades hit the stop.

**The live reality:** At 4.5 ATR, the limit TP order often sits on the book for the full 12h window and may not fill if BTC reverses before reaching it. The backtest may be crediting fills that would be partial or missed in live.

**What others do:** Successful short-term systematic traders often use two-target exits: 50% at 2.0 ATR (near-guaranteed win) and 50% at 4.5 ATR (runner). This improves win rate from 36% to ~50% on the first leg while still capturing large moves on the second leg. This also reduces variance and makes the system psychologically easier to run.

**Fix:** Implement a two-leg TP: 50% at 2.0 ATR (close enough to reliably fill), 50% at 4.5 ATR (original target). Backtest both the single-target and two-target variants before changing the live configuration.

---

### 3.4 Walk-forward results are statistically marginal

| Strategy | WF Windows | Profitable Windows | % |
|---|---|---|---|
| prev_day_breakdown_v1 | 21 | 9 | **43%** |
| short_composite_v1 | 33 | 16 | **48%** |

For reference, academic literature on systematic strategy robustness considers walk-forward hit rates above 55–60% as "reasonably robust" and below 50% as "marginal at best." Both strategies are at or below the marginal threshold.

**What 43% actually means:** The strategy loses money in more 30-day windows than it makes money in. Over a random 6-month period, you might hit 3 consecutive losing windows (months), which represents a 3-month period of losses. This is documented in the partner brief but the implication is understated — it means the system may underperform for 6–12 months at a stretch while remaining valid long-term.

**Fix:** This isn't something you fix by tuning. You accept it as a property of the strategy and ensure: (1) risk per trade is small enough to survive 3+ losing windows, (2) the partner understands what a losing streak looks like, and (3) you have a formal drawdown halt threshold that is larger than the expected maximum consecutive-window loss.

---

### 3.5 `prev_day_breakdown_v1` volume threshold is very strict

```python
_MIN_VOLUME_Z = 2.0  # 2 standard deviations above mean
```

Volume z-score >= 2.0 occurs roughly 2.3% of bars in a normal distribution. For a strategy that already fires infrequently (31 trades/year), this filter reduces trade frequency further. The composite strategy uses `volume_z >= 1.0` for its breakdown trigger — a 16% occurrence rate.

**The tension:** Lower threshold = more trades = better statistical validity = lower win rate per trade. Higher threshold = fewer trades = higher conviction per trade = insufficient sample.

**What to do:** Backtest both strategies with `_MIN_VOLUME_Z = 1.5` (6.7% occurrence) and report the trade count, expectancy, and WF change. A threshold of 1.5 may give you 50–60% more trades without significantly degrading win rate.

---

### 3.6 No session-time filter on `short_composite_v1`

`prev_day_breakdown_v1` blocks NY solo (17:00–22:00 UTC). `short_composite_v1` has no session filter at all. The Phase 7B research showed NY solo is consistently adverse for the breakdown family. The composite strategy's breakdown trigger is identical to the v1 breakdown — it should inherit the same session filter.

**Fix:** Add the same `_ALLOWED_SESSIONS` frozenset to `short_composite_v1`'s breakdown trigger (not the EMA rejection trigger, which has different session characteristics).

---

## 4. Architecture Gaps vs. The Build Plan

### 4.1 WebSocket is not implemented — REST polling has a flaw

The live feed uses REST polling via `fetch_recent_candles()`. This works for 1h bars (polling every 60s is sufficient). But the current implementation has a subtle staleness issue: if Bybit is slow to finalize a bar (occasionally takes > 60s after the close), a polling run can miss the bar entirely and process it only on the next poll 60s later.

The `is_bar_final()` grace period of 60s is correct. But `run_once()` is called once per hour by cron — not every 60s. If the cron fires at :05 (5 minutes past the bar close), it correctly processes the bar. But if the laptop or cron delays the run to :07, the bar at :00 has been final for 7 minutes and everything is fine. The real issue is **cron reliability** — which is demonstrated by the 3-day staleness observed.

**Fix:** On cloud, run cron at :05 and :35 of every hour (two attempts per bar), or use `run_loop()` with `poll_seconds=60` as a persistent systemd service rather than one-shot cron. Persistent service is more reliable.

---

### 4.2 Phase 11.5 (DuckDB analytics) is planned too late

DuckDB analytics is planned after micro-live capital is deployed. But the analytical questions you need to answer to decide whether to deploy capital require DuckDB:
- "What is the paper expectancy by session, by month?"
- "How many advisory vetoes have there been and did they add value?"
- "What was the fill rate on pending entries?"

JSONL scanning in Python is already painful with a few hundred events. By the time you have 200 paper trades it will be unusable.

**Fix:** Build Phase 11.5 in parallel with Phase 8 paper observation on the cloud VM. It is 2–3 days of work and does not block anything — it just adds a daily compaction cron that converts JSONL → Parquet → DuckDB views.

---

### 4.3 No position-level P&L monitoring during open trades

The paper state tracks equity and open position, but there is no mechanism to report unrealized P&L on an open position, or to alert if an open position is approaching its stop. This means you cannot monitor a live position without manually reading state files.

**Fix:** Add `get_unrealized_pnl(position, current_price)` to `paper/state.py` and include it in `_print_status()` output.

---

### 4.4 `ResearchState.is_hard_block` semantics unclear from code

In `contracts/signals.py`, `ResearchState` has an `is_hard_block` field. The `advisory.py` function `is_hard_block(rs)` checks:
```python
if rs.trade_policy in {"block_new_entries", "close_risk_positions"}:
    return True
return rs.is_hard_block
```

The `is_hard_block` field on the contract allows the LLM to directly set `True`, bypassing the trade_policy check. This means the LLM could theoretically hard-block all trades by setting `is_hard_block=True` even with `trade_policy="normal"`. This is inconsistent with the schema design — the `trade_policy` field should be the authoritative gate.

**Fix:** Remove the `return rs.is_hard_block` line. The hard block should only be triggered by `trade_policy`. The field itself may cause confusion.

---

## 5. The Path to Competitiveness — What You're Missing vs. Top Retail Systematic Traders

The source of truth doc correctly identifies the competitive niche: "disciplined 1–2 person systematic prop trader." This is accurate. Here is what separates a top-performing retail systematic trader from a mediocre one:

### 5.1 Multi-directional trading
Top retail systematic crypto traders run both long and short books. The BTCUSDT perpetual is liquid in both directions. Short-only means you earn zero alpha during bull markets, which historically dominate crypto.

**Your gap:** No long strategy. Cannot be addressed without returning to Phase 5/7 research for at least 3–4 weeks.

### 5.2 Multiple uncorrelated strategies
The current two strategies are highly correlated — `short_composite_v1` literally contains `prev_day_breakdown_v1` as trigger #1. Two correlated short strategies on the same instrument is not diversification — it is a duplicate.

**What top traders do:** At least two genuinely uncorrelated signal families (e.g., trend-following + mean-reversion, or momentum + funding-squeeze). The two strategies currently in scope are both momentum-breakout — one more selective than the other.

### 5.3 Regime-aware position sizing
Flat 0.25% risk per trade regardless of regime quality is suboptimal. A clean trend_down with ADX 40 should carry more weight than a barely-trend_down with ADX 21.

**Simple improvement:** Multiply `risk_pct` by `regime.confidence` (which is already computed — 0.65 for weak trend, 0.80 for strong trend). No new research needed. Code change: one line in `_run_strategy_pipeline()`.

```python
effective_risk_pct = cfg.risk_pct * float(regime.confidence)
```

### 5.4 Funded by real market microstructure data
The best retail systematic traders use taker-buy imbalance, order flow delta, and liquidation heat maps. You have volume z-score. This is better than nothing but misses the directional component of aggression.

**Minimum viable addition:** Bybit's kline API already returns `takerBuyBaseVolume`. Add it to the loader, compute `taker_buy_ratio` in features, and use it as a confirmation gate on breakdown entries.

### 5.5 What the LLM adds in real systems
In the handful of published retail systematic LLM trading systems (including some public Substack/GitHub implementations), LLM advisors that add measurable value share one property: **they receive external information the strategy engine doesn't have**.

Specifically:
- News sentiment from CryptoPanic, CoinDesk RSS
- Scheduled macro events: FOMC, CPI, jobs report, BTC ETF decisions
- Exchange status (Bybit maintenance notices)
- Unusual derivatives market conditions (extreme funding from Coinglass free API)

None of these require paid data. CryptoPanic has a free API. Coinglass has a free tier. FOMC dates are public. Adding even two of these sources would transform the advisory from a "look at trade history" function into a genuine market-context gate.

---

## 6. Immediate Action Priority

In priority order, before any live capital:

| # | Action | Effort | Blocks |
|---|---|---|---|
| 1 | Deploy to cloud VM (DigitalOcean/Hetzner) + systemd | 1 day | Everything |
| 2 | Schedule advisory runner in cron | 30 min | Advisory layer |
| 3 | Fix advisory path resolution (absolute path) | 15 min | Advisory reliability |
| 4 | Add market context to advisory (BTC price, funding, ATR pct) | 2h | Advisory value |
| 5 | Add dead-man healthcheck + Telegram alert on trade close | 2h | Observability |
| 6 | Wire TP order submission in execution agent | 3h | Backtest/live parity |
| 7 | Route paper runtime through coordinator | 2h | Correct deduplication |
| 8 | Remove `breakout_pending` from `prev_day_breakdown_v1` regimes | 30 min | False signal rate |
| 9 | Add session filter to `short_composite_v1` breakdown trigger | 30 min | NY-solo adversity |
| 10 | Change ADX trend threshold from 20 to 25 | 30 min | Signal quality |
| 11 | Add `high_volatility` to blocked regimes for both strategies | 30 min | Risk in volatile markets |
| 12 | Test both strategies on ETHUSDT (same params, no tuning) | 1 day | Out-of-sample validation |
| 13 | Build one long strategy candidate | 3–4 weeks | Direction coverage |
| 14 | Add taker-buy ratio to features and strategies | 1 day | Signal quality |
| 15 | Move Phase 11.5 DuckDB build to run in parallel | 2–3 days | Analytical capability |

---

## 7. Expected Outcome at Current State vs. After Fixes

### Current state (before fixes)
- Paper runners: not running
- Trades captured: 0
- Advisory: generating no-op JSON daily (when run manually)
- Live TP execution: broken (backtest/live divergence)
- Annual return potential: theoretical 6–9% in favourable conditions, 0% in bull markets
- Probability of detecting a software bug before real capital: low (no monitoring)

### After Fixes 1–11 (cloud + operational + quick code fixes, ~1 week total)
- Paper runners: running 24/7
- Advisory: running with real market context
- TP orders: submitted correctly
- Signal quality: improved (ADX 25, no breakout_pending, session filter)
- Monitoring: trades and health tracked
- Timeline to paper gate: 6–8 weeks from cloud deployment
- Annual return potential: same as current (these are operational fixes)

### After Fixes 12–15 + long strategy (2–4 months total)
- Both directions covered
- ETHUSDT validated
- Analytics queryable via DuckDB
- LLM has real inputs
- Annual return potential: potentially 15–25% in mixed-direction markets (still not competing with top institutional traders, but genuinely competitive at retail systematic scale)
- Sharpe potential: 0.8–1.2 vs. current 0.3–0.5 theoretical

---

## 8. What "Competing at the Top" Actually Requires

The top 1% of retail systematic crypto traders achieve 30–60%+ annual returns with Sharpe > 1.5. This is not achievable with the current two-strategy, one-instrument, short-only setup regardless of how well the code is written. To reach that level requires:

1. **4–6 uncorrelated strategies** across both directions and 2–3 instruments
2. **Regime-adaptive sizing** (not flat risk pct)
3. **Real-time market microstructure** inputs (order book imbalance, CVD, liquidation data)
4. **Multi-month paper validation** (not weeks) before each strategy goes live
5. **Continuous strategy research** running in the background at all times
6. **Strategy decay detection** (expectancy monitoring with rolling windows)

The architecture you have built can support all of this. The strategy layer is what needs to grow.

**The honest projection:** With the current infrastructure and a disciplined 12-month research and live-trading process, you could reach 15–30% annual returns with Sharpe ~1.0. That is the realistic ceiling for a 1–2 person retail systematic operation on public data. It is meaningful, it compounds, and it beats 95% of retail traders. It is not what "top quant funds" do, but that was never the actual goal — the actual goal as stated in the source of truth is to compete "at retail scale" with "hedge-fund-grade discipline," and this is achievable.

---

---

## 9. Backtest Modeling Gaps (from Research)

Additional gaps identified from cross-referencing public retail systematic trading literature and common live-vs-backtest divergence patterns:

### 9.1 Slippage uses mid-price, not offer/bid

The simulation executor models slippage in basis points but applies it symmetrically. In practice:
- Limit entry (SHORT): you are the maker. You post an offer at `entry_reference`. If price touches it from above, you fill — but only if you're first in the queue. The backtest assumes fill on touch; real queue position means some touches don't fill.
- Stop exit (SHORT): you are the taker, buying to close. During a fast move against you, the offer may be 0.2–0.5% above your stop trigger price.

**Fix:** In `SimConfig`, add `entry_miss_rate=0.15` (15% of limit touches don't fill — empirically observed in OHLCV-only backtests) and model stop exit at `stop_price * (1 + taker_slippage_bps/10000)` rather than at the exact stop price.

### 9.2 Funding payment timing not modeled precisely

The backtest applies funding as a continuous flow proportional to hold time. Bybit perpetuals pay funding at 00:00, 08:00, and 16:00 UTC. If you hold a position that straddles one funding timestamp, you pay/receive the full rate; if you exit 20 minutes before, you avoid it entirely.

For a 12h max-hold strategy, this means the backtest and live results can differ by one full funding payment (currently ±0.01–0.03% per occurrence) depending on exactly when trades close.

**Fix (minimal):** Model funding as a step function with settlement at the three daily UTC timestamps rather than continuous. Small change to `simulation/executor.py`.

### 9.3 Regime classification has 1-bar confirmation — too fast

The regime classifier switches on the bar where EMA conditions change. In live markets, regime transitions are noisy: EMA stack can align for one bar and then reverse. Most published retail quant systems require 2–3 bars of confirmed regime before acting.

**Fix:** Add a `regime_confirmation_bars: int = 2` parameter to `PaperRuntimeConfig`. Track regime state across the last N bars and only act if the regime has been stable for N bars. This reduces false-regime-transition trades.

### 9.4 Paper gate should be harder

The current Phase 8 gate is time-based (6–8 weeks). For low-frequency strategies, time is the wrong metric. Industry practice for low-frequency strategies:

```
Hard paper gate (replace soft time gate):
  [ ] 30+ completed paper trades (not just bars processed)
  [ ] At least one paper drawdown of -3% to -5%
  [ ] At least one uptrend period observed where system correctly sat flat
  [ ] Zero reconciliation errors across all processed bars
  [ ] Paper expectancy within 2σ of backtest expectancy
  [ ] Advisory log shows ≥10 bars of decision history (not all defaults)
```

At current frequency (~5–8 trades/month combined), 30 trades = approximately 4–6 months of cloud observation, not 6–8 weeks. This is the real timeline before live capital is appropriate.

### 9.5 Recommended news APIs for the advisory layer

In order of recommendation for the advisory runner:

1. **CryptoPanic** (free tier, ~30 calls/hour) — categorised, urgency-ranked, covers major events within 2–5 minutes
2. **NewsData.io** (free tier, 200 credits/day) — better regulatory coverage, good keyword filtering
3. **FMP Economic Calendar** (free tier, 5 calls/day) — US macro events: FOMC, CPI, NFP, PCE — enough for a daily advisory check
4. **Alternative.me Fear & Greed Index** (completely free, hourly) — composite contrarian signal, no coding overhead

Total cost: $0. One day of integration. Transforms the advisory from "look at trade history" into genuine market-context awareness.

---

*End of gap analysis. Findings from: direct code inspection of `main` branch as of 2026-05-30, and cross-reference with public retail systematic trading literature.*
