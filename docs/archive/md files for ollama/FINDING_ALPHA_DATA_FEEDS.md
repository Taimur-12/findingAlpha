# Finding Alpha — Complete Data Feed Architecture

This document lists every data source that should feed into the Matrix state layer. Organized by priority tier (Tier 1 = essential, Tier 3 = nice-to-have). For each source: what it provides, why it matters, which agent consumes it, and API/access details.

---

## TIER 1 — ESSENTIAL (MUST HAVE)

These sources are non-negotiable. Without them, the reasoning layer is operating half-blind.

### 1.1 MEXC Contract API (already connected)

**What it provides:** Single-exchange raw market data for the exchange where trades will actually execute.

**Endpoints in use / should be in use:**
- `kline/{symbol}` — OHLCV candles (all timeframes)
- `depth/{symbol}` — live order book (20 levels)
- `deals/{symbol}` — recent trades stream (build CVD from this)
- `funding_rate/{symbol}` — current funding and next funding time
- `funding_rate/history/{symbol}` — historical funding data
- `open_interest/{symbol}` — current OI
- `index_price/{symbol}` — spot reference
- `mark_price/{symbol}` — liquidation reference
- `ticker/{symbol}` — 24h stats

**Base URL:** `https://contract.mexc.com/api/v1/contract/`
**Auth:** None for public data
**Rate limit:** ~20 req/sec per IP (verify current)
**Websocket:** `wss://contract.mexc.com/edge` — subscribe to klines, depth, deals for real-time streaming instead of polling

**Why essential:** execution venue data. Must match what your orders actually fill against.

---

### 1.2 Coinglass API

**What it provides:** Aggregated cross-exchange data — the single most important data layer beyond MEXC. This is where liquidation heatmaps, aggregated OI, and funding comparisons live.

**Key data:**
- **Liquidation heatmap** — visualization of leveraged position clusters across exchanges. The "liquidity map" that shows where price is magnetically drawn.
- **Aggregated open interest** — total OI across all major exchanges (Binance, Bybit, OKX, MEXC, Bitget, etc.). More meaningful than any single exchange.
- **Funding rate dashboard** — current funding on every exchange for every major pair. Cross-exchange comparison lets you spot divergences.
- **Long/short ratio** — global positioning sentiment gauge
- **Liquidation data (historical + real-time)** — actual liquidations as they happen, size, exchange, side
- **Options data** — put/call ratio, max pain, gamma exposure (for BTC/ETH)
- **ETF flow data** — institutional spot ETF inflows/outflows (US BTC/ETH ETFs)

**Access:** `https://open-api.coinglass.com` (paid API) or public endpoints on coinglass.com
**Auth:** API key required for full access (paid tiers starting around $29/month — worth it)
**Free tier:** Limited to certain endpoints; rate-limited

**Consumer agents:** Positioning Agent, Liquidity Agent, Risk Agent

**Why essential:** Single-exchange data is systematically biased. Aggregated data reveals the true state of the market. A funding spike on MEXC alone might be local; a spike across all exchanges is a real signal.

---

### 1.3 Binance Public API

**What it provides:** The largest exchange by volume. Even if you're not trading on Binance, its data is the deepest liquidity reference in crypto.

**Endpoints to consume:**
- Spot klines, trades, order book
- Futures klines, funding, OI
- Long/short ratio endpoints
- Top trader long/short ratios (position and account)

**Base URL:** `https://api.binance.com` (spot), `https://fapi.binance.com` (futures)
**Auth:** None for public
**Rate limit:** Generous (1200 weight/minute public)

**Consumer agents:** Positioning Agent, Order Flow Agent, Structure Agent (for cross-reference)

**Why essential:** If MEXC shows a signal and Binance doesn't, the signal is exchange-specific noise. If both show it, the signal is real.

---

### 1.4 Bybit Public API

**What it provides:** Second major futures exchange. Often leads or confirms moves that Binance and MEXC lag on.

**Endpoints:**
- Klines, trades, order book
- Funding, OI
- Long/short ratio

**Base URL:** `https://api.bybit.com`
**Auth:** None for public
**Rate limit:** 120 req/sec general

**Consumer agents:** Same as Binance

**Why essential:** Three-exchange confirmation (MEXC + Binance + Bybit) is the baseline for any signal involving positioning.

---

### 1.5 OKX Public API

**What it provides:** Major Asian-leaning exchange. Often moves differently from Binance during Asia session. Strong options and derivatives presence.

**Endpoints:**
- Klines, trades, order book
- Funding, OI
- Options data (stronger than most exchanges)

**Base URL:** `https://www.okx.com`
**Auth:** None for public

**Consumer agents:** Positioning Agent, News/Macro Agent (Asia session bias)

**Why essential:** Regional bias detection. If Asia is buying/selling differently than US/EU, OKX reveals it first.

---

## TIER 2 — HIGH VALUE (STRONGLY RECOMMENDED)

These dramatically improve the model's context and signal quality. Add after Tier 1 is stable.

### 2.1 Coinalyze API

**What it provides:** Similar to Coinglass but cleaner for some use cases. Good secondary source for aggregated derivatives data.

**Key data:**
- Aggregated OI by exchange (clean breakdown)
- Funding rate aggregation
- Liquidation data
- Long/short ratio by exchange
- Predicted funding rates

**Access:** `https://coinalyze.net/api/` (paid API)
**Auth:** API key

**Consumer agents:** Positioning Agent

**Why it matters:** Redundancy. When Coinglass data looks anomalous, cross-reference here. Also cheaper for certain data types.

---

### 2.2 Velo Data API

**What it provides:** Professional-grade derivatives analytics. Used by institutional traders.

**Key data:**
- Futures term structure (basis curves)
- Options volatility surfaces
- Funding rate heatmaps and z-scores
- Cross-exchange arbitrage spreads
- Implied vs realized volatility

**Access:** `https://api.velodata.app` (free tier + paid tiers)
**Auth:** API key

**Consumer agents:** Positioning Agent, Risk Agent (volatility regime detection)

**Why it matters:** Options data provides forward-looking risk information that futures data doesn't. High IV = market expecting volatility. Term structure inversions often precede major moves.

---

### 2.3 Glassnode / CryptoQuant (On-chain data)

**What it provides:** On-chain flows — the "real" liquidity that moves between wallets, exchanges, and protocols. Different dimension from exchange data.

**Key data:**
- **Exchange inflows/outflows** — BTC/ETH moving onto exchanges = potential selling pressure. Off exchanges = accumulation.
- **Whale wallet movements** — transactions above 1000 BTC or 10000 ETH
- **Stablecoin flows** — USDT/USDC movements onto exchanges often precede buying
- **Miner behavior** — miner selling pressure, reserve changes
- **Long-term holder (LTH) vs short-term holder (STH) ratios**
- **Realized price, MVRV, SOPR** — cycle position indicators

**Access:**
- Glassnode: `https://api.glassnode.com/v1/` (paid, starts ~$30/month for basic)
- CryptoQuant: `https://api.cryptoquant.com` (paid, free tier limited)

**Consumer agents:** News/Macro Agent, Liquidity Agent

**Why it matters:** Whales moving coins onto exchanges is a leading indicator of selling that happens before it shows in price. On-chain data is the only way to see the whale before the trade.

---

### 2.4 Hyblock Capital

**What it provides:** Retail sentiment and order flow analytics, including some liquidity heatmap data.

**Key data:**
- Retail sentiment indicators
- Liquidity levels visualization
- Order flow indicators
- Market-maker positioning estimates

**Access:** `https://hyblockcapital.com` (paid subscription, API access on higher tiers)
**Auth:** Subscription-based

**Consumer agents:** Liquidity Agent, Order Flow Agent

**Why it matters:** Purpose-built retail positioning tools. Complements Coinglass.

---

### 2.5 Tensorcharts

**What it provides:** Order book heatmaps across exchanges showing persistent liquidity over time (not spoofed).

**Key data:**
- Order book depth heatmap
- Volume-weighted price zones
- Liquidity gradients

**Access:** `https://tensorcharts.com` (web + API on paid tier)

**Consumer agents:** Order Flow Agent

**Why it matters:** Spoofed orders disappear. Persistent orders over time show up as brighter zones. This visualization reveals where *real* liquidity sits vs market-maker games.

---

### 2.6 News APIs

The model needs to know what's happening in the world and correlate it to price action.

**Options (pick 1–2):**

**CryptoPanic API** — aggregated crypto news feed
- `https://cryptopanic.com/developers/api/`
- Free tier available
- Categorized by coin, sentiment, urgency

**NewsData.io** — broad news aggregator with crypto category
- `https://newsdata.io/`
- Free tier: 200 credits/day

**CoinDesk / CoinTelegraph RSS** — free but unstructured

**Santiment** — includes news + sentiment scoring
- `https://api.santiment.net`
- Paid

**Consumer agents:** News/Macro Agent, Coordinator Agent

**Why it matters:** Catalysts cause participation. The model needs to know when a major news event hits so it can distinguish news-driven pumps (distribution opportunity) from organic moves.

---

### 2.7 Twitter/X API (or scraping)

**What it provides:** Social sentiment, influencer positioning, real-time market reactions.

**Access:**
- Official X API: tiered pricing ($100+/month for meaningful access)
- Alternative: ScrapingBee, Apify, or custom scraping infrastructure

**Key data to extract:**
- Mentions of BTC/ETH/specific pairs
- Trending crypto topics
- Tracked influencer tweets (Waqar Zaka, known traders, Arthur Hayes, etc.)
- Sentiment scoring on major coins

**Consumer agents:** News/Macro Agent

**Why it matters:** A Trump tweet about trade or Iran moves crypto before traditional news feeds pick it up. Twitter is the fastest signal channel for unscheduled catalysts.

**Note:** easy to over-weight social data. Use it as a trigger flag, not a directional signal.

---

### 2.8 Macro / TradFi Data

Crypto correlates with traditional markets. The model should see macro context.

**Key data feeds:**
- **DXY (Dollar Index)** — inverse correlation with BTC
- **SPY / QQQ** — US equity indices, general risk-on/risk-off
- **VIX** — fear gauge, spikes often precede crypto volatility
- **US 10Y Treasury yield** — risk appetite signal
- **Gold** — alternative store of value comparison

**Access options:**
- Alpha Vantage (free tier): `https://www.alphavantage.co` — 25 req/day free
- Yahoo Finance (unofficial via yfinance Python library): free
- Polygon.io: `https://polygon.io` — generous free tier
- TwelveData: `https://twelvedata.com` — free tier with good coverage

**Consumer agents:** News/Macro Agent, Coordinator Agent

**Why it matters:** BTC doesn't move in isolation. A sharp DXY rally or equity selloff changes the probability of BTC breaking support, even without crypto-specific news.

---

### 2.9 Economic Calendar

**What it provides:** Scheduled macro events that historically move crypto (CPI, FOMC, NFP, PCE).

**Options:**
- **TradingEconomics API** — `https://tradingeconomics.com/api` (paid)
- **Forex Factory** — free calendar, scrape or RSS
- **Investing.com** — calendar via scraping
- **FMP (Financial Modeling Prep)** — `https://financialmodelingprep.com/developer/docs/economic-calendar-api/` (free tier)

**Consumer agents:** News/Macro Agent, Risk Agent

**Why it matters:** The Risk Agent should be aware that CPI drops in 2 hours and reduce position size or halt trading during high-impact events. Trading blind into a Fed announcement is a known way to blow up.

---

## TIER 3 — NICE TO HAVE (ADVANCED)

Add these once Tiers 1 and 2 are fully operational and you want to extend the edge.

### 3.1 DeFi / DEX data

**What it provides:** On-chain DEX activity — often leading for smaller altcoins.

**Sources:**
- **DEX Screener API** — `https://docs.dexscreener.com/api/reference` (free)
- **GeckoTerminal API** — `https://api.geckoterminal.com/` (free)
- **The Graph / subgraphs** — protocol-specific data

**Consumer agents:** News/Macro Agent (altcoin expansion later)

**Why it matters:** If the bot ever expands beyond BTC/ETH, DEX flows are critical for smaller coins where CEX data is thin.

---

### 3.2 Perpetual options (Deribit, Lyra)

**What it provides:** Options flow gives forward-looking information that futures don't.

**Sources:**
- **Deribit API** — `https://www.deribit.com/api/v2` (free public data)
- Key metrics: DVOL, put/call skew, gamma exposure, max pain

**Consumer agents:** Risk Agent, Positioning Agent

**Why it matters:** Gamma walls on major expiries often act as magnets. Put/call skew reveals fear/greed quantitatively.

---

### 3.3 Stablecoin supply and flows

**What it provides:** USDT and USDC minting/burning events and flow patterns. Stablecoin supply growth often precedes rallies.

**Sources:**
- **Tether transparency page** — daily supply
- **Glassnode stablecoin metrics**
- **DefiLlama stablecoin API** — free: `https://stablecoins.llama.fi/`

**Consumer agents:** News/Macro Agent

**Why it matters:** When $1B of USDT is minted in 24 hours, it eventually finds its way into BTC/ETH. Supply changes are a leading liquidity indicator.

---

### 3.4 Miner / validator data (BTC, ETH)

**What it provides:** Hash rate, miner reserves, miner selling pressure.

**Sources:**
- Glassnode / CryptoQuant miner metrics
- BTC.com pool data
- Bitcoin node data (if running own node)

**Consumer agents:** News/Macro Agent

**Why it matters:** Miner capitulation historically marks bottoms. Large miner outflows to exchanges signal supply pressure.

---

### 3.5 Whale wallet tracking

**What it provides:** Specific large wallets entering/exiting positions, both on-chain and on exchanges.

**Sources:**
- **Whale Alert API** — `https://docs.whale-alert.io/` (paid)
- **Arkham Intelligence** — free tier, API access
- **Nansen** — paid, highest quality
- **Etherscan API** for ETH whale tracking

**Consumer agents:** Liquidity Agent, News/Macro Agent

**Why it matters:** A known fund wallet moving 50K ETH onto Binance is an early signal. Institutional wallets leave footprints.

---

### 3.6 Fear & Greed Index

**What it provides:** Composite sentiment indicator.

**Source:** Alternative.me — `https://api.alternative.me/fng/` (free, no auth)

**Consumer agents:** News/Macro Agent

**Why it matters:** Simple contrarian indicator. Extreme greed = caution on longs. Extreme fear = caution on shorts. Not an entry signal but useful context.

---

### 3.7 Google Trends data

**What it provides:** Retail attention gauge.

**Source:** pytrends library or Google Trends unofficial APIs

**Consumer agents:** News/Macro Agent

**Why it matters:** Retail search interest peaks often coincide with cycle tops. Useful as a late-stage distribution confirmation signal.

---

## PROPOSED ARCHITECTURE FOR DATA INGESTION

```
┌─────────────────────────────────────────────────┐
│                   MATRIX                        │
│         (Central State / Ontology Layer)        │
└─────────────────────────────────────────────────┘
         ▲                    ▲                ▲
         │                    │                │
   ┌─────┴─────┐      ┌───────┴──────┐   ┌─────┴─────┐
   │ Realtime  │      │  Periodic    │   │ Event     │
   │ Streamers │      │  Pollers     │   │ Webhooks  │
   └─────┬─────┘      └───────┬──────┘   └─────┬─────┘
         │                    │                │
┌────────┴───────┐   ┌────────┴────────┐   ┌───┴────────┐
│ MEXC WS        │   │ Coinglass REST  │   │ News RSS   │
│ Binance WS     │   │ Coinalyze REST  │   │ Twitter    │
│ Bybit WS       │   │ Glassnode REST  │   │ Webhooks   │
│ OKX WS         │   │ Macro APIs      │   │            │
└────────────────┘   └─────────────────┘   └────────────┘
```

**Three ingestion patterns:**

1. **Realtime streamers (websockets)** — MEXC, Binance, Bybit, OKX for price, book, trades. Low latency. Keep these always-on.

2. **Periodic pollers (REST)** — Coinglass, Coinalyze, Glassnode, macro data. Poll at intervals appropriate to the data (funding every 5 min, OI every 1 min, ETF flows every hour, etc.).

3. **Event-driven** — news, whale alerts, calendar events. Push into Matrix when they arrive.

---

## DATA LAYER RECOMMENDATIONS

### Storage

- **Redis** — for real-time state (latest prices, order book snapshots, active signals). Every agent reads from Redis for current market state.
- **TimescaleDB or ClickHouse** — for historical time-series (klines, funding history, OI history). Essential for calculating z-scores and historical baselines.
- **Postgres** — for structured data (trades, signals, positions, journal entries).

### Processing

- **Dedicated signal computation layer** between raw data and Matrix. Don't let agents recompute CVD or OI deltas on every query — compute once, cache in Redis with TTL.
- **Normalization layer** — every exchange has quirks (MEXC uses `BTC_USDT`, Binance uses `BTCUSDT`). Normalize symbols, funding intervals, and timestamps at ingestion.

### Key derived metrics to compute from raw data

These should be pre-computed and cached, not calculated on every reasoning call:

- CVD (per symbol, per timeframe) from trade streams
- OI delta (15m, 1h, 4h, 24h changes)
- Funding z-score (vs 30-day mean/stddev)
- Cross-exchange OI aggregate (sum across MEXC, Binance, Bybit, OKX)
- Cross-exchange funding average
- Aggregated long/short ratio
- Liquidation cluster estimates (from OI + price + assumed leverage distribution)
- Volatility (realized, 24h/7d/30d)
- Volume z-score (current vs average)

---

## RECOMMENDED IMPLEMENTATION ORDER

Don't try to wire all of this at once. Build in stages:

**Stage 1 — Get aggregated view (week 1)**
- Binance + Bybit + OKX public data (alongside existing MEXC)
- Compute aggregated OI and average funding across 4 exchanges
- Positioning Agent now sees cross-exchange picture

**Stage 2 — Add Coinglass (week 2)**
- Subscribe to Coinglass API (paid tier)
- Ingest liquidation heatmap data
- Ingest aggregated long/short ratios
- Liquidity Agent operational

**Stage 3 — Add news and macro (week 3)**
- CryptoPanic or similar for news feed
- Economic calendar API
- DXY, SPY, VIX, 10Y via TwelveData or Alpha Vantage
- News/Macro Agent operational

**Stage 4 — Add on-chain (week 4)**
- Glassnode or CryptoQuant (exchange flows, whale wallet data)
- Stablecoin supply via DefiLlama (free)
- Leading indicator layer operational

**Stage 5 — Add advanced (optional, month 2+)**
- Options data (Deribit)
- Tensorcharts / Hyblock
- Social sentiment (X/Twitter)

By the end of Stage 4, the bot has more data context than 95% of retail traders and most retail-facing trading bots.

---

## COST ESTIMATE (MONTHLY)

Approximate costs for a production setup:

| Tier | Service | Monthly Cost |
|---|---|---|
| Free | Binance, Bybit, OKX, MEXC public APIs | $0 |
| Free | TwelveData / Alpha Vantage (macro) | $0 |
| Free | CryptoPanic (basic), DefiLlama, Fear & Greed | $0 |
| Paid | Coinglass Pro | ~$29 |
| Paid | Coinalyze (optional alt) | ~$30 |
| Paid | Glassnode Advanced | ~$39 |
| Paid | X/Twitter API (if using) | ~$100 |
| Paid | Velo Data (optional) | ~$50+ |
| **Total realistic minimum** | | **~$70 (Coinglass + Glassnode)** |
| **Total with everything** | | **~$250** |

For early stages, $70/month gets you Coinglass + Glassnode which covers the highest-impact paid data. Everything else can be free-tier or delayed.

---

## IMPORTANT NOTE ON DATA QUALITY

Not all data is equal. Priority of signal quality (highest to lowest):

1. **Direct exchange data** (MEXC, Binance, Bybit, OKX) — source of truth, no intermediary
2. **Aggregated derivatives** (Coinglass, Coinalyze) — trustworthy, well-maintained
3. **On-chain data** (Glassnode, CryptoQuant) — accurate but laggy (blockchain confirmation times)
4. **News feeds** — variable quality, requires filtering
5. **Social sentiment** — extremely noisy, use as confirmation only
6. **Google Trends** — slow, smoothed, retrospective

Weight signals from higher tiers more heavily in the confluence scoring. A Twitter sentiment flip alone is not a trade; a Twitter flip + on-chain whale outflow + funding divergence is.

---

## FINAL CHECKLIST FOR THE AI MODEL

When designing prompts for Llama, make sure it has access to the following current state fields at minimum:

**Price context:**
- Current price, 24h change, 24h high/low
- Current timeframe structure (weekly/daily/4h bias)
- Nearest support and resistance zones
- Distance to each level (%)

**Positioning context:**
- Aggregated OI (current + 24h delta + z-score)
- Aggregated funding rate (current + z-score vs 30d mean)
- Long/short ratio
- Largest liquidation clusters above and below current price

**Flow context:**
- CVD divergence status (aligned/diverging/neutral)
- Volume z-score
- Recent large trades (>$500k)
- Order book imbalance

**Macro context:**
- DXY, SPY, VIX current state and 24h change
- Next scheduled high-impact event and time
- Any recent news flagged by sentiment agent
- BTC dominance and trend

**Risk context:**
- Current account state (P&L, open positions)
- Daily drawdown vs limits
- Volatility regime (normal/elevated/extreme)
- Circuit breaker status

With this data set populated in Matrix, the Coordinator Agent has everything needed to apply the six-dimension confluence framework and make decisions that match or exceed experienced human traders.
