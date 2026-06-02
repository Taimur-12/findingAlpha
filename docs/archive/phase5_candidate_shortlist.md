# Phase 5 — Strategy Candidate Shortlist

Generated: 2026-05-27  
Backtest period: Bybit BTCUSDT 1h, 2025-12-07 to 2026-05-27

---

## Summary of Tested Strategies

| Strategy | Trades | Win Rate | Expectancy (R) | Net PnL | Status |
|---|---|---|---|---|---|
| liquidity_sweep_v1 | 21 | 47.6% | +0.030 | +$62 | MARGINAL |
| squeeze_v1 | 7 | 28.6% | -0.374 | -$262 | REJECTED |
| trend_pullback_v1 | 251 | 43.4% | -0.097 | -$2,435 | REJECTED |

---

## Rejected Strategies

### squeeze_v1 — REJECTED

**Reason**: Structural contradiction between the squeeze condition (low volatility) and the regime filter (blocks high-volatility). In practice, this produces only 7 signals in 6 months — too few to be useful. Negative expectancy (-0.374R). The stop placement at bb_middle is vulnerable to post-breakout noise.

**Not carried forward to Phase 8.**

### trend_pullback_v1 — REJECTED (current parameters)

**Reason**: Negative expectancy (-0.097R) consistent across all RSI parameter variants tested. The strategy overtriggers (251 signals in 6 months) and nearly half of trades time out without hitting target or stop. The proximity zone is too wide, diluting signal quality.

**Potential for v2**: The underlying idea (enter EMA pullbacks in confirmed trends) is sound. Requires tighter proximity zone, better entry timing, and a trailing stop approach. Flagged for Phase 14 research backlog.

---

## Marginal Strategies

### liquidity_sweep_v1 — MARGINAL

**Reason**: Barely positive expectancy (+0.030R) on a sample of only 21 trades. Fee drag at 79.8% of gross is unsustainable. The structural logic (sweep + reclaim + volume) is sound and well-documented in the literature.

**Promoted to v1 live candidate with caveats**:
- Must be validated on a larger dataset (2+ years) before live capital
- Needs target multiplier increase (2.5-3.0× ATR) to reduce fee drag
- First live test will be in paper trading mode (Phase 8) with strict position sizing

---

## v1 Live Strategy Candidate

**liquidity_sweep_v1** is the only strategy promoted to the Phase 8 paper trading candidate list.

Rationale:
- Positive expectancy on available data (insufficient sample but not disqualifying)
- Low signal frequency (3-4/month) means manageable drawdown exposure
- Clear, testable hypothesis with defined invalidation conditions
- All entry/exit logic is deterministic and rules-based (no ambiguity in live execution)

---

## Strategies Considered but Not Implemented

The following strategy ideas were considered during Phase 5 research and rejected before implementation:

### Funding Rate Extremes
**Idea**: Enter against the prevailing trend when funding rate reaches extreme levels (> +0.1% or < -0.1%), betting on mean reversion as the funding drag becomes unsustainable.  
**Why rejected**: Funding extremes can persist for weeks in strong trends (especially in BTC bull markets). The strategy requires a regime filter that isn't reliable enough. Carries large adverse carry risk while waiting for the reversion. Deferred to Phase 14.

### OI Divergence
**Idea**: When price makes a new high but OI is declining (smart money unwinding), fade the move.  
**Why rejected**: OI data quality on 1h bars is insufficient for this — OI snapshots can miss intra-hour peaks. Requires tick-level OI data. Also, OI divergence frequently fails in sustained trends. Deferred to Phase 14.

### Session Open Breakout (London/NY)
**Idea**: Enter in the direction of the first 30-minute move at session open (London 08:00 UTC, NY 13:30 UTC).  
**Why rejected**: Requires 15m or 5m bar data and a separate session-open detection mechanism. The 1h bar timeframe is too coarse to capture the session-open setup accurately. Phase 5 scope was 1h bars. Can be revisited when 15m pipeline is stable.

### VWAP Reversion
**Idea**: When price deviates more than 1.5×ATR from session VWAP with elevated volume, fade the deviation.  
**Why rejected**: Session VWAP reversion is a mean-reversion strategy and requires very tight stops. At 1h granularity, the risk/reward is unfavorable — by the time a 1h bar closes far from VWAP, the opportunity may have passed. Better suited to 15m bars.

---

## Phase 14 Research Backlog

Strategies deferred for future research (not blocking Phase 8):
- Funding rate extremes reversal
- OI divergence (requires tick-level data)
- Multi-timeframe confluence (15m signal + 1h regime alignment)
- VWAP reversion (15m bars)
- Session open breakout (15m bars)
- RL-based position sizing overlay (blocked until deterministic system is live and proven)
