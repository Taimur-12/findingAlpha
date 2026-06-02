# Docs index

Three folders, by purpose:

## `canon/` — source of truth (read these first)
The current APEX plan. If something here conflicts with an older doc, **canon wins.**

| File | What it is |
|---|---|
| `architecture_and_stack.md` | The 8-layer architecture, per-layer inputs/outputs, decided tech stack, and the staged-infrastructure table. The single source of truth for *what we're building*. |
| `build_plan.md` | The phased build plan (Phases A–G), ML doctrine (adopt / defer / refuse), strategy roadmap, budget tiers. |
| `code_vs_plan_audit.md` | What's actually built in code today vs the plan — the honest gap analysis. |
| `execution_and_fees.md` | Fee-minimization research and the execution-cost policy (maker/taker, post-only, funding avoidance). |
| `partner_brief.md` | Plain-language brief of what the system does — for partners/stakeholders. |

## `reference/` — still-valid technical & operational notes
| File | What it is |
|---|---|
| `bybit_order_semantics.md` | How Bybit V5 orders behave (used by the execution layer). |
| `nautilus_vs_custom_decision.md` | Why NautilusTrader for backtesting (L5). |
| `advisory_layer_design.md`, `advisory_final_vision.md` | LLM advisory (L2) design. |
| `dashboard_operations.md`, `dashboard_shareholder_walkthrough.md`, `ui_dashboard_guide.md` | Running and reading the Streamlit dashboard. |
| `blocked_features.md` | Known limitations / intentionally-disabled features. |

## `archive/` — historical, superseded
Old phase reports, the prior QuantFusion blueprint/roadmap, dropped-strategy research, and prior "source of truth" docs. Kept for provenance; **do not treat as current.** `archive/results/` holds old backtest JSON outputs.
