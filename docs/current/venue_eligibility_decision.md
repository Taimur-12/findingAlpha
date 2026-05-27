# Venue Eligibility Decision

Date: 2026-05-27
Status: PARTIALLY RESOLVED — see action required below

## Jurisdictions

Account holder operates from: Pakistan and Australia

## Venue Assessment

### Bybit — First Technical Execution Target

| Jurisdiction | Status | Notes |
|---|---|---|
| Pakistan | CLEAR | Not on Bybit restricted-country list |
| Australia | VERIFY BEFORE LIVE | Bybit has had ASIC regulatory friction. Must confirm current status for Australian-registered accounts before Phase 10 |

**Decision**: Proceed with Bybit as the build target for all phases. Jurisdiction gate is re-checked at Phase 10 (private API + testnet) before any live order is placed.

If Pakistani account is used for live trading: proceed normally.
If Australian account is used: verify Bybit AU eligibility at Phase 10 before going live.

### Binance — Reference Data Only

- USD-M futures public data: accessible from both jurisdictions
- Not used for live execution in v1

### OKX — Reference Data Only

- Has AU-specific API domain (app.okx.com) — accessible from Australia
- Accessible from Pakistan
- Not used for live execution in v1

### MEXC — Reference Data Only

- Not first live execution venue regardless of jurisdiction
- Public data accessible

## Hard Rule

If the account jurisdiction is not allowed for the exact product at execution time, live trading is blocked. Backtest and paper trading proceed regardless.

## Action Required Before Phase 10

- [ ] Confirm current Bybit status for Australian accounts (check bybit.com/en-AU or contact support)
- [ ] Confirm which account (PK or AU) will be used for live trading
- [ ] Confirm API trading is enabled for that account type
- [ ] Confirm testnet/demo is available for USDT linear perpetuals
