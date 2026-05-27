# QuantFusionDevelopment Roadmap

##### Phase-by-phase build plan for the QuantFusion AI Quant Trading System. Each phase produces a

##### working deliverable that can be tested before moving to the next.

##### Total Phases 7 phases

##### Estimated Timeline 12-16 weeks to live trading

##### Approach Build one agent at a time, test, validate, then add the next

##### First Live Trade End of Phase 4 (paper trading from Phase 3)

##### ML Integration Phase 6 (after collecting enough trade data)

##### Full Autonomous Phase 7 (all agents live, ML optimised)


## Timeline Overview

##### Each phase builds on the previous one. Nothing gets skipped. Every phase has a clear deliverable and a

##### milestone that must be hit before moving forward.

Phase Name Duration Key Deliverable Agent(s) Built

```
1 Foundation Week 1-2 Local dev environment + data pipeline running Data Agent
2 The Brain Week 2-4 All indicators calculating live on real data Math Agent
3 Paper Trading Week 4-6 System taking paper trades with full checklist Position + Execution
4 Risk Cage Week 6-8 All risk controls active, paper trading validated Risk Agent
5 Context Layer Week 8-11 LLM reading news and adjusting scores Research Agent
6 Learning Loop Week 11-14 ML models trained, weights optimised Analytics Agent + ML
7 Full Deploy Week 14-16 Live trading with real capital, all agents active Full system
```

### Phase 1: Foundation — Data Agent Week 1-

##### Before anything can work, data must flow. This phase sets up the development environment and builds the

##### Data Agent — the plumbing that feeds everything else.

#### Week 1: Environment setup

Task Details Tools
Python environment Set up virtual env, install core libraries Python 3.11+, pip, venv
Install ccxt Unified exchange API library pip install ccxt
Install pandas-ta Technical indicator library pip install pandas-ta
Install asyncio/websockets Real-time data streaming pip install websockets aiohttp
Set up PostgreSQL Local database for historical data PostgreSQL + psycopg
Set up Redis In-memory cache for Ontology state Redis + redis-py
MEXC API keys Create API key on MEXC (read-only first) MEXC account settings
Bybit API keys Backup exchange API key Bybit account settings
Project structure Create folder structure for all agents FastAPI project scaffold

#### Week 2: Data Agent live

Task Details
WebSocket price stream Connect to MEXC WebSocket, receive BTC/ETH/SOL/XRP ticks in real-time
OHLCV candle builder Aggregate ticks into 5M, 15M, 1H candles locally
Funding rate polling REST API call every 8 hours, store in database
Open interest polling REST API call every 1 minute, store in database
Volume tracking Calculate current volume and MA(5), MA(10), MA(20)
Historical data download Download 2 years of OHLCV data for all 4 pairs, all 3 timeframes
Data validation Detect stale data (no update > 10 sec), missing candles, corrupt values
Failover test Simulate MEXC disconnect, verify switch to Bybit within 2 seconds
Ontology state Write all live data to Redis shared state — first version of the Ontology

```
MILESTONE Data Agent streaming live BTC/ETH/SOL/XRP data with failover working
```

### Phase 2: The Brain — Math Agent Week 2-

##### Now that data is flowing, the Math Agent calculates all indicators in real-time and implements the

##### confirmation checklist. This is the quantitative core of the system.

#### Week 3: Indicator engine

Task Details
RSI calculation Implement dual RSI (6 and 24 period) across all 3 timeframes for all 4 pairs
MACD calculation MACD line, signal line, histogram (12, 26, 9) — detect shrinking/growing bars
EMA 200 200-period EMA on all timeframes — price above or below check
Bollinger Bands 20-period, 2 std dev — upper, middle, lower band positions
ATR 14-period ATR for stop loss sizing — outputs dollar value for each pair
Volume ratio Current candle volume vs MA(20) — flag when > 1.5x and > 3x
Correlation matrix Rolling 30-day correlation between all 4 pairs — update every hour
Indicator validation Compare calculated values against MEXC chart values — must match

#### Week 4: Checklist + trigger + backtesting

Task Details
Trigger gate RSI threshold detection — fires when RSI crosses below 25/28/30 or above 70/72/
5-point checklist When trigger fires: check EMA trend, MACD momentum, volume, funding, OI
Score calculation Sum confirmations — output 0 to 5 score
Session detection Determine current session (Asia/London/NY) based on UTC time
Session thresholds Apply different minimum scores per session
Higher TF override If 1H is bearish, block 5M/15M long signals
Backtest engine Run the full checklist against 2 years of historical data
Backtest results Calculate win rate, expectancy, Sharpe, profit factor on historical signals

```
MILESTONE Backtest shows positive expectancy — the edge is statistically validated
```

### Phase 3: Paper Trading — Position + Execution Agents Week 4-

##### The system starts taking simulated trades. No real money yet. Position Agent sizes the trades, Execution

##### Agent places paper orders. This validates the strategy works in real-time, not just in backtests.

Task Details
Position sizing formula Implement: risk = balance x 0.25%, stop = 1.5x ATR, size = risk / stop
DCA layer logic Layer 1 at threshold, Layer 2 at threshold-5, Layer 3 at extreme — each with own checklist
Portfolio exposure tracking Track total open exposure, enforce max 3 concurrent positions
Paper order engine Simulated order placement — tracks entry, stop, TP without real exchange orders
Paper P&L tracking Calculate simulated P&L on every tick — mirror real exchange behaviour
Stop loss simulation Trigger simulated stop when price hits 1.5x ATR from entry
Take profit simulation Trigger simulated TP when RSI crosses back to 45-50 zone
Daily target tracking Track simulated daily P&L — flag when +0.5% target hit
Trade logging Log every paper trade: entry, exit, score, confirmations, session, duration, P&L
2-week paper trading run Run the system for 2 weeks on live data with paper trades — validate results

```
MILESTONE 2 weeks of paper trading show consistent positive P&L with < 5% drawdown
```

### Phase 4: Risk Cage — Risk Agent Week 6-

##### The Risk Agent gets built and tested. This is the guardian. Every risk rule is implemented, tested against

##### historical worst-case scenarios, and validated. Nothing goes live without the Risk Agent being bulletproof.

Task Details
Per-trade risk cap Enforce max 0.25% of account per trade — verify Position Agent complies
Max concurrent positions Block 4th trade regardless of score — test with rapid signals
Correlation blocker If already long BTC, block ETH/SOL if correlation > 0.
Losing streak breaker 3 consecutive losses → pause 30 min. 5 consecutive → stop for session
Daily loss limit -1.5% → all trading stops. Test by simulating bad day.
Daily target shutoff +0.5% → all trading stops. Verify no new trades after target hit.
Max drawdown kill switch -8% from peak → everything stops. CEO must manually restart.
Session threshold enforcement Asia: 5/5 only. London: 4/5. Prime: 3/5. Verify correct per session.
Stress testing Run Risk Agent against Luna crash data, FTX collapse data, COVID crash data
Survival validation Confirm the system survives worst historical scenarios without breaching limits
First real money test Deploy with $50-100 real capital. Tiny size. Validate real exchange execution.

```
MILESTONE Risk cage survives Luna/FTX/COVID stress tests. First real trade executes.
```

### Phase 5: Context Layer — Research Agent Week 8-

##### The LLM-powered Research Agent adds contextual awareness. The system can now understand WHY

##### price is dropping, not just that it is dropping. This is the difference between catching a normal dip and

##### walking into a systemic collapse.

Task Details
CryptoPanic API integration Connect to news feed, receive structured articles every 5 minutes
Fear & Greed Index Pull daily index from Alternative.me — add to Ontology
Claude API integration Set up Anthropic SDK, design prompt for sentiment classification
Sentiment scoring pipeline News article → Claude → bullish/bearish/neutral + score -1.0 to +1.
Event type classification Normal volatility vs systemic crisis vs regulatory vs exchange-specific
Confidence multiplier logic Map sentiment score to multiplier (0.15x for crisis, 1.1x for positive)
ChromaDB setup Vector database to store past news + outcomes for similarity search
News embedding pipeline Convert articles to embeddings, store in ChromaDB with market reaction data
Historical calibration Run past news through the pipeline, compare multiplier vs actual outcome
A/B test Compare math-only performance vs math+context for 2 weeks — measure improvement
Telegram alerts Send trade signals to your Telegram when system enters/exits positions

```
MILESTONE A/B test shows math+context outperforms math-only. Research Agent improves win rate.
```

### Phase 6: Learning Loop — Analytics Agent + ML Week 11-

##### By now the system has weeks of trade data. The Analytics Agent analyses everything and trains ML

##### models to optimise the strategy. Fixed thresholds get replaced by learned weights. The system evolves

##### from rule-following to pattern-recognising.

#### Analytics Agent build

Task Details
Trade log database Structured log: entry, exit, pair, TF, side, score, confirmations, session, P&L
Performance calculator Rolling win rate, Sharpe, profit factor, expectancy — updated after each trade
Session breakdown Which session produces best returns? Best win rate? Best risk-adjusted return?
Indicator contribution Which confirmation check has highest predictive value? Rank them.
Daily report generator Auto-generate PDF/HTML report every morning for CEO review
Dashboard API FastAPI endpoints serving all metrics to the Next.js frontend

#### ML model training

Model Purpose Library
Random Forest classifier Which indicator combos best predict bounces scikit-learn
XGBoost classifier Higher accuracy signal classification xgboost
Logistic regression Simple baseline to compare against scikit-learn
Regime detection (HMM) Classify market as normal/trending/volatile/crisis hmmlearn
Indicator weight optimiser Learn optimal weight for each confirmation check scikit-learn
Sentiment calibration Optimise the news multiplier based on outcomes scikit-learn
Strategy decay detector Alert if win rate trends downward over time statsmodels
Position size optimiser Learn optimal size given volatility and score scikit-learn
Hyperparameter tuning Automatically find best model settings optuna

```
MILESTONE ML-optimised weights outperform fixed thresholds in backtest. Models deployed.
```

### Phase 7: Full Deployment — All Systems Live Week 14-

##### Everything comes together. All 7 agents are live. ML models are deployed. The system trades

##### autonomously with real capital. The CEO monitors and adjusts.

Task Details
Capital deployment Start with $500-1,000. Scale only after 30 days of profitability.
Next.js dashboard Build the CEO dashboard — live P&L, positions, metrics, risk gauges
Telegram notifications Trade entries, exits, daily summary, risk alerts, kill switch notifications
Weekly model retrain ML models retrain every Sunday on latest trade data
Monthly strategy review CEO reviews monthly performance, adjusts targets, tweaks parameters
Compounding activation Position sizes auto-scale with growing account balance
Daily target scaling Month 1: 0.5%. Month 2-3: 0.75%. Month 4+: 1.0%. Based on proven consistency.
Documentation All parameters, model versions, and changes documented in git
Redundancy System running on both local machine and VPS backup
Scale capital After 3 months profitability: deposit additional capital, increase position sizes

```
MILESTONE System is autonomous, profitable, and compounding. The AI hedge fund is live.
```

## Complete Install & Setup Checklist

##### Everything you need to install before writing a single line of code.

Category Package / Service Install Command or Action
Python Python 3.11+ brew install python (Mac) / python.org (Windows)
Exchange ccxt pip install ccxt
Indicators pandas-ta pip install pandas-ta
Data pandas + numpy pip install pandas numpy
Data scipy pip install scipy
Streaming websockets + aiohttp pip install websockets aiohttp
Database PostgreSQL brew install postgresql / apt install postgresql
Database psycopg2 pip install psycopg2-binary
Cache Redis brew install redis / apt install redis
Cache redis-py pip install redis
API FastAPI + uvicorn pip install fastapi uvicorn
LLM anthropic SDK pip install anthropic
Vector DB chromadb pip install chromadb
Embeddings sentence-transformers pip install sentence-transformers
ML scikit-learn pip install scikit-learn
ML xgboost pip install xgboost
ML hmmlearn pip install hmmlearn
ML optuna pip install optuna
ML statsmodels pip install statsmodels
Dashboard Node.js + Next.js brew install node && npx create-next-app
Charts plotly pip install plotly
Notifications python-telegram-bot pip install python-telegram-bot
Account MEXC API keys MEXC → Account → API Management → Create key
Account Bybit API keys Bybit → Account → API Management → Create key
Account Anthropic API key console.anthropic.com → API Keys → Create
Account CryptoPanic API key cryptopanic.com → API → Get free key
Account Telegram Bot BotFather on Telegram → /newbot → save token

##### The rule: complete each phase's milestone before starting the next. No skipping. No shortcuts.

##### Each phase produces a working, testable deliverable.
