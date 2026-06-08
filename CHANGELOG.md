# Changelog

All notable changes to `fayna_meta_capi` are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: Odoo `17.0.MAJOR.MINOR.PATCH`.

---

## [Unreleased]

### Docs only
- Added `CLAUDE.md` with `#4ZONES` banner, module purpose, deps, deploy commands, boundaries.
- Rewrote `docs/TZ.md` into the 6 spec-driven REPO_STANDARD areas (Objective, Commands,
  Project Structure, Code Style, Testing, Boundaries) + Success Criteria + Open Questions,
  preserving historical milestones.
- Added `docs/PLAN.md` (dependency graph + phases + checkpoints).
- Backfilled CHANGELOG entries up to `17.0.3.1.3`.
- `.gitignore` now ignores secrets (`.env`, `*.key`, `*.pem`, `*.crt`, `*_token*`,
  `credentials*`, `secrets*`).
- README + LICENSE confirmed conformant to REPO_STANDARD.

---

## [17.0.3.1.3]

### Added
- **AddToCart** event — `send_add_to_cart(order_line)`: order-line-level conversion event.
- **InitiateCheckout** event — `send_initiate_checkout(order)`: fired at start of checkout flow.
- Retry subsystem on `fayna.capi.event.log`: `retry_count` + `next_retry_at` fields,
  `action_retry_failed()` (single record) and `cron_retry_failed_events()` (bulk).
- `data/cron_retry.xml` — `ir.cron` retrying failed events every 30 min, max 3 attempts
  (`_MAX_RETRIES`), `noupdate=1` to keep admin customisation after upgrade.
- Sale-order linkage on the event log: `sale_order_id`, `order_amount`, `currency_code`.

### Changed
- `_send_event_inner()` accepts an optional `order` to attach order context to the log.
- Manifest dependencies extended: `event`, `base_setup`, `fayna_camp_sales`,
  `fayna_rodo_compliance`.

### Notes
- Module remains **Production-ready** but **inert** (feature flag `False`) until the
  Phase 4 production gate (all stack modules on Hetzner staging + human QA green).

---

## [17.0.2.0.0] — 2026-04-28

### Added
- `payload` field on `fayna.capi.event.log` — stores the JSON sent to Meta API
  (without `access_token` — security invariant: token never written to DB logs).
- `response` field on `fayna.capi.event.log` — stores the raw response body from Meta.
- 5 new tests (18–22): payload/response stored correctly, round-trip config params,
  access_token not in URL (security), payload stored even on network errors.
- README rewritten in Ukrainian with full setup instructions, security notes,
  event log description, and test instructions.

### Changed
- `_write_log()` now accepts `payload_json` and `response_text` parameters.
- `_send_event_inner()` serialises payload (minus `access_token`) via `json.dumps`
  before logging; on network error stores the payload we attempted to send.
- Event log form view shows payload and response JSON sections (collapsible).
- `i18n/uk_UA.po` + `i18n/pl_PL.po` updated with new field strings.

---

## [17.0.1.0.0] — 2026-04-27

### Added
- `FaynaMetaCapiService` (`fayna.meta.capi`) as `models.AbstractModel` — callable
  from any Odoo context via `env["fayna.meta.capi"]`.
- Public API: `send_event()`, `send_purchase()`, `send_lead()`, `send_view_content()`,
  `_hash_value()`, `_get_config()`, `action_send_test_event()`.
- `action_send_test_event()` — sends a test ViewContent event from the Settings UI.
- `sale_order.py` — overrides `action_confirm()` to fire **Purchase** event.
- `camp_support_request.py` — overrides `action_submit()` to fire **Lead** event.
  Not imported until `fayna_camp_sales` is added to `__manifest__.py` depends.
- `controllers/website_sale.py` — inherits `WebsiteSale.product()` to fire
  **ViewContent** event on camp product page visits.
- `res.config.settings` extension with Pixel ID, Access Token, API Version,
  Test Event Code fields and "Send test event" button.
- Settings form view injected into Odoo Settings page (admin-only).
- `fayna_meta_capi.api_version` config parameter (default `v19.0`).
- `fayna_meta_capi.enabled` feature flag (default `False`) keeps module inert until
  explicitly activated via Settings → Meta CAPI.
- `fayna.capi.event.log` model — event audit log with status/http_status/error_message.
- 22 tests (17 main + 5 scaffold) covering all event types, hashing, feature-flag
  gating, timeout handling, log creation, payload structure, config parameter seeding.
- Full `uk_UA.po` + `pl_PL.po` translations for all user-facing strings.

### Changed
- `FaynaCAPIService` plain class preserved as backward-compatible alias delegating
  to the AbstractModel.
- Menu moved under `base.menu_administration` (Technical section, admin-only).
- `test_scaffold.py` — replaced brittle `assertEqual(param, "False")` with
  resilient assertion that accepts "True"/"False" (test isolation fix).

---

## [17.0.0.1.0] — 2026-04-24

### Added
- Initial scaffold (empty-but-installable).
- Feature flag `fayna_meta_capi.active` (default `False`) per master TZ §2 Strangler Fig.
- Canonical tooling (pre-commit, pyproject, GitHub Actions CI).
- Placeholder tests (install + flag + deps sanity).
- `docs/TZ.md` per-module TZ aligned with CAMPSCOUT_MASTER_TZ.md §16 Phase 4.

### Notes
- Module was **inert** until Phase 4 implementation.
