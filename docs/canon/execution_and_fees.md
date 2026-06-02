# Execution Cost & Fee Minimization

**Date:** 2026-06-02
**Companion to:** `apex_quant_architecture_and_stack_2026_06.md` (touches L5, L6, L7).
**Why this exists:** We trade on a thin edge with short-hold, data-driven scalps (minutes, off microstructure features — CVD, order-book imbalance). On a thin edge, fees + spread + slippage are often the entire difference between profit and loss. This is the research and the policy for keeping that cost down.

> **Scope assumption:** "data scalping" here = signal-driven, minutes-hold trades off microstructure features. **Not** sub-minute HFT. If we move to sub-minute, the maker-fill and adverse-selection assumptions below change materially and this doc must be revisited.

---

## 1. The actual numbers (Bybit perps, non-VIP, 2026)

| | Maker | Taker |
|---|---|---|
| Per side | **0.020%** | **0.055%** |
| Round trip (both sides) | **0.040%** | **0.110%** |
| Mixed (maker in / taker out) | — | **0.075%** |

- The single biggest lever is **maker vs taker**: a full taker round-trip (0.11%) costs **~2.75×** a full maker round-trip (0.04%).
- VIP tiers can reach **0.000% maker / 0.030% taker**, but require ~millions in 30-day volume — **irrelevant at our micro size.** Ignore until much larger.
- **Funding** settles every 8h (00:00 / 08:00 / 16:00 UTC). It is a *position-holding* cost, not a per-trade fee.

---

## 2. The levers, ranked for our scale

### Lever 1 — Post-only (maker) entries *(biggest)*
Place entries as `post-only` limit orders → pay 0.020% instead of 0.055%. The catch is the real design problem:
- A maker order **may not fill** (price walks away → missed trade).
- When it *does* fill, you're often **adversely selected** — filled precisely because price came to you, i.e. moved against your intended direction. Realized edge on maker fills is worse than a backtest-on-mid assumes.

**This is the central scalping tradeoff: fee savings vs fill-certainty + adverse selection.** It must be *measured*, not assumed.

**Policy:** maker-or-cancel entry with a short chase window; explicit rule on unfilled orders (skip, re-post, or cross-and-pay-taker based on how stale the signal is).

### Lever 2 — Funding-stamp avoidance *(cheap, high value)*
A scalp that holds minutes and doesn't straddle a funding timestamp pays **zero funding.**
**Policy:** don't open a short-hold position in the minutes before a funding stamp unless the signal is strong enough to eat it.
**Exception:** this rule does NOT apply to the funding-rate *mean-reversion* strategy, which deliberately wants funding exposure — different strategy, different rule.

### Lever 3 — Spread + slippage *(often dominates the explicit fee)*
For scalping, paying the spread / slipping on a market order is frequently a *larger* cost than the 0.055% fee. Maker limits sit inside/at the spread and attack both at once.
**Policy:** model spread and slippage as first-class costs, not a rounding error (see §3).

### Lever 4 — Fewer, better trades *(the structural fix)*
Fee drag scales linearly with trade count. Two structural defenses:
- **Fee-aware entry threshold:** only take a trade whose *expected* move exceeds round-trip cost by a set margin. Bake cost into the signal gate so marginal trades never fire.
- **Meta-labeling (the §3.1 GBDT filter) is, in effect, a fee-reduction tool** — it cuts low-precision trades that pay fees without earning enough.

### Lever 5 — Exchange / instrument choice *(minor now)*
Binance perps are similar (~0.02% maker). Not worth multi-exchange complexity yet; revisit only when volume justifies VIP tiers or a second venue (already deferred to Phase G).

---

## 3. Where this lands in the architecture

| Layer | Change |
|---|---|
| **L5 Validation** | Upgrade the cost model from a single blended bps to **separate maker-fill-rate + adverse-selection + funding** modeling, so scalping backtests aren't optimistic by construction. The existing 0–20 bps sweep stays, but cost is no longer one blended number. |
| **L6 Decision** | Add a **fee-aware entry threshold**: reject trades where `expected_move < round_trip_cost × margin`. |
| **L7 Execution** | Add the **post-only-with-chase** entry policy, the maker/taker decision rule, and funding-stamp avoidance for scalps. |

---

## 4. Open questions

- **Maker-fill rate is unknown until measured.** We can't size the fee-savings-vs-missed-trades tradeoff from theory; it needs live shadow/paper data (quarantine Q1/Q2) on our actual signals.
- **Adverse selection on maker fills** must be quantified before we trust any maker-based backtest result.
- Confirm scope: minutes-hold vs sub-minute. The whole doc assumes minutes-hold.

---

## Sources

- [Bybit — Perpetual Futures Contract Fees Explained](https://www.bybit.com/en/help-center/article/Perpetual-Futures-Contract-Fees-Explained)
- [Bybit — Trading Fee Structure](https://www.bybit.com/en/help-center/article/Trading-Fee-Structure)
- [TradersUnion — Bybit Futures Fees: Maker-Taker Rates & VIP Discounts](https://tradersunion.com/brokers/crypto/view/bybit/futures-fees/)
- [Phemex — Best Crypto Exchanges for Scalping 2026](https://phemex.com/academy/best-crypto-exchange-for-scalping-2026)
- [Bybit vs Binance Perpetual Futures Fees Compared (2026)](https://www.coinperps.com/learn/bybit-vs-binance-perpetual-futures-fees)
