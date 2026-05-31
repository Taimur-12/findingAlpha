# APEX QUANT — Updated Build Plan (v3)

**Date:** 2026-06-01
**Supersedes:** the implicit roadmap in `STATE.md` and the "PAUSE pending partner review" posture.
**Reconciles:** what we have *built* (Finding Alpha / QuantFusion) with the partners' written vision (`idea_docs/APEX_QUANT_v2_Blueprint.pdf`).
**Decision inputs from this session:**
- We commit to the APEX ambition: build a system that does justice to the blueprint and can compete in the lane where we can actually win.
- Budget is no longer the hard blocker. ~$50–100/month now, scaling **from revenue** as the system earns.
- Build philosophy: **build until it genuinely works and shows real profit, then deploy and earn while we keep improving.** Not deploy-first.
- Team: two technical people + Claude writing code. Pace is fast; this plan sequences by **dependency**, not calendar.
- ML: **only techniques proven in real fund/finance settings in the last ~2 years.** Nothing unjustified. No "fancy" ML in the hot execution path.

---

## 1. The thesis — how we do justice to the blueprint without lying to ourselves

The APEX PDF has two voices. The cover says *"compete with Tier-1 hedge funds."* Its own honest-assessment page says *"not competing on latency… target signals at minutes-to-hours horizon… focus on strategies that scale at our size."* **Both are right, and they are not in conflict** once you separate *ambition* from *method*:

- **Ambition (from the partners):** a real, multi-strategy, both-directions, self-monitoring, institutionally-validated trading firm — not one short-only bot.
- **Method (what actually wins at our size):** discipline, proven techniques, integration of many cheap edges, and ruthless validation — not a microsecond/$50M-data-budget arms race we'd lose.

So the target is: **institutional-grade discipline and architecture, built in the order that compounds and can't blow up the account, funded by its own early profits.** Every APEX layer gets built — but each one earns its place with evidence before the next.

What we already have is not a competing vision. It is **the de-risked core of APEX** (Layers 1-lite, 5-lite, 6-risk, 7-execution, plus the advisory). This plan grows the rest *on top of* that core instead of replacing it.

---

## 2. Operating principles (APEX's five + our discipline)

1. **The feedback loop is the system.** Every layer teaches the layers above and below it. Build each component with its upstream feedback obligation in mind.
2. **Trust real data over everything.** No idea touches live capital until real BTC market data has validated it through the full quarantine process.
3. **Understand *why*, not just *what*.** A signal we can explain survives a regime change that kills a signal we only correlated.
4. **The graveyard is as valuable as the library.** Every rejected strategy is stored with *why* it failed. We already do this informally — we formalize it.
5. **Innovate on combinations, not just sources.** The edge in 2026 is combining affordable data in ways others haven't, not buying data others can't.
6. **(Ours) The hot path stays deterministic.** Signal → filter → sizing → risk → execution is inspectable, fast, and frozen at runtime. ML trains offline and is consumed as frozen, interpretable scores. ML never *invents* a trade or overrides a stop.
7. **(Ours) Simplicity until evidence forces complexity.** GBDT before transformers. Block-bootstrap before diffusion models. We add sophistication only when the simpler tool measurably plateaus.

---

## 3. The ML doctrine — what we use, what we defer, what we refuse (and why)

This is the core research deliverable. It answers: *of everything funds actually use, what do we adopt?* Sourced from recent (2024-2026) fund practice and literature; see Sources at the end.

**The single most important fact we design around:** independent studies find **>90% of academic trading strategies fail when run on real capital**, and out-of-sample, deep models frequently *barely beat simple baselines* because of overfitting and regime shift. This is not a reason to avoid ML — it's the reason to use the *boring, proven* ML and to spend most of our ML effort on **validation**, not on bigger models.

### 3.1 ADOPT NOW — proven, fits our scale, non-hot-path

| Technique | What it does for us | Where funds use it | Role in our system |
|---|---|---|---|
| **Gradient-Boosted Trees** (LightGBM / XGBoost / CatBoost) | The workhorse of tabular financial prediction. Interpretable, fast at inference, hard to overfit relative to deep nets. | Dominant in production tabular finance, Numerai, virtually every systematic shop's first model. | **Decision-layer / cold-path.** Scores trade quality and sizing. Frozen at runtime → hot path stays deterministic. |
| **Meta-labeling + Triple-Barrier labeling** (López de Prado) | An ML model that decides *whether to act on* a deterministic signal and *how big*, instead of predicting price directly. Raises precision, cuts false entries. | Standard advanced-financial-ML practice; production-ready. | **Overlay on our existing rule-based strategies.** This is the cleanest way to add ML edge without ML inventing trades. Directly attacks our thin-edge / low-precision problem. |
| **Purged & Embargoed CV + Combinatorial Purged Cross-Validation (CPCV)** | Validation that doesn't leak future info across overlapping samples. 2024 work shows CPCV markedly beats plain walk-forward at catching overfit. | The serious-quant standard for honest backtesting. | **Validation layer (Layer 5).** Replaces/augments our current walk-forward. Cheap, high-value, partner-credible. |
| **HMM / regime models** (Gaussian HMM, non-homogeneous HMM, or HDBSCAN clustering on a market-state vector) | Probabilistic bull/bear/neutral regime detection with transition probabilities — an upgrade to our hand-rule classifier. | Proven for crypto regime detection (BTC studies 2024-2026). | **Cold-path regime engine.** Feeds posture/sizing to the decision layer; never trades directly (matches APEX Agent 07). |
| **Block-bootstrap Monte Carlo** (resample real returns in blocks, 10k paths, report 5th-percentile outcome) | Robustness distribution, not a single Sharpe. Gives ~90% of "synthetic regime" value at ~1% of the cost. | Standard institutional risk reporting. | **Validation layer.** Replaces APEX's diffusion-model idea for now. |

> **Design note to flag explicitly:** meta-labeling puts a *trained model* into the trade decision. We keep this honest by (a) training it offline, (b) freezing it, (c) consuming it at runtime as a single interpretable probability that gates a *deterministic* threshold, and (d) logging every score. The hot path still just evaluates a frozen, fast, inspectable function — no live learning, no black box. **If you'd rather keep ML out of the trade decision entirely and use GBDT only for post-trade analytics, say so — this is the one place ML touches "should we trade," and it's your call.**

### 3.2 ADOPT LATER — proven, but needs scale/data we don't have yet

| Technique | Why it's real | Why *later* for us | How it would work when we get there |
|---|---|---|---|
| **RL for optimal execution** (Almgren-Chriss + Double-DQN; JPMorgan's LOXM is the production example) | Genuinely deployed to minimize slippage and market impact on large orders. | At $50–$100 and micro size, **our market impact is ≈ 0** — there's almost nothing for RL execution to optimize. The payoff scales with order size. Adopting it now is effort with no measurable return. | When single orders get large enough that slippage matters, train an agent (state = remaining qty, time, spread, book imbalance, vol; action = how aggressively to post/cross) against our own fill history + a market simulator, rewarding fill price vs arrival price. Until then, our limit+chase logic is fine. |
| **Sequence models for return forecasting** (Temporal Fusion Transformer, LSTM/xLSTM, PatchTST, sentiment-enhanced hybrids) | Best academic results on financial time series come from these; sentiment-enhanced TFT/LSTM catch moves linear models miss. | Out-of-sample they **barely beat GBDT** while overfitting far more, and they need large clean datasets + heavy validation to trust. Premature before GBDT plateaus and before we have the data scale + CPCV discipline. | Once GBDT stops improving and we have months of microstructure features: a TFT on a sequence of order-flow + funding + sentiment features, trained with CPCV, used as **one more signal feeding the decision layer**, never as a standalone autopilot. |
| **Dedicated NLP sentiment** (FinBERT / transformer sentiment on news + social, à la Point72) | Sentiment as a quantified feature is in production at multiple funds. | Our Claude advisory already covers a lite, qualitative version. A dedicated quantified feed is a refinement, not a foundation. | Stream crypto news/social → transformer sentiment score → a cold-path feature (fear index, social-volume z-score) that the regime engine and decision layer can read. |

### 3.3 PROVEN-OR-HYPED, BUT WE REFUSE (for now) — with the reason and how it would work

You asked me to name anything that's proven-ish but I'd still avoid, explain why, and describe how it would have worked. Here they are:

| Technique | How it would work | Why we refuse it (the abc reason) |
|---|---|---|
| **Deep RL for alpha / position decisions** (not execution — the *what to trade* decision) | An agent learns a trading policy directly from market state, rewarded on P&L. | (a) Reward hacking and instability are endemic; (b) sample-inefficient — we'll never have enough independent episodes on one instrument; (c) big-fund literature on RL-for-alpha is mixed-to-negative. Our own `STATE.md` already bans it. **Stays banned.** |
| **Echo State Networks / "neuromorphic hybrid"** (the blueprint's L4 model) | A fixed random reservoir + trained readout, gated with a transformer by regime. | (a) Exotic with thin, unmaintained tooling; (b) not a fund standard, so no production track record to lean on; (c) very hard to validate honestly — we'd be the QA team for a research idea. GBDT + a later TFT gets us the same job with far more support. |
| **Diffusion-model synthetic regime generation** (blueprint L5) | Train a generative model on the full joint distribution of market microstructure, sample "plausible but unseen" crises to stress strategies. | (a) Months of work to do correctly; (b) extremely easy to fool yourself — a bad generator produces confident garbage; (c) **block-bootstrap Monte Carlo + regime-bucketed historical testing gives most of the benefit at a fraction of the risk.** Revisit only if we ever have a dedicated research hire. |
| **Transfer entropy / microstructure entropy as a primary signal-discovery engine** (blueprint L3) | Continuously measure directed information flow between every feature pair to "discover new leading indicators." | (a) Notoriously noisy and false-positive-prone on financial series; (b) needs huge clean datasets to estimate stably; (c) the blueprint itself admits microstructure entropy is "barely studied in crypto" = unproven. We can run it as an offline *research curiosity* that proposes hypotheses into quarantine — but never as a live signal source. |
| **GNN on the on-chain transaction graph** (blueprint L3/L11) | Learn wallet-cluster embeddings (accumulator/distributor/miner) that shift before price. | (a) Heavy data engineering for a slow, weak, days-to-weeks-horizon edge; (b) no convincing production track record at retail scale; (c) the same on-chain *signal* (exchange netflow, whale accumulation) is available as simple features from a data vendor without building a GNN. Buy the feature, skip the graph net — at least until we're much bigger. |

**Net doctrine:** GBDT + meta-labeling for edge, HMM for regime, CPCV + Monte-Carlo for honesty, RL/transformers/NLP staged for when scale justifies them, and the exotic blueprint ML deferred or refused with reasons. This is exactly the stack a disciplined modern quant shop runs — and it keeps the hot path deterministic.

### 3.4 Sizing & weighting — staged by assumption ("deterministic at runtime" ≠ "assumption-free")

*Why this section exists (revision 2026-06-01).* An earlier draft put fractional Kelly, volatility targeting, and Bayesian posterior strategy-weighting into the decision layer (Layer 6) **from the start**. All three are deterministic *at runtime*, but each encodes a statistical assumption at **design time** — and on small live samples those assumptions are exactly where systems blow up. So we change the approach (not delete the techniques): **deterministic and assumption-light now; probabilistic only when the data earns it; every probabilistic upgrade must beat the simpler baseline under CPCV (Layer 5) before it touches live capital.** Each technique keeps an explicit re-entry gate — nothing is closed off permanently.

- **Now — baseline:** fixed-fractional sizing (risk % per trade, defined by the stop) + hard rules + circuit breakers + equal / simple strategy weights + the L8 decay monitor. This is *more* deterministic than our current build's gaps, not less.
- **Volatility targeting — re-enters when:** a strategy has enough live history to A/B it under CPCV and it **measurably beats fixed-fractional for that strategy**. Its assumption (vol clusters) is sound, but it's a risk-*normalizer*, not tail protection — always paired with hard stops.
- **Fractional Kelly — re-enters when:** edge (`p`, `b`) is measured on **hundreds** of real trades. Then it enters only as an *upper-bound cap*, never the primary sizer — Kelly is brutally sensitive to overestimating edge and the penalty for overbetting is ruin. Replacing "fractional" is itself an admission the inputs are noisy.
- **Bayesian posterior weighting — re-enters when:** we run multiple strategies each with enough live trades that posteriors are **data-dominated, not prior-dominated** (otherwise it just means "trust the overfit backtest"). Until then: equal / simple weights + decay monitor.

Full per-technique table (hidden assumption, baseline, re-entry gate) lives in the architecture doc → **L6 → "Sizing & weighting, staged by assumption."**

---

## 4. Target architecture — APEX's 8 layers mapped to reality

For each layer: what's **built**, what we **add**, the **ML** (if any), and the **rough cost tier**.

| Layer | APEX wants | Built today | We add | ML | Cost tier |
|---|---|---|---|---|---|
| **1 Data Foundation** | L2 book @100ms, tick+aggressor, on-chain, sentiment, macro; Redis/Kafka/Flink/Timescale | Bybit+Binance candles, funding, OI → Parquet | Order-book imbalance + CVD + **liquidation feed** (cheap aggregator API); DuckDB-on-Parquet; later on-chain netflow/whale features | none (feature eng) | T1 now, T2 later |
| **2 Research Engine** | Auto-read arXiv/SSRN → LLM extract → Neo4j graph → quarantine | Claude **advisory**; manual research; informal quarantine | Formal **quarantine→graveyard** store (start as Parquet/SQLite, Neo4j only if it earns it); Claude paper-extraction into hypothesis schema | LLM extraction | T1 |
| **3 Signal Discovery** | Transfer entropy, association mining, causal graphs, toxic flow, GNN | none | **Association-rule / feature-combination mining** (proven, cheap) to find multi-condition setups; toxic-flow *features* (Kyle's lambda, book thinning) as inputs — not a GNN | GBDT feature importance | T1 |
| **4 Quant Agents** | 6–7 neural agents (Transformer+ESN) | rule-based strategies, no ML | **Multiple strategies, both directions** (see §6), each wrapped in **meta-labeling**; a mean-reversion strat on funding extremes | GBDT meta-labels; HMM regime | T1 |
| **5 Validation** | Walk-forward + adversarial + diffusion + Monte Carlo | walk-forward + cost modeling | **CPCV**, **regime-bucketed stress test** (2021 bull / 2022 bear / 2019 range / Mar-2020 shock), **cost-sensitivity sweep** (0–20 bps), **block-bootstrap Monte Carlo** | CPCV | T1 |
| **6 Decision Layer** | Bayesian aggregation + reflexivity + fractional Kelly + hard rules | deterministic risk gate + risk-% sizing | **Fixed-fractional sizing + hard rules + simple strategy weights now**; vol-targeting → capped Kelly → Bayesian weighting **staged by assumption** (see §3.4) | GBDT confidence | T1 |
| **7 Execution** | Cross-exchange routing, TWAP, toxic-flow-aware | single-exchange Bybit, 11-state machine, reconciliation | keep as-is; add **second exchange** only when capital justifies; RL execution **deferred** | none now | T2 |
| **8 Meta-Learner** | MAML regime adaptation + decay diagnosis + correlation-capped allocation | none | **Strategy-decay monitor** (rolling live-vs-backtest Sharpe) + **correlation-capped capital allocation** across strategies | simple stats / GBDT | T1→T2 |

The exotic ML (ESN, diffusion, GNN, transfer-entropy-as-signal, deep RL) is intentionally **absent** from this table per §3.3.

---

## 5. The phased build plan (dependency-ordered)

Each phase has a **gate** that must pass before the next begins. Phases overlap only where dependencies allow. No calendar dates — we move as fast as the gates clear.

### Phase A — Stabilize & honest baseline *(unblocks everything)*
- Resolve the current live-testnet mess: clean up the stuck unfilled order / divergent price state; reconcile `paper/live/`.
- Fix `STATE.md`'s live-vs-paused contradiction; make the dashboard's simulated-vs-live distinction unmissable.
- Re-run our two existing strategies through the **new validation stack** (CPCV + regime buckets + cost sweep + Monte Carlo) to get an *honest* baseline edge.
- **Gate:** one clean source-of-truth on current real edge; zero reconciliation errors; green test suite.

### Phase B — Validation engine (Layer 5) *(the cheapest, highest-trust upgrade)*
- Implement CPCV, regime-bucketed stress testing, transaction-cost sensitivity, block-bootstrap Monte Carlo as reusable validation modules.
- Backfill: re-score every existing/rejected strategy through it; populate the **graveyard** with structured failure reasons.
- **Gate:** any strategy can be run through one command and get a full institutional validation report (per-regime, per-cost, 5th-percentile).

### Phase C — Data depth (Layer 1, affordable tier) *(feeds everything downstream)*
- Add order-book imbalance, CVD, and a liquidation feed (cheap aggregator API). Stand up 24/7 cloud VM. Migrate analytics to DuckDB-on-Parquet.
- **Gate:** new features are live, gap-checked, and queryable; 24/7 collection running.

### Phase D — Both-directions strategy book + meta-labeling (Layers 3–4) *(fixes the #1 weakness)*
- Build a **mean-reversion strategy on funding-rate extremes** (long *and* short — kills the "flat in every bull market" problem).
- Wrap existing + new strategies in **meta-labeling** (triple-barrier labels + GBDT filter).
- Run association/feature-combination mining to surface multi-condition setups → into quarantine.
- **Gate:** ≥3 strategies, covering both directions, each passing the Phase-B validation bar; meta-labeling measurably improves precision vs raw signals.

### Phase E — Decision layer + regime ML (Layers 6 + 4-regime)
- HMM/clustering regime engine feeding posture & sizing.
- Multi-strategy aggregation with **equal / simple performance-bucketed weights**; **fixed-fractional sizing**; hard risk rules retained. Probabilistic upgrades (vol-targeting → capped Kelly → Bayesian weighting) are **staged by assumption** — each must beat the fixed baseline under CPCV before going live (see §3.4 and architecture doc L6).
- **Gate:** the integrated system, in paper, shows combined edge ≥ the best single strategy, with controlled drawdown across regime buckets.

### Phase F — Prove real profit in paper/quarantine *(the "does justice to the PDF" gate)*
- Run the full integrated system 24/7 in paper through the quarantine criteria (Q1 shadow → Q2 paper): meaningful trade count, a real drawdown survived, both-direction behavior observed, paper edge within tolerance of backtest, zero reconciliation errors.
- **Gate:** this is the **deploy decision gate.** Only when paper shows a genuine, validated, both-directions edge do we move real money.

### Phase G — Micro-live & earn-while-improving (Layer 7 + 8 monitor)
- Flip to mainnet with a hard, low position cap. Strategy-decay monitor + correlation-capped allocation live.
- Scale capital and data spend **from realized profit + monthly budget**, not ahead of it.
- Add Layer-2 data (on-chain, second exchange) and the deferred ML (transformers, RL-execution) **only when scale justifies them** per §3.2.
- **Gate (ongoing):** never escalate capital on a phase that failed its review. A clean micro-live month → discuss uncapping.

---

## 6. Strategy roadmap — killing the short-only weakness

Our biggest real weakness (and the partners' best instinct): **both live strategies are short-only**, so we sit flat through every bull market. The fix is concrete and proven:

1. **Mean-reversion on funding-rate extremes** — when perp funding goes extreme, it's one of the most reliable contrarian signals in crypto, and it works **both directions**. This becomes our first long-capable strategy. (APEX Agent 02 is the same idea; it's the strongest concrete strategy in their doc.)
2. **Meta-labeling overlay** on every strategy to lift precision and right-size winners.
3. **Multi-strategy book** with correlation-capped allocation — the goal is *uncorrelated* edges, not the same bet repeated. This is what turns "a bot" into "a book."
4. Keep the two validated shorts as part of the book — they're still positive-expectancy in down/compression regimes.

---

## 7. Data & budget tiers

| Tier | ~Cost/mo | What it buys | When |
|---|---|---|---|
| **T0** | $0 | Bybit/Binance candles, funding, OI (have it) | now |
| **T1** | $50–100 | 24/7 cloud VM; order-book/CVD capture; liquidation+funding aggregator API; storage | now → Phase C |
| **T2** | $150–500 | Premium on-chain (whale/netflow), options IV (Deribit), second exchange, more compute | funded by profit, Phase G+ |
| **T3** | $500+ | Heavier data + the deferred ML (transformers, RL execution) | only once revenue clearly justifies |

The discipline: **T2/T3 spend is unlocked by realized profit, not by optimism.**

---

## 8. Honest risks & caveats

- **The edge is still small and could be zero.** Our real strategies show +0.2–0.4 R with coin-flip walk-forward windows. Meta-labeling + a mean-reversion strat should help, but >90% of academic strategies die live — Phase B/F exist precisely to find that out *before* real money.
- **Meta-labeling is the one place ML touches the trade decision.** Documented in §3.1; your call to keep or cut.
- **"Compete with hedge funds" is a direction, not a month-12 deliverable.** We earn each layer. The win condition is a disciplined, multi-strategy, both-directions book that's *honestly* profitable at our scale — then scale it.
- **The blueprint's most exciting items are its most dangerous.** We're deliberately declining ESN/diffusion/GNN/transfer-entropy-as-signal/deep-RL-alpha. If the partners specifically want one of these, we treat it as a *research project in quarantine*, never a live dependency.

---

## 9. Immediate next actions

1. **Phase A cleanup** — reconcile live-testnet state, fix `STATE.md` contradiction, lock an honest baseline.
2. **Stand up the CPCV + regime-bucket + cost-sweep + Monte-Carlo validation modules** (Phase B) — highest trust-per-hour.
3. **Spec the funding-rate mean-reversion strategy** and the meta-labeling overlay (Phase D design).
4. **Decide the meta-labeling question** (§3.1 note) — ML in the trade decision: yes or analytics-only?

---

## Sources (ML research, 2024–2026)

- [How Hedge Funds Use Machine Learning](https://navnoorbawa.substack.com/p/how-hedge-funds-use-machine-learning) · [AI in hedge fund returns 2025](https://www.clarigro.com/ai-impact-on-hedge-fund-returns-performance/) · [J.P. Morgan AM — ML in hedge fund investing](https://am.jpmorgan.com/lu/en/asset-management/institutional/insights/portfolio-insights/machine-learning-in-hedge-fund-investing/)
- [Deep Learning in Quantitative Trading (Cambridge)](https://www.cambridge.org/core/elements/abs/deep-learning-in-quantitative-trading/C39DE06D255470F6232BC97E2E5474E7) · [DL for Financial Time Series: risk-adjusted benchmark (arXiv)](https://arxiv.org/pdf/2603.01820) · [HRformer hybrid transformer (MDPI)](https://www.mdpi.com/2079-9292/14/22/4459)
- [ML for crypto market microstructure (Amberdata)](https://blog.amberdata.io/machine-learning-for-crypto-market-microstructure-analysis) · [Better inputs > deeper nets, crypto LOB (arXiv 2506.05764)](https://arxiv.org/html/2506.05764v2) · [Order flow and crypto returns (EFMA)](http://www.efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2025-Greece/papers/OrderFlowpaper.pdf)
- [XGBoost is All You Need (gradient-boosted trees)](https://www.xgblog.ai/p/xgboost-is-all-you-need-part-3-gradient) · [LightGBM (NeurIPS)](https://proceedings.neurips.cc/paper/6907-lightgbm-a-highly-efficient-gradient-boosting-decision-tree.pdf)
- [Triple-barrier labeling (Quantreo)](https://www.newsletter.quantreo.com/p/the-triple-barrier-labeling-of-marco) · [Advances in Financial Machine Learning — notes](https://reasonabledeviations.com/notes/adv_fin_ml/) · [GA-driven triple-barrier for crypto pairs (MDPI)](https://www.mdpi.com/2227-7390/12/5/780)
- [Optimal Execution with RL (arXiv 2411.06389)](https://arxiv.org/abs/2411.06389) · [JPMorgan LOXM / ML execution](https://medium.com/@navnoorbawa/jpmorgans-29-8b-trading-operation-machine-learning-execution-c6527a679518) · [RL execution, time-varying liquidity (arXiv 2402.12049)](https://arxiv.org/pdf/2402.12049)
- [HMM regime detection in crypto, 2024–2026 (Preprints.org)](https://www.preprints.org/manuscript/202603.0831) · [Regime-adaptive trading (QuantInsti)](https://blog.quantinsti.com/regime-adaptive-trading-python/)
- [Backtest overfitting in the ML era / CPCV (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4686376) · [Traditional backtesting is outdated — use CPCV](https://www.insightbig.com/post/traditional-backtesting-is-outdated-use-cpcv-instead) · [Purged cross-validation (Wikipedia)](https://en.wikipedia.org/wiki/Purged_cross-validation)
</content>
</invoke>
