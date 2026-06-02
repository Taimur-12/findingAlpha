"""
Phase 9 advisory runner.

Generates the daily LLM advisory by:
  1. Reading recent closed trades from both paper strategies.
  2. Reading the previous advisory (for continuity).
  3. Asking Claude to produce a bounded JSON advisory for the next 24h.
  4. Validating the response into a ResearchState (Pydantic schema check).
  5. Writing advisory.json (consumed by the runtime) + advisory_log.jsonl (audit).

Usage:
    python notebooks/phase9_advisory_runner.py --once
    python notebooks/phase9_advisory_runner.py --dry-run

Requires ANTHROPIC_API_KEY in environment or .env at project root.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

import anthropic
from dotenv import load_dotenv

from finding_alpha.contracts.signals import ResearchState
from finding_alpha.features.snapshot import build_feature_df, build_snapshot
from finding_alpha.live.feed import (
    fetch_recent_candles, fetch_recent_funding, fetch_recent_oi,
)
from finding_alpha.regime.classifier import classify_regime
from finding_alpha.research.advisory import save_advisory

MODEL_ID = "claude-sonnet-4-6"
PROMPT_VERSION = "v1.1"
TRADE_LOOKBACK_DAYS = 14
ADVISORY_VALIDITY_HOURS = 24
MACRO_LOOKAHEAD_DAYS = 7
MARKET_LOOKBACK_BARS = 300

ADVISORY_PATH = _ROOT / "advisory.json"
LOG_PATH = _ROOT / "paper" / "advisory_log.jsonl"
MACRO_CALENDAR_PATH = _ROOT / "data" / "macro_calendar.json"
TRADE_FILES = [
    _ROOT / "paper" / "trades.jsonl",
    _ROOT / "paper" / "composite" / "trades.jsonl",
]
MARKET_SYMBOL = "BTCUSDT"
MARKET_TIMEFRAME = "1h"


SYSTEM_PROMPT = """You are a risk advisor for a deterministic crypto trading bot.

Your job: produce a JSON advisory that gates whether the bot may take entries
during the next 24 hours. You have no other authority.

You CANNOT:
- Predict prices or direction
- Suggest entries, exits, stops, or targets
- Change strategy parameters
- Recommend confidence_multiplier above 1.0

You CAN:
- Reduce sizing (confidence_multiplier in [0.0, 1.0])
- Block new entries (trade_policy = "block_new_entries")
- Restrict to one strategy (allowed_strategies)

The bot trades two short-only strategies on BTCUSDT 1h perpetuals on Bybit:
- prev_day_breakdown_v1: shorts when close < prev-day low with vol spike
- short_composite_v1: same + EMA20 intra-bar rejection in confirmed downtrend

Inputs you receive each call:
- Recent paper trade outcomes (last 14 days)
- Current BTC market context: price, 24h change, funding rate, ATR percentile,
  regime classification, volume z-score
- Upcoming US macro events in the next 7 days (FOMC, CPI, NFP, PCE)
- The previous advisory (for continuity)

Guidance for reasoning:
- High ATR percentile (>80) or extreme funding (|z| > 2) suggests a tighter
  regime — consider reducing sizing.
- A macro event in the next 24h (especially FOMC, CPI) often warrants reduced
  sizing or temporary hard block around the release window.
- Recent paper losses in similar conditions argue for caution; recent wins
  argue for normal sizing.
- When you have no clear signal to act, default to normal/1.0. The LLM is
  upside-only; "no opinion" is a valid response.

Output ONLY a single valid JSON object matching this exact schema:

{
  "as_of": "2026-05-30T12:00:00+00:00",
  "expires_at": "2026-05-31T12:00:00+00:00",
  "assets": ["BTC"],
  "event_type": "none",
  "severity": 0.0,
  "directional_bias": 0.0,
  "confidence_multiplier": 1.0,
  "trade_policy": "normal",
  "reason_codes": [],
  "sources": [],
  "one_sentence_summary": "Short one-line explanation of advisory.",
  "allowed_strategies": []
}

Valid event_type values: none, macro, geopolitical, regulatory, exchange_risk,
stablecoin_risk, protocol_risk, market_structure, unknown.

Valid trade_policy values: normal, raise_thresholds, reduce_size,
block_new_entries, close_risk_positions.

Empty allowed_strategies = both strategies allowed.
severity in [0, 1]. directional_bias in [-1, 1]. confidence_multiplier in [0, 1].

Output ONLY the JSON. No prose, no markdown fences."""


def load_recent_trades(now: datetime, lookback_days: int = TRADE_LOOKBACK_DAYS) -> list[dict]:
    cutoff = now - timedelta(days=lookback_days)
    trades: list[dict] = []
    for path in TRADE_FILES:
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    t = json.loads(line)
                    exit_ts = datetime.fromisoformat(t["exit_ts"])
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
                if exit_ts >= cutoff:
                    trades.append({
                        "strategy": t.get("strategy_id", "?"),
                        "side": t.get("side", "?"),
                        "exit_ts": t["exit_ts"],
                        "r_multiple": float(t.get("r_multiple", 0)),
                        "exit_reason": t.get("exit_reason", "?"),
                    })
    trades.sort(key=lambda x: x["exit_ts"])
    return trades


def load_previous_advisory(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def fetch_market_context(symbol: str = MARKET_SYMBOL, timeframe: str = MARKET_TIMEFRAME) -> dict:
    """Return a snapshot of current market state: price, 24h change, funding,
    ATR percentile, regime, volume z-score. Returns {} on any fetch failure
    so the advisory can still run with degraded inputs."""
    try:
        candles = fetch_recent_candles(symbol, timeframe, n=MARKET_LOOKBACK_BARS + 5)
        if candles.empty or len(candles) < 50:
            return {"error": "insufficient_candles"}

        funding_df = fetch_recent_funding(symbol, days=14)
        oi_df = fetch_recent_oi(symbol, timeframe, days=14)

        feature_df = build_feature_df(candles, funding_df, oi_df)
        snapshot = build_snapshot(feature_df, "bybit", symbol, timeframe)
        regime = classify_regime(snapshot)

        last_row = feature_df.iloc[-1]
        close = Decimal(str(last_row["close"]))
        bar_24_ago = feature_df.iloc[-24] if len(feature_df) >= 25 else feature_df.iloc[0]
        close_24h_ago = Decimal(str(bar_24_ago["close"]))
        change_24h_pct = ((close - close_24h_ago) / close_24h_ago * 100).quantize(Decimal("0.01"))

        return {
            "price": str(close),
            "change_24h_pct": str(change_24h_pct),
            "funding_rate": str(snapshot.funding_rate) if snapshot.funding_rate is not None else None,
            "funding_z": str(snapshot.funding_z_score) if snapshot.funding_z_score is not None else None,
            "atr_percentile": (
                str(snapshot.atr_percentile) if snapshot.atr_percentile is not None else None
            ),
            "adx_14": str(snapshot.adx_14) if snapshot.adx_14 is not None else None,
            "rsi_14": str(snapshot.rsi_14) if snapshot.rsi_14 is not None else None,
            "volume_z": str(snapshot.volume_z_score) if snapshot.volume_z_score is not None else None,
            "oi_z": str(snapshot.oi_z_score) if snapshot.oi_z_score is not None else None,
            "regime": regime.regime,
            "regime_confidence": str(regime.confidence),
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def load_upcoming_macro_events(
    now: datetime,
    lookahead_days: int = MACRO_LOOKAHEAD_DAYS,
    path: Path = MACRO_CALENDAR_PATH,
) -> list[dict]:
    """Return macro events whose date falls within [now, now + lookahead_days]."""
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    events = data.get("events", [])
    cutoff = (now + timedelta(days=lookahead_days)).date()
    today = now.date()

    upcoming: list[dict] = []
    for ev in events:
        try:
            ev_date = datetime.fromisoformat(ev["date"]).date()
        except (KeyError, ValueError):
            continue
        if today <= ev_date <= cutoff:
            upcoming.append(ev)
    return upcoming


def build_user_message(now: datetime) -> str:
    trades = load_recent_trades(now)
    prev = load_previous_advisory(ADVISORY_PATH)
    market = fetch_market_context()
    macro_events = load_upcoming_macro_events(now)

    lines = [
        f"Current UTC time: {now.isoformat()}",
        f"Advisory needed for the next {ADVISORY_VALIDITY_HOURS} hours.",
        "",
    ]

    lines.append("## Current market context (BTCUSDT 1h)")
    if "error" in market:
        lines.append(f"(market context unavailable: {market['error']})")
    else:
        lines.append(f"price: ${market.get('price')} | 24h change: {market.get('change_24h_pct')}%")
        lines.append(
            f"regime: {market.get('regime')} "
            f"(confidence {market.get('regime_confidence')})"
        )
        lines.append(
            f"ADX(14): {market.get('adx_14')} | RSI(14): {market.get('rsi_14')} | "
            f"ATR %ile: {market.get('atr_percentile')}"
        )
        lines.append(
            f"funding rate: {market.get('funding_rate')} (z={market.get('funding_z')}) | "
            f"volume z: {market.get('volume_z')} | OI z: {market.get('oi_z')}"
        )
    lines.append("")

    lines.append(f"## Upcoming US macro events (next {MACRO_LOOKAHEAD_DAYS}d)")
    if macro_events:
        for ev in macro_events:
            lines.append(
                f"- {ev.get('date')} {ev.get('time_utc')} UTC {ev.get('type')}: {ev.get('detail')}"
            )
    else:
        lines.append("None scheduled.")
    lines.append("")

    if trades:
        wins = sum(1 for t in trades if t["r_multiple"] > 0)
        avg_r = sum(t["r_multiple"] for t in trades) / len(trades)
        lines.append(f"## Recent paper trades (last {TRADE_LOOKBACK_DAYS} days)")
        lines.append(f"Total: {len(trades)} | Wins: {wins} | Avg R: {avg_r:+.3f}")
        lines.append("")
        for t in trades[-10:]:
            lines.append(
                f"- {t['exit_ts'][:16]} {t['strategy']} {t['side']} "
                f"→ {t['r_multiple']:+.2f}R ({t['exit_reason']})"
            )
    else:
        lines.append("## Recent paper trades")
        lines.append("None in the lookback window.")
    lines.append("")

    if prev:
        lines.append("## Previous advisory")
        lines.append(
            f"trade_policy: {prev.get('trade_policy', '?')} | "
            f"confidence_multiplier: {prev.get('confidence_multiplier', '?')} | "
            f"allowed_strategies: {prev.get('allowed_strategies', [])}"
        )
        lines.append(f"summary: {prev.get('one_sentence_summary', '')}")
        lines.append("")

    lines.append("## Task")
    lines.append(
        "Produce a JSON advisory for the next 24h based on the data above. "
        "Output ONLY a single valid JSON object."
    )
    return "\n".join(lines)


def call_claude(user_message: str) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL_ID,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def parse_response(text: str) -> ResearchState:
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.endswith("```"):
            s = s.rsplit("```", 1)[0]
    raw = json.loads(s.strip())

    for key in ("as_of", "expires_at"):
        v = raw.get(key, "")
        if isinstance(v, str) and v and "+" not in v and "Z" not in v.upper():
            raw[key] = v + "+00:00"

    raw["model_id"] = MODEL_ID
    raw["prompt_version"] = PROMPT_VERSION

    return ResearchState.model_validate(raw)


def append_log(rs: ResearchState, log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(rs.model_dump_json() + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 9 advisory runner")
    parser.add_argument("--once", action="store_true", help="Generate one advisory and exit")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt without calling Claude")
    args = parser.parse_args()

    load_dotenv()
    now = datetime.now(timezone.utc)
    user_message = build_user_message(now)

    if args.dry_run:
        print("=== SYSTEM PROMPT ===")
        print(SYSTEM_PROMPT)
        print("\n=== USER MESSAGE ===")
        print(user_message)
        print("\n=== (dry run — no API call made) ===")
        return

    print(f"[advisory] calling {MODEL_ID} at {now.isoformat()}")
    try:
        text = call_claude(user_message)
    except Exception as exc:
        print(f"[advisory] ERROR calling Claude: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        rs = parse_response(text)
    except Exception as exc:
        print(f"[advisory] ERROR parsing response: {exc}", file=sys.stderr)
        print(f"Raw text:\n{text}", file=sys.stderr)
        sys.exit(1)

    save_advisory(rs, ADVISORY_PATH)
    append_log(rs, LOG_PATH)

    print(f"[advisory] wrote {ADVISORY_PATH}")
    print(f"  trade_policy:          {rs.trade_policy}")
    print(f"  confidence_multiplier: {rs.confidence_multiplier}")
    print(f"  allowed_strategies:    {rs.allowed_strategies}")
    print(f"  expires:               {rs.expires_at.isoformat()}")
    print(f"  summary:               {rs.one_sentence_summary}")


if __name__ == "__main__":
    main()
