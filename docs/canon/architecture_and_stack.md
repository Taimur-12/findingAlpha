# APEX QUANT — Consolidated Architecture, Inputs & Tech Stack

**Date:** 2026-06-01
**Companion to:** `apex_quant_updated_build_plan_2026_06.md` (the phased build plan).
**Purpose:** The single source of truth for the system's layers — what each one *does*, what *flows into it*, what it emits, and the **decided production tech stack** for each. This is "ours" — a consolidation of our build and the partners' APEX blueprint, not a lite version of either.

## Design decisions baked in here
- **Production-grade from day one, but right-sized** — proper tools, not maximal infra. Deferrals and three "stopped short" calls are documented in the staged-infrastructure table near the end.
- **Multi-asset by design.** The product targets multiple cryptocurrencies; **BTC is the first test market, not the scope.** Single-asset simplifications are temporary — and several infra choices (Rust collectors, the Neo4j knowledge graph, feature management) are justified by the multi-asset target even though BTC-only wouldn't need them yet.
- **Functionality-first right-sizing.** The bar is *capability*, not size. We accept simpler tools or a smaller deployment **as long as the functionality exists** — we do not drop a capability to save ops. We defer or simplify only when the same functionality is delivered more simply, or genuinely isn't needed until a later scale (see the staged-infrastructure table).
- **Sentiment & world events are a first-class, real-time input from the start** — not deferred. BTC is narrative- and sentiment-reflexive; we must see *what's happening in the world*, not just the market numbers.
- **The old strategies are not an anchor.** They were thin and barely traded (~20 trades = noise). The strategy layer is designed fresh around the richer data below, both directions, with real sample sizes.
- **Hot path stays deterministic.** ML trains offline and is consumed as frozen, inspectable scores. ML never invents a trade or overrides a stop.

---

## How to read each layer

Every layer below is described as four blocks:
- **Function** — what it does.
- **Inputs** — specifically what flows in, and from where.
- **Outputs** — what it emits downstream.
- **Tech** — the decided stack.

---

## L1 — Data Foundation

**Function.** Ingests everything the system can see, normalizes it into canonical events, computes features in-stream, and serves them with guaranteed train/serve consistency across three storage tiers (hot / warm / cold).

**Inputs.**
- **Exchange real-time feeds** (Bybit, Binance, OKX WebSocket + REST):
  - Trades: `price`, `size`, `aggressor_side` (buyer/seller-taker), `timestamp`
  - L2 order book deltas: bid/ask `price` × `size` per level, ~100ms snapshots
  - Candles: 1m / 15m / 1h OHLCV
  - Funding: current 8h rate + predicted rate, per exchange
  - Open interest: contracts + USD notional, per exchange
  - Liquidation events: `size`, `side`, `price`, `exchange` (raw feed, not aggregated)
- **On-chain feeds** (vendor APIs — CryptoQuant / Amberdata now, Glassnode/Nansen at scale): exchange netflow, whale-wallet accumulation/distribution, miner outflow, UTXO age bands, stablecoin (USDT/USDC) supply delta, transaction-fee rate
- **Macro feeds**: DXY, S&P 500 / Nasdaq, gold, Fed rate expectations (risk-on/risk-off context)
- **Sentiment/world raw stream** (handed up from L2's classifier, then stored as features here): per-event sentiment score, social-volume z-score, fear/greed index, regulatory event flags

**Outputs.**
- Canonical event streams on the bus (one topic per data type)
- Computed features: order-book imbalance, CVD (5/15/60m), funding z-score, OI delta z-score, realized vol, liquidation-proximity score, sentiment score — written to hot/warm/cold
- A single **feature-store API** every other layer reads from (no layer recomputes features)
- *Example output:* `feature_store.get("BTCUSDT", t=12:00:00) → {ob_imbalance: 0.72, cvd_15m: -412, funding_z: 2.3, oi_delta_z: 1.8, realized_vol_1h: 0.041, liq_proximity: 0.6, sentiment_score: -0.40}` — context-free numbers, no opinion attached.

**Tech.** Rust collectors (hot path, justified by multi-asset throughput) + Python async (rest) → **Bytewax** (streaming feature computation; **fall back to micro-batch Polars** if Bytewax gives us trouble) → **Redis 7** (hot, sub-ms live features), **ClickHouse** (warm, queryable tick/book history — uses native **`ASOF JOIN`** for point-in-time-correct, leakage-free feature reads), **Parquet on Cloudflare R2** (cold archive). **Feature access:** a **thin in-house layer** — one `get_features(symbol, t)` API over ClickHouse + Redis that both training and live code call (kills train/serve skew) — *not* a full feature-store framework (Feast was dropped: ~0.3 FTE to run, and it doesn't even do the realtime compute we need). Dataframes: **Polars**. **Event bus (Redpanda)** is **deferred** — re-enters with multi-asset, when multiple consumers / durable replay justify it (see staged-infrastructure table).

---

## L2 — Research & Knowledge Engine

**Function.** Reads the world on two streams: (a) academic/strategy research → structured hypotheses → knowledge graph → quarantine; (b) real-time news/social/sentiment → quantified features + hard event-flags. Owns the **graveyard** of failed hypotheses.

**Inputs.**
- **Research sources**: arXiv (q-fin, cs.LG), SSRN finance working papers, crypto research (Messari, Chainalysis), GitHub trending quant/crypto repos — fetched daily
- **Real-time world feeds**: CryptoPanic, NewsAPI, X/Twitter API, Reddit API, regulatory-filing monitors (SEC/CFTC/MiCA)
- **From L1**: market context for tagging events (e.g. attach price/vol state to a news item)
- **Human input**: manual hypotheses from us / the partners
- **From L8 (feedback)**: strategy-decay and failure events to record in the graveyard with cause

**Outputs.**
- Structured hypothesis records (`strategy_type`, `signals`, `data_required`, `claimed_edge`, `mechanism`, `novelty_score`, `conflicts_with`) → quarantine queue (consumed by L3/L5)
- **Sentiment features & event flags** → pushed into L1's feature store (e.g. `sentiment_score`, `social_vol_z`, `regulatory_event=true → reduce_risk`)
- Knowledge-graph nodes/edges (strategy ↔ signal ↔ regime ↔ paper ↔ outcome)
- Graveyard entries (failed hypothesis + fingerprint + reason)
- *Example output:* a hypothesis record `{strategy_type: "funding_mean_reversion", signals: ["funding_z>2", "price_vs_vwap"], claimed_edge: "+0.3R fading funding extremes", mechanism: "overleveraged longs pay to hold → snapback", novelty_score: 0.3, conflicts_with: none}` → quarantine queue; **and** a feature push to L1: `{sentiment_score: -0.40, social_vol_z: 2.1, regulatory_event: false}`.

**Tech.** Python ingest + **Claude API** (paper→hypothesis extraction, nuanced sentiment). **Neo4j Community** (knowledge graph — free; see note). **CryptoBERT/FinBERT** (quantified sentiment, cheap to run — kept from the start) + Claude (nuance). **pgvector in Postgres** (embeddings for semantic search / dedup of news & papers) — avoids a separate vector service early; a dedicated vector DB (Qdrant) re-enters only if embedding volume outgrows pgvector.

> **Why the Neo4j graph (and why multi-asset justifies it).** The graph stores relationships: `strategy ↔ signal ↔ regime ↔ source-paper ↔ outcome`, plus the graveyard. Its job is **relationship memory + conflict detection + graveyard similarity** — before testing a new signal, L3 asks the graph "what have we tried like this, what's it connected to, did a cousin of this already fail and why." A graph DB beats Postgres specifically when you do **multi-hop traversal** ("find strategies two hops away that share a signal with a failed strategy in the same regime cluster"). On one asset that's overkill; **across many cryptos** the strategy↔signal↔regime↔asset web explodes and multi-hop "what's related / what conflicts" becomes a real, frequent query — Neo4j's home turf. That's the functionality; we keep it.

---

## L3 — Signal Discovery

**Function.** Turns raw features into ranked *candidate* signals before any strategy commits. Finds multi-condition setups, builds microstructure signals, screens for genuine predictive value.

**Inputs.**
- **From L1 feature store**: the full feature set as time series (microstructure, funding, OI, on-chain, sentiment, macro)
- **From L2**: hypotheses from the quarantine queue to test; knowledge-graph context (what's been tried, what conflicts)
- **From graveyard**: fingerprints of known-failed patterns (so we don't re-discover dead ends)

**Outputs.**
- Ranked candidate signals (each with the conditions, the hypothesized mechanism, out-of-sample lift + SHAP importance, and the data it needs) → into quarantine for L5 validation
- Microstructure signal series (Kyle's lambda, toxic-flow proxy/VPIN, book-thinning) → available as features. *Note:* these are noisy to estimate at our data quality — keep a couple as research inputs, don't over-invest. (Iceberg detection dropped — genuinely hard, low-ROI rabbit hole.)
- *Example output:* a discovered pattern (RuleFit rule extracted from the GBDT, ranked by SHAP) — `{rule: "funding_z>2 AND cvd_15m falling AND regime=bear", outcome: "4h forward return positive", oos_lift: 1.6, support: 0.03, shap_rank: top-5, mechanism: "funding-paid longs unwind"}`. A *finding*, not a trade — no entry/stop/target yet.

**Tech.** **Polars** (feature computation) + **LightGBM** (the discovery engine — a GBDT's split paths *are* the multi-condition combinations) + **SHAP** (feature importance & interaction discovery). Optional readability: **RuleFit via `imodels`** to extract human-readable `IF A AND B THEN` rules. **Genetic programming / symbolic regression** (`gplearn` or a modern alpha-mining framework) for *formulaic* alpha discovery is **staged later** — heavier and overfit-prone, gated behind CPCV. *Dropped: mlxtend / FP-Growth* — a market-basket / association-mining tool that false-discovers on correlated financial series (the exact failure CPCV exists to catch), and not a quant-alpha technique.

---

## L4 — Strategy / Agent Layer

**Function.** Produces directional trade intents. Multiple independent strategies, **both directions**, each = primary logic + a GBDT meta-label filter ("should we take *this* signal?") + a regime gate. A separate non-trading HMM regime engine broadcasts market state to all of them.

**Inputs.**
- **From L1 feature store**: live + historical features for each strategy's specific signals
- **From L3**: validated candidate signals promoted into live strategies
- **From the regime engine** (within this layer): current regime label + transition probabilities
- **From L2**: sentiment scores and event flags (used both as features and as gates)
- **From L8 (feedback)**: each strategy's current weight / down-weight status

**Outputs.**
- Per-strategy `SignalCandidate`: `direction`, `entry`, `stop`, `target`, `confidence`, `strategy_id`, `regime_at_signal` → to L6
- Regime state broadcast → to L6 and L8
- *Example output:* `SignalCandidate{strategy_id: "funding_mr_v1", direction: SHORT, entry: 67420, stop: 68100, target: 66050, confidence: 0.68, regime_at_signal: "bear_trend"}` (meta-label passed: 0.68 > 0.55 threshold; regime gate allowed). Plus the regime broadcast `{regime: "bear_trend", p_transition→range: 0.18}`. Now it's an actual *trade plan*, not just a finding.

**Tech.** **LightGBM** (primary) + **CatBoost** (challenger, benchmarked specifically for its overfit-resistance via ordered boosting — overfitting is our central enemy) for meta-labels + primary tabular models. **hmmlearn** Gaussian HMM as the regime v1 (gives probabilistic states + transition odds — the functionality we want); **HDBSCAN** kept as an *experimental* alternative, not the default (clustered regimes can be unstable across refits, so it must prove itself before it's load-bearing). **MLflow** (model/version tracking). **PyTorch** reserved for later sequence models, only once GBDT plateaus. *XGBoost dropped from the headline* — fine, but adds nothing over LightGBM for us.

---

## L5 — Validation Engine

**Function.** Proves a signal/strategy before it touches capital and keeps proving it after. Runs the quarantine ladder (shadow → paper → micro-live), promotes survivors, buries failures.

**Inputs.**
- **From L4 / L3**: the strategy or candidate-signal definition to test
- **From L1 cold store**: full historical feature + price data (ClickHouse / Parquet)
- **From L2**: regime labels for bucketing; graveyard fingerprints for similarity screening
- **Cost assumptions**: fee, slippage (0–20 bps sweep), full 8h funding model

**Outputs.**
- A full validation report per strategy: CPCV out-of-sample metrics, per-regime performance, cost-sensitivity curve, 5th-percentile Monte-Carlo outcome, walk-forward
- A promote / extend / bury verdict (failures → graveyard with reason)
- *Example output:* `funding_mr_v1 → {cpcv_oos_sharpe: 1.1, profit_factor: 1.3, by_regime: {bear: +0.4R, range: +0.2R, bull: -0.1R}, mc_5th_pct: -8%, cost_breakeven: 14bps, trades: 340} → VERDICT: promote to Q2 paper}`. A *verdict*, computed offline — the runtime later just reads "promoted".

**Tech.** **NautilusTrader** (event-driven, backtest/live parity), **vectorbt** (fast research sweeps), **custom CPCV + NumPy** (purged combinatorial CV, block-bootstrap Monte Carlo).

### L5 — The quarantine ladder

The quarantine ladder is the staged promotion pipeline a strategy must climb before it is allowed to touch real money — and keeps being checked after. A signal discovered in L3 doesn't go live; it earns its way up, one rung at a time, and a failure at any rung gets **buried in the graveyard with the reason it died** (L2).

| Rung | What happens | Real money? | Typical dwell |
|---|---|---|---|
| **0 — Backtest / CPCV** | Run on full history through CPCV + regime buckets + cost sweep + block-bootstrap Monte Carlo. The honest out-of-sample gate. | none | hours (one batch run) |
| **Q1 — Shadow** | Runs on **live** data but places **no orders** — only logs the trade it *would* have made, then compares to its backtest expectation. Catches "looked great on history, behaves nothing like it live." | none | days–weeks |
| **Q2 — Paper** | Trades fake money on the **real exchange** (testnet) — real fills, real slippage, real funding, real latency. | none | weeks |
| **Q3 — Micro-live** | Tiny real capital behind a hard, low position cap. The first time a wrong decision actually costs something. | minimal | weeks–months |
| **Promoted** | Full allocation. L8 keeps watching rolling live-vs-backtest Sharpe and can **demote** on decay. | yes | ongoing |

Each rung has an explicit promote / extend / bury gate; nothing skips a rung.

**Why this doesn't slow live trading (the key design point).** The ladder runs **out-of-band**, not in the hot path. It is the *hiring committee, not the trader on the desk*:

- The slow work (rung 0's CPCV / Monte Carlo — minutes to hours) runs **offline on historical data**, orchestrated on a schedule by **Dagster** (nightly, or when a new strategy is submitted). It never touches the latency of an actual order.
- At runtime the live loop does one cheap thing: check **"is this strategy in `promoted` state?"** — a lookup — then evaluate the frozen strategy function. Microseconds.
- A strategy graduates over **days and weeks**, not per-signal and not per-millisecond. The expensive thinking happens *before* a strategy is live; the runtime only executes an already-proven, frozen verdict.

This is the same principle as keeping ML out of the hot path: heavy validation offline, frozen/fast decisions online.

---

## L6 — Decision Layer

**Function.** The portfolio manager — the only component allowed to authorize a trade. Aggregates active strategies, applies regime posture, sizes the position, enforces non-negotiable risk rules. Fully deterministic.

**Inputs.**
- **From L4**: all active strategies' `SignalCandidate`s (direction, entry, stop, target, confidence)
- **From the regime engine**: current regime + transition odds
- **From L2**: real-time event flags (e.g. regulatory halt → block/scale-down) and the Claude advisory read
- **From L8**: current strategy weights, pairwise correlation matrix, capital allocation, circuit-breaker state
- **From risk state**: open positions, equity, drawdown, daily P&L
- **From L1 (live)**: latest mark price, spread, realized vol (for risk-based sizing now; vol-targeting / Kelly inputs later — see staging below)

**Outputs.**
- A single authorized **order intent**: `symbol`, `side`, `size`, `entry_type`, `stop`, `target`, `urgency` → to L7
- Or an explicit no-trade decision with reason code → logged to the matrix
- *Example output:* `OrderIntent{symbol: "BTCUSDT", side: SHORT, size: 0.012, entry_type: limit, stop: 68100, target: 66050, urgency: normal}` — sized fixed-fractional off the stop, passed every hard rule. **Or**, if a rule blocks it: `NoTrade{reason: "DAILY_LOSS_CAP_HIT"}`. The first component allowed to *authorize* — exactly one decision out.

**Tech.** **Pure Python, deterministic** (no framework in the hot path). Hard-rule + circuit-breaker engine (our existing risk agent, extended) + **fixed-fractional position sizing** as the baseline. Probabilistic sizing/weighting (volatility targeting, fractional Kelly, Bayesian posterior weighting) is **staged by assumption** — see below — and implemented in NumPy only once each earns its place.

### L6 — Sizing & weighting, staged by assumption

> **Why this changed (revision 2026-06-01).** The first draft put Bayesian posterior weighting + fractional Kelly × volatility targeting into L6 *from the start*. That was wrong: **"deterministic at runtime" is not "assumption-free."** A frozen formula still bakes in whatever statistical model was assumed when it was written, and on small live samples those assumptions are exactly where systems blow up. We replace **"probabilistic from day one"** with **"deterministic now, probabilistic when earned."** Nothing is discarded — each technique stays on the roadmap behind an explicit re-entry gate, and every probabilistic upgrade must beat the simpler baseline under L5 (CPCV) validation *before* it touches live capital.

| Technique | Hidden assumption | Use now? | Baseline it's replaced with | Re-enters when… |
|---|---|---|---|---|
| Hard rules + circuit breakers | none — pure guardrail | **Yes** | — (keep as-is) | — |
| Fixed-fractional sizing (risk % per trade, defined by the stop) | only that the stop defines the risk | **Yes** | — (this *is* the baseline) | — |
| **Volatility targeting** | vol is forecastable (sound — vol clusters) | **Staged** | fixed-fractional | a strategy has enough live history to A/B it under CPCV and it **measurably beats fixed-fractional for *that* strategy**. It's a risk-normalizer, not tail protection → always paired with hard stops |
| **Fractional Kelly** | edge (`p`, `b`) is known; returns i.i.d.; distribution known | **No (early)** | fixed-fractional | edge is measured on **hundreds** of real trades. Then Kelly enters only as an *upper-bound cap*, never the primary sizer — it's brutally sensitive to overestimating edge, and the penalty for overbetting is ruin |
| **Bayesian posterior strategy weighting** | past edge predicts future edge; sane prior | **No (early)** | equal / simple performance-bucketed weights + L8 decay monitor | multiple strategies each have enough live trades that posteriors are **data-dominated, not prior-dominated** (otherwise it just means "trust the overfit backtest") |

**Early L6 (what we build first):** fixed-fractional sizing + hard rules + circuit breakers + equal/simple strategy weights + the L8 decay monitor. More deterministic and assumption-light than the original draft — each probabilistic layer is added later, and only after it proves itself.

---

## L7 — Execution Engine

**Function.** Turns an authorized intent into a filled, *protected* position, and keeps the system's view of reality synced to the exchange.

**Inputs.**
- **From L6**: the authorized order intent
- **From L1 (live)**: current order book / best bid-ask / spread (for routing and limit placement)
- **From the exchange (feedback)**: order acknowledgements, fill reports, position state, errors

**Outputs.**
- Live orders + immediate stop placement on the exchange
- Fill/exit events, realized P&L, slippage → to L8 and the trade log
- Reconciliation reports (ghost / unprotected / orphan position alerts)
- *Example output:* `Filled SHORT 0.012 BTCUSDT @ 67415 (orderId a3f…); stop @ 68100 placed (orderId b7c…); slippage: 5bps` → trade log, **and** a reconciliation tick `{position: SHORT 0.012, protected: true, drift: none}`. The plan is now a real, stop-protected position.

**Tech.** **CCXT** (unified multi-exchange) + **our verified Bybit V5 client** + 11-state order machine + reconciliation module. *Rust execution routing is **not** planned* — a minutes-to-hours holding horizon never needs microsecond routing; revisit only if we ever add a genuinely latency-sensitive strategy. (Add the fee-minimization policy from `execution_fee_minimization_2026_06.md` here: post-only-with-chase entries, maker/taker decision rule, funding-stamp avoidance.)

---

## L8 — Meta-Learner & Observability

**Function.** Watches the whole system and closes the feedback loop: detects strategy decay, allocates capital across uncorrelated strategies, and surfaces system health.

**Inputs.**
- **From L7**: per-trade fills, P&L, slippage, execution quality
- **From L4**: each strategy's live trade-level returns
- **From L5**: backtest expectancy/Sharpe baselines (to compare live vs backtest)
- **From L1**: regime context (to attribute performance to the right regime)

**Outputs.**
- Strategy health scores (rolling live Sharpe ÷ backtest Sharpe) + decay flags
- Updated strategy weights + correlation-capped capital allocation → back to L6
- Down-weight / retire signals → back to L4; decay-cause records → back to L2 (graveyard)
- System metrics, logs, alerts (dashboards + paging)
- *Example output:* `funding_mr_v1 → {live_sharpe/backtest_sharpe: 0.55, decay_flag: true, weight: 0.30→0.18, corr(short_composite): 0.71 → allocation capped}` → fed back to L6 (new weight) and L2 (decay cause: "edge halved post-regime-shift"). Intelligence flowing backward — closing the loop.

**Tech.** Custom stats jobs (decay, correlation) on **Polars/NumPy**. **Grafana + Sentry** to start (dashboards + error tracking — enough for the current footprint); **Prometheus** (metrics) and **Loki** (logs) re-enter as the system scales to more services.

---

## Cross-cutting infrastructure

| Concern | Choice | Why |
|---|---|---|
| Scheduling / orchestration | **cron** now → **Dagster** later | cron on the always-on server covers periodic jobs; Dagster re-enters when pipelines multiply. **Scheduling runs on the cloud box, never the laptop** (the laptop sleeps). |
| Containers | **Docker + Compose** now → **k3s** later | One strong box runs all of this; k8s is premature ops cost |
| Hosting | **DigitalOcean (GitHub Student Pack $200) / Oracle Always Free** now → **Hetzner dedicated** as data volume grows | Free/near-free always-on box now; the open-source stack self-hosts on it via Compose. Move to Hetzner when crypto data volumes justify it. |
| Object storage | **Cloudflare R2** | Columnar archive, zero egress fees |
| Provisioning / config | **Setup script + Docker Compose** now → **Ansible** if we run several machines | A single box doesn't need config management; Ansible earns its place with multiple machines |
| CI/CD | **GitHub Actions** | Build/test/deploy |
| Internal dashboard | **Streamlit** now → **Next.js** if partner-facing | Upgrade only if it goes external |
| Languages | **Python 3.12** + **Rust** (hot-path collectors) | Python for breadth; Rust where collector throughput bites (justified by multi-asset). Not used in execution. |

---

## Consolidated tech stack at a glance

| Layer | Primary tech |
|---|---|
| L1 Data Foundation | Rust/Python collectors · Bytewax (→ micro-batch Polars fallback) · Redis · ClickHouse (ASOF JOIN) · Parquet/R2 · thin feature-access layer · Polars · *(Redpanda deferred)* |
| L2 Research & Knowledge | Claude API · Neo4j Community · CryptoBERT/FinBERT · pgvector |
| L3 Signal Discovery | Polars · LightGBM · SHAP · imodels/RuleFit (optional) · *(gplearn later)* |
| L4 Strategy/Agents | LightGBM (+CatBoost challenger) · hmmlearn · HDBSCAN (experimental) · MLflow · *(PyTorch later)* |
| L5 Validation | NautilusTrader · vectorbt · custom CPCV + NumPy |
| L6 Decision | Pure Python (deterministic) · NumPy |
| L7 Execution | CCXT · Bybit V5 client |
| L8 Meta/Observability | Polars/NumPy · Grafana · Sentry · *(Prometheus/Loki later)* |
| Cross-cutting | cron→Dagster · Docker/Compose→k3s · DigitalOcean(student)/Oracle→Hetzner · R2 · setup-script→Ansible later · GitHub Actions |

---

## Right-sizing — what runs now vs what re-enters at scale

"Proper from day one" ≠ "maximal." Every choice below delivers the **functionality** now; the heavier deployment is staged behind an explicit re-entry trigger (same discipline as the L6 sizing staging). Nothing is closed off — each row says *exactly* what brings it back.

| Capability | Runs now | Re-enters when… | Why staged |
|---|---|---|---|
| Event bus | direct ingestion | **multi-asset** brings multiple consumers / durable-replay needs → **Redpanda** | A bus earns its place with many producers/consumers, not one feed |
| Feature management | **thin `get_features()` layer** over ClickHouse (ASOF JOIN) + Redis | feature/asset catalog across many models gets painful → reconsider **Feast** | Feast is ~0.3 FTE and doesn't do realtime compute; the thin layer gives the same train/serve consistency |
| Vector search | **pgvector** in Postgres | embedding volume outgrows pgvector → **Qdrant** | One fewer service to run early |
| Stream compute | **Bytewax** (fallback: micro-batch Polars) | — (kept; drop to micro-batch only if Bytewax misbehaves) | Real streaming for sub-minute features; lighter than Flink |
| Signal discovery | **LightGBM + SHAP** (+ optional RuleFit) | GBDT interaction search plateaus → **genetic programming (`gplearn`)** for formulaic alphas | GBDT already finds combinations; GP is heavier + overfit-prone |
| Regime model | **hmmlearn HMM** | HDBSCAN proves stable across refits → promote it | Clustered regimes can be unstable; HMM is the safe v1 |
| Observability | **Grafana + Sentry** | more services to watch → **Prometheus + Loki** | Full SRE stack is premature for the current footprint |
| Orchestration | **cron** (on the server) | pipelines multiply → **Dagster** | cron covers periodic jobs cheaply |
| Provisioning | **setup script + Compose** | several machines → **Ansible** | Config management is pointless on one box |
| Containers | **Docker Compose** | outgrow one machine → **k3s** | k8s is a second full-time job to run well |
| Tick storage | **ClickHouse** (DuckDB dropped — wrong shape for always-on ingest) | — (kept; fund-validated for tick data) | One analytical engine, not two |
| Execution latency | Python + CCXT/Bybit | a genuinely latency-sensitive strategy appears → **Rust routing** | Minutes-to-hours horizon never needs microsecond routing |

**What we deliberately keep heavy now (multi-asset justifies it):** Rust collectors (throughput across many symbols × exchanges × L2 books) and the **Neo4j** knowledge graph (multi-hop relationship/conflict queries across the asset×strategy×signal web). On one asset these would be premature; for the multi-crypto product they pay off early.

If we'd rather go maximal on any deferred row *now* (e.g. Redpanda + k8s from day one, to *be* hedge-fund-grade infra immediately rather than just deliver hedge-fund-grade results), it trades build/ops time for headroom we won't use yet. Flag the row and we switch.

---

## End-to-end data flow (one line)

External feeds → **L1** normalizes/computes/serves features → **L2** adds research hypotheses + sentiment/event flags → **L3** mines candidate signals → **L5** validates them → **L4** runs surviving strategies (both directions, meta-labeled, regime-gated) → **L6** aggregates + sizes + risk-checks → **L7** executes + protects + reconciles → **L8** monitors, attributes, re-weights, and feeds every lesson back upstream. *Data flows forward; intelligence flows backward.*
