# Phase 9 — LLM Advisory Layer Design

**Date:** 2026-05-28 (original), 2026-05-29 (accelerated build override added)  
**Status:** ACTIVE BUILD — accelerated path, validated via historical replay instead of multi-week shadow wait  
**Scope:** Cold-path only. LLM has zero execution authority.

**Related:** `phase9_llm_advisory_final_vision.md` — the long-term target state (news API, full trade history memory, all four execution paths, shorter timeframe migration). This doc is the *original detailed design* + *accelerated build override*. That doc is the *architectural overview of where this is heading*.

---

## Accelerated Build Override (2026-05-29)

The sections below describe the full long-term design. The accelerated build implements a **trimmed subset** of this design in one pass, then back-fills features only if the simpler version proves the LLM is adding value. The original design is preserved below as a reference for what comes back later.

### What the accelerated build ships

- Advisory JSON schema with `valid_until_utc`, `strategy_allowlist`, `risk_scalar`, `hard_block`, `block_reason`, `confidence`, `reasoning`, `prompt_version`, `model_id`
- `src/finding_alpha/research/advisory.py` — `generate_advisory()` (Claude API), `validate_advisory()` (schema + range clamp), `load_advisory()` (with defaults)
- One **shared** advisory file at `paper/advisory.json` (not per-strategy) — both runners read the same advisory because they trade the same instrument with the same market context
- Runtime gates in `paper/runtime.py`: hard_block, risk_scalar multiplier, strategy_allowlist check
- Daily scheduled LLM call (cron entry at 00:00 UTC) producing the advisory
- Trade memory enrichment: enrich each new closed trade with `regime_at_entry`, `funding_z_at_entry`, `oi_z_at_entry` from the matrix event log
- Historical backfill of trade enrichment for the existing paper trades (so the LLM has memory from day one)
- Validation harness: replay historical bars through `phase8_simulation_runner.py` with a fixed (or stub) advisory injected — confirm gates fire correctly and no path crashes
- Audit log: every advisory generated is appended to `paper/advisory_log.jsonl` with timestamp + raw LLM response

### What the accelerated build defers

| Deferred item | Why | Where it goes |
|---|---|---|
| Crisis scanner (every-2-min OI/liquidation/news polling) | No live capital → no urgent need | Phase 11 (when capital is real) |
| CryptoPanic + Fed calendar event tagging | Adds complexity, free tier insufficient for 2-min cadence | Phase 11 or skipped |
| Regime-change trigger with debounce/cooldown | Daily cadence is sufficient for 1h bars at this scale | Add later if daily proves under-reactive |
| Macro event pre/post triggers (FOMC, CPI) | Manual flagging is fine for now | Phase 11 |
| `estimated_clear_condition` free-form parsing | Unsafe — text-to-code gap | Replace with enum (see below) when needed |
| Multi-week "shadow mode" before gating | Validated by historical replay instead | N/A — replaced by sim-based validation |

### Specific overrides to the original design

1. **Default `risk_scalar` when no advisory exists: `1.0`** (original said 0.5). Rationale: the LLM is upside-only. Missing LLM means "no opinion," not "be cautious." Risk policy already lives in the Risk Agent.

2. **Single shared advisory** at `paper/advisory.json`. Both runners read it. Per-strategy advisories were duplication.

3. **`estimated_clear_condition` is an enum, not free text.** Allowed values for the accelerated build:
   - `time_elapsed_4h`, `time_elapsed_8h`, `time_elapsed_24h`
   - `manual_clear_required` (default for crisis advisories — human reviews before clearing)
   
   The free-form text → runtime-parsing path from the original design is unsafe and is explicitly out of scope until there is a constrained DSL.

4. **Prompt and model versioning are required fields.** Every advisory JSON must include `prompt_version` (string, e.g., `"v1.0"`) and `model_id` (e.g., `"claude-sonnet-4-6"`). Without these, the audit log becomes uninterpretable when prompts evolve.

5. **Trade enrichment backfill.** Before the LLM runs for the first time, `enrich_existing_trades()` reads each row in `paper/trades.jsonl` and `paper/composite/trades.jsonl`, looks up the matrix event log for the matching `signal_id`, and writes an enriched copy to `paper/trades_enriched.jsonl`. The LLM reads the enriched copy.

6. **Cost budget.** Daily call only = ~30 calls/month. Estimated ~1-2k tokens in, ~500 out per call. With Claude Sonnet 4.6, this is well under $5/month. Documented so future-me does not over-engineer caching.

7. **Validation = historical sim, not 4-week shadow.** The accelerated path proves the LLM-gated runtime works by injecting a fixed advisory (e.g., `{"hard_block": true}`, `{"strategy_allowlist": []}`, `{"risk_scalar": 0.5}`) into the historical replay and asserting expected behavior. Multi-week real-time shadow observation is not a build gate.

### Implementation order under the accelerated build

1. Define `Advisory` Pydantic model in `src/finding_alpha/research/advisory.py` (frozen, validated, with all override fields)
2. Implement `load_advisory(paper_dir) -> Advisory` with default `risk_scalar=1.0, hard_block=False, strategy_allowlist=["prev_day_breakdown_v1", "short_composite_v1"]` when file missing or expired
3. Wire three gates into `process_final_bar()`: hard_block, strategy_allowlist check, risk_scalar multiplier on `cfg.risk_pct`
4. Add `validate_advisory()` — schema, range clamps (0.25 ≤ risk_scalar ≤ 1.0), reject if `valid_until_utc` in the past
5. Implement trade enrichment (`enrich_trade()`, `enrich_existing_trades()`)
6. Implement `generate_advisory()` — Claude API call with structured output, system prompt enforcing JSON schema, retries on transient errors
7. Build `notebooks/phase9_advisory_runner.py` — daily cron entry that calls `generate_advisory()` and writes `advisory.json` + appends to `advisory_log.jsonl`
8. Validation: replay historical sim with stub advisories, confirm gates work
9. Add cron entry for the daily advisory call (00:00 UTC)

Everything below this section is the **original design** — kept as the reference for what eventually gets built in Phase 11+ when the simpler version proves out.

---

## The Core Constraint

The hot path — signal → sizing → risk → execution — stays fully deterministic. The LLM is a separate process that produces a **bounded JSON advisory document**. The runtime reads that document as one more gate before entering a trade. The LLM never calls an API, never modifies a position, and never overrides a stop.

---

## What the LLM Can Control (4 Variables Only)

```json
{
  "valid_until_utc": "2026-05-29T06:00:00Z",
  "macro_stance": "risk_off",
  "strategy_allowlist": ["prev_day_breakdown_v1"],
  "risk_scalar": 0.5,
  "hard_block": false,
  "block_reason": null,
  "confidence": 0.72
}
```

| Field | Type | Range | Effect in Runtime |
|---|---|---|---|
| `strategy_allowlist` | string[] | subset of registry keys | Strategies not listed are skipped |
| `risk_scalar` | float | 0.25 – 1.0 | Multiplied into `PortfolioConfig.risk_pct` |
| `hard_block` | bool | true/false | If true, no new entries until advisory expires |
| `valid_until_utc` | datetime | future UTC | Advisory treated as stale after this timestamp |

The LLM **cannot** change: stop placement, target levels, entry logic, max hold time, or any strategy parameter. Those live in the strategy files and are only changed by human review.

---

## Data Layer (3 Inputs)

### 1. Strategy Performance Memory

The existing `trades.jsonl` files are the base. Each trade record is enriched with market context at the time it opened:

```json
{
  "trade_id": "...",
  "strategy": "prev_day_breakdown_v1",
  "entry_time_utc": "2026-05-15T09:00:00Z",
  "outcome_r": 1.2,
  "regime_at_entry": "trend_down",
  "btc_7d_return_pct": -8.3,
  "funding_z_at_entry": 2.1,
  "oi_z_at_entry": -0.4,
  "macro_tags": ["POST_FOMC", "RISK_OFF_WEEK"],
  "fear_greed_at_entry": 28
}
```

This creates a queryable memory: *"in risk-off weeks with elevated funding z-score, breakdown strategy win rate is 40% vs 25% baseline."* No vector DB needed at this scale — structured JSON retrieval filtered by regime + macro_tags is sufficient until you have 1,000+ trades.

### 2. Macro / News Event Tags

The LLM does not read raw news articles on the hot path. A lightweight pre-processor polls public sources and converts them into **structured event tags** stored alongside the trade ledger.

**Sources (all free, no private API keys):**
- Fed calendar (FOMC meeting dates, CPI release dates) — hardcoded annually + BLS RSS
- CryptoPanic API — free tier, crypto-specific news headlines
- Alternative.me Fear & Greed Index — single number, public endpoint

**Event tag format:**
```
2026-05-22: FOMC_MEETING_DAY
2026-05-23: CPI_RELEASE_DAY
2026-05-28: BTC_SPOT_ETF_OUTFLOW_LARGE
2026-05-28: FUNDING_RATE_SPIKE (z=3.2)
```

The LLM receives the last 48h of event tags as a short, structured list — not raw article text.

### 3. Market Microstructure Anomalies (already collected)

Funding z-scores and OI z-scores are already fetched every run. These are the highest-signal, zero-cost inputs. When funding z-score > 3.0, it signals extreme long positioning — the breakdown strategy performs differently in this environment. The LLM learns this from the enriched trade memory without any new data sources.

---

## Cadence: When the LLM Runs

The LLM does **not** run every bar. It runs on three triggers:

---

### Trigger 1 — Daily Scheduled (midnight UTC)

**When:** Once per day, at 00:00 UTC (between NY close and Asia open — least active period).

**What it produces:** The baseline advisory valid for 24h.

**Why midnight UTC specifically:**
- 00:00 UTC = 7pm NY = just after US session close
- Asia session starts ~01:00 UTC, so the advisory is ready before the first liquid session
- Catches overnight macro developments (Asian central bank actions, crypto-specific news)

**What happens if the call fails:**
- Keep the previous day's advisory but set a `stale` flag
- Runtime continues at 50% risk_scalar (conservative default), all strategies allowed, no block
- Log the failure to Matrix

**Typical prompt context:** last 14 days of enriched trades, current regime, last 48h event tags, current microstructure readings.

---

### Trigger 2 — Macro Event (FOMC, CPI, scheduled high-impact events)

**When:** Two sub-cases:

**2a. Scheduled events** (known in advance):
- Pre-event: LLM runs 2h before the event window → advisory likely sets `risk_scalar: 0.25` or `hard_block: true`
- Post-event: LLM runs 1h after event → re-assesses, typically lifts the block or confirms new regime

Example: FOMC announcement at 18:00 UTC → LLM fires at 16:00 UTC (pre) and 19:00 UTC (post).

**2b. Unscheduled crisis events** (exchange hacks, regulatory bans, flash crashes, black swans):

This case requires a fundamentally different response sequence. The LLM cannot be your first line of defense — an API call takes 3-8 seconds, and detection + poller latency adds more. Waiting for the LLM to block entries is too slow.

The correct sequence is two-phase:

```
CRISIS DETECTED
      │
      ├─► [< 30 seconds]  Hard block written IMMEDIATELY — deterministic, no LLM
      │
      └─► [5 minutes later]  LLM fires async → quality advisory for RECOVERY
```

See the dedicated **Crisis Response** section below for full detail.

**Key design point:** The pre-event advisory should almost always reduce risk or block entries. It is not trying to predict the event outcome — it is protecting against the uncertainty window around the event.

---

### Trigger 3 — Regime Change Detection

**When:** `classify_regime()` output changes between consecutive bar evaluations.

This is the most technically nuanced trigger. Three rules govern it:

**Rule A — Significance filter.** Not all regime transitions are equal. Only trigger LLM when the transition crosses a meaningful boundary:

| From | To | Trigger? | Reason |
|---|---|---|---|
| `trend_down` | `high_volatility` | YES | Structural shift, strategy performance changes |
| `trend_down` | `crisis` | YES | Hard block warranted immediately |
| `range` | `breakout_pending` | YES | New opportunity class opening |
| `breakout_pending` | `trend_down` | YES | Breakout confirmed, re-assess parameters |
| `trend_down` | `range` | YES | Momentum dying, composite strategy affected |
| `range` | `range` | NO | No change |
| `trend_up` → `trend_down` | (any) | YES | Direction flip — always trigger |
| `high_volatility` ↔ `crisis` | (oscillation) | Debounce | See Rule B |

**Rule B — Debounce.** If the regime flips between two states more than twice in 6 bars, suppress LLM triggers until the regime has been stable for 3 consecutive bars. This prevents rapid oscillation at a regime boundary from generating dozens of LLM calls and contradictory advisories.

```
Example of debounce triggering:
bar 1: trend_down → high_volatility  [LLM fires]
bar 2: high_volatility → trend_down  [suppressed - too fast]
bar 3: trend_down → high_volatility  [suppressed - too fast]
bar 4: high_volatility (stable)
bar 5: high_volatility (stable)
bar 6: high_volatility (stable for 3 bars) [LLM fires - regime confirmed]
```

**Rule C — Cooldown.** After any LLM trigger (regardless of cause), a minimum 60-minute cooldown applies before the next regime-change trigger can fire. Macro event triggers bypass this cooldown. Daily scheduled trigger always fires regardless.

**What the LLM does differently on a regime-change trigger:**
- The prompt explicitly notes *"regime just changed from X to Y"*
- It retrieves from memory: *"last 5 times regime transitioned from X to Y, here are the outcomes"*
- The advisory may tighten the allowlist (e.g., regime = `high_volatility` → only allow `prev_day_breakdown_v1`, which has tighter stops)

---

---

## Crisis Response (Unscheduled Events)

### Phase A — Instant Deterministic Block

A separate lightweight **crisis scanner** runs every 2-3 minutes. It is pure rule-based Python, no LLM, sub-second execution. It is completely independent of the 1h bar processor.

**Detection thresholds (any one sufficient):**

| Signal | Threshold | Source |
|---|---|---|
| Price drop | BTC drops > 3% in last 15 minutes | 15m candles (already fetched) |
| Volatility spike | Current ATR > 3× 30-day ATR average | Indicators (already computed) |
| OI collapse | Open interest drops > 10% in 1h | OI feed (already fetched) |
| Funding flip | Funding rate sign reversal + z-score > 3.5 | Funding feed (already fetched) |
| Liquidation cascade | Large liquidation volume on Bybit public endpoint | `GET /v5/market/liquidation` (new, free) |
| Breaking news | CryptoPanic returns HIGH severity item in last 10 min | Polling every 2 min (free tier) |

When any threshold fires, the scanner writes `crisis.flag` to the paper dir with a timestamp and reason. The next runner invocation sees this file and sets `hard_block: true` immediately — no LLM call. The flag costs nothing to check and takes under 1ms to read.

The Bybit liquidation endpoint (`GET /v5/market/liquidation`) is the single best new signal here. Liquidation cascades consistently precede the final price drop by 2-5 minutes — it's the earliest available warning for a crash in progress.

### Phase B — LLM Advisory for Recovery (async)

The LLM fires 5 minutes after the crisis flag is set. Its job is not to detect the crisis — that already happened. Its job is to answer: *"given what just happened, when should we resume trading and at what risk level?"*

The crisis prompt is richer than a normal advisory prompt:

```
Crisis event detected at {timestamp}.
Detection trigger: {reason} (e.g., OI dropped 12% in 40 min + funding z-score 3.8)

Market state at detection:
- BTC price: $62,400 (−4.1% from 1h ago)
- Regime: high_volatility
- Funding z-score: 3.8
- News tags (last 2h): [BINANCE_WITHDRAWAL_HALT, LARGE_LIQUIDATION_CASCADE]

Recent strategy performance (last 14 days): {enriched_trades}

Historical similar events from memory:
- 2025-08-14: OI drop 11%, funding spike → regime returned to trend_down after 6h,
  both strategies resumed normally, no missed edge
- 2024-03-05: Exchange hack rumor → hard block 48h, false alarm, missed 2 signals

Your task: classify the crisis type and advise recovery conditions.
Output JSON only. Do not predict price direction.
```

The crisis advisory JSON has **additional fields** not present in normal advisories:

```json
{
  "hard_block": true,
  "block_reason": "liquidation cascade + exchange withdrawal halt rumor",
  "crisis_type": "liquidity_shock",
  "estimated_clear_condition": "regime returns to trend_down for 2 consecutive bars",
  "risk_scalar_on_resume": 0.25,
  "strategy_allowlist_on_resume": ["prev_day_breakdown_v1"],
  "valid_until_utc": "2026-05-29T14:00:00Z",
  "reasoning": "OI collapse of this magnitude typically resolves within 4-8h. Composite strategy avoided on resume due to EMA cross signal unreliability during liquidity recovery."
}
```

`estimated_clear_condition` is the key field. The runtime polls this condition on each bar while the block is active. When satisfied, it automatically lifts the block and applies `risk_scalar_on_resume` instead of normal sizing. The human does not need to manually clear the flag.

### Fast Detection Data Sources

| Source | Latency to detect | Cost | Covers |
|---|---|---|---|
| Price action (15m candles) | ~2 min | Free, already fetched | Flash crash |
| OI delta | ~2 min | Free, already fetched | Liquidation cascade |
| Funding rate flip | ~2 min | Free, already fetched | Leverage unwind |
| Bybit liquidation endpoint | ~1 min | Free, public, new | Earliest crash signal |
| CryptoPanic polling (2 min) | 2-4 min | Free tier | Exchange hacks, regulatory |
| CryptoPanic webhook | < 30 sec | $29/mo | Same, faster |

The first 3 rows are already in the pipeline. Adding the Bybit liquidation endpoint and 2-minute CryptoPanic polling covers 90% of crisis scenarios at zero incremental cost.

### Pre-Warming: Better Crisis Advice Before the Crisis Hits

The LLM gives better advice during a crisis if it already has market context loaded before the event. The daily midnight advisory partially does this, but a dedicated daily **market health check** improves it further:

```json
{
  "date": "2026-05-28",
  "known_risks": ["FOMC in 3 days", "BTC ETF outflow trend ongoing"],
  "microstructure_flags": ["OI at 30-day high", "funding rate approaching extreme"],
  "pre_loaded_summary": "Market is in trend_down, short strategies performing above baseline."
}
```

This document is stored alongside `advisory.json`. When a crisis fires, it is injected directly into the crisis prompt. The LLM connects pre-loaded risk awareness to the new event rather than reconstructing context from scratch.

### What Changes in the Sequence

```
BEFORE (original design — too slow):
  News poller detects tag
  → LLM fires
  → advisory produced (3-8 sec API + detection latency)
  → block applied
  Total latency to block: 3-10 minutes

AFTER (corrected):
  Crisis scanner (price/OI/liquidation/news) detects threshold
  → crisis.flag written immediately
  → hard_block active on next runner tick (< 30 seconds)
  → LLM fires async 5 minutes later
  → quality recovery advisory produced
  Total latency to block: < 30 seconds
  Total latency to quality recovery advice: 5-8 minutes
```

---

## Advisory Priority and Conflict Resolution

When multiple triggers fire close together, higher-priority advisories win:

```
Priority (highest first):
1. Macro event (unscheduled black swan)
2. Macro event (scheduled, post-event)
3. Regime change (crisis involved)
4. Regime change (other)
5. Macro event (scheduled, pre-event)
6. Daily scheduled
```

A lower-priority advisory never overwrites a higher-priority one that hasn't expired. Example: daily midnight advisory fires, then 3h later a regime change trigger fires — the regime-change advisory replaces the daily one (higher priority for that time window).

---

## Default Behavior (No Valid Advisory)

The LLM is an upside-only enhancement. If it's absent, the system must behave sensibly:

| Condition | Runtime Behavior |
|---|---|
| No advisory file exists | `risk_scalar=0.5`, all strategies allowed, no block |
| Advisory file expired | Same as above |
| LLM call timed out | Log to Matrix, keep previous advisory, set `stale=true` |
| Advisory JSON malformed | Log to Matrix, use defaults, alert operator |

The default 50% risk scalar is deliberately conservative — it means a missing LLM is treated as mild uncertainty, not green light.

---

## System Architecture

### New Module: `src/finding_alpha/research/`

```
src/finding_alpha/research/
├── __init__.py
├── advisory.py        — generate_advisory(), validate_advisory(), load_advisory()
├── memory.py          — enrich_trade(), retrieve_similar_windows(), build_memory_context()
├── news_feed.py       — poll_news(), get_fear_greed(), build_event_tags()
└── crisis_scanner.py  — run_crisis_scan(), check_price_drop(), check_oi_collapse(),
                         check_liquidations(), check_news_severity(), write_crisis_flag()
```

### New Files at Runtime

```
paper/
├── advisory.json          — current live advisory (prev_day_breakdown_v1 runner)
├── advisory_log.jsonl     — every advisory generated (audit trail)
├── crisis.flag            — written by crisis scanner, read by runner on each tick
├── market_health.json     — daily pre-warming context (injected into crisis prompts)
└── composite/
    ├── advisory.json      — current live advisory (short_composite_v1 runner)
    ├── advisory_log.jsonl
    ├── crisis.flag
    └── market_health.json
```

### Execution Code Changes (Minimal)

In `src/finding_alpha/paper/runtime.py`, additions to `process_final_bar()` and `run_once()`:

```python
# run_once(): check crisis flag before processing any bars
crisis = load_crisis_flag(cfg.paper_dir)
if crisis.active:
    apply_crisis_hard_block(cfg.paper_dir, crisis)   # writes advisory.json
    trigger_async_llm_crisis_advisory(crisis)         # fires LLM in background
    # runner continues — exits on open positions are still processed

# process_final_bar(): read advisory as before
advisory = load_advisory(cfg.paper_dir)

# Gate 1: hard block (from either crisis scanner or LLM advisory)
if advisory.hard_block and not advisory.is_stale():
    if check_clear_condition(advisory, current_snapshot):
        lift_block(cfg.paper_dir, advisory)   # auto-clears when LLM condition met
    else:
        matrix.append(AdvisoryBlockEvent(...))
        return

# Gate 2: risk scalar
effective_risk_pct = cfg.risk_pct * advisory.risk_scalar

# Gate 3: strategy allowlist
if cfg.strategy_id not in advisory.strategy_allowlist:
    return
```

Everything else in the runtime stays unchanged. Exit processing (stops, TP, timeouts) on open positions is never blocked — the advisory only gates new entries.

---

## LLM Prompt Design Principles

1. **Structured inputs only.** No raw news text. Preprocessed event tags + enriched trade records.
2. **Constrained outputs.** System prompt specifies exact JSON schema and valid field ranges. Use `response_format=json` or equivalent.
3. **Explicit reasoning field.** Advisory JSON includes a `reasoning` string (1-2 sentences). Logged to Matrix. Not used by runtime — purely for auditability.
4. **"No change" is a valid response.** LLM can return `{"action": "no_change"}` — runtime keeps current advisory. Saves tokens on uneventful triggers.
5. **No speculation.** Prompt instructs: "Do not predict price direction. Only assess uncertainty level and which strategies are appropriate for current conditions."

---

## What Phase 9 Builds (Implementation Sequence)

1. `memory.py` — trade enrichment and context retrieval (no LLM yet, just data)
2. `news_feed.py` — event tag poller (Fear & Greed + CryptoPanic free tier)
3. Advisory JSON schema + `load_advisory()` in runtime (with defaults)
4. `crisis_scanner.py` — deterministic detection thresholds + `crisis.flag` writer
5. Crisis flag reader in `run_once()` — instant hard block, no LLM dependency
6. `advisory.py` — LLM call + validation (Claude API, structured output)
7. Daily scheduled trigger wired into both runners (produces `market_health.json`)
8. Regime-change trigger wired into `process_final_bar()` (debounce + cooldown)
9. Macro event calendar (FOMC dates, CPI dates hardcoded for current year)
10. Async crisis LLM trigger (fires 5 min after crisis flag, recovery advisory)
11. `check_clear_condition()` in runtime — auto-lifts block when LLM condition met
12. Audit logging to `advisory_log.jsonl`

Phase 9 does **not** build:
- Vector database (not needed at this data volume)
- Fine-tuning (cold-path RAG is sufficient)
- Any LLM write path to execution state
- Webhook infrastructure (polling every 2 min is sufficient for a 1h system)
