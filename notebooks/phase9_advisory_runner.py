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
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

import anthropic
from dotenv import load_dotenv

from finding_alpha.contracts.signals import ResearchState
from finding_alpha.research.advisory import save_advisory

MODEL_ID = "claude-sonnet-4-6"
PROMPT_VERSION = "v1.0"
TRADE_LOOKBACK_DAYS = 14
ADVISORY_VALIDITY_HOURS = 24

ADVISORY_PATH = _ROOT / "advisory.json"
LOG_PATH = _ROOT / "paper" / "advisory_log.jsonl"
TRADE_FILES = [
    _ROOT / "paper" / "trades.jsonl",
    _ROOT / "paper" / "composite" / "trades.jsonl",
]


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

Use recent paper trade performance as your main input. If recent trades have
been losing, reduce sizing. If recent trades have been winning, default to
normal sizing. If you see no signal to act, return normal/1.0 — the LLM is
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


def build_user_message(now: datetime) -> str:
    trades = load_recent_trades(now)
    prev = load_previous_advisory(ADVISORY_PATH)

    lines = [
        f"Current UTC time: {now.isoformat()}",
        f"Advisory needed for the next {ADVISORY_VALIDITY_HOURS} hours.",
        "",
    ]

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
