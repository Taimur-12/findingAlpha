# Finding Alpha — Dashboard UI Guide
**Date:** 2026-05-30  
**Purpose:** Complete specification for a partner/shareholder-facing dashboard that monitors the trading system in real time  
**Audience:** Partners, shareholders, operator (you)

---

## 0. Design Philosophy

The dashboard serves two different audiences simultaneously:

**Partners / Shareholders** want to see: Is the money safe? Is the system working? Is it making money? They think in USDT, not R-multiples. They want clean, big numbers, and confidence-inspiring visual design.

**Operator (you)** want to see: Is the code healthy? What regime is active? Did the advisory fire? Why did that signal get rejected? You think in R-multiples, reason codes, and log events.

The solution: one system, two views. A **Summary View** (partner-facing, no jargon) and an **Operator View** (full technical depth). Both share the same data layer.

---

## 1. Reference — What Top Systems Show

| Platform | Key UI Patterns They Use |
|---|---|
| **QuantConnect** | Equity curve vs benchmark, rolling Sharpe widget, drawdown shading, per-strategy P&L breakdown, trade annotation on chart |
| **Interactive Brokers TWS** | Real-time risk gauge meters, position heat, live P&L tickers, customisable alert banners |
| **Freqtrade UI** | Strategy card grid, profit factor chart, trade table with colour coding, daily/weekly/monthly breakdown calendar |
| **Alpaca** | Clean equity curve, recent trades with green/red colouring, position cards with unrealised P&L |
| **Grafana** | Time-series panels, alert status lights, gauge widgets for thresholds, heatmap calendars |
| **Numerai** | Correlation + Sharpe radar chart, per-model performance, risk-adjusted return comparison |
| **Bloomberg Terminal** | Dense data grids, colour-coded risk levels, multi-pane chart layout, news feed panel |

**What the best shareholder-facing dashboards share:**
1. Five or fewer KPI numbers at the top, very large font
2. Equity curve as the hero chart — nothing else comes first
3. No unexplained jargon (no "R-multiple" without an explanation, no raw log output)
4. Green/red colour coding that is unambiguous
5. A system status indicator that shows "everything is working" in one glance
6. Mobile readable (partners check on their phone)

---

## 2. Recommended Tech Stack

### Primary Recommendation: Streamlit

**Why:** Finding Alpha already generates all data in JSONL and JSON formats. Streamlit reads Python natively, connects directly to those files, and produces a professional interactive dashboard in 2–3 days of work with zero frontend expertise needed.

```
finding_alpha/
└── dashboard/
    ├── app.py              ← main Streamlit entry point
    ├── pages/
    │   ├── 1_Performance.py
    │   ├── 2_Live_Status.py
    │   ├── 3_Risk_Monitor.py
    │   ├── 4_Strategy_Research.py
    │   ├── 5_Advisory_Log.py
    │   └── 6_Trade_Log.py
    ├── data/
    │   ├── loader.py       ← reads JSONL/JSON/Parquet, returns dataframes
    │   └── metrics.py      ← thin wrapper over analytics/metrics.py
    └── components/
        ├── kpi_card.py
        ├── equity_chart.py
        ├── trade_table.py
        └── status_lights.py
```

**Dependencies to add:**
```
streamlit>=1.35
plotly>=5.22
pandas>=2.2
altair>=5.3
streamlit-autorefresh   ← auto-refresh every 60s for live mode
```

**Run command:**
```bash
streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0
```

Accessible from any browser on your cloud VM: `http://your-vm-ip:8501`

### Alternative: Grafana + JSON datasource
Use only if you have DuckDB/Phase 11.5 built first. More powerful for time-series but requires more setup. Recommended post-Phase 11.5.

### Not Recommended Yet: Next.js + FastAPI
Production quality but adds 2–3 weeks of setup. Build Streamlit first, migrate when the system is live and you have real capital to justify it.

---

## 3. Colour System and Visual Design

### Colour Palette (dark theme — standard for trading systems)

```
Background:     #0D1117   (near black, GitHub dark style)
Card surface:   #161B22
Border:         #30363D
Text primary:   #E6EDF3
Text secondary: #8B949E

Profit/positive: #3FB950   (green)
Loss/negative:   #F85149   (red)
Warning/caution: #D29922   (amber)
Neutral:         #58A6FF   (blue)
Flat/inactive:   #6E7681   (grey)

Strategy 1:     #58A6FF   (blue — prev_day_breakdown_v1)
Strategy 2:     #BC8CFF   (purple — short_composite_v1)
Benchmark:      #6E7681   (grey — BTC buy-and-hold)
```

### Typography
```
Headers:    Inter or Geist — large (32–48px for KPIs, 18–24px for section headers)
Body:       Inter 14px
Monospace:  JetBrains Mono or Fira Code — for log output and raw values
```

### Status Indicators

Use coloured dot + text, not just colour alone (accessibility):
```
● OPERATIONAL       #3FB950
● SIMULATION        #BC8CFF   ← replay of historical bars via paper/sim/
● PAPER TRADING     #58A6FF   ← real-time REST polling, no real money
● CIRCUIT BREAKER   #F85149
● DATA STALE        #D29922
● OFFLINE           #6E7681
```

---

## 4. Global Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  FINDING ALPHA                          ● PAPER TRADING    Last: 14:00 UTC   │
│  Systematic Crypto Trading              BTCUSDT 1H — Bybit                   │
├──────────────────────────────────────────────────────────────────────────────┤
│  [Overview]  [Performance]  [Live Status]  [Risk]  [Research]  [Advisory]    │
│             [Trade Log]                                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   PAGE CONTENT                                                               │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

The header is always visible. It shows:
- System name
- Mode badge (SIMULATION / PAPER / TESTNET / LIVE) — colour-coded. Source of truth: `execution_mode` field in `PaperRuntimeConfig` (runtime.py). SIMULATION = historical replay (paper/sim/); PAPER = real-time REST polling; TESTNET = Bybit testnet with live_execution; LIVE = real capital.
- Last data refresh timestamp (`last_processed_bar_ts` from state.json)
- Symbol and timeframe

---

## 5. Page 1 — Overview (Partner/Shareholder Landing Page)

This is what a partner sees first. Zero trading jargon. Everything expressed in dollars and plain language.

### 5.1 KPI Strip (top of page, 5 large cards)

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ ACCOUNT EQUITY   │  │ TOTAL RETURN      │  │ TODAY'S P&L      │
│ $10,247.83       │  │ +$247.83          │  │ +$23.50          │
│ ↑ since start    │  │ +2.48% all-time   │  │ +0.23% today     │
└──────────────────┘  └──────────────────┘  └──────────────────┘

┌──────────────────┐  ┌──────────────────┐
│ CURRENT DRAWDOWN │  │ SYSTEM STATUS     │
│ −1.2%            │  │ ● OPERATIONAL     │
│ from peak equity │  │ Running normally  │
└──────────────────┘  └──────────────────┘
```

**Colour rules for KPIs:**
- Equity: always white
- Total return: green if positive, red if negative
- Today's P&L: green/red/grey (grey if zero)
- Drawdown: red if > 5%, amber if 2–5%, green if < 2%
- Status: dot colour as per §3

### 5.2 Equity Curve (hero chart)

Full-width chart. This is the most important visual on the page.

```
Equity ($)
$10,300 ┤                                              ╭──
$10,200 ┤                                         ╭───╯
$10,100 ┤                           ╭─────╮  ╭───╯
$10,000 ┤╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌ Starting Capital
 $9,900 ┤                  ╰─────╯
         Week 1   Week 2   Week 3   Week 4   Week 5   Week 6
         
Legend:  ── Finding Alpha   ╌╌ Starting Capital   ░░ Drawdown periods
```

**Chart requirements:**
- Plotly line chart, dark theme
- Drawdown highlighted as red fill between equity line and rolling peak
- Trade markers (dots) on the curve at each closed trade — green for win, red for loss
- Hover tooltip shows: date, equity, trade details if applicable
- Time range selector: 1W / 1M / 3M / ALL
- Toggle: "Show benchmark (BTC buy & hold)" — compare against passive holding

### 5.3 Strategy Performance Cards

Two cards side by side, one per strategy.

```
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│ prev_day_breakdown_v1           │  │ short_composite_v1              │
│ ────────────────────────────── │  │ ────────────────────────────── │
│ Trades:      12                 │  │ Trades:      21                 │
│ Win rate:    33%                │  │ Win rate:    38%                │
│ Avg profit:  +0.42R = +$10.50  │  │ Avg profit:  +0.24R = +$6.00   │
│ Net P&L:     +$87.30           │  │ Net P&L:     +$118.40          │
│ ────────────────────────────── │  │ ────────────────────────────── │
│ Status: ● MONITORING           │  │ Status: ● MONITORING            │
└─────────────────────────────────┘  └─────────────────────────────────┘
```

**Plain-language status labels:**
- ● MONITORING — paper trading, no real money
- ● ACTIVE — live trading with real money
- ● PAUSED — circuit breaker tripped
- ● FLAT — no trades in past 7 days (normal for low-frequency)

### 5.4 Recent Trades Table (last 10)

```
Date/Time          Strategy              Side   Entry      Exit     P&L      Result
─────────────────  ───────────────────  ─────  ─────────  ───────  ───────  ──────────
2026-05-28 08:00   short_composite_v1   SHORT  $69,240    $66,100  +$31.20  ✓ +3.14R
2026-05-25 14:00   prev_day_breakdown   SHORT  $68,510    $69,100  -$14.75  ✗ -0.93R
2026-05-22 07:00   short_composite_v1   SHORT  $71,200    $67,800  +$42.10  ✓ +4.21R
...
```

**Colour coding:**
- Row background: subtle green tint for wins, red tint for losses
- P&L column: green text / red text
- Result: checkmark (win) or x (loss) with colour

**Tooltip on hover:** Shows full trade details — strategy trigger, regime at entry, LLM advisory decision, fee breakdown

### 5.5 Partner-Friendly Explanation Panel (collapsible)

```
▼ How does this work?

Finding Alpha is an automated trading system that shorts Bitcoin futures on the 
Bybit exchange. It uses two rule-based strategies that look for specific market 
conditions before entering a trade:

• Each trade risks exactly $25 (0.25% of the $10,000 account)
• Every position has an automatic stop-loss placed immediately upon entry
• The system trades 1–5 times per week depending on market conditions
• An AI advisor reviews conditions daily and can reduce or block trading if 
  risk conditions are unfavourable

The equity curve above shows how the account has grown since we started. 
Green dots are winning trades. Red dots are losing trades.
```

---

## 6. Page 2 — Performance (Deep Analytics)

For more sophisticated partners and for your own research. All the numbers.

### 6.1 Performance Metrics Grid

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ALL TIME           │  LAST 30 DAYS       │  BACKTEST COMPARISON            │
│  ─────────────────  │  ─────────────────  │  ───────────────────────────── │
│  Trades:      33    │  Trades:      7     │  Expected trades/mo:  6–8       │
│  Win rate:    36%   │  Win rate:    43%   │  Backtest win rate:   36.9%    │
│  Expectancy: +0.27R │  Expectancy: +0.31R│  Backtest expectancy: +0.235R  │
│  Profit factor: 1.32│  Profit factor: 1.45│  Backtest PF:         1.30    │
│  Max drawdown: -3.2%│  Max drawdown: -1.1%│  Backtest max dd:    -5.1%    │
│  Sharpe:      0.84  │  Sharpe:      1.12  │  Backtest Sharpe:    ~0.70    │
│  Net P&L:   +$206   │  Net P&L:    +$54   │                               │
│  Total fees:  $31   │  Total fees:   $7   │                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Colour on backtest comparison column:** Green if live is beating backtest, amber if within 20%, red if significantly underperforming.

### 6.2 Equity Curve with Drawdown Subplot

```
                    ─────── Equity ($) ───────
$10,400 ┤                                              ╭──
$10,200 ┤                                         ╭───╯
$10,000 ┤═══════════════════════════════════════════════════ Starting Capital
 $9,900 ┤                  ╰───╯

                    ─────── Drawdown (%) ───────
   0.0% ┤──────────────────────────────────────────────────
  -2.0% ┤                  ░░░░░
  -4.0% ┤ ░░░░
  
Zoom:  [ 1W ]  [ 1M ]  [ 3M ]  [ 6M ]  [ ALL ]
```

### 6.3 Monthly Returns Heatmap

Calendar-style grid showing monthly P&L as a percentage. Industry standard for hedge fund reporting.

```
         Jan    Feb    Mar    Apr    May    Jun    Jul    Aug
2026    +1.2%  -0.8%  +2.1%  +0.3%  +0.9%   —      —      —
2025      —      —      —      —      —      —      —      —
```

Colour gradient: deep green (+3%) → white (0%) → deep red (-3%)

### 6.4 Trade Distribution (R-Multiple Histogram)

```
Frequency
    │
 10 ┤           ██
  8 ┤        ██ ██ ██
  6 ┤     ██ ██ ██ ██ ██
  4 ┤  ██ ██ ██ ██ ██ ██ ██
  2 ┤  ██ ██ ██ ██ ██ ██ ██ ██
    └──┬──┬──┬──┬──┬──┬──┬──┬──▶ R-multiple
      -2  -1   0  +1  +2  +3  +4  +5

Expected loss trades are -1R (stop hit). Expected win trades are +4.5R (target hit).
```

**Note for partner mode:** Replace R-multiple x-axis with dollar amounts.

### 6.5 Performance by Session

Bar chart showing win rate and expectancy by trading session:
- Asia (00:00–07:00 UTC)
- London (07:00–13:00 UTC)
- London-NY Overlap (13:00–17:00 UTC)
- NY (17:00–22:00 UTC)
- Wind-Down (22:00–00:00 UTC)

### 6.6 Performance by Regime

```
Regime          Trades   Win%    Avg R    Net P&L
──────────────  ──────   ─────   ──────   ──────────
trend_down        18     44%    +0.31R   +$145.20
breakout_pending   9     28%    +0.12R    +$22.80
high_volatility    4     25%    -0.08R    -$8.40
range              2     50%    +0.15R    +$6.00
```

### 6.7 Exit Reason Breakdown (Donut Chart)

```
        Take Profit (TP)  ████████████  36%  → average +4.5R
        Stop Loss         ████████████████████  54%  → average -1.0R  
        Max Hold Time     █████  10%  → average +0.8R
```

### 6.8 Fee Analysis

```
Total gross profit:     $318.40
Total fees paid:         $31.80  (10.0% of gross — target: < 20%)
Net profit:             $286.60

Fee breakdown:
  Entry maker fees:     $12.30  (38.7%)
  Exit taker fees:      $15.20  (47.8%)
  Stop slippage:         $4.30  (13.5%)
```

### 6.9 Rolling Performance Chart (30-day rolling window)

Line chart showing how the 30-day rolling expectancy has evolved over time. Helps detect strategy decay early — if the line trends toward zero, the edge may be disappearing.

---

## 7. Page 3 — Live Status (Operator + Partner)

Everything about what the system is doing right now. Auto-refreshes every 60 seconds.

### 7.1 System Health Panel

```
┌────────────────────────────────────────────────────────────────────────────┐
│  SYSTEM HEALTH                                        Last refresh: 14:01  │
│                                                                            │
│  Data Feed         ● LIVE      Last bar: 14:00 UTC (1 min ago)            │
│  Paper Runner 1    ● RUNNING   prev_day_breakdown_v1 — last run: 14:01    │
│  Paper Runner 2    ● RUNNING   short_composite_v1 — last run: 14:01       │
│  LLM Advisory      ● CURRENT   Expires: 2026-05-31 06:00 UTC              │
│  Exchange API      ● CONNECTED Bybit testnet — ping: 48ms                 │
│  Cron Health       ● OK        Last heartbeat: 14:01 UTC                  │
└────────────────────────────────────────────────────────────────────────────┘
```

**Status rules:**
- Data feed STALE if last bar > 2 hours ago → amber → red
- Runner NOT RUNNING if last run > 2 hours ago → alert banner shown
- Advisory EXPIRING if < 2 hours remaining → amber
- Advisory EXPIRED if past expiry → red

### 7.2 Current Position Card

**When FLAT (no position):**
```
┌──────────────────────────────────────┐
│  CURRENT POSITION                    │
│  ───────────────────────────────    │
│          NO OPEN POSITION            │
│                                      │
│  Strategy slot: AVAILABLE            │
│  Next signal check: ~14:00 UTC       │
└──────────────────────────────────────┘
```

**When SHORT position is open:**
```
┌──────────────────────────────────────────────────────┐
│  CURRENT POSITION — SHORT BTCUSDT                    │
│  ────────────────────────────────────────────────── │
│  Strategy:     short_composite_v1 (EMA rejection)   │
│  Entered:      2026-05-30 07:00 UTC (4h 12m ago)    │
│  Entry price:  $69,240.00                           │
│  ────────────────────────────────────────────────── │
│  Stop loss:    $70,100.00  (+$860 / +1.24%)         │
│  Take profit:  $65,800.00  (-$3,440 / -4.97%)       │
│  Max hold:     12h → exits by 19:00 UTC             │
│  ────────────────────────────────────────────────── │
│  Current price: $68,950.00                         │
│  Unrealised P&L: +$145.80 (+0.42R)   ↑ winning     │
│  Risk at stake:  $25.00              (0.25%)        │
└──────────────────────────────────────────────────────┘
```

**Colour:** Card border green when winning, red when losing.

### 7.3 Market Context Panel

```
┌──────────────────────────────────────────────────────────────────────────┐
│  MARKET CONTEXT — BTCUSDT 1H                        as of 14:00 UTC     │
│                                                                          │
│  Regime:          trend_down (confidence: 80%)                          │
│  ADX:             31.4  (strong trend)                                   │
│  EMA Stack:       20 < 50 < 200 ✓  (bearish alignment)                  │
│  ATR (14):        $820  (52nd percentile — normal volatility)           │
│  RSI (14):        43.2  (mildly bearish)                                │
│  Funding rate:    +0.008%  (slightly positive — longs paying)           │
│  Funding z-score: +0.4  (neutral)                                       │
│  Volume z-score:  +1.8  (elevated)                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

### 7.4 LLM Advisory Card

```
┌──────────────────────────────────────────────────────────────────────────┐
│  LLM ADVISORY                               Generated: 06:00 UTC today  │
│                                                                          │
│  Trade Policy:    NORMAL — trading permitted                            │
│  Risk Scalar:     1.00 × (full sizing)                                  │
│  Expires:         06:00 UTC tomorrow                                    │
│                                                                          │
│  Summary: "No material risk events identified. Recent paper trades       │
│  are within expected range. No changes to trading parameters."          │
│                                                                          │
│  Strategies allowed: ALL                                                │
└──────────────────────────────────────────────────────────────────────────┘
```

**When advisory has reduced risk:**
```
│  Trade Policy:    REDUCE_SIZE                                           │
│  Risk Scalar:     0.50 × (half sizing today)                           │
│  Summary: "FOMC meeting in 6 hours. Elevated macro uncertainty.         │
│  Reducing position sizing until outcome known."                         │
```

### 7.5 Signal History (today's bar-by-bar decisions)

Table showing what happened on each bar today:

```
Bar Time    Regime         Signal?   Decision         Advisory Gate
──────────  ─────────────  ────────  ───────────────  ──────────────
14:00 UTC   trend_down     ✓ SHORT   APPROVED         Risk scalar: 1.0
13:00 UTC   trend_down     ✗ none    —                —
12:00 UTC   breakout_pend  ✗ none    —                —
11:00 UTC   trend_down     ✓ SHORT   REJECTED (heat)  —
10:00 UTC   high_volat.    ✗ none    BLOCKED (regime) —
09:00 UTC   trend_down     ✗ none    —                —
```

---

## 8. Page 4 — Risk Monitor

### 8.1 Risk Gauge Meters (top row)

Three large gauge/speedometer style widgets:

```
         Daily Loss Limit           Drawdown              Portfolio Heat
         ─────────────────         ─────────────         ──────────────────
         
              ████░░               ██░░░░               ████░░
         
         Current: -0.8%            Current: -1.2%        Current: 0.25%
         Limit:   -3.0%            Limit:   -10.0%       Limit:   6.0%
         Used:     27%             Used:      12%         Used:     4%
         
         ● SAFE                   ● SAFE                ● SAFE
```

Colours: Green → Amber (at 60% used) → Red (at 85% used)

### 8.2 Circuit Breaker Status

Large visual indicator. Cannot be missed.

**When inactive (normal):**
```
┌────────────────────────────────────────────────┐
│                                                │
│          ● CIRCUIT BREAKER: INACTIVE           │
│          Trading is permitted                  │
│                                                │
│  Consecutive losses:  1 / 5 (reset threshold) │
│  Daily loss:         -0.8% / -3.0%            │
│  Max drawdown:       -1.2% / -10.0%           │
│                                                │
└────────────────────────────────────────────────┘
```

**When tripped (critical):**
```
┌────────────────────────────────────────────────┐
│                                                │
│    ██  CIRCUIT BREAKER: ACTIVE  ██             │
│    NO NEW TRADES PERMITTED                     │
│                                                │
│  Reason:  Daily loss limit reached (-3.2%)     │
│  Tripped: 2026-05-30 11:32 UTC                │
│  Resets:  2026-05-31 00:00 UTC (midnight)     │
│                                                │
│  [Manual Reset]  ← requires confirmation       │
└────────────────────────────────────────────────┘
```

### 8.3 Risk Policy Table

```
Risk Policy (current configuration)
──────────────────────────────────────────────────────────────
Parameter                    Value          Status
Risk per trade:              0.25% ($25)    ● Active
Daily loss limit:            3.0%  ($300)   ● Active
Max drawdown from peak:      10.0% ($1,000) ● Active
Max portfolio heat:          6.0%           ● Active
Max open positions:          1              ● Active
Circuit breaker (losses):    5 consecutive  ● Active
Data stale threshold:        2h             ● Active
Max snapshot age:            2h             ● Active
```

### 8.4 Risk Event Log

Chronological log of all risk decisions:

```
Time          Event                              Details
────────────  ─────────────────────────────────  ───────────────────────────
14:01 UTC     ✓ Trade approved                   short_composite_v1
13:01 UTC     — No signal                        regime=trend_down, no trigger
11:15 UTC     ✗ Trade rejected — MAX_POSITIONS   already 1 open position
08:00 UTC     ✓ Trade approved                   prev_day_breakdown_v1
2026-05-29    ✗ Trade rejected — DATA_STALE      feed offline 2h
```

---

## 9. Page 5 — Strategy Research (Operator + Sophisticated Partners)

This page shows the validation evidence for each strategy — the "why we trust these strategies" page.

### 9.1 Backtest Summary Cards

```
┌─────────────────────────────────────────────────────────────────────┐
│  prev_day_breakdown_v1 — Backtest Evidence (3 years BTCUSDT 1H)    │
│  ─────────────────────────────────────────────────────────────────  │
│  Total trades:       95        Walk-forward windows:  21           │
│  Win rate:          31.6%      WF profitable:          9/21 (43%)  │
│  Expectancy:       +0.42R      WF avg expectancy:     +0.47R       │
│  Profit factor:     1.44       Net P&L (backtest):  +$1,015        │
│  Max drawdown:     -4.2%       Status: PAPER OBSERVATION ONLY      │
│                                                                     │
│  ⚠ Small sample (95 trades). Observation only until live evidence. │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  short_composite_v1 — Backtest Evidence (3 years BTCUSDT 1H)       │
│  ─────────────────────────────────────────────────────────────────  │
│  Total trades:      233        Walk-forward windows:  33           │
│  Win rate:         36.9%       WF profitable:         16/33 (48%)  │
│  Expectancy:      +0.235R      WF avg expectancy:    +0.24R        │
│  Profit factor:    1.30        Net P&L (backtest):  +$1,398        │
│  Max drawdown:    -5.1%        Status: PAPER OBSERVATION           │
└─────────────────────────────────────────────────────────────────────┘
```

### 9.2 Walk-Forward Results Chart

Visual showing all walk-forward windows, colour-coded profitable/losing:

```
Window    Return    ████████████████████████████████████████████████
  1/33     +1.2%   ████████████████████████████████████ (green)
  2/33     -0.4%   ██████████████████ (red, short)
  3/33     +0.8%   ████████████████████████████ (green)
  ...
 16/33     +0.3%   ████████████████████████████████████████ (green)
 33/33     -0.1%   ████████████████████ (red, short)
           
Profitable windows:  16/33 (48%)   [██████████████████████░░░░░░░░░░░]
```

### 9.3 Backtest vs Live Comparison (updates as live data accumulates)

```
Metric           Backtest    Paper (live)    Status
───────────────  ──────────  ──────────────  ──────────────────────
Win rate         36.9%       38.0%           ✓ Within range
Expectancy       +0.235R     +0.27R          ✓ Slightly better
Profit factor    1.30        1.32            ✓ Within range
Avg hold time    7.2h        7.8h            ✓ Within range
Stop hit rate    63%         60%             ✓ Within range
TP hit rate      37%         40%             ✓ Within range
Fee share        18%         21%             ⚠ Slightly higher live
```

### 9.4 Validation Checklist (Paper → Live Gate)

```
Phase 11 Pre-Flight Gate                                   (as of 2026-05-30)
─────────────────────────────────────────────────────────────────
[ ] 30+ live paper trades completed         ✗  0/30 (14 sim replay trades exist —
                                                  not counted; sim ≠ live observation)
[x] No unprotected positions ever            ✓  0 incidents
[x] Exchange reconciliation clean            ✓  0 divergences (testnet verified)
[ ] 6-8 weeks continuous cloud operation    ✗  Not deployed
[ ] Live expectancy within 2σ of backtest   ✗  Insufficient live data
[ ] Advisory log shows daily decision hist  ⚠  1 advisory entry (runner ran once)
[ ] No circuit breaker trips from code bug  ✗  Insufficient live data
[ ] Manual intervention count: 0            ✗  Insufficient live data
```

**Note on sim vs live trade counts:** The `paper/sim/` trades (14 total) are historical simulation replays — the runtime processed past bars using stored candle data. They confirm the pipeline fires correctly but do **not** satisfy the live observation gate. The gate requires trades executed against real-time Bybit data in cloud operation.

---

## 10. Page 6 — Advisory Log

### 10.1 Advisory Timeline

Chronological view of all LLM advisory decisions:

```
Date         Policy     Risk Scalar  Summary
───────────  ─────────  ───────────  ──────────────────────────────────────
2026-05-30   NORMAL     1.00         No material events. Trading normal.
2026-05-29   REDUCE     0.75         Elevated macro uncertainty. FOMC data.
2026-05-28   NORMAL     1.00         No material events.
2026-05-27   BLOCK      0.00 ██      Exchange maintenance detected. No trading.
2026-05-26   NORMAL     1.00         No material events.
```

### 10.2 Advisory Value Analysis

As live data accumulates, show:

```
LLM Advisory Performance (shadow mode analysis)
─────────────────────────────────────────────────────────────────────
Advisory decisions analysed:  47 bars with signals

NORMAL decisions (allowed trading):  39 bars
  → Avg trade outcome: +0.28R
  
REDUCE decisions (half sizing):  5 bars
  → Avg trade outcome at full size would have been: -0.12R
  → Saving from reduce: +0.06R per avoided trade
  
BLOCK decisions (no trading):  3 bars  
  → Avg outcome if traded: -0.85R (would have been losses)
  → Saving from block: $63.75

Estimated advisory value: +$71.40 total (+0.71% of account)
```

### 10.3 Advisory Input/Output Inspector

For each advisory, show what was sent to Claude and what came back. Useful for debugging and improving the prompts.

---

## 11. Page 7 — Trade Log (Full History)

### 11.1 Filters Bar

```
Date range: [2026-01-01] to [2026-05-30]  
Strategy: [ All ▾]  Exit reason: [ All ▾]  Result: [ All ▾]  [Export CSV]
```

### 11.2 Full Trade Table

```
#   Date/Time        Strategy             Side   Entry      Exit       Qty    P&L      R       Exit Reason
─── ──────────────   ──────────────────   ─────  ─────────  ─────────  ─────  ───────  ──────  ───────────────
33  2026-05-30 07h   short_composite_v1   SHORT  $69,240    —          0.036  open     open    (in progress)
32  2026-05-28 08h   short_composite_v1   SHORT  $69,240   $66,100    0.036  +$31.20  +3.14R  take_profit ✓
31  2026-05-25 14h   prev_day_breakdown   SHORT  $68,510   $69,100    0.036  -$14.75  -0.93R  stop_loss ✗
30  2026-05-22 07h   short_composite_v1   SHORT  $71,200   $67,800    0.035  +$42.10  +4.21R  take_profit ✓
```

**Expandable row** (click any trade): shows full details including:
- Feature snapshot at entry (regime, ATR, RSI, EMA stack, funding z-score)
- Signal evidence (what triggered the entry)
- LLM advisory at time of entry
- Risk decision reason codes
- Fee breakdown (entry fee, exit fee, slippage)
- MFE (maximum favourable excursion — how far in profit it got)
- MAE (maximum adverse excursion — how close to stop it got)

---

## 12. Shareholder Report — Standalone PDF View

A separate export function that generates a clean one-page PDF report for monthly partner updates. Auto-generated from the dashboard data.

### Report Layout:

```
FINDING ALPHA — MONTHLY PERFORMANCE REPORT
Month: May 2026

ACCOUNT SUMMARY
───────────────────────────────────────────────────
Starting equity:    $10,000.00
Ending equity:      $10,247.83
Month P&L:          +$247.83 (+2.48%)
Month trades:       11
Win rate:           36%
Profit factor:      1.32

RISK SUMMARY
───────────────────────────────────────────────────
Maximum drawdown this month:    -2.1%
Circuit breaker trips:          0
Unprotected positions:          0
System uptime:                  99.7%

STRATEGY BREAKDOWN
───────────────────────────────────────────────────
prev_day_breakdown_v1:  4 trades, 25% wins, +$42.50
short_composite_v1:     7 trades, 43% wins, +$205.33

NEXT MONTH
───────────────────────────────────────────────────
Continuing paper observation. Target: 30 total trades
before any live capital discussion.

RISK DISCLOSURE: This is a systematic trading system.
Past performance does not guarantee future results.
```

---

## 13. Mobile View (Partner Checks on Phone)

The Streamlit layout must be mobile-responsive. On mobile, simplify to:

**Home screen (phone):**
```
FINDING ALPHA             ● PAPER

Equity
$10,247.83
+$247.83 (+2.48%)

Drawdown: -1.2%     Status: ● OK

──────────────────────────────
CURRENT POSITION: FLAT

Next signal check: 15:00 UTC
──────────────────────────────
LAST 3 TRADES
✓ +3.14R  2026-05-28
✗ -0.93R  2026-05-25
✓ +4.21R  2026-05-22
──────────────────────────────
[View Full Dashboard]
```

---

## 14. Alert System (Integrated with Dashboard)

### 14.1 In-Dashboard Alert Banner

When a critical condition exists, a persistent red banner appears at the top of every page:

```
⚠  CIRCUIT BREAKER ACTIVE — Daily loss limit reached. No new trades.
   Resets: 2026-05-31 00:00 UTC.                              [Dismiss]
```

### 14.2 Telegram Bot Notifications (recommended)

Set up a Telegram bot that sends a message when:

| Event | Message |
|---|---|
| Trade opened | `📊 SHORT BTCUSDT @$69,240 — short_composite_v1` |
| Trade closed (win) | `✅ +$31.20 (+3.14R) — stop: $70.1k target: $65.8k` |
| Trade closed (loss) | `❌ -$14.75 (-0.93R) — stop hit` |
| Circuit breaker tripped | `🚨 CIRCUIT BREAKER: daily loss -3.1% — no new trades today` |
| Data stale | `⚠️ Data feed stale — no bar received in 2+ hours` |
| Advisory generated | `🤖 Advisory: NORMAL (1.0×) — no material events` |
| System offline | `🔴 Paper runner offline — last heartbeat 3h ago` |

Cost: $0. One day to set up.

### 14.3 Email Report (weekly, automated)

A cron job that sends a weekly email every Sunday with the month-to-date summary. Plain text, no images (works on all email clients).

---

## 15. Implementation Roadmap

### Phase A: Minimum Viable Dashboard (3–4 days)
Everything needed to show partners the system is working.

| Day | Work |
|---|---|
| 1 | Set up Streamlit app, data loader (reads JSONL/JSON), KPI cards, equity curve |
| 2 | Trade table, position card, system health panel |
| 3 | Risk gauges, circuit breaker status, monthly P&L |
| 4 | Partner-friendly language, mobile test, deploy to cloud VM |

**Output:** Shareable URL, partners can check anytime.

### Phase B: Full Analytics (3–4 additional days)
For sophisticated partners and your own research.

| Day | Work |
|---|---|
| 5 | Performance page: drawdown chart, distribution histogram, session breakdown |
| 6 | Strategy research page: backtest vs live, walk-forward chart, validation gate |
| 7 | Advisory log page: timeline, value analysis |
| 8 | Trade log: full table, expandable rows, CSV export, PDF report generator |

### Phase C: Live System Integration (after cloud deployment)
Once the system is live on a cloud VM.

| Feature | Work |
|---|---|
| Telegram bot notifications | 1 day |
| Auto-refresh (every 60s) | 30 minutes (streamlit-autorefresh) |
| Weekly email report | 2 hours (sendgrid free tier) |
| healthchecks.io dead-man | 30 minutes |
| Grafana migration (post DuckDB) | 3 days (do after Phase 11.5) |

---

## 16. Complete File Structure

```
findingAlpha/
└── dashboard/
    ├── app.py                         ← Streamlit entry point (Overview page)
    ├── requirements_dashboard.txt     ← streamlit, plotly, pandas, altair
    ├── .streamlit/
    │   └── config.toml                ← dark theme, page config
    ├── pages/
    │   ├── 1_📈_Performance.py
    │   ├── 2_🟢_Live_Status.py
    │   ├── 3_⚠️_Risk_Monitor.py
    │   ├── 4_🔬_Strategy_Research.py
    │   ├── 5_🤖_Advisory_Log.py
    │   └── 6_📋_Trade_Log.py
    ├── data/
    │   ├── loader.py                  ← loads paper state, trades, matrix, advisory
    │   └── metrics.py                 ← wraps analytics/metrics.py for dashboard use
    └── components/
        ├── kpi_card.py                ← reusable styled metric card
        ├── equity_chart.py            ← plotly equity curve with drawdown
        ├── trade_table.py             ← styled dataframe with colour coding
        ├── gauge_widget.py            ← risk gauge meters
        ├── status_light.py            ← ●/●/● health indicators
        └── position_card.py           ← current position display
```

### Streamlit Config (`.streamlit/config.toml`)
```toml
[theme]
base = "dark"
primaryColor = "#58A6FF"
backgroundColor = "#0D1117"
secondaryBackgroundColor = "#161B22"
textColor = "#E6EDF3"
font = "sans serif"

[server]
headless = true
port = 8501
address = "0.0.0.0"
enableCORS = false
enableXsrfProtection = true
```

---

## 17. Data Sources for Each Page

All data comes from files already written by the system.

### 17.1 Directory layout (as of 2026-05-30)

The paper runtime writes to two separate subdirectories, one per strategy:

```
paper/
├── sim/
│   ├── state.json              ← prev_day_breakdown_v1 runtime state
│   ├── trades.jsonl            ← prev_day_breakdown_v1 closed trades
│   └── matrix.jsonl            ← prev_day_breakdown_v1 event log
├── sim/composite/
│   ├── state.json              ← short_composite_v1 runtime state
│   ├── trades.jsonl            ← short_composite_v1 closed trades
│   └── matrix.jsonl            ← short_composite_v1 event log
└── advisory_log.jsonl          ← all LLM advisory decisions (shared)

advisory.json                   ← current LLM advisory (project root)
```

When `execution_mode='live'` (via `live_execution.py`), the same state schema is used but orders are submitted to Bybit instead of being simulated. The dashboard reads the same files regardless of mode.

### 17.2 Page-to-file mapping

| Page | Data Source |
|---|---|
| Overview KPIs | `paper/sim/state.json` + `paper/sim/composite/state.json` (merge equity) |
| Equity curve | `paper/sim/trades.jsonl` + `paper/sim/composite/trades.jsonl` |
| Position card | `paper/sim/state.json` and/or `paper/sim/composite/state.json` (`open_position` field) |
| System health | Both `state.json` files (`last_processed_bar_ts`), file mtimes |
| Market context | `paper/sim/matrix.jsonl` (last FeatureSnapshot + RegimeState events) |
| Advisory card | `advisory.json` (project root) |
| Advisory log | `paper/advisory_log.jsonl` |
| Risk gauges | Both `state.json` files (`equity`, `peak_equity`, `daily_start_equity`) |
| Circuit breaker | Both `state.json` files (`circuit_breaker_active`) |
| Strategy research | `docs/current/_phase7c_short_composite_v1.json`, `_phase7b_*.json` |
| Trade log | `paper/sim/trades.jsonl` + `paper/sim/composite/trades.jsonl` |

No new data generation needed. The dashboard is a read-only view of files the system already writes.

---

## 18. Security

The dashboard will be publicly accessible via the cloud VM IP. Minimum security measures:

```python
# In app.py — basic password gate for partner access
import streamlit_authenticator as stauth

credentials = {
    "usernames": {
        "partner": {"password": hashed_password, "name": "Partner"},
        "operator": {"password": hashed_password_2, "name": "Operator"},
    }
}
```

Or simpler: restrict by IP using Nginx reverse proxy in front of Streamlit, allowing only known partner IPs.

**Never expose the dashboard without authentication** — it reveals position information, strategy details, and account state.

---

*End of UI Dashboard Guide. All design decisions are grounded in the actual data Finding Alpha produces today. Implementation starts with Phase A (3–4 days) immediately after cloud deployment.*
