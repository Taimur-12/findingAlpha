# NautilusTrader vs Custom Simulator — Decision

Date: 2026-05-27
Status: DECIDED

## Decision: Adopt NautilusTrader as substrate

## What the Spike Proved

The Phase 1 spike (`phase1_nautilus_spike.py`) confirmed:

1. NautilusTrader v1.227.0 installs cleanly on Python 3.12 / Windows
2. The Bybit adapter (`BybitLiveDataClientFactory`) is present and importable
3. Our `SignalCandidate -> RiskDecision -> Order` pipeline fits cleanly inside
   a NT Strategy class with zero architectural friction
4. NT processed 200 BTCUSDT 15m bars, our risk check ran, 1 order was submitted
   and filled, account and fill reports were generated
5. Instrument precision enforcement is strict (volume precision must match
   size_precision) — this is a feature, not friction, as it forces correct precision

The one friction point encountered (volume precision mismatch) was a data
formatting issue fixed in one line. It revealed NT's strictness around
precision, which aligns with our Decimal-everywhere doctrine.

## Architecture Split

| Layer | Owned by |
|---|---|
| Bar streaming (backtest + live) | NautilusTrader |
| Order submission + fill simulation | NautilusTrader |
| Order state machine | NautilusTrader |
| Account + position tracking | NautilusTrader |
| Exchange adapter (Bybit live) | NautilusTrader |
| Feature computation | Finding Alpha (inside Strategy) |
| Regime classification | Finding Alpha (inside Strategy) |
| Signal generation | Finding Alpha (inside Strategy) |
| Risk checks + veto | Finding Alpha (inside Strategy) |
| Portfolio sizing | Finding Alpha (inside Strategy) |
| Analytics + logging | Finding Alpha (Analytics Agent) |

## Why Not Custom Simulator

A custom event loop is trivially easy to write (proved in phase1_spike.py).
But it would require us to build and maintain:
- Order state machine
- Fill model (market, limit, partial fill, stop trigger)
- Funding model
- Account/position tracking
- Backtest/live parity discipline (enforced only by us)
- Bybit live adapter from scratch

NautilusTrader gives all of this for free. The cost is learning NT's API,
which the spike showed is manageable.

## Constraints This Imposes

- Strategy code must inherit from `nautilus_trader.trading.strategy.Strategy`
- All domain events (bars, fills) come through NT callbacks
- Our agent pipeline runs *inside* `on_bar()` — not as separate processes
- Instrument precision must match data precision exactly
- For Phase 1-7 (backtest only), NT's BacktestEngine is the runtime
- For Phase 8+ (paper/live), the same strategy code transitions to NT's
  LiveExecutionEngine with the Bybit adapter

## What This Means For Phase 2

Phase 2 builds the canonical contracts as plain Python dataclasses/Pydantic
models. They are NOT NT objects. NT is the transport and execution layer.
Our contracts are the domain language passed between our agents internally.

Example flow in on_bar():
    bar (NT) -> FeatureAgent -> FeatureSnapshot (ours)
             -> RegimeAgent -> RegimeState (ours)
             -> StrategyAgent -> SignalCandidate (ours)
             -> PortfolioAgent -> PortfolioIntent (ours)
             -> RiskAgent -> RiskDecision (ours)
             -> if approved: self.submit_order(NT order)
             -> ExecutionReport (ours, built from NT fill event)
