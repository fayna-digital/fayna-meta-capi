# Odoo 17 Fayna Meta Conversions API — scaffold (Phase 4)

![Odoo Version](https://img.shields.io/badge/Odoo-17.0%20Community-purple)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Phase](https://img.shields.io/badge/Phase-4-red)
![License](https://img.shields.io/badge/License-LGPL--3-green.svg)
![Status](https://img.shields.io/badge/Status-Scaffold-orange)

**Developed by [Fayna Digital](https://www.fayna.agency) for CampScout and the broader Fayna Camp vertical stack.**
**Author: Volodymyr Shevchenko**

---

Meta Conversions API (server-side pixel) — purchase/lead events from Odoo.

Phase 4 of the master plan: `CAMPSCOUT_MASTER_TZ.md §16`.

Current state: **scaffold only** — installable but inert. Feature flag
`fayna_meta_capi.active` defaults to `False`. Implementation proceeds in
increments listed in `docs/TZ.md`.

---

## Features (planned)

Extracted from campscout_management.models.meta_capi; sends Purchase/Lead events to Meta.

---

## Architecture

```
fayna_meta_capi/
├── __manifest__.py
├── __init__.py
├── data/ir_config_parameter.xml       # feature flag
├── models/                             # Phase 4 implementation
├── tests/test_scaffold.py              # install + flag + deps sanity
├── docs/TZ.md                          # per-module TZ
├── .github/workflows/ci.yml            # gate-2 CI
├── .pre-commit-config.yaml             # gate-1 pre-commit
├── pyproject.toml
├── LICENSE
├── CHANGELOG.md
└── README.md
```

---

## Installation

```bash
cd /opt/campscout/custom-addons
sudo -u \#1000 git clone https://github.com/VladSh77/fayna-meta-capi.git fayna_meta_capi
docker exec campscout_web odoo -c /etc/odoo/odoo.conf -d campscout \
    -i fayna_meta_capi --stop-after-init --no-http
docker restart campscout_web
```

Module installs as **inert** (feature flag `False`). No behaviour change until flip.

---

## License

LGPL-3 — see [LICENSE](LICENSE).

---

*Developed by [Fayna Digital](https://www.fayna.agency) · Volodymyr Shevchenko*
