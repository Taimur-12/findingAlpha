# Phase 9 — LLM Advisory Layer: Final Vision

**Date:** 2026-05-29
**Status:** Long-term target. NOT what the accelerated build ships.
**Related docs:**
- `phase9_llm_advisory_layer_design.md` — original design + accelerated-build override (what ships now)
- `FINDING_ALPHA_PHASED_BUILD_PLAN.md` section 0.4 — accelerated build path doctrine

---

## Why this doc exists

The accelerated build (active 2026-05-29) ships a deliberately minimal LLM advisory layer: one daily call, one shared advisory file, three runtime gates (hard_block / allowlist / risk_scalar), no news, no crisis scanner, no regime-change trigger. That gets the LLM wired in fast so the rest of the trading stack can be built around it.

This doc describes the **final intended state** — what the LLM advisory layer grows into once:

1. Micro-live proves the deterministic engine on real capital
2. Multiple months of live trades accumulate enough sample for pattern analysis
3. The system migrates from 1h bars to a tighter timeframe (15m or 10m)
4. Multiple instruments are added (ETHUSDT after BTCUSDT proves out)

The original Phase 9 design specified **four execution paths**: daily, macro event, regime change, and crisis. The accelerated build ships only the daily path. The other three live here as the long-term target, not as discarded ideas.

---

## What the LLM does in the final state

The same one-sentence frame still holds: **the LLM is a risk advisor that writes a bounded JSON advisory the runtime consults before taking entries.** What changes between the accelerated build and the final state is *what data it sees, how often it runs, and how rich its memory is*.

The constraint never changes:
- Hot path stays deterministic
- LLM has zero execution authority
- LLM cannot raise risk above strategy/portfolio config — only reduce or block
- LLM cannot change stops, targets, entry logic, or strategy parameters
- Output is a bounded JSON with clamped numeric ranges

---

## Execution paths (all four)

### Path 1 — Daily scheduled advisory

**When:** 00:00 UTC daily.

**Purpose:** Baseline 24h advisory. Catches overnight macro developments, sets the default policy for the next day.

**Inputs:**
- Full enriched trade memory query: "last 30 days of trades across all strategies, with regime, microstructure z-scores, news tags at entry, outcome R"
- Current market snapshot (regime, ADX, EMA stack, funding z, OI z, ATR percentile)
- Last 48h of news event tags (from news API)
- Macro calendar (events scheduled in next 7 days)
- Pre-warming context from previous day's `market_health.json`
- Cross-instrument context if multiple symbols are live

**Output:** standard advisory JSON valid 24h.

### Path 2 — Scheduled macro event

**When:** Two sub-triggers per known event:
- Pre-event: 2h before scheduled event window
- Post-event: 1h after event window closes

**Purpose:** Tighten risk around scheduled volatility (FOMC, CPI, NFP, BLS data releases, BTC ETF flow reports).

**Inputs:** Same as daily, plus:
- The specific event being addressed (FOMC, CPI, etc.)
- Historical strategy performance around similar past events from memory
- Pre-event microstructure (funding z, OI z trending into the event)

**Output:** Typically reduces `risk_scalar` to 0.25 or sets `hard_block: true` pre-event. Post-event LLM call lifts the block or confirms new regime.

**Key design point:** The pre-event advisory is not trying to predict the event outcome. It is protecting against the uncertainty window around the event.

### Path 3 — Regime change trigger

**When:** `classify_regime()` output changes between consecutive bars AND the transition crosses a significance threshold AND debounce + cooldown rules permit.

**Significance filter:** Only meaningful transitions trigger the LLM. Routine oscillation does not.

| From | To | Trigger? |
|---|---|---|
| `trend_down` | `high_volatility` | YES |
| `trend_down` | `crisis` | YES |
| `range` | `breakout_pending` | YES |
| `breakout_pending` | `trend_down` | YES |
| `trend_down` | `range` | YES |
| `range` | `range` | NO |
| `trend_up` ↔ `trend_down` | (any direction flip) | YES |

**Debounce:** If regime flips between two states more than twice in 6 bars, suppress until stable for 3 consecutive bars. Prevents rapid oscillation from producing contradictory advisories.

**Cooldown:** 60-minute minimum between regime-change-triggered advisories. Macro and crisis triggers bypass cooldown. Daily trigger always fires regardless.

**Inputs:** Same as daily, plus:
- Explicit "regime just changed from X to Y" note in the prompt
- Memory retrieval: "last 5 times this transition happened, here are the strategy outcomes"

**Output:** May tighten allowlist (e.g., `high_volatility` → only allow tight-stop strategies) or reduce `risk_scalar`.

### Path 4 — Crisis response (two-phase)

The slowest LLM call can be 3–8 seconds. That is far too slow to be the first line of defense in a flash crash. So crisis response splits into two phases.

**Phase 4a — Instant deterministic block (no LLM):**

A separate `crisis_scanner.py` process runs every 2–3 minutes. It is pure rule-based Python, sub-second execution, independent of the bar processor.

Detection thresholds (any one triggers):

| Signal | Threshold | Source |
|---|---|---|
| Price drop | BTC drops > 3% in 15 min | 15m candles |
| Volatility spike | Current ATR > 3× 30-day ATR | Indicators |
| OI collapse | Open interest drops > 10% in 1h | OI feed |
| Funding flip | Sign reversal + |z| > 3.5 | Funding feed |
| Liquidation cascade | Large liquidation volume | Bybit `/v5/market/liquidation` |
| Breaking news | HIGH severity item in last 10 min | News API webhook |

When any threshold fires, the scanner writes `paper/crisis.flag`. The next runner tick reads it and sets `hard_block: true` immediately — no LLM call, <30 second total latency.

**Phase 4b — LLM recovery advisory (async):**

Five minutes after the crisis flag is set, the LLM fires asynchronously. Its job is not to detect the crisis — that already happened. Its job is to answer: *"given what just happened, when should we resume trading and at what risk level?"*

Crisis advisory adds these fields to the standard schema:

```json
{
  "crisis_type": "liquidity_shock",
  "estimated_clear_condition": "regime_stable_trend_down_2_bars",
  "risk_scalar_on_resume": 0.25,
  "strategy_allowlist_on_resume": ["prev_day_breakdown_v1"],
  "valid_until_utc": "2026-05-29T14:00:00Z"
}
```

`estimated_clear_condition` is an enum, not free text. Allowed values: `regime_stable_N_bars`, `time_elapsed_Nh`, `oi_recovered`, `funding_normalized`, `manual_clear_required`. The runtime polls the condition each bar; when satisfied, the block auto-lifts and `risk_scalar_on_resume` is applied.

---

## Advisory priority and conflict resolution

When multiple triggers fire close together, higher-priority advisories win:

```
Priority (highest first):
1. Crisis advisory (active block)
2. Macro event (unscheduled black swan)
3. Macro event (scheduled, post-event)
4. Regime change (crisis involved)
5. Regime change (other)
6. Macro event (scheduled, pre-event)
7. Daily scheduled
```

A lower-priority advisory never overwrites a higher-priority one that has not expired.

---

## Data layer — the full picture

The final-state LLM is only as good as the data it can query. The accelerated build feeds it a 14-day window of paper trades + current snapshot. The final state expands this in four dimensions.

### Dimension 1 — Full trade history (backtest + live)

The LLM must see **all** strategy performance, not just live paper. This is essential: live paper alone produces ~50–100 trades/year per strategy at 1h cadence. That is not enough sample for the LLM to reason about *"what works and why."*

Trade memory in the final state combines:

| Source | What it contributes | Format |
|---|---|---|
| Backtest trades | Large sample for pattern statistics (years of data) | `trades_backtest_enriched.jsonl` per strategy |
| Paper trades | Live-data behavior under real microstructure | `trades_paper_enriched.jsonl` |
| Micro-live trades | Real fill quality and slippage | `trades_live_enriched.jsonl` |
| Walk-forward results | Out-of-sample performance per window | `walk_forward_enriched.jsonl` |

Each record carries: strategy, entry/exit times, regime at entry, microstructure z-scores at entry, news tags within 24h of entry, macro tags, outcome R, exit reason. The LLM queries this as a structured store, not a vector DB — until trade count exceeds ~1000, structured filters (regime + macro_tags + funding_z_bucket) are sufficient and far more debuggable than embeddings.

### Dimension 2 — News API

**Source:** CryptoPanic Pro (paid tier, $29/mo) or equivalent. The free tier is insufficient for the 2-min polling cadence required by the crisis scanner.

**What it provides:**
- Crypto-specific headlines tagged by severity (low/medium/high) and category (regulation, exchange, hack, macro)
- Webhook for HIGH severity items (<30 sec latency, drives crisis scanner)
- Polling for routine items (every 5–10 min)

**How the LLM uses it:**
- Daily advisory: last 24h of news tags summarized into a few lines of structured context
- Macro event advisory: news tags within the event window
- Crisis advisory: the specific news item that triggered the crisis scanner (if news-driven)

**What we do not do:** feed raw article text to the LLM. The news API output is preprocessed into structured event tags (`BINANCE_WITHDRAWAL_HALT`, `SEC_LAWSUIT_FILED`, `BTC_ETF_LARGE_INFLOW`) before the LLM sees them.

### Dimension 3 — Macro calendar

Maintained as a small JSON file updated yearly:

```json
{
  "2026-05-30": {"type": "BLS_NFP", "release_time_utc": "12:30"},
  "2026-06-17": {"type": "FOMC_DECISION", "release_time_utc": "18:00"},
  "2026-06-12": {"type": "CPI_RELEASE", "release_time_utc": "12:30"}
}
```

The runtime reads this each tick to determine if a macro event window is approaching (triggering Path 2 advisories).

### Dimension 4 — Pre-warming / market health

A daily `market_health.json` file produced alongside the advisory:

```json
{
  "date": "2026-05-29",
  "known_risks": ["FOMC in 3 days", "BTC ETF outflow trend ongoing"],
  "microstructure_flags": ["OI at 30-day high", "funding rate approaching extreme"],
  "regime_persistence_days": 4,
  "strategy_performance_14d": {
    "prev_day_breakdown_v1": {"trades": 3, "avg_r": 0.2, "win_rate": 0.33},
    "short_composite_v1": {"trades": 8, "avg_r": 0.18, "win_rate": 0.38}
  },
  "pre_loaded_summary": "Market in trend_down. Both short strategies performing slightly above baseline."
}
```

This is injected into every prompt — daily, macro, regime-change, and crisis. It gives the LLM continuity context without having to re-derive it from raw data each call.

---

## What the LLM is asked to analyze

In the final state the LLM is doing more than just "look at recent trades and pick a risk_scalar." It is doing structured pattern analysis on demand:

**Example queries the daily advisory prompt covers:**

1. *"In the last 90 days, what regimes produced positive expectancy for each strategy?"* — drives the allowlist.
2. *"Has microstructure (funding z, OI z) been trending toward extreme readings?"* — drives the risk_scalar.
3. *"Are recent losses concentrated in a particular regime or session?"* — drives strategy-specific blocks.
4. *"Is there a news / macro event in the next 24h that historically affected our strategies?"* — drives pre-event preparation.

The LLM is **not** asked to:
- Predict the direction of BTC
- Pick new entries
- Suggest stop/target adjustments
- Modify strategy parameters
- Read raw OHLCV data

Its output is always the same bounded JSON. Its reasoning lives in the `reasoning` field for audit, but does not change runtime behavior beyond the three gates.

---

## Timeframe migration (1h → 15m or 10m)

The current system runs on 1h bars. The final state migrates to a tighter timeframe (15m as the next step; 10m later if fill quality supports it). This has direct implications for the LLM layer:

| Aspect | 1h (current) | 15m (next) | 10m (later) |
|---|---|---|---|
| Bars per day | 24 | 96 | 144 |
| Runner tick frequency | 1h | 15m | 10m |
| LLM call frequency | Daily only sufficient | Daily + regime-change advised | Daily + regime + sub-daily macro |
| Trade volume per strategy | ~50–100/yr | ~200–400/yr | ~400–700/yr |
| Crisis scanner cadence | Every 2–3 min sufficient | Every 1 min | Sub-minute polling needed |
| Slippage sensitivity | Low (1h moves) | Medium | High — fill quality dominates |

**Implications for the LLM design at 15m / 10m:**

1. Regime-change triggers fire more often → debounce + cooldown rules become critical
2. Trade volume increases → memory grows → eventually justifies vector DB (Phase 14)
3. Macro event windows look proportionally larger relative to bar size → pre-event blocks need to be tighter
4. Crisis scanner becomes the dominant latency-sensitive component — LLM crisis advisory becomes pure recovery guidance, not detection

**Strategies do not automatically work on shorter timeframes.** Each strategy must be re-validated on 15m data before the migration. The LLM layer itself is timeframe-agnostic — it reads features and regimes, not raw bars.

---

## Memory architecture in the final state

### Storage layer — open question

The final state needs a proper data store that holds **every type of data the LLM consumes**: trade ledger (backtest + paper + live), daily market health snapshots, news event tag archives, macro calendar, advisory log, walk-forward windows, microstructure series. The *shape* of this store is not yet decided.

Candidates to evaluate when the time comes:

| Option | When it fits |
|---|---|
| **Structured JSONL on disk** (current) | Trade count < ~1000, single-developer, no concurrent readers. Cheapest, most debuggable. |
| **SQLite** | Trade count 1000–100k, need joins (trades × regime × news_tag), still single-machine. |
| **Postgres / TimescaleDB** | Multiple writers, durable history, time-series queries on microstructure features, dashboard backend. |
| **Data warehouse (DuckDB, ClickHouse)** | Analytical scans across years of bars + trades for offline research. Read-heavy, append-only. |
| **Vector DB (Chroma, Qdrant, pgvector)** | Only when the LLM needs semantic retrieval — "find trade contexts *similar to today's setup*" — which requires fuzzy matching across many features. Not justified until structured filters fail to give clean retrieval. |

**Near-term decision (2026-05-30):** Phase 11.5 in the build plan commits to **DuckDB on top of Parquet** as the analytical store. JSONL stays as the append-only hot-path log; a daily compaction job rolls JSONL into Parquet; DuckDB exposes views over the Parquet files. Zero ops, free, SQL-queryable, scales to billions of rows on a laptop. This is the project's "Palantir-equivalent step" at retail scale — without buying Palantir.

Migration to TimescaleDB / ClickHouse / vector DB only happens when DuckDB hits a real limit (concurrent writers, semantic retrieval, billions of rows). At current scale that is years away.

What matters more than the storage backend is the **schema**: every record (trade, advisory, market_health) is enriched with the same set of fields (regime, microstructure z-scores, news tags, macro tags, timestamps in UTC) so any future store can ingest the existing JSONL without translation.

### Accelerated-build layout (active now)

```
data/memory/
├── trades_enriched.jsonl        — unified across backtest + paper + live, all strategies
├── walk_forward_enriched.jsonl  — out-of-sample window results
├── market_health/
│   ├── 2026-05-29.json
│   ├── 2026-05-30.json
│   └── ...                      — daily snapshots, ~365/year per instrument
├── news_tags/
│   ├── 2026-05.jsonl            — monthly news event tag archive
│   └── ...
├── macro_calendar.json          — yearly maintained
└── advisory_log.jsonl           — every advisory ever generated, full audit
```

**Query patterns the memory layer supports:**

- "Last N days of trades for strategy X in regime Y" — filtered scan
- "Trade outcomes when funding_z was in bucket [2.0, 3.0]" — filtered scan
- "Days where market_health flagged 'OI at 30-day high'" — daily snapshot scan
- "Last K LLM advisories produced and their downstream outcomes" — advisory_log scan + outcome correlation

JSONL is the starting point. Migration to a structured store happens when one of the forcing conditions in the table above triggers.

---

## What must be true before promoting from accelerated to final

The accelerated build must accumulate this evidence before features from this doc are layered in:

1. **Daily LLM advisory has produced a stable advisory.json for 4+ weeks** without runtime errors
2. **Advisory log is reviewable** — every entry has prompt_version, model_id, reasoning, and the actual JSON
3. **Counterfactual scorecard exists** — for each day the LLM blocked or down-scaled, what would have happened without the gate
4. **Net advisory value is positive** — blocks/scaling reduce drawdown more than they cost in missed upside
5. **Trade count is sufficient** to justify memory expansion — at least ~50 closed trades across strategies
6. **Micro-live has run** for some sample — the LLM needs to see real fill data, not just paper assumptions

Only then do the deferred features get built in this order:

1. News API integration (CryptoPanic Pro)
2. Macro calendar + scheduled-event triggers (Path 2)
3. Regime-change triggers (Path 3) with debounce + cooldown
4. Crisis scanner deterministic detection (Phase 4a)
5. Crisis LLM recovery advisory (Phase 4b) with enum clear conditions
6. Cross-instrument context (after ETHUSDT added)
7. Vector memory (only if trade count exceeds threshold)

---

## Cost budget at the final state

| Component | Frequency | Monthly cost estimate |
|---|---|---|
| Daily advisory | 1/day | ~$2 |
| Macro event advisories | ~6/month | ~$1 |
| Regime change advisories | ~10/month | ~$2 |
| Crisis advisories | rare, ~1/month avg | ~$0.50 |
| CryptoPanic Pro subscription | continuous | $29 |
| **Total** | | **~$35/month** |

Anthropic API costs are dominated by the subscription fee, not the per-call cost. The LLM advisory layer is operationally cheap — the engineering complexity is the real cost, which is why the accelerated build defers most of it.

---

## What this doc is not

- Not a current-build spec. The accelerated build is the current spec.
- Not a promise to build all of this. Each component above gets built only when the simpler version proves it is needed.
- Not a substitute for the original `phase9_llm_advisory_layer_design.md` — that doc has the detailed rationale for individual decisions (debounce timing, crisis thresholds, etc.). This doc is the architectural overview.

The next time this doc is opened should be after the accelerated build has been running for 4+ weeks and there is real evidence to decide which deferred component to build next.
