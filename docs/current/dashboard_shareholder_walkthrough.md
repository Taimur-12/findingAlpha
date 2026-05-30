# Shareholder demo walkthrough

I'd present in this order. It tells a story: **what we built → how it performed historically → how risk is managed → what the AI says → the trade ledger → the real bot trading live**.

**Before you start:** sidebar selector should stay on **📊 Simulation** for tabs 1–6. Switch to **🛰 Live testnet** + Tab 7 for the closing demo.

---

## 🏠 Tab 0 — Overview (`app.py`, the landing page)

**Purpose:** the 30-second summary card. If they only saw one screen, this is it.

**What's on it:**
- Top-right mode pill (SIMULATION / LIVE TESTNET)
- 5 KPI cards: Account Equity, Total Return, Today's P&L, Max Drawdown, System Status
- Equity curve with 1M / 3M / ALL ranges showing prev_day (blue dotted), composite (purple dotted), Combined (solid green)
- Two strategy cards with equity, trades, win rate, expectancy, profit factor, net P&L
- Last 10 trades table
- Advisory snapshot at the bottom

**What to say:**
> "This is the system at a glance. Two strategies — prev_day_breakdown and short_composite — each get $10k starting capital. They trade BTC perpetuals on Bybit, only on the 1-hour timeframe, and they only short on confirmed downtrend setups. The big banner up top makes it unmissable that what you're looking at is historical replay data, not live money. When we switch to live mode later, that banner turns blue and says LIVE TESTNET."

**What to flag:**
- Combined equity is ~$19,955 on $20k starting — a small unrealized loss over the 14 sim trades. Don't hide it. Say: *"That's the honest result over a short historical window. 14 trades is not a verdict — it's a code-correctness check."*

---

## 📊 Tab 1 — Performance

**Purpose:** "Show me the math behind those headline numbers."

**What's on it:**
- 6-metric strip: Trades / Win Rate / Expectancy / Profit Factor / Net P&L / Total Fees
- Equity curve with drawdown shaded red, plus per-strategy curves
- R-multiple bar chart (each trade colored green/red, dashed line = avg R)
- Exit-reason breakdown (target / stop / timeout, with avg R and net P&L per category)
- Monthly P&L calendar
- Per-strategy summary tables (best trade, worst trade, avg hold time)

**What to say:**
> "R-multiple is how we measure trades — a +1R trade means we made what we risked, -1R means we lost the full risk amount. We size every trade so the risk is 0.25% of equity. So even our biggest loss is small in dollar terms. The exit-reason table shows where the money came from and went — most exits in this window were stop-outs, which matches our backtest expectation of a low-win-rate, high-R-multiple system."

**What to flag:**
- 28.6% win rate sounds bad. Frame it correctly: *"These are short-only momentum strategies — most setups fail. The thesis is the few that work pay 4-5x what we risk. Profit factor 1.00 = breakeven in sim; backtest projected 1.3-1.4."*

---

## 🟢 Tab 2 — Live Status

**Purpose:** "Is the system healthy right now?"

**What's on it:**
- System Health card: 4 rows (Runner 1 / Runner 2 / LLM Advisory / Circuit Breaker)
- Open Positions cards for both strategies (or "NO OPEN POSITION")
- Market Context table: regime, BTC price, EMA stack, RSI, ADX, ATR, funding rate + z, volume z
- LLM Advisory detail (policy, risk scalar, model, summary, reason codes)

**What to say:**
> "This is the operational health screen. The system reads market regime every bar — right now it's classified as `range` with low confidence, which is why neither strategy fires (both require `trend_down` or `breakout_pending`). The circuit breaker on the right is our safety switch: 5 consecutive losses in a day and we auto-halt new entries until midnight UTC."

**What to flag:**
- Tab will show "STALE" warnings because sim data is 4 days old. Acknowledge: *"This is reflecting the historical snapshot — when we deploy to cloud, those go green and update hourly."*

---

## ⚠️ Tab 3 — Risk Monitor

**Purpose:** "How do you prevent a blow-up?" — this is the trust-builder for risk-conscious shareholders.

**What's on it:**
- Big banner: CIRCUIT BREAKER ACTIVE / INACTIVE
- Per-strategy gauges (Daily Loss / Drawdown / Portfolio Heat) with green→amber→red zones
- Drawdown timeline with dashed lines for the -3% daily and -10% max-drawdown limits
- Risk Parameter Reference table

**What to say:**
> "This is the risk dashboard. Every position risks 0.25% of equity — small enough that 20 losers in a row would draw us down ~5%, not blow us up. Three hard limits: 3% daily loss → halt for the day; 10% drawdown → halt entirely; 5 consecutive losses → circuit breaker. These aren't suggestions — they're enforced in code before any order leaves the system."

**What to flag:**
- The gauges may show low values because risk is small by design. Say: *"Yes, these are intentionally well below limits — that's the point. We've sized the system to be boring on the downside."*

---

## 🔬 Tab 4 — Strategy Research

**Purpose:** "Why these two strategies and not something else?" — the credibility section.

**What's on it:**
- Two backtest evidence cards (3-year BTCUSDT 1H): trades, win rate, expectancy, profit factor, net P&L, max drawdown, walk-forward profitable windows — backtest vs live (sim) side by side
- Walk-forward bar chart (selectable strategy)
- **Phase 11 Pre-Flight Gate** — 8 checklist items with ✅/❌ icons
- Strategy specification expanders (entry triggers, stop rules, exit rules)

**What to say:**
> "Both strategies passed a 3-year backtest with positive expectancy and walk-forward stability. prev_day got 95 trades over 3 years — small sample, observation only. short_composite got 233 trades, profit factor 1.30. The Phase 11 gate at the bottom is what we need to clear before deploying real capital — we're 3 of 8 today. The remaining 5 require continuous cloud operation for 4-6 months."

**What to flag:**
- The "❌ Not deployed" items — be upfront: *"These are the gates between testnet and real money. We're deliberately not in a rush."*
- Walk-forward chart is *approximated* (the page caveats it). Don't oversell.

---

## 🤖 Tab 5 — Advisory Log

**Purpose:** "How does the AI actually help?" — the LLM story without overselling it.

**What's on it:**
- 4 cards: Policy / Risk Scalar / Event Type / Validity
- Quote block with the AI's one-sentence summary + model ID
- Allowed-strategies / reason-codes detail
- Advisory History table (chronological)
- "How the Advisory Works" expandable explanation

**What to say:**
> "Claude reads the market state once a day, looks at upcoming macro events — Fed meetings, CPI prints — and returns a structured decision: normal trading, reduce size, block new entries, or close risky positions. Critically: the AI cannot invent trades. It can only constrain or scale the deterministic strategies. If the AI file is missing, the system defaults to normal — it never blocks trading because of an AI outage."

**What to flag:**
- Be explicit about what the LLM does NOT do (the page lists it well — point to it). Shareholders are increasingly skeptical of "AI does trading" claims; this is your differentiator.

---

## 📋 Tab 6 — Trade Log

**Purpose:** "Show me every single trade." — the audit-trail tab.

**What's on it:**
- Filters: strategy / exit reason / wins-or-losses / date range
- 5-metric strip that recomputes as filters change
- Full trade table with entry/exit times, prices, P&L, R-multiple, hold time, exit reason
- CSV download
- Trade Detail Inspector for any single trade

**What to say:**
> "Every trade is logged. You can filter by strategy, exit reason, win/loss, date range — and export to CSV if you want to run your own analysis. The detail inspector at the bottom shows the full anatomy of any single trade: signal ID, entry, stop, fees, R-multiple, why we exited."

**What to flag:**
- This is the "we have nothing to hide" tab. Even a single trade has every field traceable.

---

## 🛰 Tab 7 — Live Trading (the closer)

**Purpose:** "Show me it actually works on a real exchange." — the kicker.

**Switch the sidebar to LIVE first** (banner turns blue, other tabs go empty).

**What's on it:**
- Testnet credentials check (✓ green if .env is loaded)
- Big **▶ RUN LIVE CYCLE NOW** button
- Last cycle result per strategy
- Live state cards (equity, position, last bar, circuit breaker status)
- Independent **Exchange Position** card (queried directly from Bybit, independent source of truth)
- Live trades table
- Recent matrix events per strategy

**What to say:**
> "This is the actual production code talking to a real Bybit exchange — testnet, so no real money. When I click RUN, the system: pulls the latest 1-hour candle, classifies the market regime, runs both strategies, and if either fires, places a real order on Bybit testnet. Watch what comes back."
>
> [Click the button. Wait ~5 seconds.]
>
> "First click typically says `no_data` or `up_to_date` — that just means the bar hasn't closed yet, which is the right behavior. The Exchange Position card at the bottom is queried directly from Bybit, independent of our internal state, so if there's ever a discrepancy we'd see it instantly."

**What to flag:**
- If `live_tick_error` appears, don't panic. Say: *"The page caught the error gracefully — that's the design. The system halts rather than guess."*
- Show the **Exchange Position card** explicitly. Say: *"This isn't reading our state file — it's calling Bybit directly. Two sources, must agree."*

---

## Closing slide narrative

> "So to summarize: 3 years of backtest evidence on two strategies, fully simulated with the production runtime, real Bybit testnet integration with reconciliation, AI advisory as a daily sanity-check that can only constrain — never expand — risk, and three hard-coded risk limits before anything reaches the exchange. We're 3 of 8 on the pre-flight gate. Next milestone: 24/7 cloud operation to fill in the remaining 5."

## Things to skip / not dwell on

- Walk-forward chart (Tab 4) — it's approximated. If they ask, be honest. Don't lead with it.
- 14 sim trades net loss — acknowledge once, move on. Don't anchor on it.
- "Cron / scheduler" — you don't have one yet. If asked: *"Cloud deployment is queued; the manual UI trigger on Tab 7 is the bridge."*

## Things to lean into

- The mode toggle (sim vs live) on the sidebar — shows you take honesty seriously
- The 8-item pre-flight gate (Tab 4) — proves discipline
- The exchange-vs-state separation (Tab 7) — proves operational rigor
- The "what the AI cannot do" list (Tab 5) — differentiates you from "AI trades for you" pitches
