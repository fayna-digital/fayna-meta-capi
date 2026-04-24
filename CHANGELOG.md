# Changelog

All notable changes to `fayna_meta_capi` are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: Odoo `17.0.MAJOR.MINOR.PATCH`.

---

## [17.0.0.1.0] — 2026-04-24

### Added
- Initial scaffold (empty-but-installable).
- Feature flag `fayna_meta_capi.active` (default `False`) per master TZ §2 Strangler Fig.
- Canonical tooling (pre-commit, pyproject, GitHub Actions CI).
- Placeholder tests (install + flag + deps sanity).
- `docs/TZ.md` per-module TZ aligned with CAMPSCOUT_MASTER_TZ.md §16 Phase 4.

### Notes
- Module is **inert** until Phase 4 implementation lands.
