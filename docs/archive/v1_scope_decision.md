# v1 Scope Decision

Date: 2026-05-27
Status: FROZEN

## Symbols

- Primary: BTCUSDT
- Secondary: ETHUSDT (only after BTC path is fully working)

## Timeframes

- 15m and 1h only
- 5m is blocked until paper trading proves fill quality

## Strategies To Research

Research these separately. Do not combine.

1. Liquidity sweep reversal
2. Short/long squeeze
3. Trend pullback

Only the single best validated strategy moves to paper trading first.

## Position Limits

- Micro-live: 1 position max
- Live v1: 2 positions max (only after single-position live is stable)

## Risk Policy (v1)

| Mode | Risk per trade | Daily loss stop |
|---|---|---|
| Paper | simulated | simulated |
| Micro-live | 0.10–0.25% | 0.75–1.00% |
| Live v1 | 0.25% | 1.50% |

## Execution Venue

- Bybit USDT linear perpetuals — first technical execution target
- One-way mode, isolated margin
- Subject to venue eligibility gate (see venue_eligibility_decision.md)

## Reference Data Venues

- Binance USD-M futures — primary reference (klines, funding, OI)
- OKX public data — secondary reference
- MEXC public data — optional reference only, not live execution

## Blocked For v1

- 5m live scalping
- DCA / averaging down
- Multi-exchange live execution
- Autonomous LLM trade approval
- Reinforcement learning
- Auto parameter changes in production
- Market making / arbitrage / options
- Full dashboard (before engine is validated)
