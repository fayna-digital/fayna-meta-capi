# fayna_meta_capi — Per-module TZ

Scope: master TZ §16 Phase 4. Owner: Fayna Digital (Volodymyr Shevchenko).

## Mission

Meta Conversions API (server-side pixel) — purchase/lead events from Odoo.

Extracted from campscout_management.models.meta_capi; sends Purchase/Lead events to Meta.

## Non-goals

- Anything outside Phase 4 scope per master TZ.
- Production deployment before all 26 modules are on Hetzner staging with
  human QA green (see `feedback_prod_deploy_gate.md` — ЗАКОН).

## Incremental milestones

### M.0 Scaffold ✅ (2026-04-24)

Empty module, installable, feature flag seeded `False`, CI green.

### M.1 — TBD

First concrete behaviour. Details land when Phase 4 starts active development.

## Quality (per master TZ §4.6 ЗАКОН)

- pre-commit gates green on every commit (ruff + ruff-format + OCA + bandit + gitleaks + base hooks)
- tests ≥ 70% coverage on critical paths
- QUALITY_AUDIT_*.md entry before each phase gate promotion

## Rollback

- Flip `fayna_meta_capi.active` → `False`.
- If still misbehaving, uninstall the module; core Odoo tables remain untouched.

## Reference

- Master TZ `CAMPSCOUT_MASTER_TZ.md` §16 Phase 4
- Sister modules per deps
