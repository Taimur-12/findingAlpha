# Code-vs-Plan Audit — what's built vs the updated architecture

**Date:** 2026-06-03
**Method:** Read the actual `.py` source under `src/finding_alpha/`, `dashboard/`, `notebooks/` (no `.md` docs read). Compared against `apex_quant_architecture_and_stack_2026_06.md` (the 8-layer target) and `apex_quant_updated_build_plan_2026_06.md` (phases A–G).
**Legend:** ✅ built & solid · 🟡 partial / lite · ❌ not started

---

## Headline

What exists today is the **deterministic trading spine** — the part that touches real money safely — plus a candle-level feature pipeline, rule-based strategies, walk-forward validation, an append-only event log, a Streamlit dashboard, and a genuinely strong test suite. In build-plan terms this is exactly the **"de-risked core" (Layers 1-lite / 4-rules / 5-lite / 6-risk / 7-execution + advisory)**.

What is **not** built is the entire APEX upgrade: microstructure & alt-data, proper databases, the research/knowledge engine, signal discovery, *all* ML (GBDT / meta-labels / HMM), fund-grade validation (CPCV / Monte-Carlo / quarantine ladder), both-directions + funding strategies, the meta-learner, multi-asset, and cloud deployment.

**Where we are on the roadmap:** at the **start of Phase A/B**. The spine is done; the APEX layers on top of it are greenfield.

| Layer | Status | One-line |
|---|---|---|
| L1 Data Foundation | 🟡 | Solid single-asset *candle*-level features; no microstructure/alt-data/streaming/proper-DB |
| L2 Research & Knowledge | 🟡 | Only the LLM advisory *gate* exists (and its generator is a stub); no research/sentiment/graph |
| L3 Signal Discovery | ❌ | Nothing — strategies are hand-written; only manual param sweeps exist |
| L4 Strategy / Agent | 🟡 | Real rule strategies + rule regime gate, but short-only, no ML, no meta-labels, no HMM |
| L5 Validation | 🟡 | Honest walk-forward + cost-aware metrics; **no CPCV / MC / regime-buckets / quarantine ladder** |
| L6 Decision | ✅ | Best-aligned layer — fixed-fractional sizing + 8 hard risk rules, fully deterministic |
| L7 Execution | ✅ | Live-verified Bybit client + 11-state machine + reconciliation; the real strength |
| L8 Meta / Observability | 🟡 | Great event-log/audit substrate + dashboard; no decay/correlation/feedback loop |

---

## Layer-by-layer detail

### L1 — Data Foundation 🟡
**Built**
- ✅ Candle / funding / OI loaders for Bybit + Binance — `data/bybit_loader.py`, `data/binance_loader.py`, `live/feed.py`
- ✅ Schema normalizer + data-quality checks (gaps, dupes, zero-volume) — `data/normalizer.py`, `data/quality.py`
- ✅ Local **Parquet** persistence — `data/storage.py`
- ✅ Feature computation: RSI/MACD/EMA/ATR/Bollinger/ADX/Supertrend/VWAP (`features/indicators.py`), volume/funding/OI z-scores (`features/orderflow.py`), session & prior-period levels (`features/structure.py`)
- ✅ Point-in-time `merge_asof` for funding/OI with staleness flags — `features/orderflow.py`
- ✅ `FeatureSnapshot` contract + builder — `features/snapshot.py`, `contracts/features.py`

**Not built (vs architecture)**
- ❌ **L2 order book** (no imbalance/depth) and ❌ **trades/aggressor → CVD** — only OHLCV. CVD is in the arch doc but absent in code.
- ❌ Liquidation feed · ❌ on-chain feeds · ❌ macro feeds · ❌ sentiment stream
- ❌ **ClickHouse / Redis / R2** — storage is local Parquet + JSON files
- ❌ **Bytewax streaming** — feed is REST polling (`live/feed.py`, ~60s)
- ❌ Rust collectors · ❌ thin feature-access layer (features are recomputed per run)
- ❌ **Multi-asset** — BTCUSDT throughout

### L2 — Research & Knowledge 🟡
**Built**
- 🟡 LLM advisory **gate**: `ResearchState` load/validate/save + three gates (hard-block, strategy allowlist, risk scalar) — `research/advisory.py`. Consumed by risk/coordinator.

**Not built**
- ❌ The advisory **generator is a stub** returning a permissive default (`research/advisory.py:98` `generate_advisory`); the live Claude call lives only in a notebook runner.
- ❌ Research ingestion (arXiv/SSRN/news/social) · ❌ FinBERT sentiment · ❌ **Neo4j graph** · ❌ pgvector · ❌ hypothesis schema · ❌ formal quarantine/graveyard

### L3 — Signal Discovery ❌
- ❌ No GBDT/SHAP discovery, no RuleFit, no microstructure signals (Kyle's λ etc.). Strategies are hand-coded.
- 🟡 Closest analog: `validation/research_grid.py` (manual parameter sweeps) + the `notebooks/research/*` sweep scripts — useful, but manual grid search, not a discovery engine.

### L4 — Strategy / Agent 🟡
**Built**
- ✅ Rule-based strategies — `strategies/`: `ema_scalp_15m_v1`, `prev_day_breakdown_v1`, `short_composite_v1`, plus research variants (`squeeze_v1`, `liquidity_sweep_v1`, `trend_pullback_v1`, `prev_day_breakout_v1`, `ema_scalp_1m_v1`)
- ✅ Rule-based **regime classifier** (7 regimes, deterministic, with per-regime strategy blocks) — `regime/classifier.py`
- ✅ `SignalCandidate` contract + a `fast_reject` pre-filter

**Not built**
- ❌ **Both-directions** — strategies are SHORT-only (the known #1 weakness); no **funding-rate mean-reversion** strategy
- ❌ GBDT **meta-labeling** + triple-barrier labels · ❌ **HMM** regime (rule-based only) · ❌ MLflow

### L5 — Validation 🟡
**Built**
- ✅ Walk-forward windows + runner — `validation/walk_forward.py`
- ✅ Event-driven validation runner (560 lines) — `validation/event_runner.py`
- ✅ Cost-aware metrics (expectancy R, profit factor, max DD, fee share, per-strategy) — `analytics/metrics.py`; fees/slippage in `PortfolioConfig`
- 🟡 Reporting + a NautilusTrader **spike** (`notebooks/research/phase1_nautilus_spike.py`) — explored, not integrated

**Not built (the crown jewel is missing)**
- ❌ **CPCV** (combinatorial purged CV) — only plain walk-forward
- ❌ Regime-bucketed stress test · ❌ cost-sensitivity sweep (0–20 bps) · ❌ **block-bootstrap Monte Carlo**
- ❌ **Quarantine ladder** as promotion states (shadow → paper → micro-live) — informal only
- ❌ vectorbt · ❌ NautilusTrader integration (spike only)

### L6 — Decision ✅ (best-aligned layer)
**Built**
- ✅ **Fixed-fractional sizing** (risk %, leverage cap, min-notional gate, qty-precision floor) — `portfolio/agent.py`
- ✅ **8 hard risk checks** in strict order (circuit breaker → research block → stale data → funding stale → daily loss → drawdown → max positions → heat) — `risk/agent.py`
- ✅ Coordinator: multi-signal dedup, ranked-by-confidence, running-heat accounting — `coordinator/coordinator.py`
- ✅ Fully deterministic, pure Python — exactly matches "deterministic now" staging
- ✅ Correctly **no** Kelly/Bayesian/vol-targeting yet (matches the staged-by-assumption plan)

**Not built**
- ❌ **Fee-aware entry threshold** (from `execution_fee_minimization_2026_06.md`)
- ❌ Cross-strategy **weighting / allocation** (coordinator dedups but doesn't weight)

### L7 — Execution ✅ (the real strength)
**Built**
- ✅ Bybit V5 client with unwrap pattern — `execution/bybit_client.py`
- ✅ 11-state **order state machine** — `execution/order_state.py`
- ✅ Execution agent: entry + protective stop, **deterministic `orderLinkId` idempotency**, `reconcile_leg` ground-truth recovery — `execution/execution_agent.py`
- ✅ **Reconciliation**: detects unprotected / ghost / missing / state-mismatch positions — `execution/reconciliation.py`
- ✅ Live runtime + state persistence — `paper/live_execution.py`, `paper/runtime.py`, `paper/state.py`
- ✅ Emergency closer (market → limit+chase) — `notebooks/close_position.py`

**Not built**
- ❌ **CCXT / multi-exchange** — single Bybit client only
- ❌ Fee policy from the fee doc: **post-only-with-chase**, maker/taker decision, funding-stamp avoidance (entry is plain limit GTC)
- ❌ Take-profit legs (intentionally deferred — strategies exit on stop/time)

### L8 — Meta-Learner & Observability 🟡
**Built**
- ✅ **Matrix event log** — append-only, immutable, deterministic replay, in-memory projections — `matrix/event_log.py` (excellent audit/observability substrate)
- ✅ Per-strategy analytics — `analytics/metrics.py`
- ✅ Streamlit dashboard (overview, KPIs, risk monitor, advisory, trade log, live control) — `dashboard/`

**Not built**
- ❌ **Strategy-decay monitor** (rolling live ÷ backtest Sharpe) · ❌ **correlation-capped allocation**
- ❌ Feedback loop back to L6/L4/L2 · ❌ Grafana / Prometheus / Loki / Sentry (Streamlit only)

---

## Cross-cutting / infrastructure

| Concern | Target | Built | Status |
|---|---|---|---|
| Storage | ClickHouse + Postgres + Redis + R2 | Local Parquet + JSON/JSONL files | ❌ |
| Hosting | DigitalOcean/Oracle cloud box | Local laptop, manual runs | ❌ |
| Scheduling | cron on server → Dagster | Manual notebook runners / dashboard button | ❌ |
| Containers | Docker Compose | none | ❌ |
| Event bus | (deferred) | none | ✅ (correctly absent) |
| Observability | Grafana + Sentry | Streamlit dashboard | 🟡 |
| Tests | — | ~12 test files, deep coverage (`test_execution.py` 669, `test_paper.py` 511, `test_live_execution.py` 455, …) | ✅ strong |
| Multi-asset | many cryptos | BTCUSDT only | ❌ |

---

## ML doctrine status

The entire ML half of the plan is **greenfield** — and that's consistent with "hot path stays deterministic," but it means the *offline* ML work hasn't started:

| Technique (per §3 doctrine) | Built? |
|---|---|
| GBDT (LightGBM/CatBoost) | ❌ |
| Meta-labeling + triple-barrier | ❌ |
| CPCV / purged CV | ❌ |
| Block-bootstrap Monte Carlo | ❌ |
| HMM regime | ❌ (rule-based regime instead) |
| FinBERT / quantified sentiment | ❌ |

The current system is **100% deterministic rules** end-to-end — which is the safe core, but the discovery/meta-label/regime-ML/validation-rigor upgrades are all still to build.

---

## What this means for the phases (build plan A–G)

- **Phase A (stabilize + honest baseline):** mostly a cleanup of existing live-testnet state + re-scoring existing strategies. The code to *run* exists; the honest re-baseline doesn't.
- **Phase B (validation engine — CPCV/MC/regime-buckets/cost-sweep):** ❌ **not started.** This is the highest-trust-per-hour gap and the doc's crown jewel. We have walk-forward + cost-aware metrics to build on, but the fund-grade pieces are missing.
- **Phase C (data depth — order book/CVD/liquidations, cloud VM, ClickHouse):** ❌ not started.
- **Phase D (both-directions + meta-labeling — funding-MR strategy, GBDT meta-labels):** ❌ not started; directly fixes the short-only weakness.
- **Phase E (decision + regime ML — HMM, multi-strategy weights):** ❌ not started (L6 deterministic base is ready to receive it).
- **Phase F (prove real profit in paper):** ❌ gated on B–E.
- **Phase G (micro-live + meta-learner):** ❌ gated.

**Strongest foundations to build on:** L6 (risk/sizing), L7 (execution/reconciliation), the matrix event log, the contracts, and the test suite. **Biggest gaps to close first:** Phase B (CPCV/MC validation) and the both-directions/funding-MR strategy — those two unlock honest measurement and fix the #1 weakness, before any data-depth or ML spend.
