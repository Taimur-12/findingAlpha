# APEX QUANT — Consolidated Architecture, Inputs & Tech Stack

**Date:** 2026-06-01
**Companion to:** `apex_quant_updated_build_plan_2026_06.md` (the phased build plan).
**Purpose:** The single source of truth for the system's layers — what each one *does*, what *flows into it*, what it emits, and the **decided production tech stack** for each. This is "ours" — a consolidation of our build and the partners' APEX blueprint, not a lite version of either.

## Design decisions baked in here
- **Production-grade from day one, but right-sized** — proper tools, not maximal infra. Three deliberate "stopped short" calls are documented at the end.
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

**Tech.** Rust collectors (hot path) + Python async (rest) → **Redpanda** (event bus) → **Bytewax** (stream feature computation) → **Redis 7** (hot, sub-ms live features), **ClickHouse** (warm, queryable tick/book history), **Parquet on Cloudflare R2** (cold archive) → **Feast** (feature store, online=Redis / offline=ClickHouse). Dataframes: **Polars**.

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

**Tech.** Python ingest + **Claude API** (paper→hypothesis extraction, nuanced sentiment). **Neo4j** (knowledge graph). **CryptoBERT/FinBERT** (quantified sentiment) + Claude (nuance). **Qdrant** (embeddings for semantic search / dedup of news & papers).

---

## L3 — Signal Discovery

**Function.** Turns raw features into ranked *candidate* signals before any strategy commits. Finds multi-condition setups, builds microstructure signals, screens for genuine predictive value.

**Inputs.**
- **From L1 feature store**: the full feature set as time series (microstructure, funding, OI, on-chain, sentiment, macro)
- **From L2**: hypotheses from the quarantine queue to test; knowledge-graph context (what's been tried, what conflicts)
- **From graveyard**: fingerprints of known-failed patterns (so we don't re-discover dead ends)

**Outputs.**
- Ranked candidate signals (each with the conditions, the hypothesized mechanism, support/confidence/lift, and the data it needs) → into quarantine for L5 validation
- Microstructure signal series (Kyle's lambda, toxic-flow proxy, book-thinning, iceberg-detection) → available as features

**Tech.** **Polars + scikit-learn + mlxtend (FP-Growth)** for combination mining; **SHAP** for feature-importance/interpretability. No deep learning here.

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

**Tech.** **LightGBM / XGBoost / CatBoost** (meta-labels, primary tabular models). **hmmlearn (HMM) + HDBSCAN** (regime). **MLflow** (model/version tracking). **PyTorch** reserved for later sequence models, only once GBDT plateaus.

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

**Tech.** **NautilusTrader** (event-driven, backtest/live parity), **vectorbt** (fast research sweeps), **custom CPCV + NumPy** (purged combinatorial CV, block-bootstrap Monte Carlo).

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

**Tech.** **CCXT** (unified multi-exchange) + **our verified Bybit V5 client** + 11-state order machine + reconciliation module. **Rust** for any latency-critical routing once multi-exchange is live.

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

**Tech.** Custom stats jobs (decay, correlation) on **Polars/NumPy**. **Prometheus + Grafana** (metrics), **Grafana Loki** (logs), **Sentry** (errors).

---

## Cross-cutting infrastructure

| Concern | Choice | Why |
|---|---|---|
| Orchestration (batch retrains, nightly scoring) | **Dagster** | Asset-based, Python-native; better DX than Airflow |
| Containers | **Docker + Compose** now → **k3s** later | One strong box runs all of this; k8s is premature ops cost |
| Hosting | **Hetzner dedicated** | Best price/performance for crypto data volumes |
| Object storage | **Cloudflare R2** | Columnar archive, zero egress fees |
| IaC / config | **Ansible** | Reproducible infra |
| CI/CD | **GitHub Actions** | Build/test/deploy |
| Internal dashboard | **Streamlit** now → **Next.js** if partner-facing | Upgrade only if it goes external |
| Languages | **Python 3.12** + **Rust** (hot path) | Python for breadth, Rust where latency bites |

---

## Consolidated tech stack at a glance

| Layer | Primary tech |
|---|---|
| L1 Data Foundation | Rust/Python collectors · Redpanda · Bytewax · Redis · ClickHouse · Parquet/R2 · Feast · Polars |
| L2 Research & Knowledge | Claude API · Neo4j · CryptoBERT/FinBERT · Qdrant |
| L3 Signal Discovery | Polars · scikit-learn · mlxtend (FP-Growth) · SHAP |
| L4 Strategy/Agents | LightGBM/XGBoost/CatBoost · hmmlearn · HDBSCAN · MLflow · (PyTorch later) |
| L5 Validation | NautilusTrader · vectorbt · custom CPCV + NumPy |
| L6 Decision | Pure Python (deterministic) · NumPy |
| L7 Execution | CCXT · Bybit V5 client · Rust (latency) |
| L8 Meta/Observability | Polars/NumPy · Prometheus · Grafana · Loki · Sentry |
| Cross-cutting | Dagster · Docker/Compose→k3s · Hetzner · R2 · Ansible · GitHub Actions |

---

## "Proper from day one" ≠ "maximal" — three deliberate stop-short calls

These are production-grade choices made to avoid pure ops burden with no payoff at our stage. Each is reversible if we decide we want the headroom now.

1. **Flink → Bytewax.** Flink is real but built for hundred-node clusters; we have one asset and a few exchanges. Bytewax is production-grade and Python-native. Flink would be weeks of babysitting for zero benefit at our volume.
2. **Kubernetes → Docker Compose (for now).** The whole stack runs on one strong Hetzner box. k8s is the right move *once we outrun one machine*, not before — it's effectively a second full-time job to run well.
3. **DuckDB → dropped.** Not a toy, but an embedded single-process engine — wrong shape for an always-on, multi-writer ingest system. **ClickHouse** subsumes its role; we don't run two analytical engines.

If we'd rather go maximal on any of these (Flink + k8s from the start, to *be* hedge-fund-grade infra immediately, not just deliver hedge-fund-grade results), it trades weeks of build/ops time for headroom we won't use yet. Flag it and we switch.

---

## End-to-end data flow (one line)

External feeds → **L1** normalizes/computes/serves features → **L2** adds research hypotheses + sentiment/event flags → **L3** mines candidate signals → **L5** validates them → **L4** runs surviving strategies (both directions, meta-labeled, regime-gated) → **L6** aggregates + sizes + risk-checks → **L7** executes + protects + reconciles → **L8** monitors, attributes, re-weights, and feeds every lesson back upstream. *Data flows forward; intelligence flows backward.*
