# Finding Alpha

Deterministic crypto trading engine. Bybit USDT linear perpetuals, BTCUSDT v1.

---

## Quick Start (macOS / Linux)

```bash
git clone <repo-url>
cd findingAlpha
bash setup.sh
```

That's it. The script will:
- Check for Python 3.12+
- Create a `.venv` virtual environment
- Install the package + all dev/research dependencies
- Run the full test suite (275 tests) to confirm everything works

---

## Manual Setup

If you prefer to set up yourself:

```bash
# Option A — venv (standard)
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,research]"

# Option B — conda
conda create -n finding_alpha python=3.12 -y
conda activate finding_alpha
pip install -e ".[dev,research]"
```

### Requirements

- Python 3.12 or later
- No other system-level dependencies — everything installs via pip

### Install Python 3.12 if you don't have it

```bash
# Homebrew (recommended on macOS)
brew install python@3.12

# pyenv
pyenv install 3.12
pyenv local 3.12

# conda
conda install python=3.12
```

---

## Run Tests

```bash
# Activate the environment first
source .venv/bin/activate   # or: conda activate finding_alpha

# All tests
pytest tests/ -v

# Single module
pytest tests/test_features.py -v
pytest tests/test_strategies.py -v
pytest tests/test_pipeline.py -v
```

Expected output: **275 tests passing** across 12 test files.

| Test file | Tests | What it covers |
|---|---|---|
| `test_contracts.py` | 15 | Pydantic contracts, reason codes |
| `test_matrix.py` | 6 | Event log, replay |
| `test_data_loaders.py` | 23 | Data loaders (mocked HTTP — no API key needed) |
| `test_features.py` | 38 | Indicators, regime classifier |
| `test_strategies.py` | 35 | Strategy fast-reject, signal production |
| `test_pipeline.py` | 32 | Portfolio sizing, risk agent, sim, analytics |
| `test_paper.py` | 22 | Paper runtime safety (finality, staleness, state) |
| `test_advisory.py` | 14 | LLM advisory schema, TTL, structured output |
| `test_execution.py` | 61 | Bybit client, order state machine |
| `test_reconciliation.py` | 12 | Exchange/local divergence detection |
| `test_live_execution.py` | 14 | Live tick, runtime-managed take-profit |
| `test_validation.py` | 3 | End-to-end validation harness |

---

## Historical Data (optional)

Tests run fine without real data — loaders are mocked in the test suite.

To download 6 months of real Bybit + Binance BTCUSDT data (no API key required, public endpoints):

```bash
python notebooks/phase3_fetch_data.py
```

Data saves to `data/` (gitignored, ~50 MB).

To run the full backtest after fetching data:

```bash
python notebooks/phase5_backtest_runner.py
```

---

## Project Structure

```
findingAlpha/
├── README.md
├── STATE.md                    <- current phase, decisions, checklist
├── pyproject.toml              <- package config and dependencies
├── setup.sh                    <- one-shot environment setup (macOS/Linux)
├── docs/current/               <- design docs, research reports, decision logs
├── src/finding_alpha/          <- main package
│   ├── contracts/              <- Pydantic data models
│   ├── data/                   <- Bybit + Binance historical data loaders
│   ├── features/               <- indicators, regime classifier, feature snapshots
│   ├── strategies/             <- signal generation (prev_day_breakdown_v1, short_composite_v1 live; sweep/squeeze/pullback rejected)
│   ├── portfolio/              <- position sizing
│   ├── risk/                   <- risk agent, daily loss limits
│   ├── coordinator/            <- signal deduplication + heat tracking
│   ├── simulation/             <- trade outcome simulator
│   └── analytics/              <- metrics (win rate, expectancy, drawdown)
├── tests/                      <- 142 tests, no external dependencies
├── notebooks/                  <- research scripts (fetch data, run backtest)
└── data/                       <- gitignored, created by phase3_fetch_data.py
```

---

## Dashboard

A Streamlit dashboard visualizes performance, live status, risk, strategy research,
the advisory log, and the full trade log.

```bash
pip install -e ".[dashboard]"
streamlit run dashboard/app.py
```

Opens at `http://localhost:8501`.

> **Note:** The dashboard currently reads seeded **simulation** data from `paper/sim/`
> (historical replay), not live trading. Equity and P&L shown are simulated, not a
> live track record. The live cron paper runners (`paper/`, `paper/composite/`) start
> flat until deployed to 24/7 cloud operation.

---

## Current Phase

**Phase 10 — Bybit Testnet Execution: COMPLETE.** Testnet round-trip verified
(submit → reconcile → cancel, 0 divergences) on 2026-05-30.

Currently **paused before any capital deployment** pending a partner strategy review.
Two strategies are frozen in paper observation: `prev_day_breakdown_v1` and
`short_composite_v1`. See `STATE.md` for full phase status and `critical_gap.md` for
the standing self-audit of known gaps.
