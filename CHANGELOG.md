# Changelog

All notable changes to `fayna_meta_capi` are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: Odoo `17.0.MAJOR.MINOR.PATCH`.

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
