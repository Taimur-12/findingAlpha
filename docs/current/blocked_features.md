# Blocked Features — v1

Date: 2026-05-27
Status: ACCEPTED

These are not allowed in v1 under any circumstances.
Do not build, do not prototype into the live path, do not revisit until Phase 13+.

## Blocked Until After Phase F (Paper Trading)

- Full dashboard / UI
- Mobile app
- Multi-agent LLM debate system
- RL policy
- On-chain whale model
- Social sentiment model
- Multi-exchange live execution
- DCA layer manager
- 5m scalping
- Auto parameter optimizer
- Strategy marketplace
- Market-making bot

## Blocked Until Paper + Micro-Live Gates Pass

- Second symbol (ETHUSDT) — only after BTCUSDT live path is stable
- Second strategy — only after first strategy passes all gates
- Research Agent influencing live orders — shadow mode only until paper evidence proves value

## Never In v1 (No Exceptions)

- DCA / averaging down
- Autonomous LLM trade approval
- RL controlling live risk or sizing
- ML optimizer changing production parameters
- 5m live trading
- Multi-exchange live execution

## Reason

The core question is: can the deterministic engine produce positive expectancy after realistic costs while maintaining correct execution and risk state? Everything on this list distracts from that proof.
