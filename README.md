# APEX Quant

Autonomous, multi-strategy crypto trading system. Bybit USDT linear perpetuals.
**Multi-asset by design — BTC is the first test market, not the scope.**

The hot path (signal → sizing → risk → execution) is fully deterministic and inspectable.
ML trains offline and is consumed as frozen scores; it never invents a trade or overrides a stop.

> **Start here:** [`docs/canon/`](docs/canon/) is the source of truth — the architecture, the build plan,
> and an honest code-vs-plan audit. If an older doc conflicts with canon, **canon wins.**

---

## What's built today

The **deterministic trading spine** is built, tested, and testnet-verified:

- **Data + features (L1):** Bybit + Binance candle/funding/OI loaders, quality checks, ~30 features (RSI/MACD/EMA/ATR/Bollinger/ADX/Supertrend/VWAP, volume/funding/OI z-scores, session levels).
- **Strategies + regime (L4):** rule-based strategies + a 7-state rule regime classifier (currently short-only).
- **Decision (L6):** fixed-fractional sizing + an 8-check hard risk gate (circuit breaker, daily loss, drawdown, heat, stale data…). Fully deterministic.
- **Execution (L7):** Bybit V5 client + 11-state order machine + reconciliation (detects unprotected / ghost / missing positions). Live-verified on testnet.
- **Validation (L5):** walk-forward + cost-aware metrics.
- **Observability:** append-only matrix event log + Streamlit dashboard.

**What's next (the APEX upgrade):** fund-grade validation (CPCV / Monte-Carlo / quarantine ladder),
both-directions + funding-mean-reversion strategies, GBDT meta-labeling, microstructure & alt-data,
proper databases, multi-asset, and cloud deployment. See
[`docs/canon/code_vs_plan_audit.md`](docs/canon/code_vs_plan_audit.md) for the exact gap and
[`docs/canon/build_plan.md`](docs/canon/build_plan.md) for the phased plan (we're at the start of Phase A/B).

---

## Quick start (macOS / Linux)

```bash
git clone <repo-url>
cd apex            # or whatever you name the clone
bash setup.sh      # checks Python 3.12+, creates .venv, installs deps, runs the test suite
cp .env.example .env   # then fill in your keys (see below)
```

### Manual setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,research]"
```

### Secrets — `.env`

Copy `.env.example` to `.env` and fill it in. **Never commit `.env`** (it is gitignored).

- `BYBIT_TESTNET_API_KEY` / `BYBIT_TESTNET_API_SECRET` — required for the live testnet cycle
- `ANTHROPIC_API_KEY` — for the LLM advisory layer
- `BYBIT_LIVE_*` — leave blank until explicitly going to mainnet

---

## Run tests

```bash
source .venv/bin/activate
pytest -q                    # all 275 tests
pytest tests/test_execution.py -v   # a single module
```

Expected: **275 passing** across 12 test files (`test_contracts`, `test_matrix`, `test_data_loaders`,
`test_features`, `test_strategies`, `test_pipeline`, `test_paper`, `test_advisory`, `test_execution`,
`test_reconciliation`, `test_live_execution`, `test_validation`). Loaders are mocked — no API key needed to run tests.

---

## Dashboard

```bash
pip install -e ".[dashboard]"
.venv/bin/streamlit run dashboard/app.py     # opens http://localhost:8501
```

Tabs: overview, KPIs, live status, risk monitor, strategy research, advisory log, trade log, live control.

---

## Common runners

All operational scripts live in `notebooks/runners/`:

```bash
python notebooks/runners/phase7b_fetch_extended_bybit.py   # fetch historical data → data/ (gitignored)
python notebooks/runners/phase8_simulation_runner.py        # historical simulation
python notebooks/runners/phase9_advisory_runner.py          # refresh the LLM advisory
python notebooks/runners/close_position.py                  # emergency position closer (market → limit+chase)
```

One-off research / sweeps live in `notebooks/research/`.

---

## Repo map

```
.
├── README.md
├── CLAUDE.md                   <- behavioral guidelines (team + Claude)
├── primer.md / STATE.md        <- project overview / current state
├── pyproject.toml  setup.sh
├── .env.example                <- copy to .env (gitignored)
├── src/finding_alpha/          <- main package
│   ├── contracts/              <- Pydantic data models + reason codes
│   ├── data/                   <- Bybit + Binance loaders, normalizer, quality, storage (Parquet)
│   ├── features/               <- indicators, orderflow, structure, snapshot builder
│   ├── regime/                 <- rule-based regime classifier
│   ├── strategies/             <- signal generation (rule-based)
│   ├── coordinator/            <- multi-signal dedup + heat tracking
│   ├── portfolio/              <- fixed-fractional position sizing
│   ├── risk/                   <- 8-check hard risk gate
│   ├── execution/              <- Bybit client, order state machine, execution agent, reconciliation
│   ├── paper/  live/           <- live runtime, feed, state persistence
│   ├── simulation/             <- trade outcome simulator
│   ├── validation/             <- walk-forward, event runner, research grid, reporting
│   ├── analytics/              <- metrics (win rate, expectancy, drawdown)
│   ├── matrix/                 <- append-only event log (replayable audit trail)
│   └── research/               <- LLM advisory layer
├── tests/                      <- 275 tests
├── dashboard/                  <- Streamlit app + pages
├── notebooks/
│   ├── runners/                <- operational scripts (data fetch, runners, advisory, close)
│   └── research/               <- one-off sweeps & probes
├── docs/
│   ├── canon/                  <- SOURCE OF TRUTH (architecture, build plan, audit, fees, partner brief)
│   ├── reference/              <- still-valid technical/operational notes
│   └── archive/                <- superseded historical docs
├── idea_docs/                  <- APEX blueprint (partner vision)
└── data/  paper/               <- gitignored runtime/data artifacts
```

---

## Status

Deterministic spine **complete and testnet-verified** (submit → reconcile → cancel, 0 divergences).
Now building the APEX layers on top of it — start of **Phase A/B**. No real capital is deployed.
Full status and the honest gap analysis live in [`docs/canon/`](docs/canon/).
