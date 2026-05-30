# Dashboard operations

How to actually *do things* with the QuantFusion dashboard. Skips read-only tabs — covers only buttons, toggles, and controls that change state or run something.

---

## 1. Start the dashboard

From the project root:

```bash
.venv/bin/streamlit run dashboard/app.py
```

- Opens at `http://localhost:8501`
- Stop with **Ctrl+C** in the terminal
- If you see "Port 8501 is not available", another streamlit is already running. Either visit `localhost:8501` directly, or kill it:
  ```bash
  lsof -nP -iTCP:8501 -sTCP:LISTEN     # find the PID
  kill <PID>                            # free the port
  ```

---

## 2. Switch between SIM and LIVE data

**Where:** sidebar, top-left, on every page.

**What it does:**
- **📊 Simulation** — every tab (except Live Trading) reads from `paper/sim/`. Historical replay data. Used for the shareholder demo.
- **🛰 Live testnet** — same tabs read from `paper/live/`. Reflects actual Bybit testnet activity. Empty until you run live cycles.

**When you switch:**
- Top-of-page banner colour flips (amber → blue)
- Equity, trades, KPIs all refresh automatically
- Tab 7 (Live Trading) is unaffected — always live

The selection persists as you navigate between tabs.

---

## 3. Run a live testnet trade cycle

**Where:** Tab **7 — Live Trading**.

**Pre-check at the top of the page:**
- ✓ green = `.env` has `BYBIT_TESTNET_API_KEY` + `BYBIT_TESTNET_API_SECRET` and they loaded.
- ✗ red = credentials missing. Check `.env` at project root.

**The button: ▶ RUN LIVE CYCLE NOW**

Each click does, in order, for both strategies:
1. Loads live state from `paper/live/{strategy}/state.json`
2. If a position is open, polls Bybit testnet for fills, stops, target/timeout breaches
3. Fetches latest 1h candle + funding + OI from Bybit
4. Classifies regime, runs strategy
5. If strategy fires, submits a real testnet order
6. Persists updated state + trades + matrix events

**Timing:** click ~30 seconds after the top of each hour (00:00:30, 01:00:30, 02:00:30 UTC, etc.). That's when the previous 1h bar has finalised.

**What the result panel shows:**
| Status | Meaning | Action |
|---|---|---|
| `ok` | Cycle ran, bars processed | Nothing — working |
| `no_data` | Bybit returned no candles | Retry in a minute |
| `no_final_bars` | Bar hasn't closed yet | Wait, click again at next hour |
| `up_to_date` | Already processed this bar | Nothing — already done |
| `live_tick_error` | Exception in live polling | Check matrix events at bottom of page |
| `ghost_position_halt` | Exchange has a position, we don't | Halt and investigate manually |

**Exchange Position card** (independent of state file): queries Bybit directly. If this disagrees with the Live State card above, something is wrong — that's the whole point of showing both.

---

## 4. Refresh SIM data (CLI — not in UI)

Refreshes the historical-replay data the dashboard shows in Simulation mode.

```bash
# 1. Fetch fresh candles from Bybit
FINDING_ALPHA_FETCH_DAYS=1095 python notebooks/phase7b_fetch_extended_bybit.py

# 2. Re-run sim against the new data
python notebooks/phase8_simulation_runner.py --weeks 8
```

After both finish, refresh your browser. The "STALE" warnings disappear once the last bar is within 4 hours of now.

**If you hit `RuntimeError: Too many visits` (rate limit):** wait 60s and retry. 15m candles tend to trigger this. The 1h fetch usually completes before it hits.

**If `merge_asof` errors with a dtype mismatch:** that's pandas-side — the sim runner already coerces timestamps to `[ns, UTC]`. If it ever happens again, check that `_to_ns_utc` in `phase8_simulation_runner.py` is still applied to candles, funding, and OI.

---

## 5. Filter and export the trade log

**Where:** Tab **6 — Trade Log**.

**Filters (4 dropdowns at the top):**
- **Strategy** — `All` / `prev_day_breakdown_v1` / `short_composite_v1`
- **Exit reason** — `All` / `stop_loss` / `take_profit` / `max_hold_time`
- **Result** — `All` / `Wins only` / `Losses only`
- **Date range** — entry-date range picker

Filters compose. The metric strip at the top recalculates with each change.

**Export:** `⬇ Download CSV` button below the table — exports the current filtered view as `finding_alpha_trades.csv`.

**Inspect a single trade:** at the bottom, enter the trade `#` from the table column. Shows full anatomy: signal ID, entry/exit prices, fees, R-multiple, exit reason.

The trade log reflects whatever the sidebar is set to (sim or live), like every other tab.

---

## 6. Refresh the LLM advisory (CLI — not in UI)

The advisory drives the policy / risk-scalar cards on tabs 0, 2, 5. It expires (~24h). When it does, those cards turn red.

To refresh:

```bash
python notebooks/phase9_advisory_runner.py
```

Writes a new `advisory.json` at the project root and appends to `paper/advisory_log.jsonl`. Refresh the browser — the advisory cards update immediately. The "Advisory History" table on Tab 5 grows by one row.

The runner is interactive-safe — run it before a shareholder demo to ensure the advisory card is green and the model summary is current.

---

## 7. Common operational scenarios

| Scenario | What to do |
|---|---|
| Dashboard says everything is "STALE" | Run section 4 to refresh sim, or section 3 to run a live cycle |
| Advisory says "EXPIRED" | Run section 6 |
| Live cycle says `no_data` repeatedly | Bybit may be throttling — wait 5 min and retry |
| `Live Trading` page shows ghost position halt | Position on testnet that the bot didn't open. Either close manually on Bybit, or delete `paper/live/state.json` to reset (only safe if exchange is actually flat) |
| Demo time and sim data is stale | Section 4 takes ~30 sec; sidebar can switch to live for the trading demo without re-fetching |
| Want to wipe live state and start over | `rm -rf paper/live/` — next live cycle starts at $10k starting equity |

---

## 8. Files this dashboard touches

- `paper/sim/state.json`, `paper/sim/trades.jsonl`, `paper/sim/matrix.jsonl` — sim strategy 1
- `paper/sim/composite/...` — sim strategy 2
- `paper/live/...` and `paper/live/composite/...` — live testnet strategies
- `advisory.json` — current LLM advisory
- `paper/advisory_log.jsonl` — advisory history
- `data/bybit/BTCUSDT/...` — fetched market data (candles, funding, OI)
- `.env` — Bybit testnet credentials (gitignored — never commit)

Anything outside this list is read-only from the dashboard's perspective.
